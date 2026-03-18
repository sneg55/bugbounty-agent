"""Protocol Agent: creates bounties, watches for resolution and patch guidance events."""
import argparse
import json
import os
import time

from web3 import Web3

from common.config import RPC_URL, load_deployments
from common.contracts import get_web3, get_all_contracts
from protocol.risk_model import get_default_tiers, get_default_funding


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


def main():
    parser = argparse.ArgumentParser(description="Protocol Agent")
    parser.add_argument("command", choices=["create-bounty", "watch"])
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
    elif args.command == "watch":
        print("Watching for events... (Ctrl+C to stop)")
        # Event watching implemented in Slice 5
        while True:
            time.sleep(5)


if __name__ == "__main__":
    main()
