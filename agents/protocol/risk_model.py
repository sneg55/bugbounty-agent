"""Hardcoded risk model for demo. Returns tier amounts in USDC base units (6 decimals)."""


def get_default_tiers() -> dict:
    """Default bounty tier amounts."""
    return {
        "critical": 25_000 * 10**6,
        "high": 10_000 * 10**6,
        "medium": 2_000 * 10**6,
        "low": 500 * 10**6,
    }


def get_default_funding() -> int:
    """Default total bounty funding."""
    return 50_000 * 10**6
