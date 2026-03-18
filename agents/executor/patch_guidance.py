# agents/executor/patch_guidance.py
"""Generate patch guidance via Venice private inference."""
import json

from common.inference import complete

PATCH_PROMPT = """You are a smart contract remediation advisor.
Given an exploit proof-of-concept and the target contract source,
generate specific patch guidance.

RULES:
- Specify which functions need changes and what checks to add.
- Do NOT describe the attack mechanism or exploit sequence.
- Do NOT include the exploit payload or attacker contract code.
- Focus only on defensive changes to the target contract.
- Output valid JSON matching this schema:

{
  "affectedFunctions": ["function1", "function2"],
  "recommendedChanges": [
    {"function": "...", "change": "...", "line": null}
  ],
  "verificationTests": ["test description 1", "test description 2"]
}
"""


def generate_patch_guidance(poc_source: str, target_source: str, state_diff: dict) -> dict:
    """Generate remediation guidance without exposing exploit details."""
    response = complete(
        messages=[
            {"role": "system", "content": PATCH_PROMPT},
            {
                "role": "user",
                "content": f"TARGET CONTRACT:\n{target_source}\n\nSTATE DIFF:\n{json.dumps(state_diff, indent=2)}",
            },
        ],
        temperature=0.0,
        max_tokens=2000,
    )

    try:
        return json.loads(response)
    except json.JSONDecodeError:
        start = response.find("{")
        end = response.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(response[start:end])
        return {"affectedFunctions": [], "recommendedChanges": [], "verificationTests": []}
