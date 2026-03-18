import json
from pathlib import Path
from unittest.mock import patch

from common.contracts import load_abi, get_web3


def test_load_abi_reads_foundry_artifact():
    """Verify load_abi reads from contracts/out/ and extracts abi key."""
    contracts_out = Path(__file__).parent.parent.parent / "contracts" / "out"
    # MockUSDC should exist after forge build
    abi = load_abi("MockUSDC")
    assert isinstance(abi, list)
    assert len(abi) > 0
    # Should have mint function
    fn_names = [item["name"] for item in abi if item.get("type") == "function"]
    assert "mint" in fn_names


def test_get_web3_returns_provider():
    w3 = get_web3()
    assert w3.provider is not None
    assert hasattr(w3.provider, 'endpoint_uri')
