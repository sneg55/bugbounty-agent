"""Severity evaluation via Venice private inference."""
import json

from common.inference import complete

RUBRIC = """
CRITICAL (4): Direct loss of funds, consensus failure, or permanent bricking
              of core contracts. Exploitable with no or minimal prerequisites.

HIGH (3):     Indirect fund loss, significant DoS (>1 hour), unauthorized
              privilege escalation to admin-equivalent roles. Exploitable
              with moderate prerequisites.

MEDIUM (2):   Limited fund loss (<$10k), temporary DoS (<1 hour), state
              corruption recoverable by admin action. Requires specific
              conditions.

LOW (1):      Informational findings, gas optimizations, best-practice
              violations with no direct exploit path.

INVALID (0):  Exploit failed, didn't compile, targeted wrong contract,
              or out of scope.
"""

EVAL_PROMPT = """You are a smart contract security arbiter.
Evaluate the following state diff against the severity rubric.
Respond with ONLY a single integer:
0 = INVALID (exploit failed or out of scope)
1 = LOW
2 = MEDIUM
3 = HIGH
4 = CRITICAL
No other text."""


def evaluate_severity(
    state_impact: dict,
    model: str | None = None,
    temperature: float = 0.0,
    max_retries: int = 1,
) -> int:
    """Evaluate severity from State Impact JSON. Returns integer 0-4."""
    for attempt in range(max_retries + 1):
        response = complete(
            messages=[
                {"role": "system", "content": EVAL_PROMPT},
                {"role": "user", "content": f"RUBRIC:\n{RUBRIC}\n\nSTATE DIFF:\n{json.dumps(state_impact, indent=2)}"},
            ],
            model=model,
            temperature=temperature,
            max_tokens=4,
        )

        # Parse integer
        cleaned = response.strip()
        try:
            severity = int(cleaned)
            if 0 <= severity <= 4:
                return severity
        except ValueError:
            pass

        if attempt < max_retries:
            continue

    raise ValueError(f"Failed to parse severity from arbiter output: {response}")
