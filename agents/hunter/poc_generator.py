"""Generate Foundry PoC test scripts from vulnerability analysis."""
import re

from common.inference import complete

POC_PROMPT = """You are an expert smart contract exploit developer.

Generate a complete Foundry test file that demonstrates the exploit.
The test should:
1. Fork the chain at the current block
2. Set up the attacker contract (if needed)
3. Execute the exploit
4. Assert that funds were drained / access was gained / state was corrupted

Use these imports:
- forge-std/Test.sol

The target contract is at address: {contract_address}

Output ONLY the Solidity code, wrapped in ```solidity ... ``` markers.
"""


def generate_poc(finding: dict, contract_source: str, contract_address: str) -> str:
    """Generate a Foundry PoC test script for a vulnerability finding."""
    response = complete(
        messages=[
            {"role": "system", "content": POC_PROMPT.format(contract_address=contract_address)},
            {
                "role": "user",
                "content": (
                    f"VULNERABILITY:\n{finding['check']} - {finding.get('strategy', '')}\n\n"
                    f"CONTRACT SOURCE:\n{contract_source}"
                ),
            },
        ],
        temperature=0.0,
        max_tokens=4000,
    )

    # Extract Solidity code from markdown fences
    match = re.search(r"```solidity\n(.*?)```", response, re.DOTALL)
    if match:
        return match.group(1).strip()

    # If no fences, try to find pragma
    if "pragma solidity" in response:
        start = response.index("pragma solidity")
        return response[start:].strip()

    return response
