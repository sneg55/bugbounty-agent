# agents/executor/state_diff.py
"""Produces State Impact JSON from fork execution results."""
import hashlib
import json
import re


def parse_forge_trace(trace_output: str) -> tuple[list, list]:
    """Parse balance and storage changes from forge verbose output or JSON traces.

    Returns a tuple of (balance_changes, storage_changes) where:
      balance_changes: list of {"address": str, "deltaWei": str, "deltaUSD": str}
      storage_changes: list of {"contract": str, "slot": str, "slotLabel": str, "before": str, "after": str}
    """
    balance_changes = []
    storage_changes = []

    # Parse JSON output from `forge test --json`
    try:
        data = json.loads(trace_output)
        if isinstance(data, dict):
            for _test_name, test_data in data.items():
                if not isinstance(test_data, dict):
                    continue
                for trace in test_data.get("traces", []):
                    _extract_from_trace_node(trace, balance_changes, storage_changes)
        return balance_changes, storage_changes
    except (json.JSONDecodeError, ValueError):
        pass

    # Fallback: parse human-readable forge -vvv output
    # Match ETH balance changes: "Balance: X -> Y (address)"
    balance_pattern = re.compile(
        r"Balance:\s+(0x[0-9a-fA-F]+|\d+)\s+->\s+(0x[0-9a-fA-F]+|\d+)"
        r"(?:\s+\(([^)]+)\))?"
    )
    for match in balance_pattern.finditer(trace_output):
        before_raw = match.group(1)
        after_raw = match.group(2)
        address = match.group(3) or "unknown"
        try:
            before_wei = int(before_raw, 16) if before_raw.startswith("0x") else int(before_raw)
            after_wei = int(after_raw, 16) if after_raw.startswith("0x") else int(after_raw)
            delta_wei = after_wei - before_wei
            balance_changes.append({
                "address": address,
                "deltaWei": str(delta_wei),
                "deltaUSD": "0",  # USD conversion requires external price feed
            })
        except ValueError:
            continue

    # Match storage slot changes: "slot 0x... | before: 0x... | after: 0x..."
    storage_pattern = re.compile(
        r"slot\s+(0x[0-9a-fA-F]+)\s*\|"
        r"\s*before:\s*(0x[0-9a-fA-F]+)\s*\|"
        r"\s*after:\s*(0x[0-9a-fA-F]+)"
        r"(?:\s*\[([^\]]+)\])?"
        r"(?:\s*@\s*(0x[0-9a-fA-F]+))?",
        re.IGNORECASE,
    )
    for match in storage_pattern.finditer(trace_output):
        slot = match.group(1)
        before = match.group(2)
        after = match.group(3)
        label = match.group(4) or ""
        contract = match.group(5) or "unknown"
        if before != after:
            storage_changes.append({
                "contract": contract,
                "slot": slot,
                "slotLabel": label,
                "before": before,
                "after": after,
            })

    # Also match forge's compact state-change lines:
    # "  [0x1234] Slot changed: 0xABC -> 0xDEF"
    compact_storage = re.compile(
        r"\[(0x[0-9a-fA-F]+)\]\s+Slot changed:\s+(0x[0-9a-fA-F]+)\s*->\s*(0x[0-9a-fA-F]+)",
        re.IGNORECASE,
    )
    for match in compact_storage.finditer(trace_output):
        contract = match.group(1)
        before = match.group(2)
        after = match.group(3)
        if before != after:
            storage_changes.append({
                "contract": contract,
                "slot": "unknown",
                "slotLabel": "",
                "before": before,
                "after": after,
            })

    return balance_changes, storage_changes


def _extract_from_trace_node(node: object, balance_changes: list, storage_changes: list) -> None:
    """Recursively extract balance and storage changes from a forge JSON trace node."""
    if not isinstance(node, dict):
        return

    # Some forge JSON schemas include state_diff or stateDiff at the top level
    state_diff = node.get("state_diff") or node.get("stateDiff") or {}
    for address, diff in state_diff.items():
        balance_diff = diff.get("balance")
        if isinstance(balance_diff, dict):
            before = balance_diff.get("from", "0x0")
            after = balance_diff.get("to", "0x0")
            try:
                before_int = int(before, 16) if isinstance(before, str) and before.startswith("0x") else int(before)
                after_int = int(after, 16) if isinstance(after, str) and after.startswith("0x") else int(after)
                delta = after_int - before_int
                if delta != 0:
                    balance_changes.append({
                        "address": address,
                        "deltaWei": str(delta),
                        "deltaUSD": "0",
                    })
            except (ValueError, TypeError):
                pass

        storage_diff = diff.get("storage") or {}
        for slot, slot_diff in storage_diff.items():
            if isinstance(slot_diff, dict):
                before = slot_diff.get("from", "0x0")
                after = slot_diff.get("to", "0x0")
                if before != after:
                    storage_changes.append({
                        "contract": address,
                        "slot": slot,
                        "slotLabel": "",
                        "before": before,
                        "after": after,
                    })

    # Recurse into child calls
    for child in node.get("calls", []):
        _extract_from_trace_node(child, balance_changes, storage_changes)


def compute_impact_flags(balance_changes: list, storage_changes: list) -> dict:
    """Derive impact flags from state changes."""
    fund_loss = 0
    direct_fund_loss = False
    unauthorized_role_change = False

    for bc in balance_changes:
        try:
            delta = int(bc.get("deltaWei", "0"))
        except (ValueError, TypeError):
            delta = 0
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
