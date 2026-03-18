"""Arbiter Agent: watches for jury selection, evaluates, votes."""
import argparse
import os
import time

from common.contracts import get_web3, get_all_contracts
from common.config import load_deployments
from common.ipfs import download_json
from common.block_cursor import BlockCursor
from arbiter.evaluator import evaluate_severity
from arbiter.voter import commit_and_reveal_vote

# Model configs per arbiter slot (from spec)
ARBITER_CONFIGS = {
    1: {"model": "llama-3.3-70b", "temperature": 0.0, "key_env": "ARBITER_1_PRIVATE_KEY"},
    2: {"model": "llama-3.3-70b", "temperature": 0.1, "key_env": "ARBITER_2_PRIVATE_KEY"},
    3: {"model": "mistral-large", "temperature": 0.0, "key_env": "ARBITER_3_PRIVATE_KEY"},
}


def run_arbiter(slot: int):
    """Run a single arbiter agent."""
    config = ARBITER_CONFIGS[slot]
    w3 = get_web3()
    contracts = get_all_contracts(w3)
    deployments = load_deployments()
    arbiter_agent_id = deployments["agentIds"][f"arbiter{slot}"]
    private_key = os.getenv(config["key_env"])
    account = w3.eth.account.from_key(private_key)

    print(f"Arbiter {slot} (agent #{arbiter_agent_id}) watching for jury selection...")
    cursor = BlockCursor(f"arbiter{slot}")
    processed = set()

    while True:
        latest = w3.eth.block_number
        last = cursor.get_last_block()
        if latest > last:
            # Poll for arbitration assignments only when new blocks exist
            bug_count = contracts["bugSubmission"].functions.getSubmissionCount().call()
            for bug_id in range(1, bug_count + 1):
                if bug_id in processed:
                    continue

                try:
                    arb = contracts["arbiterContract"].functions.getArbitration(bug_id).call()
                    phase = arb[11]  # phase
                    jurors = arb[3]  # jurors array

                    # Check if this arbiter is on the jury and voting is open
                    if arbiter_agent_id not in jurors:
                        continue
                    if phase < 1:  # Not yet in voting phase
                        continue
                    if phase >= 3:  # Already resolved
                        processed.add(bug_id)
                        continue

                    processed.add(bug_id)
                    print(f"  Selected as juror for bug #{bug_id}")

                    # Fetch state impact from IPFS
                    state_impact_cid = arb[1]  # stateImpactCID
                    state_impact = download_json(state_impact_cid)

                    # Evaluate severity
                    severity = evaluate_severity(
                        state_impact,
                        model=config["model"],
                        temperature=config["temperature"],
                    )
                    print(f"  Evaluated severity: {severity}")

                    # Vote
                    commit_and_reveal_vote(bug_id, severity, config["key_env"])

                except Exception as e:
                    print(f"  Error processing bug #{bug_id}: {e}")

            cursor.set_last_block(latest)

        time.sleep(5)


def main():
    parser = argparse.ArgumentParser(description="Arbiter Agent")
    parser.add_argument("--slot", type=int, required=True, choices=[1, 2, 3])
    args = parser.parse_args()
    run_arbiter(args.slot)


if __name__ == "__main__":
    main()
