# agents/executor/test_state_diff.py
from executor.state_diff import build_state_impact_json, compute_impact_flags


def test_compute_impact_flags_fund_loss():
    balance_changes = [
        {"address": "0xVault", "deltaWei": "-1000000000000000000", "deltaUSD": "0"},
        {"address": "0xAttacker", "deltaWei": "+1000000000000000000", "deltaUSD": "0"},
    ]
    flags = compute_impact_flags(balance_changes, [])
    assert flags["directFundLoss"] is True
    assert flags["fundLossUSD"] == 1000000000000000000


def test_compute_impact_flags_role_change():
    storage_changes = [
        {"slotLabel": "owner", "before": "0xAdmin", "after": "0xAttacker"},
    ]
    flags = compute_impact_flags([], storage_changes)
    assert flags["unauthorizedRoleChange"] is True


def test_build_state_impact_json():
    result = build_state_impact_json(
        bug_id=1,
        bounty_id=1,
        hunter_agent_id=2,
        claimed_severity=4,
        target_contract="0x1234",
        fork_block=100,
        chain_id=84532,
        exploit_succeeded=True,
        tx_reverted=False,
        gas_used=450000,
        out_of_scope=False,
        balance_changes=[],
        storage_changes=[],
        executor_agent_id=6,
    )
    assert result["bugId"] == 1
    assert result["execution"]["exploitSucceeded"] is True
    assert "impactFlags" in result
