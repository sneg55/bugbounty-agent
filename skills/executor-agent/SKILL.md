---
name: executor-agent
description: Operates the Executor Agent — verifies bug submissions by running PoCs in forked chains, produces objective state diffs, and registers results on-chain for arbitration. Use when working with PoC execution, state impact generation, fork runner, or the executor verification pipeline.
---

# Executor Agent

Verifies ALL revealed submissions via PoC execution, then registers on-chain only after dispute.

## Quick Start

```bash
python -m executor.service
```

## Two-Phase Pipeline

```
Phase A: VERIFY (runs for ALL revealed submissions)
  BugRevealed event
    ├─ Decrypt payload (executor ECIES key)
    ├─ Run PoC in Anvil fork
    ├─ Parse balance/storage changes from trace
    ├─ Build State Impact JSON
    ├─ Upload to IPFS
    └─ Cache result in .verification_cache.json

Phase B: REGISTER (runs only after protocol disputes)
  SubmissionDisputed event
    ├─ Read cached verification
    ├─ Submit to ValidationRegistry
    ├─ Register on ArbiterContract (triggers jury selection)
    └─ Wait for resolution → generate patch guidance if HIGH+
```

## Key Files

| File | Purpose |
|------|---------|
| `agents/executor/service.py` | Main loop + verify_bug/register_on_chain split |
| `agents/executor/fork_runner.py` | Runs PoC in Anvil fork, captures trace |
| `agents/executor/state_diff.py` | Parses traces, builds State Impact JSON |
| `agents/executor/patch_guidance.py` | Venice AI: generates remediation guidance |
| `agents/executor/abi_resolver.py` | Resolves contract ABIs from Foundry artifacts |

## Verification Cache

`verify_bug()` writes results to `.verification_cache.json`:

```json
{
  "1": {
    "bug_id": 1,
    "exploit_succeeded": true,
    "state_impact_cid": "ipfs://Qm...",
    "req_hash": "0xabcdef...",
    "state_impact": { ... },
    "poc_source": "...",
    "report": { ... }
  }
}
```

The protocol agent reads this cache to make evidence-based triage decisions. The `exploit_succeeded` field is the hard signal — if false, the protocol always disputes.

## State Impact JSON

Objective, machine-readable format consumed by arbiters:

```json
{
  "bugId": 1,
  "exploitSucceeded": true,
  "txReverted": false,
  "gasUsed": 150000,
  "balanceChanges": [
    {"address": "0x...", "deltaWei": "-1000000000000000000", "deltaUSD": "0"}
  ],
  "storageChanges": [
    {"contract": "0x...", "slot": "0x0", "before": "0x01", "after": "0x00"}
  ]
}
```

Fund-loss detection uses `deltaWei` (not `deltaUSD` which requires a price oracle).

## Environment Variables

```
EXECUTOR_PRIVATE_KEY=0x...        # Ethereum wallet
EXECUTOR_ECIES_PRIVATE_KEY=0x...  # Decryption key for hunter payloads
```

## Workflow: Debugging a Failed PoC

1. Check `.verification_cache.json` for the bug ID
2. Read `exploit_succeeded` and `state_impact`
3. If PoC failed, examine the fork runner trace in `fork_result["stdout"]`
4. Common issues: wrong contract address, ABI mismatch, insufficient fork block
