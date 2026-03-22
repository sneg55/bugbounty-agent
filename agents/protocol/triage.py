"""Protocol triage: AI-powered accept/dispute decision for bug submissions."""
import json

from common.inference import complete

SEVERITY_LABELS = ["INVALID", "LOW", "MEDIUM", "HIGH", "CRITICAL"]
SEVERITY_MAP = {"INVALID": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}

# Accept if estimated severity is within 1 tier of claimed
SEVERITY_TOLERANCE = 1

TRIAGE_SYSTEM_PROMPT = """You are a smart contract security expert performing triage on a bug bounty submission.

Given a bug report and the target contract source code, assess:
1. Is this a real, exploitable vulnerability in the given contract?
2. What severity level would you assign? (LOW, MEDIUM, HIGH, CRITICAL)
3. How confident are you? (0.0 to 1.0)

Respond with ONLY a JSON object (no markdown, no explanation outside JSON):
{
    "valid": true/false,
    "estimated_severity": "LOW" | "MEDIUM" | "HIGH" | "CRITICAL",
    "confidence": 0.0-1.0,
    "reasoning": "Brief explanation of your assessment"
}

Severity guidelines:
- CRITICAL: Direct fund loss, privilege escalation allowing drain
- HIGH: Significant fund loss under specific conditions, access control bypass
- MEDIUM: Limited fund loss, griefing, DoS of core functionality
- LOW: Minor issues, gas optimizations, informational findings"""


def triage_submission(
    report: dict,
    scope_source: str,
    claimed_severity: int,
) -> dict:
    """
    Assess a bug report via AI inference.

    Args:
        report: The hunter's bug report dict with keys: contract, finding, severity, strategy
        scope_source: The Solidity source code of the target contract
        claimed_severity: Hunter's claimed severity (1=LOW, 2=MEDIUM, 3=HIGH, 4=CRITICAL)

    Returns:
        {
            "valid": bool,
            "estimated_severity": str,  # e.g. "HIGH"
            "confidence": float,        # 0.0-1.0
            "reasoning": str,
            "action": str,              # "ACCEPT" or "DISPUTE"
        }
    """
    prompt = _build_triage_prompt(report, scope_source, claimed_severity)

    try:
        raw = complete(
            messages=[
                {"role": "system", "content": TRIAGE_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
            max_tokens=1000,
        )
        result = _parse_triage_response(raw)
    except Exception:
        # Safe fallback: dispute on any failure
        result = {
            "valid": False,
            "estimated_severity": "INVALID",
            "confidence": 0.0,
            "reasoning": "Triage failed — defaulting to dispute",
        }

    # Decide accept vs dispute
    action = _decide_action(result, claimed_severity)
    result["action"] = action
    return result


def _decide_action(result: dict, claimed_severity: int) -> str:
    """Accept if valid and severity within tolerance; dispute otherwise."""
    if not result.get("valid", False):
        return "DISPUTE"

    estimated = SEVERITY_MAP.get(result.get("estimated_severity", "").upper(), 0)
    if abs(estimated - claimed_severity) <= SEVERITY_TOLERANCE:
        return "ACCEPT"

    return "DISPUTE"


def _build_triage_prompt(report: dict, scope_source: str, claimed_severity: int) -> str:
    claimed_label = SEVERITY_LABELS[claimed_severity] if 0 <= claimed_severity < len(SEVERITY_LABELS) else "UNKNOWN"

    return f"""## Bug Report

**Contract:** {report.get('contract', 'unknown')}
**Finding:** {report.get('finding', 'N/A')}
**Claimed Severity:** {claimed_label}
**Attack Strategy:** {report.get('strategy', 'N/A')}

## Target Contract Source

```solidity
{scope_source[:8000]}
```

Assess this bug report. Is the described vulnerability real and exploitable in the given contract? What severity would you assign?"""


def _parse_triage_response(raw: str) -> dict:
    """Parse the LLM's JSON response. Raises on malformed output."""
    # Try to extract JSON from the response (LLM may wrap in markdown code blocks)
    text = raw.strip()
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()

    data = json.loads(text)

    return {
        "valid": bool(data.get("valid", False)),
        "estimated_severity": str(data.get("estimated_severity", "INVALID")).upper(),
        "confidence": float(data.get("confidence", 0.0)),
        "reasoning": str(data.get("reasoning", "")),
    }
