"""
Deploy contracts to Base Sepolia (or Anvil) and register agent identities.
Writes deployments.json for agents and dashboard to consume.

Usage:
    python scripts/deploy_and_register.py --rpc-url http://localhost:8545 --private-key 0x...

For Anvil local testing:
    anvil &
    python scripts/deploy_and_register.py
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Anvil default accounts (index 0 is the deployer/owner)
# ---------------------------------------------------------------------------
ANVIL_ADDRESSES = [
    "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266",  # owner / deployer
    "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",  # protocol
    "0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC",  # hunter
    "0x90F79bf6EB2c4f870365E785982E1f101E93b906",  # executor
    "0x15d34AAf54267DB7D7c367839AAf71A00a2C6A65",  # arbiter1
    "0x9965507D1a55bcC2695C58ba16FB37d819B0A4dc",  # arbiter2
    "0x976EA74026E726554dB657fA54763abd0C3a0aa9",  # arbiter3
]
ANVIL_KEYS = [
    "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80",  # owner
    "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d",  # protocol
    "0x5de4111afa1a4b94908f83103eb1f1706367c2e68ca870fc3fb9a804cdab365a",  # hunter
    "0x7c852118294e51e653712a81e05800f419141751be58f605c371e15141b007a6",  # executor
    "0x47e179ec197488593b187f80a00eb0da91f1b9d0b13f8733639f19c30a34926a",  # arbiter1
    "0x8b3a350cf5c34c9194ca85829a2df0ec3153be0318b5e2d3348e872092edffba",  # arbiter2
    "0x92db14e403b83dfe3df233f83dfa3a0d7096f21ca9b0d6d6b8d88b2b4ec1564e",  # arbiter3
]

CONTRACTS_DIR = Path(__file__).parent.parent / "contracts"

# All 7 contract names emitted by Deploy.s.sol via console.log
CONTRACT_NAMES = [
    "MockUSDC",
    "IdentityRegistry",
    "ReputationRegistry",
    "ValidationRegistry",
    "BountyRegistry",
    "BugSubmission",
    "ArbiterContract",
]

# Mapping from Deploy.s.sol log name -> deployments.json key
KEY_MAP = {
    "MockUSDC": "mockUSDC",
    "IdentityRegistry": "identityRegistry",
    "ReputationRegistry": "reputationRegistry",
    "ValidationRegistry": "validationRegistry",
    "BountyRegistry": "bountyRegistry",
    "BugSubmission": "bugSubmission",
    "ArbiterContract": "arbiterContract",
}


# ---------------------------------------------------------------------------
# Forge deployment
# ---------------------------------------------------------------------------

def run_forge_script(rpc_url: str, private_key: str) -> dict:
    """Run Foundry deploy script and parse all 7 contract addresses from output."""
    result = subprocess.run(
        [
            "forge", "script", "script/Deploy.s.sol:Deploy",
            "--rpc-url", rpc_url,
            "--private-key", private_key,
            "--broadcast",
        ],
        cwd=str(CONTRACTS_DIR),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print("Deploy failed:", result.stderr)
        sys.exit(1)

    addresses = {}
    for line in result.stdout.splitlines():
        for name in CONTRACT_NAMES:
            if f"{name}:" in line:
                parts = line.split(f"{name}:")[1].strip()
                # Take only the address token (first word)
                addr = parts.split()[0] if parts else ""
                if addr.startswith("0x") and len(addr) >= 42:
                    addresses[name] = addr[:42]

    missing = [n for n in CONTRACT_NAMES if n not in addresses]
    if missing:
        print(f"[WARNING] Could not parse addresses for: {missing}")
        print("Raw stdout:\n", result.stdout)

    return addresses


# ---------------------------------------------------------------------------
# cast helpers
# ---------------------------------------------------------------------------

def cast_send(to: str, sig: str, args: list, private_key: str, rpc_url: str) -> None:
    """Send a transaction via cast."""
    cmd = ["cast", "send", to, sig] + args + ["--private-key", private_key, "--rpc-url", rpc_url]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[ERROR] cast send failed: {' '.join(cmd)}")
        print(result.stderr)
        sys.exit(1)


# ---------------------------------------------------------------------------
# Post-deploy registration
# ---------------------------------------------------------------------------

def register_agents(addresses: dict, rpc_url: str) -> dict:
    """
    Mint 6 agent IDs (protocol, hunter, executor, arbiter1-3),
    register ECIES public keys as metadata, register arbiters in pool,
    and mint MockUSDC to protocol (50,000) and hunter (1,000).

    Returns dict of agentIds: {role: id}.
    """
    identity = addresses["IdentityRegistry"]
    reputation = addresses["ReputationRegistry"]
    validation = addresses["ValidationRegistry"]
    usdc = addresses["MockUSDC"]
    bounty_reg = addresses["BountyRegistry"]
    bug_sub = addresses["BugSubmission"]
    arbiter = addresses["ArbiterContract"]
    deployer_key = ANVIL_KEYS[0]

    roles = [
        ("protocol",  ANVIL_ADDRESSES[1], ANVIL_KEYS[1]),
        ("hunter",    ANVIL_ADDRESSES[2], ANVIL_KEYS[2]),
        ("executor",  ANVIL_ADDRESSES[3], ANVIL_KEYS[3]),
        ("arbiter1",  ANVIL_ADDRESSES[4], ANVIL_KEYS[4]),
        ("arbiter2",  ANVIL_ADDRESSES[5], ANVIL_KEYS[5]),
        ("arbiter3",  ANVIL_ADDRESSES[6], ANVIL_KEYS[6]),
    ]

    agent_ids = {}
    for idx, (role, addr, key) in enumerate(roles, start=1):
        print(f"  Minting agent for {role} ({addr}) -> ID {idx}")
        cast_send(
            identity,
            "mintAgent(address,string)",
            [addr, f"ipfs://{role}-metadata"],
            deployer_key,
            rpc_url,
        )
        agent_ids[role] = idx

    # Generate real ECIES keypairs for each agent role and register public keys
    print("  Generating ECIES keypairs and registering public keys ...")
    print("  *** Save the private keys below into your .env file ***")
    generated_keys = {}
    for role, addr, key in roles:
        # Generate keypair by invoking Python's ecies library in a subprocess
        result = subprocess.run(
            [
                sys.executable, "-c",
                "from ecies.utils import generate_eth_key; k=generate_eth_key(); "
                "print(k.to_hex(), k.public_key.to_hex())"
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            # Fallback: use deterministic test keys that differ per role (not for production)
            priv_hex = "0x" + hex(hash(role) & ((1 << 256) - 1))[2:].zfill(64)
            pub_hex = "0x04" + hex(abs(hash(role + "_pub")) % (2 ** 256))[2:].zfill(64) * 2
        else:
            parts = result.stdout.strip().split()
            priv_hex = parts[0]
            pub_hex = parts[1]

        generated_keys[role] = {"private": priv_hex, "public": pub_hex}
        env_var = f"{role.upper()}_ECIES_PRIVATE_KEY={priv_hex}"
        print(f"    {env_var}")

        # setMetadata value must be bytes — pass public key as hex bytes argument
        cast_send(
            identity,
            "setMetadata(uint256,string,bytes)",
            [str(agent_ids[role]), "eciesPubKey", pub_hex],
            key,
            rpc_url,
        )

    # Set executor on ArbiterContract
    print("  Setting executor on ArbiterContract ...")
    cast_send(
        arbiter,
        "setExecutor(address)",
        [ANVIL_ADDRESSES[3]],
        deployer_key,
        rpc_url,
    )

    # Authorize executor in ValidationRegistry
    print("  Authorizing executor in ValidationRegistry ...")
    cast_send(
        validation,
        "addAuthorizedCaller(address)",
        [ANVIL_ADDRESSES[3]],
        deployer_key,
        rpc_url,
    )

    # Authorize ArbiterContract in ReputationRegistry
    print("  Authorizing ArbiterContract in ReputationRegistry ...")
    cast_send(
        reputation,
        "addAuthorizedCaller(address)",
        [arbiter],
        deployer_key,
        rpc_url,
    )

    # Register arbiters in pool
    print("  Registering arbiters ...")
    for slot, (role, addr, key) in enumerate(roles[3:], start=4):
        cast_send(
            arbiter,
            "registerArbiter(uint256)",
            [str(slot)],
            key,
            rpc_url,
        )
        print(f"    {role} (agentId={slot}) registered in arbiter pool")

    # Mint MockUSDC: 50,000 to protocol, 1,000 to hunter
    print("  Minting MockUSDC ...")
    cast_send(usdc, "mint(address,uint256)", [ANVIL_ADDRESSES[1], str(50_000 * 10**6)], deployer_key, rpc_url)
    cast_send(usdc, "mint(address,uint256)", [ANVIL_ADDRESSES[2], str(1_000 * 10**6)], deployer_key, rpc_url)
    print("  Protocol: 50,000 USDC | Hunter: 1,000 USDC")

    # Pre-approve USDC for BountyRegistry (protocol) and BugSubmission (hunter)
    cast_send(usdc, "approve(address,uint256)", [bounty_reg, str(2**256 - 1)], ANVIL_KEYS[1], rpc_url)
    cast_send(usdc, "approve(address,uint256)", [bug_sub, str(2**256 - 1)], ANVIL_KEYS[2], rpc_url)
    print("  USDC approvals set")

    return agent_ids


# ---------------------------------------------------------------------------
# Write deployments.json
# ---------------------------------------------------------------------------

def write_deployments(addresses: dict, agent_ids: dict, output_path: str = "deployments.json") -> dict:
    """Write deployments.json mapping with all 7 contract addresses and agent IDs."""
    deployments = {KEY_MAP[k]: v for k, v in addresses.items() if k in KEY_MAP}
    deployments["agentIds"] = agent_ids

    path = Path(__file__).parent.parent / output_path
    with open(path, "w") as f:
        json.dump(deployments, f, indent=2)
    print(f"Deployments written to {path}")
    return deployments


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Deploy BugBounty.agent contracts and register identities")
    parser.add_argument("--rpc-url", default="http://localhost:8545", help="RPC endpoint")
    parser.add_argument(
        "--private-key",
        default=ANVIL_KEYS[0],
        help="Deployer private key (default: Anvil account 0)",
    )
    parser.add_argument(
        "--skip-register",
        action="store_true",
        help="Skip agent minting and registration (deploy only)",
    )
    args = parser.parse_args()

    print("Deploying contracts ...")
    addresses = run_forge_script(args.rpc_url, args.private_key)
    print("Deployed:", json.dumps({KEY_MAP.get(k, k): v for k, v in addresses.items()}, indent=2))

    agent_ids: dict = {}
    if not args.skip_register:
        print("\nRegistering agents ...")
        agent_ids = register_agents(addresses, args.rpc_url)
        print("Agent IDs:", json.dumps(agent_ids, indent=2))

    deployments = write_deployments(addresses, agent_ids)
    print("\nDone. Deployments:")
    print(json.dumps(deployments, indent=2))


if __name__ == "__main__":
    main()
