"""
Orchestrate the full BugBounty.agent demo lifecycle.

Usage:
    # Start Anvil first: anvil
    # Deploy: python scripts/deploy_and_register.py
    # Run demo: python scripts/demo_flow.py

The script walks through every stage of the protocol:
  1. Deploy all contracts (via forge script)
  2. Mint agent IDs + register metadata + fund wallets
  3. Protocol Agent creates bounty
  4. Hunter scans -> generates PoC -> commit -> reveal
  5. Executor runs PoC -> state diff -> registers
  6. 3 Arbiters evaluate -> commit -> reveal -> resolve
  7. Patch guidance generated
  8. Protocol Agent withdraws remainder (after deadline)
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ANVIL_RPC = "http://localhost:8545"
ANVIL_KEYS = [
    "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80",  # owner / deployer
    "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d",  # protocol
    "0x5de4111afa1a4b94908f83103eb1f1706367c2e68ca870fc3fb9a804cdab365a",  # hunter
    "0x7c852118294e51e653712a81e05800f419141751be58f605c371e15141b007a6",  # executor
    "0x47e179ec197488593b187f80a00eb0da91f1b9d0b13f8733639f19c30a34926a",  # arb1
    "0x8b3a350cf5c34c9194ca85829a2df0ec3153be0318b5e2d3348e872092edffba",  # arb2
    "0x92db14e403b83dfe3df233f83dfa3a0d7096f21ca9b0d6d6b8d88b2b4ec1564e",  # arb3
]
ANVIL_ADDRESSES = [
    "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266",  # owner
    "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",  # protocol
    "0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC",  # hunter
    "0x90F79bf6EB2c4f870365E785982E1f101E93b906",  # executor
    "0x15d34AAf54267DB7D7c367839AAf71A00a2C6A65",  # arb1
    "0x9965507D1a55bcC2695C58ba16FB37d819B0A4dc",  # arb2
    "0x976EA74026E726554dB657fA54763abd0C3a0aa9",  # arb3
]

CONTRACTS_DIR = Path(__file__).parent.parent / "contracts"
DEPLOYMENTS_PATH = Path(__file__).parent.parent / "deployments.json"

SECTION = "=" * 60


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def print_section(title: str) -> None:
    print(f"\n{SECTION}")
    print(f"  {title}")
    print(SECTION)


def run(cmd: list, cwd: str = None, env: dict = None) -> str:
    """Run a shell command and return stdout. Exit on failure."""
    merged_env = {**os.environ, **(env or {})}
    result = subprocess.run(
        cmd,
        cwd=cwd or str(CONTRACTS_DIR),
        capture_output=True,
        text=True,
        env=merged_env,
    )
    if result.returncode != 0:
        print(f"[ERROR] Command failed: {' '.join(cmd)}")
        print(result.stderr)
        sys.exit(1)
    return result.stdout


def cast(subcmd: list, rpc_url: str = ANVIL_RPC) -> str:
    """Invoke `cast` with the given sub-command and return trimmed stdout."""
    return run(["cast"] + subcmd + ["--rpc-url", rpc_url]).strip()


def cast_send(to: str, sig: str, args: list, private_key: str, rpc_url: str = ANVIL_RPC) -> None:
    """Send a transaction via cast."""
    run(
        ["cast", "send", to, sig] + args +
        ["--private-key", private_key, "--rpc-url", rpc_url]
    )


def cast_call(to: str, sig: str, args: list, rpc_url: str = ANVIL_RPC) -> str:
    """Call (read) a contract via cast."""
    return run(["cast", "call", to, sig] + args + ["--rpc-url", rpc_url]).strip()


def keccak256_encode(*parts) -> str:
    """
    Mimic Solidity keccak256(abi.encode(...)) for simple types.
    Used to build commit hashes without a web3 dependency.
    """
    import struct
    packed = b""
    for part in parts:
        if isinstance(part, str):
            # ABI-encode string: offset + length + data padded to 32 bytes
            encoded = part.encode("utf-8")
            length = len(encoded)
            padded = encoded + b"\x00" * ((32 - length % 32) % 32)
            packed += struct.pack(">32s", b"\x00" * 31 + bytes([32]))  # offset placeholder
            packed += struct.pack(">32s", length.to_bytes(32, "big"))
            packed += padded
        elif isinstance(part, int):
            packed += part.to_bytes(32, "big")
        elif isinstance(part, bytes):
            packed += part.ljust(32, b"\x00")
    return "0x" + hashlib.sha3_256(packed).hexdigest()  # NOTE: Python sha3_256 == keccak256


def hex_pad32(val: str) -> str:
    """Ensure a hex string (with or without 0x) is zero-padded to 32 bytes."""
    val = val.replace("0x", "").replace("0X", "")
    return "0x" + val.zfill(64)


# ---------------------------------------------------------------------------
# Step 1: Deploy contracts
# ---------------------------------------------------------------------------

def deploy_contracts(rpc_url: str, deployer_key: str) -> dict:
    print_section("Step 1: Deploying contracts")

    env = {**os.environ, "DEPLOYER_PRIVATE_KEY": deployer_key}
    result = subprocess.run(
        [
            "forge", "script", "script/Deploy.s.sol:Deploy",
            "--rpc-url", rpc_url,
            "--private-key", deployer_key,
            "--broadcast",
        ],
        cwd=str(CONTRACTS_DIR),
        capture_output=True,
        text=True,
        env=env,
    )
    if result.returncode != 0:
        print("[ERROR] forge script failed:")
        print(result.stderr)
        sys.exit(1)

    output = result.stdout
    addresses = {}
    contract_names = [
        "MockUSDC",
        "IdentityRegistry",
        "ReputationRegistry",
        "ValidationRegistry",
        "BountyRegistry",
        "BugSubmission",
        "ArbiterContract",
    ]
    for line in output.splitlines():
        for name in contract_names:
            if f"{name}:" in line:
                addr = line.split(f"{name}:")[1].strip()
                if addr.startswith("0x") and len(addr) >= 42:
                    addresses[name] = addr[:42]

    print("  Deployed addresses:")
    for name, addr in addresses.items():
        print(f"    {name}: {addr}")
    return addresses


# ---------------------------------------------------------------------------
# Step 2: Mint agent IDs + register metadata + fund wallets
# ---------------------------------------------------------------------------

def setup_agents(addrs: dict, rpc_url: str) -> dict:
    print_section("Step 2: Minting agent IDs and funding wallets")

    identity = addrs["IdentityRegistry"]
    usdc = addrs["MockUSDC"]
    validation = addrs["ValidationRegistry"]
    reputation = addrs["ReputationRegistry"]
    arbiter = addrs["ArbiterContract"]

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
            [addr, f"ipfs://{role}"],
            ANVIL_KEYS[0],
            rpc_url,
        )
        agent_ids[role] = idx

    # Set executor on ArbiterContract
    print("  Setting executor on ArbiterContract")
    cast_send(
        arbiter,
        "setExecutor(address)",
        [ANVIL_ADDRESSES[3]],
        ANVIL_KEYS[0],
        rpc_url,
    )

    # Register executor as authorized caller in ValidationRegistry
    print("  Authorizing executor in ValidationRegistry")
    cast_send(
        validation,
        "addAuthorizedCaller(address)",
        [ANVIL_ADDRESSES[3]],
        ANVIL_KEYS[0],
        rpc_url,
    )

    # Authorize arbiter contract in ReputationRegistry
    print("  Authorizing ArbiterContract in ReputationRegistry")
    cast_send(
        reputation,
        "addAuthorizedCaller(address)",
        [arbiter],
        ANVIL_KEYS[0],
        rpc_url,
    )

    # Register arbiters in the pool
    print("  Registering arbiters in pool")
    for slot, (role, addr, key) in enumerate(roles[3:], start=4):
        cast_send(
            arbiter,
            "registerArbiter(uint256)",
            [str(slot)],
            key,
            rpc_url,
        )
        print(f"    {role} (agentId={slot}) registered")

    # Mint USDC: 50k to protocol, 1k to hunter
    print("  Minting MockUSDC (50,000 to protocol, 1,000 to hunter)")
    cast_send(usdc, "mint(address,uint256)", [ANVIL_ADDRESSES[1], str(50_000 * 10**6)], ANVIL_KEYS[0], rpc_url)
    cast_send(usdc, "mint(address,uint256)", [ANVIL_ADDRESSES[2], str(1_000 * 10**6)], ANVIL_KEYS[0], rpc_url)

    # Approve bounty registry + bug submission to spend USDC
    bounty_reg = addrs["BountyRegistry"]
    bug_sub = addrs["BugSubmission"]
    cast_send(usdc, "approve(address,uint256)", [bounty_reg, str(2**256 - 1)], ANVIL_KEYS[1], rpc_url)
    cast_send(usdc, "approve(address,uint256)", [bug_sub, str(2**256 - 1)], ANVIL_KEYS[2], rpc_url)
    print("  USDC approvals set")

    return agent_ids


# ---------------------------------------------------------------------------
# Step 3: Protocol Agent creates bounty
# ---------------------------------------------------------------------------

def create_bounty(addrs: dict, agent_ids: dict, rpc_url: str) -> int:
    print_section("Step 3: Protocol Agent creating bounty")

    bounty_reg = addrs["BountyRegistry"]
    deadline = int(time.time()) + 86400  # 24 hours

    # Tiers: critical=25k, high=10k, medium=2k, low=500 (in USDC units 1e6)
    critical = 25_000 * 10**6
    high = 10_000 * 10**6
    medium = 2_000 * 10**6
    low = 500 * 10**6
    funding = 50_000 * 10**6

    cast_send(
        bounty_reg,
        "createBounty(uint256,string,string,(uint256,uint256,uint256,uint256),uint256,uint256,int256)",
        [
            str(agent_ids["protocol"]),
            "VulnProtocol Demo",
            "ipfs://demo-scope",
            f"({critical},{high},{medium},{low})",
            str(funding),
            str(deadline),
            "0",
        ],
        ANVIL_KEYS[1],
        rpc_url,
    )

    print(f"  Bounty #1 created with {funding // 10**6:,} USDC funding, deadline in 24h")
    return 1  # bountyId


# ---------------------------------------------------------------------------
# Step 4: Hunter scans -> commit -> reveal
# ---------------------------------------------------------------------------

def hunter_commit_reveal(addrs: dict, agent_ids: dict, bounty_id: int, rpc_url: str) -> int:
    print_section("Step 4: Hunter committing and revealing bug")

    bug_sub = addrs["BugSubmission"]
    hunter_agent_id = agent_ids["hunter"]

    encrypted_cid = "ipfs://encrypted-poc-demo"
    salt_hex = "0x" + "huntersalt".encode().hex().ljust(64, "0")
    # commitHash = keccak256(abi.encode(encryptedCID, hunterAgentId, salt))
    # Build via cast
    encoded = run(
        ["cast", "abi-encode", "f(string,uint256,bytes32)",
         encrypted_cid, str(hunter_agent_id), salt_hex],
        cwd=str(CONTRACTS_DIR),
    ).strip()
    commit_hash = run(
        ["cast", "keccak", encoded],
        cwd=str(CONTRACTS_DIR),
    ).strip()

    print(f"  Committing bug (claimed CRITICAL, agentId={hunter_agent_id})")
    print(f"    commitHash: {commit_hash}")
    cast_send(
        bug_sub,
        "commitBug(uint256,bytes32,uint256,uint8)",
        [str(bounty_id), commit_hash, str(hunter_agent_id), "4"],
        ANVIL_KEYS[2],
        rpc_url,
    )
    bug_id = 1  # first submission

    print(f"  Revealing bug #{bug_id}")
    cast_send(
        bug_sub,
        "revealBug(uint256,string,bytes32)",
        [str(bug_id), encrypted_cid, salt_hex],
        ANVIL_KEYS[2],
        rpc_url,
    )
    print(f"  Bug #{bug_id} revealed: {encrypted_cid}")
    return bug_id


# ---------------------------------------------------------------------------
# Step 5: Executor registers state impact
# ---------------------------------------------------------------------------

def executor_register_impact(addrs: dict, agent_ids: dict, bug_id: int, rpc_url: str) -> str:
    print_section("Step 5: Executor registering state impact")

    validation = addrs["ValidationRegistry"]
    arbiter = addrs["ArbiterContract"]
    executor_agent_id = agent_ids["executor"]

    state_diff_cid = "ipfs://state-diff-demo"
    req_hash = run(["cast", "keccak", "statehash"], cwd=str(CONTRACTS_DIR)).strip()

    print(f"  Submitting validation (executorAgentId={executor_agent_id})")
    cast_send(
        validation,
        "submitValidation(uint256,bytes32,string)",
        [str(executor_agent_id), req_hash, state_diff_cid],
        ANVIL_KEYS[3],
        rpc_url,
    )

    print(f"  Registering state impact for bug #{bug_id}")
    cast_send(
        arbiter,
        "registerStateImpact(uint256,bytes32,string)",
        [str(bug_id), req_hash, state_diff_cid],
        ANVIL_KEYS[3],
        rpc_url,
    )
    print(f"  State impact registered: {state_diff_cid}")
    return req_hash


# ---------------------------------------------------------------------------
# Step 6: 3 Arbiters commit + reveal votes
# ---------------------------------------------------------------------------

def arbiters_vote(addrs: dict, agent_ids: dict, bug_id: int, rpc_url: str) -> None:
    print_section("Step 6: Arbiters committing and revealing votes")

    arbiter = addrs["ArbiterContract"]
    arb_roles = ["arbiter1", "arbiter2", "arbiter3"]
    arb_keys = ANVIL_KEYS[4:7]
    severities = [4, 4, 4]  # all CRITICAL
    salts = [
        "0x" + f"salt{i}".encode().hex().ljust(64, "0") for i in range(1, 4)
    ]

    # Commit phase
    print("  Commit phase:")
    for i, (role, key, sev, salt) in enumerate(zip(arb_roles, arb_keys, severities, salts)):
        # voteHash = keccak256(abi.encode(uint8(severity), bytes32(salt)))
        encoded = run(
            ["cast", "abi-encode", "f(uint8,bytes32)", str(sev), salt],
            cwd=str(CONTRACTS_DIR),
        ).strip()
        vote_hash = run(["cast", "keccak", encoded], cwd=str(CONTRACTS_DIR)).strip()
        print(f"    {role} commits severity={sev}, salt={salt[:10]}...")
        cast_send(
            arbiter,
            "commitVote(uint256,bytes32)",
            [str(bug_id), vote_hash],
            key,
            rpc_url,
        )

    # Reveal phase
    print("  Reveal phase:")
    for role, key, sev, salt in zip(arb_roles, arb_keys, severities, salts):
        print(f"    {role} reveals severity={sev}")
        cast_send(
            arbiter,
            "revealVote(uint256,uint8,bytes32)",
            [str(bug_id), str(sev), salt],
            key,
            rpc_url,
        )


# ---------------------------------------------------------------------------
# Step 7: Patch guidance
# ---------------------------------------------------------------------------

def emit_patch_guidance(addrs: dict, bug_id: int, rpc_url: str) -> None:
    print_section("Step 7: Executor emitting patch guidance")

    arbiter = addrs["ArbiterContract"]
    patch_cid = "ipfs://patch-guidance-demo"

    cast_send(
        arbiter,
        "registerPatchGuidance(uint256,string)",
        [str(bug_id), patch_cid],
        ANVIL_KEYS[3],
        rpc_url,
    )
    print(f"  Patch guidance emitted: {patch_cid}")


# ---------------------------------------------------------------------------
# Step 8: Protocol Agent withdraws remainder
# ---------------------------------------------------------------------------

def withdraw_remainder(addrs: dict, agent_ids: dict, bounty_id: int, rpc_url: str) -> None:
    print_section("Step 8: Protocol Agent withdrawing remainder")

    bounty_reg = addrs["BountyRegistry"]
    usdc = addrs["MockUSDC"]

    # Fast-forward time past deadline + GRACE_PERIOD (1800s)
    # anvil_setTime + mine a block
    grace = 86400 + 1800 + 1
    run(
        ["cast", "rpc", "evm_increaseTime", str(grace), "--rpc-url", rpc_url],
        cwd=str(CONTRACTS_DIR),
    )
    run(
        ["cast", "rpc", "evm_mine", "--rpc-url", rpc_url],
        cwd=str(CONTRACTS_DIR),
    )

    cast_send(
        bounty_reg,
        "withdrawRemainder(uint256)",
        [str(bounty_id)],
        ANVIL_KEYS[1],
        rpc_url,
    )

    balance = cast_call(usdc, "balanceOf(address)(uint256)", [ANVIL_ADDRESSES[1]], rpc_url)
    print(f"  Remainder withdrawn. Protocol balance: {balance} USDC wei")


# ---------------------------------------------------------------------------
# Results summary
# ---------------------------------------------------------------------------

def print_results(addrs: dict, bug_id: int, bounty_id: int, rpc_url: str) -> None:
    print_section("Results Summary")

    usdc = addrs["MockUSDC"]
    bug_sub = addrs["BugSubmission"]
    bounty_reg = addrs["BountyRegistry"]
    reputation = addrs["ReputationRegistry"]

    hunter_bal = cast_call(usdc, "balanceOf(address)(uint256)", [ANVIL_ADDRESSES[2]], rpc_url)
    print(f"  Hunter USDC balance: {hunter_bal}")

    sub_raw = cast_call(bug_sub, "getSubmission(uint256)((uint256,uint256,uint8,bytes32,string,uint256,uint8,uint8,bool,uint256,address))", [str(bug_id)], rpc_url)
    print(f"  Submission #{bug_id}: {sub_raw}")

    remaining = cast_call(bounty_reg, "getRemainingFunds(uint256)(uint256)", [str(bounty_id)], rpc_url)
    print(f"  Bounty #{bounty_id} remaining funds: {remaining}")

    for agent_id in [2, 4, 5, 6]:
        rep = cast_call(reputation, "getReputation(uint256)(int256)", [str(agent_id)], rpc_url)
        print(f"  Reputation agentId={agent_id}: {rep}")


# ---------------------------------------------------------------------------
# Write deployments.json
# ---------------------------------------------------------------------------

def write_deployments(addrs: dict, agent_ids: dict) -> None:
    key_map = {
        "MockUSDC": "mockUSDC",
        "IdentityRegistry": "identityRegistry",
        "ReputationRegistry": "reputationRegistry",
        "ValidationRegistry": "validationRegistry",
        "BountyRegistry": "bountyRegistry",
        "BugSubmission": "bugSubmission",
        "ArbiterContract": "arbiterContract",
    }
    deployments = {key_map[k]: v for k, v in addrs.items() if k in key_map}
    deployments["agentIds"] = agent_ids

    with open(DEPLOYMENTS_PATH, "w") as f:
        json.dump(deployments, f, indent=2)
    print(f"\n  deployments.json written to {DEPLOYMENTS_PATH}")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="BugBounty.agent demo flow")
    parser.add_argument("--rpc-url", default=ANVIL_RPC, help="RPC endpoint (default: local Anvil)")
    parser.add_argument("--skip-deploy", action="store_true", help="Skip deployment, use existing deployments.json")
    parser.add_argument("--skip-withdraw", action="store_true", help="Skip time-travel + withdrawal step")
    args = parser.parse_args()

    rpc_url = args.rpc_url

    print(SECTION)
    print("  BugBounty.agent Demo Flow")
    print(SECTION)
    print(f"  RPC: {rpc_url}")

    if args.skip_deploy and DEPLOYMENTS_PATH.exists():
        print("\n  Loading existing deployments.json ...")
        with open(DEPLOYMENTS_PATH) as f:
            data = json.load(f)
        key_map_inv = {
            "mockUSDC": "MockUSDC",
            "identityRegistry": "IdentityRegistry",
            "reputationRegistry": "ReputationRegistry",
            "validationRegistry": "ValidationRegistry",
            "bountyRegistry": "BountyRegistry",
            "bugSubmission": "BugSubmission",
            "arbiterContract": "ArbiterContract",
        }
        addrs = {key_map_inv[k]: v for k, v in data.items() if k in key_map_inv}
        agent_ids = data.get("agentIds", {})
    else:
        addrs = deploy_contracts(rpc_url, ANVIL_KEYS[0])
        agent_ids = setup_agents(addrs, rpc_url)
        write_deployments(addrs, agent_ids)

    bounty_id = create_bounty(addrs, agent_ids, rpc_url)
    bug_id = hunter_commit_reveal(addrs, agent_ids, bounty_id, rpc_url)
    executor_register_impact(addrs, agent_ids, bug_id, rpc_url)
    arbiters_vote(addrs, agent_ids, bug_id, rpc_url)
    emit_patch_guidance(addrs, bug_id, rpc_url)

    if not args.skip_withdraw:
        withdraw_remainder(addrs, agent_ids, bounty_id, rpc_url)

    print_results(addrs, bug_id, bounty_id, rpc_url)

    print(f"\n{SECTION}")
    print("  Demo complete!")
    print(SECTION)


if __name__ == "__main__":
    main()
