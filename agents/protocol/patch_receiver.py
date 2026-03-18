# agents/protocol/patch_receiver.py
"""Receives and decrypts patch guidance from the Executor via on-chain events."""
import json
import os
import time

from common.contracts import get_web3, get_all_contracts
from common.config import load_deployments
from common.crypto import decrypt
from common.ipfs import download_json


def watch_for_patch_guidance():
    """Watch for PatchGuidance events and decrypt guidance."""
    w3 = get_web3()
    contracts = get_all_contracts(w3)
    ecies_key = os.getenv("PROTOCOL_ECIES_PRIVATE_KEY")

    print("Watching for patch guidance...")
    last_block = w3.eth.block_number

    while True:
        current_block = w3.eth.block_number
        if current_block > last_block:
            # Query PatchGuidance events
            events = contracts["arbiterContract"].events.PatchGuidance.get_logs(
                fromBlock=last_block + 1,
                toBlock=current_block,
            )

            for event in events:
                bug_id = event["args"]["bugId"]
                cid = event["args"]["encryptedPatchCID"]
                print(f"\nPatch guidance received for bug #{bug_id}")

                # Download and decrypt
                encrypted_data = download_json(cid)
                encrypted_bytes = bytes.fromhex(encrypted_data["encrypted"])
                guidance = json.loads(decrypt(ecies_key.encode(), encrypted_bytes))

                print(f"  Affected functions: {guidance.get('affectedFunctions', [])}")
                for change in guidance.get("recommendedChanges", []):
                    print(f"  - {change['function']}: {change['change']}")
                print(f"  Verification tests:")
                for test in guidance.get("verificationTests", []):
                    print(f"  - {test}")

            last_block = current_block
        time.sleep(5)


if __name__ == "__main__":
    watch_for_patch_guidance()
