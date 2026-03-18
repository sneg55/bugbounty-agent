from eth_abi import encode
from web3 import Web3

from hunter.submitter import compute_commit_hash


def test_compute_commit_hash():
    """Verify commit hash matches Solidity's keccak256(abi.encode(...))."""
    encrypted_cid = "ipfs://QmTest123"
    hunter_agent_id = 42
    salt = bytes.fromhex("aa" * 32)

    result = compute_commit_hash(encrypted_cid, hunter_agent_id, salt)

    # Must match Solidity: keccak256(abi.encode(string, uint256, bytes32))
    # abi.encode uses ABI standard encoding (NOT packed), so we use eth_abi.encode
    encoded = encode(["string", "uint256", "bytes32"], [encrypted_cid, hunter_agent_id, salt])
    expected = Web3.keccak(encoded)
    assert result == expected
