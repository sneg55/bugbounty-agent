---
name: protocol-agent
description: Operates the Protocol Agent — creates bounties with escrow, triages bug submissions via AI-powered accept/dispute decisions, and monitors resolution events. Use when working with bounty creation, submission triage, or the protocol agent's respond/watch commands.
---

# Protocol Agent

Creates bounties and makes evidence-based accept/dispute decisions on hunter submissions.

## Quick Start

```bash
# Create a bounty
python -m protocol.agent create-bounty --name "MyProtocol" --scope-uri "ipfs://scope-cid"

# Respond to submissions (AI triage)
python -m protocol.agent respond

# Watch for resolutions and patch guidance
python -m protocol.agent watch
```

## Architecture

```
BugRevealed event
  │
  ├─ Decrypt hunter report (ECIES, protocolEncrypted field)
  ├─ Poll verification cache (executor's PoC result)
  ├─ Venice AI triage: validity + severity assessment
  │
  ├─ PoC FAILED → DISPUTE (hard rule, no LLM override)
  ├─ Valid + severity within 1 tier → ACCEPT at min(claimed, estimated)
  └─ Invalid OR severity mismatch ≥ 2 tiers → DISPUTE
```

## Key Files

| File | Purpose |
|------|---------|
| `agents/protocol/agent.py` | Main agent: create-bounty, respond, watch commands |
| `agents/protocol/triage.py` | AI triage: Venice inference + decision logic |
| `agents/protocol/risk_model.py` | Default tier amounts and funding |

## Bounty Creation

```python
# Tier validation enforced on-chain:
# critical >= high >= medium >= low > 0
# funding >= critical
tiers = Tiers(critical=25000e6, high=10000e6, medium=2000e6, low=500e6)
```

The contract enforces tier ordering and minimum funding. See [bounty-validation.md](bounty-validation.md) for details.

## Triage Decision Logic

The `respond` command processes revealed submissions:

1. **Decrypt** — reads `protocolEncrypted` field from IPFS payload
2. **Wait for verification** — polls executor's `.verification_cache.json` (60s timeout)
3. **Triage** — sends report + scope + PoC result to Venice
4. **Decide** — accept at `min(claimed, estimated)` severity, or dispute

**Hard rules (skip LLM):**
- PoC execution failed → always DISPUTE
- Cannot decrypt report → always DISPUTE

**LLM-informed rules:**
- Valid + severity within 1 tier of claim → ACCEPT
- Invalid or severity mismatch ≥ 2 tiers → DISPUTE

## Environment Variables

```
PROTOCOL_AGENT_PRIVATE_KEY=0x...   # Ethereum wallet
PROTOCOL_ECIES_PRIVATE_KEY=0x...   # Decryption key for reports
```

## Workflow: Adding a New Triage Rule

1. Edit `protocol/triage.py` — modify `_decide_action()` or the system prompt
2. Add a test case in `protocol/test_triage.py` with mocked Venice response
3. Run `pytest protocol/test_triage.py -v`
4. Test with `python -m protocol.agent respond` against local Anvil
