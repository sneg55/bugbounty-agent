"""Protocol Agent: creates bounties, watches for resolution and patch guidance events."""
import argparse
import json
import os
import time

from web3 import Web3

from common.block_cursor import BlockCursor
from common.config import RPC_URL, load_deployments
from common.contracts import get_web3, get_all_contracts
from common.crypto import decrypt
from common.ipfs import download_json
from protocol.risk_model import get_default_tiers, get_default_funding
from protocol.triage import triage_submission, SEVERITY_LABELS


def create_bounty(
    w3: Web3,
    contracts: dict,
    agent_id: int,
    name: str,
    scope_uri: str,
    deadline_seconds: int = 86400,
):
    """Create a bounty on-chain."""
    private_key = os.getenv("PROTOCOL_AGENT_PRIVATE_KEY")
    account = w3.eth.account.from_key(private_key)
    tiers = get_default_tiers()
    funding = get_default_funding()

    # Approve USDC
    usdc = contracts["mockUSDC"]
    bounty_registry = contracts["bountyRegistry"]

    nonce = w3.eth.get_transaction_count(account.address)

    approve_tx = usdc.functions.approve(
        bounty_registry.address, funding
    ).build_transaction({
        "from": account.address,
        "nonce": nonce,
        "gas": 100_000,
    })
    signed = account.sign_transaction(approve_tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    w3.eth.wait_for_transaction_receipt(tx_hash)

    # Create bounty
    nonce += 1
    deadline = int(time.time()) + deadline_seconds
    create_tx = bounty_registry.functions.createBounty(
        agent_id,
        name,
        scope_uri,
        (tiers["critical"], tiers["high"], tiers["medium"], tiers["low"]),
        funding,
        deadline,
        0,  # minHunterReputation
    ).build_transaction({
        "from": account.address,
        "nonce": nonce,
        "gas": 500_000,
    })
    signed = account.sign_transaction(create_tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

    print(f"Bounty created! TX: {tx_hash.hex()}")
    return receipt


def respond_to_submissions(w3: Web3, contracts: dict, deployments: dict):
    """Poll for revealed submissions and make evidence-based accept/dispute decisions."""
    private_key = os.getenv("PROTOCOL_AGENT_PRIVATE_KEY")
    ecies_key = os.getenv("PROTOCOL_ECIES_PRIVATE_KEY")
    account = w3.eth.account.from_key(private_key)
    processed = set()

    print("Protocol Agent responding to submissions (evidence-based triage)... (Ctrl+C to stop)")

    cursor = BlockCursor("protocol_respond")

    while True:
        try:
            latest = w3.eth.block_number
            last = cursor.get_last_block()

            if latest > last:
                revealed_events = contracts["bugSubmission"].events.BugRevealed.get_logs(
                    fromBlock=last + 1, toBlock=latest
                )
                for event in revealed_events:
                    bug_id = event["args"]["bugId"]
                    if bug_id in processed:
                        continue

                    sub = contracts["bugSubmission"].functions.getSubmission(bug_id).call()
                    status = sub[6]              # 0=Committed, 1=Revealed, 2=Resolved
                    protocol_response = sub[12]  # 0=None, 1=Accepted, 2=Disputed
                    if status != 1 or protocol_response != 0:
                        processed.add(bug_id)
                        continue

                    claimed_severity = sub[2]  # claimedSeverity
                    encrypted_cid = sub[4]     # encryptedCID
                    bounty_id = sub[0]         # bountyId

                    # 1. Download and decrypt the bug report
                    report, scope_source = _decrypt_and_fetch_scope(
                        contracts, deployments, ecies_key, encrypted_cid, bounty_id
                    )

                    if report is None:
                        # Can't read report — dispute as safe fallback
                        print(f"  Bug #{bug_id}: cannot decrypt report — DISPUTE (fallback)")
                        _send_dispute(w3, contracts, account, bug_id)
                        processed.add(bug_id)
                        continue

                    # 2. Triage via AI inference
                    result = triage_submission(report, scope_source, claimed_severity)

                    claimed_label = SEVERITY_LABELS[claimed_severity] if 0 <= claimed_severity < len(SEVERITY_LABELS) else "?"
                    print(f"  Bug #{bug_id}: claimed={claimed_label} | "
                          f"estimated={result['estimated_severity']} | "
                          f"valid={result['valid']} | confidence={result['confidence']:.2f} | "
                          f"action={result['action']}")
                    print(f"    Reasoning: {result['reasoning']}")

                    # 3. Execute decision
                    nonce = w3.eth.get_transaction_count(account.address)
                    if result["action"] == "ACCEPT":
                        # Accept at the lower of claimed vs estimated severity to prevent overpay
                        from protocol.triage import SEVERITY_MAP
                        estimated_num = SEVERITY_MAP.get(result["estimated_severity"], 0)
                        accept_severity = min(claimed_severity, estimated_num) if estimated_num > 0 else claimed_severity
                        accept_label = SEVERITY_LABELS[accept_severity] if 0 <= accept_severity < len(SEVERITY_LABELS) else "?"
                        tx = contracts["bugSubmission"].functions.acceptSubmission(
                            bug_id, accept_severity
                        ).build_transaction({"from": account.address, "nonce": nonce, "gas": 300_000})
                        signed = account.sign_transaction(tx)
                        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
                        w3.eth.wait_for_transaction_receipt(tx_hash)
                        print(f"    → ACCEPTED bug #{bug_id} at {accept_label} (tx: {tx_hash.hex()})")
                    else:
                        _send_dispute(w3, contracts, account, bug_id)
                        print(f"    → DISPUTED bug #{bug_id}")

                    processed.add(bug_id)

                cursor.set_last_block(latest)
        except Exception as e:
            print(f"  [WARN] respond poll error: {e}")
        time.sleep(5)


def _decrypt_and_fetch_scope(contracts, deployments, ecies_key, encrypted_cid, bounty_id):
    """Download IPFS payload, decrypt for protocol, and fetch bounty scope source."""
    try:
        cid = encrypted_cid.replace("ipfs://", "")
        encrypted_data = download_json(cid)

        # Decrypt the protocol-specific encrypted field
        proto_hex = encrypted_data.get("protocolEncrypted")
        if not proto_hex:
            return None, ""

        encrypted_bytes = bytes.fromhex(proto_hex)
        decrypted = decrypt(ecies_key.encode(), encrypted_bytes)
        payload = json.loads(decrypted)
        report = payload.get("report", {})

        # Fetch bounty scope to get the contract source
        bounty = contracts["bountyRegistry"].functions.getBounty(bounty_id).call()
        scope_uri = bounty[2]  # scopeURI
        scope_data = download_json(scope_uri.replace("ipfs://", ""))
        contract_name = report.get("contract", "")
        scope_source = scope_data.get("contracts", {}).get(contract_name, "")

        return report, scope_source
    except Exception as e:
        print(f"    [WARN] Decryption/scope fetch failed: {e}")
        return None, ""


def _send_dispute(w3, contracts, account, bug_id):
    """Send a disputeSubmission transaction."""
    nonce = w3.eth.get_transaction_count(account.address)
    tx = contracts["bugSubmission"].functions.disputeSubmission(
        bug_id
    ).build_transaction({"from": account.address, "nonce": nonce, "gas": 200_000})
    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    w3.eth.wait_for_transaction_receipt(tx_hash)


def main():
    parser = argparse.ArgumentParser(description="Protocol Agent")
    parser.add_argument("command", choices=["create-bounty", "watch", "respond"])
    parser.add_argument("--name", default="TestProtocol")
    parser.add_argument("--scope-uri", default="ipfs://demo-scope")
    parser.add_argument("--deadline", type=int, default=86400)
    args = parser.parse_args()

    w3 = get_web3()
    contracts = get_all_contracts(w3)
    deployments = load_deployments()

    if args.command == "create-bounty":
        agent_id = deployments["agentIds"]["protocol"]
        create_bounty(w3, contracts, agent_id, args.name, args.scope_uri, args.deadline)
    elif args.command == "respond":
        respond_to_submissions(w3, contracts, deployments)
    elif args.command == "watch":
        print("Watching for SubmissionResolved and PatchGuidance events... (Ctrl+C to stop)")
        ecies_key = os.getenv("PROTOCOL_ECIES_PRIVATE_KEY")
        last_block = w3.eth.block_number

        while True:
            current_block = w3.eth.block_number
            if current_block > last_block:
                # Poll SubmissionResolved events on BugSubmission contract
                try:
                    resolved_events = contracts["bugSubmission"].events.SubmissionResolved.get_logs(
                        fromBlock=last_block + 1,
                        toBlock=current_block,
                    )
                    for event in resolved_events:
                        bug_id = event["args"]["bugId"]
                        valid = event["args"].get("isValid", False)
                        severity = event["args"].get("finalSeverity", 0)
                        print(f"\nSubmissionResolved: bug #{bug_id} | valid={valid} | severity={severity}")
                except Exception as e:
                    print(f"  [WARN] SubmissionResolved poll error: {e}")

                # Poll PatchGuidance events on ArbiterContract
                try:
                    patch_events = contracts["arbiterContract"].events.PatchGuidance.get_logs(
                        fromBlock=last_block + 1,
                        toBlock=current_block,
                    )
                    for event in patch_events:
                        bug_id = event["args"]["bugId"]
                        cid = event["args"]["encryptedPatchCID"]
                        print(f"\nPatchGuidance received for bug #{bug_id} (CID: {cid})")

                        # Download and decrypt patch guidance
                        try:
                            encrypted_data = download_json(cid)
                            encrypted_bytes = bytes.fromhex(encrypted_data["encrypted"])
                            guidance = json.loads(decrypt(ecies_key.encode(), encrypted_bytes))

                            print(f"  Affected functions: {guidance.get('affectedFunctions', [])}")
                            for change in guidance.get("recommendedChanges", []):
                                print(f"  - {change['function']}: {change['change']}")
                            print("  Verification tests:")
                            for test in guidance.get("verificationTests", []):
                                print(f"  - {test}")
                        except Exception as e:
                            print(f"  [ERROR] Failed to decrypt patch guidance: {e}")
                except Exception as e:
                    print(f"  [WARN] PatchGuidance poll error: {e}")

                last_block = current_block
            time.sleep(5)


if __name__ == "__main__":
    main()
