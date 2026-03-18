# agents/executor/abi_resolver.py
"""Labels storage slots and addresses from known ABIs."""
import json
from pathlib import Path
from typing import Optional


# Well-known address labels for common protocols
KNOWN_ADDRESSES: dict[str, str] = {
    "0x0000000000000000000000000000000000000000": "zero",
}

# Common storage slot labels derived from ERC-20 / OpenZeppelin patterns
KNOWN_SLOT_LABELS: dict[str, str] = {
    "0x0000000000000000000000000000000000000000000000000000000000000000": "slot0",
    "0x0000000000000000000000000000000000000000000000000000000000000001": "slot1",
    "0x0000000000000000000000000000000000000000000000000000000000000002": "slot2",
    # OpenZeppelin Ownable: keccak256('owner') style mappings are dynamic,
    # but the canonical _owner slot is slot 0 in OwnableUpgradeable (proxy pattern).
}

# Variable name hints derived from common ABI patterns
_ROLE_SLOT_NAMES = frozenset({"owner", "admin", "governance", "authority", "pendingOwner"})


def load_abi(abi_path: str | Path) -> list:
    """Load an ABI JSON file and return the list of entries."""
    with open(abi_path) as f:
        data = json.load(f)
    # Support both raw arrays and {"abi": [...]} wrappers
    if isinstance(data, list):
        return data
    return data.get("abi", [])


def label_address(address: str, extra_labels: Optional[dict[str, str]] = None) -> str:
    """Return a human-readable label for an address, or the address itself."""
    addr_lower = address.lower()
    combined = {**KNOWN_ADDRESSES, **(extra_labels or {})}
    for known, label in combined.items():
        if known.lower() == addr_lower:
            return label
    return address


def label_slot(slot_hex: str, abi_entries: Optional[list] = None) -> str:
    """Return a human-readable label for a storage slot.

    Attempts to match the slot against known canonical slot positions derived
    from the provided ABI's state-variable ordering (Solidity storage layout).
    Falls back to the raw hex slot if no match is found.
    """
    slot_normalized = slot_hex.lower()
    if slot_normalized in KNOWN_SLOT_LABELS:
        return KNOWN_SLOT_LABELS[slot_normalized]

    if abi_entries:
        # Heuristic: state variables appear as inputs on constructor or as named
        # storage slots.  We derive slot indices from non-function/non-event entries.
        state_vars = [
            entry for entry in abi_entries
            if entry.get("type") not in ("function", "event", "error", "constructor")
            and entry.get("name")
        ]
        for idx, var in enumerate(state_vars):
            candidate = hex(idx).replace("0x", "").zfill(64)
            if candidate == slot_normalized.replace("0x", "").zfill(64):
                return var["name"]

    return slot_hex


def annotate_storage_changes(
    storage_changes: list,
    abi_entries: Optional[list] = None,
    address_labels: Optional[dict[str, str]] = None,
) -> list:
    """Attach human-readable labels to a list of storage change dicts.

    Each item in ``storage_changes`` is expected to have at least:
      - ``slot``: hex storage slot
      - ``before``: previous value (hex)
      - ``after``: new value (hex)

    Returns a new list with ``slotLabel``, ``beforeLabel``, and ``afterLabel``
    fields added.
    """
    annotated = []
    for change in storage_changes:
        slot = change.get("slot", "")
        before = change.get("before", "")
        after = change.get("after", "")

        slot_label = label_slot(slot, abi_entries)
        # If the value looks like an address (20-byte right-padded), label it
        before_label = _maybe_label_address(before, address_labels)
        after_label = _maybe_label_address(after, address_labels)

        annotated.append(
            {
                **change,
                "slotLabel": slot_label,
                "beforeLabel": before_label,
                "afterLabel": after_label,
            }
        )
    return annotated


def is_role_slot(slot_label: str) -> bool:
    """Return True if the slot label corresponds to a privileged role variable."""
    return slot_label.lower() in _ROLE_SLOT_NAMES


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _maybe_label_address(value: str, address_labels: Optional[dict[str, str]]) -> str:
    """If ``value`` looks like a padded address, attempt to label it."""
    stripped = value.lower().replace("0x", "")
    # A padded address is 64 hex chars where the first 24 are zeros
    if len(stripped) == 64 and stripped[:24] == "0" * 24:
        addr = "0x" + stripped[24:]
        return label_address(addr, address_labels)
    return value
