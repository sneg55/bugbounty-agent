---
name: keeper-service
description: Operates the Keeper Service — monitors the 72-hour dispute window and calls autoAcceptOnTimeout for submissions where the protocol failed to respond. Use when working with timeout handling, auto-accept, or ensuring hunters get paid when the protocol is offline.
---

# Keeper Service

Guarantees hunters get paid when the protocol goes offline.

## Quick Start

```bash
python -m keeper.timeout_keeper
```

## How It Works

```
BugRevealed event
  │
  ├─ Track submission revealedAt timestamp
  ├─ Check: status == Revealed AND protocolResponse == None
  ├─ If now > revealedAt + 72 hours:
  │   └─ Call autoAcceptOnTimeout(bugId)
  │       └─ Pays hunter at claimed severity + returns stake
  └─ Else: skip, check again next cycle (30s)
```

## Key Design Points

- **Permissionless:** Any funded wallet can run it. No special role needed.
- **Safe to run multiple instances:** `autoAcceptOnTimeout` reverts if already called.
- **Uses event indexing:** Watches `BugRevealed` events, not full table scans.
- **Pays at claimed severity:** Since no triage happened (protocol's fault), the hunter's claim stands.

## File

| File | Purpose |
|------|---------|
| `agents/keeper/timeout_keeper.py` | Single-file keeper service |

## Environment Variables

```
KEEPER_PRIVATE_KEY=0x...     # Any funded wallet (falls back to EXECUTOR_PRIVATE_KEY)
```

## When to Run

Run alongside the other agents. Critical for the 72-hour auto-accept guarantee — without the keeper, submissions where the protocol is offline would sit indefinitely in Revealed state until someone manually calls `autoAcceptOnTimeout`.
