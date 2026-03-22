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
    triggered = set()

    while True:
        try:
            latest = w3.eth.block_number
            last = cursor.get_last_block()

            if latest > last:
                # Watch for BugRevealed events to track submissions entering the dispute window
                revealed_events = contracts["bugSubmission"].events.BugRevealed.get_logs(
                    fromBlock=last + 1, toBlock=latest
                )
                for event in revealed_events:
                    bug_id = event["args"]["bugId"]
                    if bug_id in triggered:
                        continue

                    sub = contracts["bugSubmission"].functions.getSubmission(bug_id).call()
                    status = sub[6]              # 0=Committed, 1=Revealed, 2=Resolved
                    protocol_response = sub[12]  # 0=None, 1=Accepted, 2=Disputed
                    revealed_at = sub[11]         # timestamp

                    if status != 1 or protocol_response != 0:
                        # Already handled (accepted, disputed, or resolved)
                        triggered.add(bug_id)
                        continue

                    now = int(time.time())
                    if revealed_at > 0 and now > revealed_at + DISPUTE_WINDOW_SECONDS:
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
                            triggered.add(bug_id)
                        except Exception as e:
                            print(f"    [WARN] autoAcceptOnTimeout failed for bug #{bug_id}: {e}")

                cursor.set_last_block(latest)
        except Exception as e:
            print(f"  [WARN] keeper poll error: {e}")

        time.sleep(30)  # Check every 30 seconds


if __name__ == "__main__":
    main()
