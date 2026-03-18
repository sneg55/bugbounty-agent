# agents/executor/test_patch_guidance.py
from unittest.mock import patch

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
