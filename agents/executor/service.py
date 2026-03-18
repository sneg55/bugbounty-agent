# agents/executor/service.py
"""Executor Service: listens for BugRevealed, runs PoC, produces state diff, triggers arbitration."""
import json
import os
import time

from web3 import Web3

from common.config import RPC_URL, load_deployments
from common.contracts import get_web3, get_all_contracts
from common.crypto import decrypt
from common.ipfs import download_json, upload_json
from executor.fork_runner import run_poc_in_fork
from executor.state_diff import build_state_impact_json


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
    # For demo: construct balance/storage changes from the report
    # In production: parse Foundry trace output
    state_impact = build_state_impact_json(
        bug_id=bug_id,
        bounty_id=bounty_id,
        hunter_agent_id=hunter_agent_id,
        claimed_severity=claimed_severity,
        target_contract=report.get("contract", "0x0"),
        fork_block=current_block,
        chain_id=84532,
        exploit_succeeded=fork_result["success"],
        tx_reverted=not fork_result["success"],
        gas_used=fork_result["gas_used"],
        out_of_scope=False,
        balance_changes=[],  # Would be populated from trace
        storage_changes=[],
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
    return state_impact


def main():
    w3 = get_web3()
    contracts = get_all_contracts(w3)
    deployments = load_deployments()

    print("Executor watching for BugRevealed events... (Ctrl+C to stop)")
    processed = set()

    while True:
        # Poll for revealed submissions
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
        time.sleep(5)


if __name__ == "__main__":
    main()
