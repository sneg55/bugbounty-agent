"""Tests for protocol triage module."""
import json
from unittest.mock import patch

from protocol.triage import triage_submission, _decide_action, _parse_triage_response


# --- _decide_action unit tests ---

def test_accept_when_valid_and_severity_matches():
    result = {"valid": True, "estimated_severity": "HIGH", "confidence": 0.9, "reasoning": "real vuln"}
    assert _decide_action(result, 3) == "ACCEPT"  # claimed HIGH=3, estimated HIGH → match


def test_accept_when_severity_within_one_tier():
    result = {"valid": True, "estimated_severity": "MEDIUM", "confidence": 0.8, "reasoning": "close enough"}
    assert _decide_action(result, 3) == "ACCEPT"  # claimed HIGH=3, estimated MEDIUM=2 → diff=1 → accept


def test_dispute_when_severity_mismatch_two_tiers():
    result = {"valid": True, "estimated_severity": "LOW", "confidence": 0.8, "reasoning": "over-claimed"}
    assert _decide_action(result, 4) == "DISPUTE"  # claimed CRITICAL=4, estimated LOW=1 → diff=3


def test_dispute_when_invalid():
    result = {"valid": False, "estimated_severity": "CRITICAL", "confidence": 0.9, "reasoning": "not real"}
    assert _decide_action(result, 4) == "DISPUTE"  # invalid → always dispute


def test_dispute_on_unknown_severity():
    result = {"valid": True, "estimated_severity": "GARBAGE", "confidence": 0.5, "reasoning": "?"}
    assert _decide_action(result, 3) == "DISPUTE"  # unknown maps to 0, diff=3


# --- _parse_triage_response tests ---

def test_parse_plain_json():
    raw = '{"valid": true, "estimated_severity": "high", "confidence": 0.85, "reasoning": "reentrancy found"}'
    result = _parse_triage_response(raw)
    assert result["valid"] is True
    assert result["estimated_severity"] == "HIGH"  # normalized to uppercase
    assert result["confidence"] == 0.85
    assert "reentrancy" in result["reasoning"]


def test_parse_json_in_code_block():
    raw = """```json
{"valid": false, "estimated_severity": "LOW", "confidence": 0.3, "reasoning": "not exploitable"}
```"""
    result = _parse_triage_response(raw)
    assert result["valid"] is False
    assert result["estimated_severity"] == "LOW"


def test_parse_malformed_raises():
    try:
        _parse_triage_response("this is not json at all")
        assert False, "Should have raised"
    except (json.JSONDecodeError, ValueError, IndexError):
        pass  # expected


# --- triage_submission integration tests (mocked inference) ---

@patch("protocol.triage.complete")
def test_triage_accept_matching_severity(mock_complete):
    mock_complete.return_value = json.dumps({
        "valid": True,
        "estimated_severity": "CRITICAL",
        "confidence": 0.95,
        "reasoning": "Reentrancy allows fund drain",
    })

    report = {"contract": "Vault", "finding": "reentrancy in withdraw", "severity": "CRITICAL", "strategy": "reenter"}
    result = triage_submission(report, "contract Vault { ... }", claimed_severity=4)

    assert result["action"] == "ACCEPT"
    assert result["valid"] is True
    assert result["estimated_severity"] == "CRITICAL"
    mock_complete.assert_called_once()


@patch("protocol.triage.complete")
def test_triage_dispute_severity_mismatch(mock_complete):
    mock_complete.return_value = json.dumps({
        "valid": True,
        "estimated_severity": "LOW",
        "confidence": 0.7,
        "reasoning": "Minor gas issue, not critical",
    })

    report = {"contract": "Token", "finding": "gas optimization", "severity": "CRITICAL", "strategy": "n/a"}
    result = triage_submission(report, "contract Token { ... }", claimed_severity=4)

    assert result["action"] == "DISPUTE"
    assert result["valid"] is True
    assert result["estimated_severity"] == "LOW"


@patch("protocol.triage.complete")
def test_triage_dispute_invalid_submission(mock_complete):
    mock_complete.return_value = json.dumps({
        "valid": False,
        "estimated_severity": "INVALID",
        "confidence": 0.9,
        "reasoning": "Function does not exist in contract",
    })

    report = {"contract": "Token", "finding": "nonexistent flaw", "severity": "HIGH", "strategy": "n/a"}
    result = triage_submission(report, "contract Token { ... }", claimed_severity=3)

    assert result["action"] == "DISPUTE"
    assert result["valid"] is False


@patch("protocol.triage.complete")
def test_triage_fallback_on_malformed_response(mock_complete):
    mock_complete.return_value = "I'm not valid JSON sorry"

    report = {"contract": "Vault", "finding": "something", "severity": "HIGH", "strategy": "n/a"}
    result = triage_submission(report, "contract Vault { ... }", claimed_severity=3)

    assert result["action"] == "DISPUTE"
    assert result["valid"] is False
    assert "failed" in result["reasoning"].lower() or "defaulting" in result["reasoning"].lower()


@patch("protocol.triage.complete")
def test_triage_fallback_on_exception(mock_complete):
    mock_complete.side_effect = ConnectionError("Venice API down")

    report = {"contract": "Vault", "finding": "something", "severity": "HIGH", "strategy": "n/a"}
    result = triage_submission(report, "contract Vault { ... }", claimed_severity=3)

    assert result["action"] == "DISPUTE"
    assert result["valid"] is False


# --- Objective verification tests ---

def test_triage_dispute_on_poc_failure():
    """PoC failed = always dispute, no LLM call needed."""
    report = {"contract": "Vault", "finding": "reentrancy", "severity": "CRITICAL", "strategy": "reenter"}
    result = triage_submission(
        report, "contract Vault { ... }", claimed_severity=4,
        exploit_succeeded=False,
    )

    assert result["action"] == "DISPUTE"
    assert result["valid"] is False
    assert result["confidence"] == 1.0
    assert "failed" in result["reasoning"].lower() or "PoC" in result["reasoning"]


@patch("protocol.triage.complete")
def test_triage_accept_with_poc_success(mock_complete):
    """PoC succeeded + LLM agrees = accept."""
    mock_complete.return_value = json.dumps({
        "valid": True,
        "estimated_severity": "CRITICAL",
        "confidence": 0.95,
        "reasoning": "Reentrancy confirmed by state diff",
    })

    report = {"contract": "Vault", "finding": "reentrancy", "severity": "CRITICAL", "strategy": "reenter"}
    result = triage_submission(
        report, "contract Vault { ... }", claimed_severity=4,
        exploit_succeeded=True,
        state_diff_summary="exploit=PASS, balanceChanges=2, storageChanges=1",
    )

    assert result["action"] == "ACCEPT"
    assert result["valid"] is True


@patch("protocol.triage.complete")
def test_triage_uses_verification_in_prompt(mock_complete):
    """Verify that PoC result appears in the prompt sent to the LLM."""
    mock_complete.return_value = json.dumps({
        "valid": True,
        "estimated_severity": "HIGH",
        "confidence": 0.8,
        "reasoning": "Valid based on state diff",
    })

    report = {"contract": "Token", "finding": "overflow", "severity": "HIGH", "strategy": "n/a"}
    triage_submission(
        report, "contract Token { ... }", claimed_severity=3,
        exploit_succeeded=True,
        state_diff_summary="exploit=PASS, balanceChanges=1",
    )

    # Check the prompt included verification data
    call_args = mock_complete.call_args
    user_message = call_args[1]["messages"][1]["content"] if "messages" in call_args[1] else call_args[0][0][1]["content"]
    assert "SUCCEEDED" in user_message
    assert "balanceChanges=1" in user_message
