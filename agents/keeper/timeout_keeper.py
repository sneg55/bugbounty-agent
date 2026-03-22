"""Keeper service: calls autoAcceptOnTimeout for submissions where the 72-hour dispute window expired.

Anyone can call autoAcceptOnTimeout — no special privileges needed.
Run this alongside the other agents to guarantee hunters get paid even when the protocol is offline.

Usage:
    python -m keeper.timeout_keeper
"""
import os
import time

from common.contracts import get_web3, get_all_contracts
from common.block_cursor import BlockCursor

DISPUTE_WINDOW_SECONDS = 72 * 60 * 60  # 72 hours


def main():
    w3 = get_web3()
    contracts = get_all_contracts(w3)
    private_key = os.getenv("KEEPER_PRIVATE_KEY") or os.getenv("EXECUTOR_PRIVATE_KEY")
    account = w3.eth.account.from_key(private_key)

    print(f"Timeout keeper running (wallet: {account.address})... (Ctrl+C to stop)")
    cursor = BlockCursor("keeper")
    # Track pending submissions: bug_id -> revealedAt timestamp
    pending = {}
    completed = set()

    while True:
        try:
            latest = w3.eth.block_number
            last = cursor.get_last_block()

            if latest > last:
                # Discover newly revealed submissions
                revealed_events = contracts["bugSubmission"].events.BugRevealed.get_logs(
                    fromBlock=last + 1, toBlock=latest
                )
                for event in revealed_events:
                    bug_id = int(event["args"]["bugId"])
                    if bug_id not in completed and bug_id not in pending:
                        sub = contracts["bugSubmission"].functions.getSubmission(bug_id).call()
                        revealed_at = sub[11]
                        if revealed_at > 0:
                            pending[bug_id] = revealed_at

                # Discover accepted/disputed (remove from pending)
                for event_type in ["SubmissionAccepted", "SubmissionDisputed", "SubmissionResolved"]:
                    try:
                        events = getattr(contracts["bugSubmission"].events, event_type).get_logs(
                            fromBlock=last + 1, toBlock=latest
                        )
                        for event in events:
                            bug_id = int(event["args"]["bugId"])
                            pending.pop(bug_id, None)
                            completed.add(bug_id)
                    except Exception:
                        pass

                cursor.set_last_block(latest)

            # Re-check ALL pending submissions for timeout
            now = int(time.time())
            expired = []
            for bug_id, revealed_at in pending.items():
                if now > revealed_at + DISPUTE_WINDOW_SECONDS:
                    expired.append(bug_id)

            for bug_id in expired:
                # Verify still pending on-chain (may have been handled between cycles)
                sub = contracts["bugSubmission"].functions.getSubmission(bug_id).call()
                status = sub[6]
                protocol_response = sub[12]
                if status != 1 or protocol_response != 0:
                    pending.pop(bug_id, None)
                    completed.add(bug_id)
                    continue

                print(f"  Bug #{bug_id}: dispute window expired — calling autoAcceptOnTimeout")
                try:
                    nonce = w3.eth.get_transaction_count(account.address)
                    tx = contracts["bugSubmission"].functions.autoAcceptOnTimeout(
                        bug_id
                    ).build_transaction({
                        "from": account.address,
                        "nonce": nonce,
                        "gas": 300_000,
                    })
                    signed = account.sign_transaction(tx)
                    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
                    w3.eth.wait_for_transaction_receipt(tx_hash)
                    print(f"    autoAcceptOnTimeout called (tx: {tx_hash.hex()})")
                    pending.pop(bug_id, None)
                    completed.add(bug_id)
                except Exception as e:
                    print(f"    [WARN] autoAcceptOnTimeout failed for bug #{bug_id}: {e}")

        except Exception as e:
            print(f"  [WARN] keeper poll error: {e}")

        time.sleep(30)


if __name__ == "__main__":
    main()
