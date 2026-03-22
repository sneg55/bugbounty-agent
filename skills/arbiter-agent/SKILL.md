---
name: arbiter-agent
description: Operates the Arbiter Agent — evaluates State Impact JSON via Venice AI inference, commits and reveals severity votes using commit-reveal scheme. Use when working with jury selection, severity evaluation, arbiter voting, or the arbitration flow.
---

# Arbiter Agent

Evaluates state diffs and votes on severity via blind commit-reveal.

## Quick Start

```bash
# Run arbiter slot 1 (each slot uses a different model/temperature)
python -m arbiter.agent --slot 1

# Slots: 1 (llama-3.3-70b, temp=0.0), 2 (llama-3.3-70b, temp=0.1), 3 (mistral-large, temp=0.0)
```

## Pipeline

```
JurySelected event (checked via event args, not full scan)
  │
  ├─ Check if this arbiter's agentId is in jurors[3]
  ├─ Fetch State Impact JSON from IPFS
  ├─ Venice AI: evaluate severity (0=INVALID..4=CRITICAL)
  │
  ├─ commitVote(bugId, keccak256(abi.encode(severity, salt)))
  └─ revealVote(bugId, severity, salt)
      │
      └─ 3rd reveal auto-triggers resolution
```

## Key Files

| File | Purpose |
|------|---------|
| `agents/arbiter/agent.py` | Main loop: watches JurySelected, drives evaluation + voting |
| `agents/arbiter/evaluator.py` | Venice AI: State Impact JSON → severity score |
| `agents/arbiter/voter.py` | Commit-reveal vote transactions |

## Model Diversity

Three arbiter slots use different models/temperatures to reduce correlated errors:

| Slot | Model | Temperature | Key Env |
|------|-------|-------------|---------|
| 1 | llama-3.3-70b | 0.0 | `ARBITER_1_PRIVATE_KEY` |
| 2 | llama-3.3-70b | 0.1 | `ARBITER_2_PRIVATE_KEY` |
| 3 | mistral-large | 0.0 | `ARBITER_3_PRIVATE_KEY` |

## Prompt-Injection Firewall

Arbiters ONLY see State Impact JSON (objective, machine-generated). They never see the hunter's prose report. This prevents hunters from manipulating arbiter decisions through persuasive writing.

## Jury Selection

Score-weighted random sampling via `block.prevrandao`:
- Each arbiter's weight = `consensus_aligned` feedback count + 1
- Zero-score arbiters still have a chance (weight 1)
- Conflict-of-interest exclusion: hunter and protocol owners excluded

**Hackathon trade-off:** `prevrandao` is validator-influenceable. Production would use Chainlink VRF or commit-reveal randomness.

## Resolution

- **3 reveals:** Median severity. Majority-invalid check (2+ INVALID votes → invalid)
- **2 reveals:** Conservative minimum of the two
- **0-1 reveals:** Timeout — stake returned to hunter (arbiter failure)

## Reputation Feedback

After resolution:
- Consensus-aligned arbiters: +10 reputation
- Deviated arbiters: -5 reputation
- No-show arbiters: -20 reputation
