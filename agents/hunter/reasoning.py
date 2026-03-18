"""LLM-powered vulnerability reasoning via Venice."""
import json

from common.inference import complete

ANALYSIS_PROMPT = """You are an expert smart contract security auditor.

Given the following Slither static analysis findings and the contract source code,
determine which findings are genuinely exploitable.

For each exploitable finding:
1. Classify severity: CRITICAL, HIGH, MEDIUM, or LOW
2. Describe a proof-of-concept strategy (what attacker contract to deploy, what calls to make)

Respond with valid JSON:
{
  "exploitable": [
    {
      "finding": "<slither check name>",
      "severity": "<CRITICAL|HIGH|MEDIUM|LOW>",
      "strategy": "<brief PoC strategy>"
    }
  ],
  "not_exploitable": ["<check names that are false positives>"]
}
"""


def analyze_findings(findings: list[dict], contract_source: str) -> dict:
    """Send findings + source to Venice for exploitability analysis."""
    findings_text = json.dumps(findings, indent=2)

    response = complete(
        messages=[
            {"role": "system", "content": ANALYSIS_PROMPT},
            {"role": "user", "content": f"CONTRACT SOURCE:\n{contract_source}\n\nSLITHER FINDINGS:\n{findings_text}"},
        ],
        temperature=0.0,
        max_tokens=2000,
    )

    try:
        return json.loads(response)
    except json.JSONDecodeError:
        # Try to extract JSON from response
        start = response.find("{")
        end = response.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(response[start:end])
        return {"exploitable": [], "not_exploitable": []}
