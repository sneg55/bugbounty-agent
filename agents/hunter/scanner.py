"""Slither integration for static analysis of Solidity contracts."""
import json
import subprocess
import tempfile
from pathlib import Path

IMPACT_ORDER = ["Informational", "Low", "Medium", "High", "Critical"]


def run_slither(contract_source: str, contract_filename: str = "Target.sol") -> dict:
    """Run Slither on a contract source string. Returns raw JSON output."""
    with tempfile.TemporaryDirectory() as tmpdir:
        contract_path = Path(tmpdir) / contract_filename
        contract_path.write_text(contract_source)

        result = subprocess.run(
            ["slither", str(contract_path), "--json", "-"],
            capture_output=True,
            text=True,
            cwd=tmpdir,
        )
        # Slither returns non-zero on findings, which is expected
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            return {"results": {"detectors": []}}


def parse_findings(slither_output: dict, min_impact: str = "Medium") -> list[dict]:
    """Filter Slither findings by minimum impact level."""
    min_idx = IMPACT_ORDER.index(min_impact)
    detectors = slither_output.get("results", {}).get("detectors", [])

    findings = []
    for d in detectors:
        impact = d.get("impact", "Informational")
        if impact in IMPACT_ORDER and IMPACT_ORDER.index(impact) >= min_idx:
            findings.append({
                "check": d.get("check", ""),
                "impact": impact,
                "confidence": d.get("confidence", ""),
                "description": d.get("description", ""),
            })
    return findings
