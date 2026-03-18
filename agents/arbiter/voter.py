"""Blind commit-reveal voting on-chain."""
import os
import secrets

from web3 import Web3

from common.contracts import get_web3, get_all_contracts


def compute_vote_hash(severity: int, salt: bytes) -> bytes:
    """Compute vote hash matching Solidity's keccak256(abi.encode(uint8, bytes32)).

    IMPORTANT: Uses eth_abi.encode (ABI standard encoding), NOT Web3.solidity_keccak
    which uses abi.encodePacked. Must match the Solidity contract's abi.encode.
    """
    from eth_abi import encode
    encoded = encode(["uint8", "bytes32"], [severity, salt])
    return Web3.keccak(encoded)


def commit_and_reveal_vote(bug_id: int, severity: int, arbiter_key_env: str):
    """Full commit-reveal voting flow."""
    w3 = get_web3()
    contracts = get_all_contracts(w3)
    private_key = os.getenv(arbiter_key_env)
    account = w3.eth.account.from_key(private_key)
    arbiter_contract = contracts["arbiterContract"]

    salt = secrets.token_bytes(32)
    vote_hash = compute_vote_hash(severity, salt)

    # Commit
    nonce = w3.eth.get_transaction_count(account.address)
    tx = arbiter_contract.functions.commitVote(bug_id, vote_hash).build_transaction({
        "from": account.address, "nonce": nonce, "gas": 200_000,
    })
    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    w3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"  Committed vote for bug #{bug_id}")

    # Reveal
    nonce += 1
    tx = arbiter_contract.functions.revealVote(bug_id, severity, salt).build_transaction({
        "from": account.address, "nonce": nonce, "gas": 200_000,
    })
    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    w3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"  Revealed vote for bug #{bug_id}: severity={severity}")

    return {"severity": severity, "salt": salt.hex()}
