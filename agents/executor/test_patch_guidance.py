# agents/executor/test_patch_guidance.py
import json
from unittest.mock import patch, MagicMock, call

from executor.patch_guidance import generate_patch_guidance


@patch("executor.patch_guidance.complete")
def test_generate_patch_guidance(mock_complete):
    mock_complete.return_value = '{"affectedFunctions": ["withdraw"], "recommendedChanges": [{"function": "withdraw", "change": "Add nonReentrant modifier"}], "verificationTests": ["calling withdraw with reentrant callback should revert"]}'

    result = generate_patch_guidance(
        poc_source="contract Exploit { ... }",
        target_source="contract Vault { function withdraw() ... }",
        state_diff={"impactFlags": {"directFundLoss": True}},
    )
    assert "affectedFunctions" in result
    assert "withdraw" in result["affectedFunctions"]


@patch("executor.service.upload_json")
@patch("executor.service.encrypt")
@patch("executor.service.generate_patch_guidance")
@patch("executor.service._fetch_protocol_ecies_pubkey")
def test_handle_patch_guidance_encrypt_and_upload(
    mock_fetch_pubkey, mock_generate, mock_encrypt, mock_upload
):
    """Verify that _handle_patch_guidance encrypts guidance and uploads to IPFS."""
    from executor.service import _handle_patch_guidance

    guidance = {"affectedFunctions": ["transfer"], "recommendedChanges": [], "verificationTests": []}
    mock_fetch_pubkey.return_value = "mock-ecies-pubkey"
    mock_generate.return_value = guidance
    encrypted_payload = b"\xde\xad\xbe\xef"
    mock_encrypt.return_value = encrypted_payload
    mock_upload.return_value = "QmEncryptedGuidance"

    # Minimal mock objects
    mock_w3 = MagicMock()
    mock_w3.eth.get_transaction_count.return_value = 0
    mock_contracts = {
        "identityRegistry": MagicMock(),
        "arbiterContract": MagicMock(),
    }
    mock_tx = {"from": "0x1234", "nonce": 0, "gas": 200_000}
    mock_contracts["arbiterContract"].functions.registerPatchGuidance.return_value.build_transaction.return_value = mock_tx
    mock_account = MagicMock()
    mock_account.address = "0x1234"
    mock_account.sign_transaction.return_value = MagicMock(raw_transaction=b"rawtx")
    mock_w3.eth.send_raw_transaction.return_value = b"txhash"

    deployments = {"agentIds": {"protocol": 1}}
    state_impact = {"validationRequestHash": "0xabcd"}

    _handle_patch_guidance(
        w3=mock_w3,
        contracts=mock_contracts,
        bug_id=7,
        deployments=deployments,
        poc_source="contract Exploit {}",
        target_source="contract Vault {}",
        state_impact=state_impact,
        account=mock_account,
    )

    # Verify encrypt was called with the pubkey and guidance bytes
    mock_encrypt.assert_called_once_with(
        b"mock-ecies-pubkey", json.dumps(guidance).encode()
    )

    # Verify upload was called with the encrypted payload
    mock_upload.assert_called_once_with({"encrypted": encrypted_payload.hex()})

    # Verify registerPatchGuidance was called with the returned CID
    mock_contracts["arbiterContract"].functions.registerPatchGuidance.assert_called_once_with(
        7, "QmEncryptedGuidance"
    )
