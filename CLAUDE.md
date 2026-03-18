# BugBounty.agent

Autonomous smart contract security marketplace where AI agents find vulnerabilities, evaluate severity through private inference (Venice), and trigger automatic escrowed payouts.

## Tech Stack

- **Contracts:** Foundry, Solidity 0.8.24+, Base Sepolia
- **Agents:** Python 3.11+ (web3.py, openai, eciespy, slither-analyzer)
- **Dashboard:** React + Vite + TypeScript + Tailwind CSS + ethers.js
- **Inference:** Venice API (OpenAI-compatible)

## Repository Structure

```
contracts/    — Foundry project (ERC-8004 registries, BountyRegistry, BugSubmission, ArbiterContract)
agents/       — Python off-chain agents (protocol, hunter, executor, arbiter)
dashboard/    — React + Vite dashboard (read-only, no wallet)
vulnerable/   — Intentionally buggy contracts for demo
scripts/      — Deploy + demo orchestration
```

## Build & Test

```bash
# Contracts
cd contracts && forge build && forge test

# Agents
cd agents && pip install -e . && pytest

# Dashboard
cd dashboard && npm install && npm run dev
```

## Architecture

5 vertical slices, each independently demoable:
1. ERC-8004 registries + identity
2. Bounty creation (BountyRegistry + Protocol Agent)
3. Submission flow (BugSubmission + Hunter Agent)
4. Execution + Arbitration (Executor + ArbiterContract + 3 arbiters)
5. Patch guidance (Venice remediation + encrypted delivery)

## Key Design Decisions

- Agents never share wallets — each has its own private key
- ECIES keys are separate from Ethereum keys (secp256k1)
- Arbiters see only State Impact JSON, never hunter prose (prompt-injection firewall)
- Severity enum: 0=INVALID, 1=LOW, 2=MEDIUM, 3=HIGH, 4=CRITICAL
- Contract addresses stored in `deployments.json` (written by deploy script)
- All env vars in `.env` (see `.env.example`)

## Design Spec

Full spec: `docs/superpowers/specs/2026-03-17-bugbounty-agent-design.md`
Implementation plan: `docs/superpowers/plans/2026-03-17-bugbounty-agent.md`
