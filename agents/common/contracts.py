import json
from pathlib import Path

from web3 import Web3

from common.config import RPC_URL, load_deployments

ARTIFACTS_DIR = Path(__file__).parent.parent.parent / "contracts" / "out"


def get_web3() -> Web3:
    return Web3(Web3.HTTPProvider(RPC_URL))


def load_abi(contract_name: str) -> list:
    """Load ABI from Foundry compilation artifacts."""
    artifact_path = ARTIFACTS_DIR / f"{contract_name}.sol" / f"{contract_name}.json"
    with open(artifact_path) as f:
        artifact = json.load(f)
    return artifact["abi"]


def get_contract(w3: Web3, contract_name: str, address: str):
    """Get a web3 contract instance."""
    abi = load_abi(contract_name)
    return w3.eth.contract(address=Web3.to_checksum_address(address), abi=abi)


def get_all_contracts(w3: Web3) -> dict:
    """Load all deployed contracts from deployments.json."""
    deployments = load_deployments()
    contracts = {}
    name_map = {
        "identityRegistry": "IdentityRegistry",
        "reputationRegistry": "ReputationRegistry",
        "validationRegistry": "ValidationRegistry",
        "bountyRegistry": "BountyRegistry",
        "bugSubmission": "BugSubmission",
        "arbiterContract": "ArbiterContract",
        "mockUSDC": "MockUSDC",
    }
    for key, contract_name in name_map.items():
        if key in deployments:
            contracts[key] = get_contract(w3, contract_name, deployments[key])
    return contracts
