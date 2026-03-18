# agents/executor/service.py
"""Executor Service: listens for BugRevealed, runs PoC, produces state diff, triggers arbitration."""
import json
import os
import time

from web3 import Web3

from common.config import CHAIN_ID, RPC_URL, load_deployments
from common.contracts import get_web3, get_all_contracts
from common.crypto import decrypt, encrypt
from common.ipfs import download_json, upload_json
from common.block_cursor import BlockCursor
from executor.fork_runner import run_poc_in_fork
from executor.patch_guidance import generate_patch_guidance
from executor.state_diff import build_state_impact_json, parse_forge_trace

# Minimum severity for patch guidance (HIGH = 3)
PATCH_GUIDANCE_MIN_SEVERITY = 3


def process_revealed_bug(w3: Web3, contracts: dict, bug_id: int, deployments: dict):
    """Full executor pipeline for a revealed bug."""
    private_key = os.getenv("EXECUTOR_PRIVATE_KEY")
    ecies_private_key = os.getenv("EXECUTOR_ECIES_PRIVATE_KEY")
    account = w3.eth.account.from_key(private_key)
    executor_agent_id = deployments["agentIds"]["executor"]

    # 1. Fetch submission details
    sub = contracts["bugSubmission"].functions.getSubmission(bug_id).call()
    encrypted_cid = sub[4]  # encryptedCID
    bounty_id = sub[0]
    hunter_agent_id = sub[1]
    claimed_severity = sub[2]

    print(f"Processing bug #{bug_id} (bounty #{bounty_id}, severity claim: {claimed_severity})")

    # 2. Download and decrypt payload
    encrypted_data = download_json(encrypted_cid.replace("ipfs://", ""))
    encrypted_bytes = bytes.fromhex(encrypted_data["encrypted"])
    decrypted = decrypt(ecies_private_key.encode(), encrypted_bytes)
    payload = json.loads(decrypted)
    poc_source = payload["poc"]
    report = payload["report"]

    print(f"  Decrypted payload. Running PoC...")

    # 3. Run PoC in fork
    current_block = w3.eth.block_number
    fork_result = run_poc_in_fork(poc_source, fork_block=current_block)

    print(f"  PoC result: {'PASS' if fork_result['success'] else 'FAIL'}")

    # 4. Build State Impact JSON
    # Parse balance/storage changes from the fork runner's trace output
    trace_output = fork_result.get("stdout", "") + fork_result.get("stderr", "")
    balance_changes, storage_changes = parse_forge_trace(trace_output)

    state_impact = build_state_impact_json(
        bug_id=bug_id,
        bounty_id=bounty_id,
        hunter_agent_id=hunter_agent_id,
        claimed_severity=claimed_severity,
        target_contract=report.get("contract", "0x0"),
        fork_block=current_block,
        chain_id=CHAIN_ID,
        exploit_succeeded=fork_result["success"],
        tx_reverted=not fork_result["success"],
        gas_used=fork_result["gas_used"],
        out_of_scope=False,
        balance_changes=balance_changes,
        storage_changes=storage_changes,
        executor_agent_id=executor_agent_id,
    )

    # 5. Upload state impact to IPFS
    state_impact_cid = upload_json(state_impact)
    req_hash = bytes.fromhex(state_impact["validationRequestHash"][2:])

    print(f"  State impact uploaded: {state_impact_cid}")

    # 6. Submit to ValidationRegistry
    nonce = w3.eth.get_transaction_count(account.address)
    tx = contracts["validationRegistry"].functions.submitValidation(
        executor_agent_id, req_hash, state_impact_cid
    ).build_transaction({"from": account.address, "nonce": nonce, "gas": 200_000})
    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    w3.eth.wait_for_transaction_receipt(tx_hash)

    # 7. Register state impact on ArbiterContract
    nonce += 1
    tx = contracts["arbiterContract"].functions.registerStateImpact(
        bug_id, req_hash, state_impact_cid
    ).build_transaction({"from": account.address, "nonce": nonce, "gas": 500_000})
    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    w3.eth.wait_for_transaction_receipt(tx_hash)

    print(f"  State impact registered. Arbiters can now vote.")

    # 8. Wait for SubmissionResolved event; generate patch guidance if severity >= HIGH
    print(f"  Waiting for arbitration result (bug #{bug_id})...")
    resolved = _poll_submission_resolved(w3, contracts, bug_id)
    if resolved is None:
        print(f"  Arbitration timed out for bug #{bug_id}; skipping patch guidance.")
    else:
        final_severity = resolved.get("severity", 0)
        is_valid = resolved.get("valid", False)
        print(f"  Resolved: valid={is_valid}, severity={final_severity}")
        if is_valid and final_severity >= PATCH_GUIDANCE_MIN_SEVERITY:
            target_source = report.get("targetSource", "")
            _handle_patch_guidance(
                w3=w3,
                contracts=contracts,
                bug_id=bug_id,
                deployments=deployments,
                poc_source=poc_source,
                target_source=target_source,
                state_impact=state_impact,
                account=account,
            )

    return state_impact


def _fetch_protocol_ecies_pubkey(contracts: dict, deployments: dict) -> str:
    """Fetch Protocol Agent's ECIES public key from IdentityRegistry metadata."""
    protocol_agent_id = deployments["agentIds"]["protocol"]
    pubkey = contracts["identityRegistry"].functions.getMetadata(
        protocol_agent_id, "eciesPubKey"
    ).call()
    return pubkey


def _handle_patch_guidance(
    w3: Web3,
    contracts: dict,
    bug_id: int,
    deployments: dict,
    poc_source: str,
    target_source: str,
    state_impact: dict,
    account,
):
    """Generate patch guidance, encrypt it for Protocol Agent, and register on-chain."""
    print(f"  Generating patch guidance for bug #{bug_id}...")

    # 1. Generate patch guidance via private inference
    guidance = generate_patch_guidance(poc_source, target_source, state_impact)

    # 2. Fetch Protocol Agent's ECIES public key from IdentityRegistry
    protocol_pubkey = _fetch_protocol_ecies_pubkey(contracts, deployments)

    # 3. Encrypt guidance with Protocol Agent's public key
    guidance_bytes = json.dumps(guidance).encode()
    encrypted_bytes = encrypt(protocol_pubkey.encode(), guidance_bytes)
    encrypted_data = {"encrypted": encrypted_bytes.hex()}

    # 4. Upload encrypted guidance to IPFS
    encrypted_cid = upload_json(encrypted_data)
    print(f"  Encrypted patch guidance uploaded: {encrypted_cid}")

    # 5. Register on ArbiterContract
    nonce = w3.eth.get_transaction_count(account.address)
    tx = contracts["arbiterContract"].functions.registerPatchGuidance(
        bug_id, encrypted_cid
    ).build_transaction({"from": account.address, "nonce": nonce, "gas": 200_000})
    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    w3.eth.wait_for_transaction_receipt(tx_hash)

    print(f"  Patch guidance registered on-chain for bug #{bug_id}.")


def _poll_submission_resolved(w3: Web3, contracts: dict, bug_id: int, poll_interval: int = 5, timeout: int = 300) -> dict | None:
    """Poll for SubmissionResolved event for a given bug_id. Returns event args or None on timeout."""
    deadline = time.time() + timeout
    last_block = w3.eth.block_number

    while time.time() < deadline:
        current_block = w3.eth.block_number
        if current_block > last_block:
            events = contracts["arbiterContract"].events.SubmissionResolved.get_logs(
                fromBlock=last_block + 1,
                toBlock=current_block,
            )
            for event in events:
                if event["args"]["bugId"] == bug_id:
                    return event["args"]
            last_block = current_block
        time.sleep(poll_interval)

    return None


def main():
    w3 = get_web3()
    contracts = get_all_contracts(w3)
    deployments = load_deployments()

    print("Executor watching for BugRevealed events... (Ctrl+C to stop)")
    cursor = BlockCursor("executor")
    processed = set()

    while True:
        latest = w3.eth.block_number
        last = cursor.get_last_block()
        if latest > last:
            # Poll for revealed submissions only when new blocks exist
            bug_count = contracts["bugSubmission"].functions.getSubmissionCount().call()
            for i in range(1, bug_count + 1):
                if i in processed:
                    continue
                sub = contracts["bugSubmission"].functions.getSubmission(i).call()
                status = sub[6]  # status enum
                if status == 1:  # Revealed
                    processed.add(i)
                    try:
                        process_revealed_bug(w3, contracts, i, deployments)
                    except Exception as e:
                        print(f"  Error processing bug #{i}: {e}")
            cursor.set_last_block(latest)
        time.sleep(5)


if __name__ == "__main__":
    main()
