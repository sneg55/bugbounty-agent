from pathlib import Path
from hunter.scanner import run_slither, parse_findings


def test_parse_findings_filters_by_severity():
    """Test that parse_findings filters out low/informational."""
    raw_output = {
        "results": {
            "detectors": [
                {"check": "reentrancy-eth", "impact": "High", "confidence": "Medium",
                 "description": "Reentrancy in Vault.withdraw()", "elements": []},
                {"check": "naming-convention", "impact": "Informational", "confidence": "High",
                 "description": "Variable not in mixedCase", "elements": []},
                {"check": "unprotected-upgrade", "impact": "High", "confidence": "High",
                 "description": "Missing access control", "elements": []},
            ]
        }
    }
    findings = parse_findings(raw_output, min_impact="Medium")
    assert len(findings) == 2
    assert all(f["impact"] in ("High", "Medium", "Critical") for f in findings)
