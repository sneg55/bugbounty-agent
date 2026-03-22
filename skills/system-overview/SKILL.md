---
name: system-overview
description: Provides a complete overview of the BugBounty.agent autonomous security marketplace — the full lifecycle from bounty creation through arbitration and payout. Use when onboarding, understanding the system architecture, or deciding which agent skill to use.
---

# BugBounty.agent System Overview

Autonomous smart contract security marketplace. AI agents find vulnerabilities, evaluate severity through private inference, and trigger automatic escrowed payouts.

## Agent Roles

| Agent | Skill | What It Does |
|-------|-------|-------------|
| Protocol | [protocol-agent](../protocol-agent/SKILL.md) | Creates bounties, triages submissions (accept/dispute) |
| Hunter | [hunter-agent](../hunter-agent/SKILL.md) | Scans contracts, generates PoCs, submits findings |
| Executor | [executor-agent](../executor-agent/SKILL.md) | Runs PoCs in fork, produces objective state diffs |
| Arbiter (x3) | [arbiter-agent](../arbiter-agent/SKILL.md) | Evaluates state diffs, votes on severity |
| Keeper | [keeper-service](../keeper-service/SKILL.md) | Auto-accepts after 72h protocol silence |

## Full Lifecycle

```
1. Protocol creates bounty (escrow USDC, define scope + tiers)
2. Hunter scans scope → finds vulnerability → generates PoC
3. Hunter encrypts report (dual: executor + protocol) → commit-reveal on-chain
4. Executor verifies PoC in Anvil fork → produces State Impact JSON → caches result
5. Protocol decrypts report + reads verification → AI triage:
   - PoC failed → DISPUTE
   - Valid + severity match → ACCEPT at min(claimed, estimated)
   - Invalid/mismatch → DISPUTE
6. If accepted: payout at accepted severity, done
7. If disputed: executor registers state diff on-chain → jury selected
8. 3 arbiters evaluate State Impact JSON → blind commit-reveal vote
9. Median severity → payout (or stake slash if invalid)
10. Patch guidance generated for HIGH/CRITICAL (encrypted for protocol)
11. If protocol silent for 72h: keeper calls autoAcceptOnTimeout
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Contracts | Foundry, Solidity 0.8.24+, Base Sepolia |
| Agents | Python 3.11+ (web3.py, openai, eciespy, slither) |
| Dashboard | React + Vite + TypeScript + Tailwind + ethers.js |
| Inference | Venice API (OpenAI-compatible, zero data retention) |

## Running Locally

```bash
# 1. Start Anvil
anvil &

# 2. Deploy + register
export DEPLOYER_PRIVATE_KEY=0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80
python scripts/deploy_and_register.py

# 3. Run agents (each in separate terminal)
python -m protocol.agent create-bounty --name "TestProtocol"
python -m hunter.agent --watch
python -m executor.service
python -m arbiter.agent --slot 1
python -m arbiter.agent --slot 2
python -m arbiter.agent --slot 3
python -m protocol.agent respond
python -m keeper.timeout_keeper

# 4. Dashboard
cd dashboard && npm run dev
```

## Testing

```bash
make test        # All suites (60 Solidity + 36 Python + 47 Dashboard)
make test-sol    # Solidity only
make test-py     # Python only
make test-dash   # Dashboard only
```
