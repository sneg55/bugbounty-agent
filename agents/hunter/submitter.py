"""Handles encryption, IPFS upload, and commit-reveal submission flow."""
import json
import os
import secrets
import time

from web3 import Web3

from common.contracts import get_web3, get_all_contracts, load_abi
from common.config import load_deployments
from common.crypto import encrypt
from common.ipfs import upload_json


def compute_commit_hash(encrypted_cid: str, hunter_agent_id: int, salt: bytes) -> bytes:
    """Compute commit hash matching Solidity's keccak256(abi.encode(string, uint256, bytes32)).

    IMPORTANT: Uses eth_abi.encode (ABI standard encoding with padding), NOT
    Web3.solidity_keccak which uses abi.encodePacked (tight packing). The Solidity
    contract uses abi.encode, so we must match that exactly.
    """
    from eth_abi import encode
    encoded = encode(["string", "uint256", "bytes32"], [encrypted_cid, hunter_agent_id, salt])
    return Web3.keccak(encoded)


def submit_finding(
    report: dict,
    poc_source: str,
    bounty_id: int,
    hunter_agent_id: int,
    claimed_severity: int,
    executor_pubkey: bytes,
    protocol_pubkey: bytes,
) -> dict:
    """Full submission flow: encrypt -> IPFS -> commit -> reveal."""
    w3 = get_web3()
    contracts = get_all_contracts(w3)
    private_key = os.getenv("HUNTER_AGENT_PRIVATE_KEY")
    account = w3.eth.account.from_key(private_key)

    # 1. Encrypt report + PoC with executor's and protocol's public keys
    payload = json.dumps({"report": report, "poc": poc_source}).encode()
    encrypted = encrypt(executor_pubkey, payload)
    protocol_encrypted = encrypt(protocol_pubkey, payload)

    # 2. Upload encrypted payload to IPFS
    encrypted_cid = upload_json({
        "encrypted": encrypted.hex(),
        "protocolEncrypted": protocol_encrypted.hex(),
    })

    # 3. Generate salt and commit hash
    salt = secrets.token_bytes(32)
    commit_hash = compute_commit_hash(encrypted_cid, hunter_agent_id, salt)

    # 4. Commit on-chain
    bug_submission = contracts["bugSubmission"]
    nonce = w3.eth.get_transaction_count(account.address)
    tx = bug_submission.functions.commitBug(
        bounty_id, commit_hash, hunter_agent_id, claimed_severity
    ).build_transaction({
        "from": account.address,
        "nonce": nonce,
        "gas": 300_000,
    })
    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

    # Parse bug ID from event
    bug_id = bug_submission.events.BugCommitted().process_receipt(receipt)[0]["args"]["bugId"]
    print(f"Committed bug #{bug_id}, tx: {tx_hash.hex()}")

    # 5. Wait for confirmation then reveal immediately
    time.sleep(3)  # Wait for block confirmation

    nonce += 1
    reveal_tx = bug_submission.functions.revealBug(
        bug_id, encrypted_cid, salt
    ).build_transaction({
        "from": account.address,
        "nonce": nonce,
        "gas": 200_000,
    })
    signed = account.sign_transaction(reveal_tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    w3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"Revealed bug #{bug_id}, tx: {tx_hash.hex()}")

    return {"bug_id": bug_id, "encrypted_cid": encrypted_cid, "salt": salt.hex()}
