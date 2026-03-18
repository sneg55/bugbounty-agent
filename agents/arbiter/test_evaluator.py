from unittest.mock import patch

from arbiter.evaluator import evaluate_severity

SAMPLE_STATE_IMPACT = {
    "bugId": 1,
    "claimedSeverity": 4,
    "execution": {"exploitSucceeded": True, "txReverted": False, "outOfScope": False},
    "balanceChanges": [{"holderLabel": "Vault", "deltaUSD": "-10000000"}],
    "impactFlags": {"directFundLoss": True, "fundLossUSD": 10000000},
}


@patch("arbiter.evaluator.complete")
def test_evaluate_severity_returns_integer(mock_complete):
    mock_complete.return_value = "4"
    severity = evaluate_severity(SAMPLE_STATE_IMPACT)
    assert severity == 4


@patch("arbiter.evaluator.complete")
def test_evaluate_severity_retries_on_bad_output(mock_complete):
    mock_complete.side_effect = ["I think this is CRITICAL", "4"]
    severity = evaluate_severity(SAMPLE_STATE_IMPACT)
    assert severity == 4
