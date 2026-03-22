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

_VERIFICATION_CACHE_PATH = ".verification_cache.json"


def load_verification_cache() -> dict:
    """Read the verification cache from disk. Returns an empty dict if the file does not exist."""
    if not os.path.exists(_VERIFICATION_CACHE_PATH):
        return {}
    with open(_VERIFICATION_CACHE_PATH, "r") as f:
        return json.load(f)


def save_verification_cache(cache: dict) -> None:
    """Write the verification cache to disk."""
    with open(_VERIFICATION_CACHE_PATH, "w") as f:
        json.dump(cache, f, indent=2)


def verify_bug(w3: Web3, contracts: dict, bug_id: int, deployments: dict) -> dict:
    """Steps 1-5 of the executor pipeline: decrypt, run PoC, build state diff, upload IPFS.

    Returns a verification dict and persists it to the verification cache.
    """
    ecies_private_key = os.getenv("EXECUTOR_ECIES_PRIVATE_KEY")
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

    verification = {
        "bug_id": bug_id,
        "exploit_succeeded": fork_result["success"],
        "state_impact_cid": state_impact_cid,
        "req_hash": req_hash,
        "state_impact": state_impact,
        "poc_source": poc_source,
        "report": report,
    }

    # Persist to cache (req_hash hex-encoded for JSON serialisation)
    cache = load_verification_cache()
    cache[str(bug_id)] = {**verification, "req_hash": req_hash.hex()}
    save_verification_cache(cache)

    return verification


def register_on_chain(
    w3: Web3,
    contracts: dict,
    bug_id: int,
    verification: dict | None,
    deployments: dict,
) -> dict:
    """Steps 6-8 of the executor pipeline: ValidationRegistry + ArbiterContract + patch guidance.

    If *verification* is None the entry is loaded from the verification cache.
    Returns the state_impact dict.
    """
    if verification is None:
        cache = load_verification_cache()
        entry = cache.get(str(bug_id))
        if entry is None:
            raise ValueError(f"No cached verification found for bug #{bug_id}")
        # Restore req_hash from hex string
        verification = {**entry, "req_hash": bytes.fromhex(entry["req_hash"])}

    private_key = os.getenv("EXECUTOR_PRIVATE_KEY")
    account = w3.eth.account.from_key(private_key)
    executor_agent_id = deployments["agentIds"]["executor"]

    state_impact_cid = verification["state_impact_cid"]
    req_hash = verification["req_hash"]
    state_impact = verification["state_impact"]
    poc_source = verification["poc_source"]
    report = verification["report"]

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
        final_severity = resolved.get("finalSeverity", 0)
        is_valid = resolved.get("isValid", False)
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


def process_revealed_bug(w3: Web3, contracts: dict, bug_id: int, deployments: dict) -> dict:
    """Full executor pipeline for a revealed bug (backward-compatible wrapper).

    Calls verify_bug() then register_on_chain() and returns the state_impact dict.
    """
    verification = verify_bug(w3, contracts, bug_id, deployments)
    return register_on_chain(w3, contracts, bug_id, verification, deployments)


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

    print("Executor watching for BugRevealed + SubmissionDisputed events... (Ctrl+C to stop)")
    cursor = BlockCursor("executor")
    verified = set()   # bug IDs that have been verified (PoC run)
    registered = set() # bug IDs that have been registered on-chain

    while True:
        latest = w3.eth.block_number
        last = cursor.get_last_block()
        if latest > last:
            # 1. Verify ALL newly revealed submissions (PoC + state diff, no on-chain registration)
            revealed_events = contracts["bugSubmission"].events.BugRevealed.get_logs(
                fromBlock=last + 1, toBlock=latest
            )
            for event in revealed_events:
                bug_id = event["args"]["bugId"]
                if bug_id not in verified:
                    verified.add(bug_id)
                    try:
                        verify_bug(w3, contracts, bug_id, deployments)
                    except Exception as e:
                        print(f"  Error verifying bug #{bug_id}: {e}")

            # 2. Register on-chain for newly disputed submissions (using cached verification)
            disputed_events = contracts["bugSubmission"].events.SubmissionDisputed.get_logs(
                fromBlock=last + 1, toBlock=latest
            )
            for event in disputed_events:
                bug_id = event["args"]["bugId"]
                if bug_id not in registered:
                    try:
                        register_on_chain(w3, contracts, bug_id, None, deployments)
                        registered.add(bug_id)
                    except Exception as e:
                        print(f"  Error registering bug #{bug_id}: {e} (will retry next cycle)")

            # 3. Log accepted submissions
            accepted_events = contracts["bugSubmission"].events.SubmissionAccepted.get_logs(
                fromBlock=last + 1, toBlock=latest
            )
            for event in accepted_events:
                bug_id = event["args"]["bugId"]
                registered.add(bug_id)
                print(f"  Bug #{bug_id} accepted by protocol — skipping on-chain registration")

            cursor.set_last_block(latest)
        time.sleep(5)


if __name__ == "__main__":
    main()
