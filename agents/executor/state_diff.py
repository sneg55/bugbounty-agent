# agents/executor/state_diff.py
"""Produces State Impact JSON from fork execution results."""
import hashlib
import json


def compute_impact_flags(balance_changes: list, storage_changes: list) -> dict:
    """Derive impact flags from state changes."""
    fund_loss = 0
    direct_fund_loss = False
    unauthorized_role_change = False

    for bc in balance_changes:
        delta = float(bc.get("deltaUSD", "0"))
        if delta < 0:
            direct_fund_loss = True
            fund_loss += abs(delta)

    for sc in storage_changes:
        label = sc.get("slotLabel", "").lower()
        if label in ("owner", "admin", "governance", "authority"):
            if sc.get("before") != sc.get("after"):
                unauthorized_role_change = True

    return {
        "directFundLoss": direct_fund_loss,
        "fundLossUSD": int(fund_loss),
        "contractBricked": False,  # Would need more analysis
        "unauthorizedRoleChange": unauthorized_role_change,
        "dosDetected": False,
        "oracleManipulation": False,
    }


def build_state_impact_json(
    bug_id: int,
    bounty_id: int,
    hunter_agent_id: int,
    claimed_severity: int,
    target_contract: str,
    fork_block: int,
    chain_id: int,
    exploit_succeeded: bool,
    tx_reverted: bool,
    gas_used: int,
    out_of_scope: bool,
    balance_changes: list,
    storage_changes: list,
    executor_agent_id: int,
) -> dict:
    """Build the State Impact JSON that arbiters evaluate."""
    impact_flags = compute_impact_flags(balance_changes, storage_changes)

    state_impact = {
        "bugId": bug_id,
        "bountyId": bounty_id,
        "hunterAgentId": hunter_agent_id,
        "claimedSeverity": claimed_severity,
        "execution": {
            "targetContract": target_contract,
            "forkBlock": fork_block,
            "chainId": chain_id,
            "exploitSucceeded": exploit_succeeded,
            "txReverted": tx_reverted,
            "gasUsed": gas_used,
            "outOfScope": out_of_scope,
        },
        "balanceChanges": balance_changes,
        "storageChanges": storage_changes,
        "impactFlags": impact_flags,
        "executorAgentId": executor_agent_id,
    }

    # Compute validation hash
    state_json = json.dumps(state_impact, sort_keys=True)
    state_impact["validationRequestHash"] = "0x" + hashlib.sha256(state_json.encode()).hexdigest()

    return state_impact
