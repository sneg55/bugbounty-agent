# BugBounty.agent

Autonomous smart contract security marketplace where AI agents discover vulnerabilities, evaluate severity through zero-retention private inference, and trigger automatic escrowed payouts. Private audits, public payouts.

**Target chain:** Base Sepolia &nbsp;|&nbsp; **Contracts:** Foundry (Solidity 0.8.24+) &nbsp;|&nbsp; **Agents:** Python 3.11+ &nbsp;|&nbsp; **Dashboard:** React + Vite + TypeScript + Tailwind CSS &nbsp;|&nbsp; **Inference:** Venice API (OpenAI-compatible)

---

## Table of Contents

- [System Architecture](#system-architecture)
- [How It Works](#how-it-works)
- [Repository Structure](#repository-structure)
- [Smart Contracts](#smart-contracts)
- [Off-Chain Agents](#off-chain-agents)
- [Dashboard](#dashboard)
- [Algorithms](#algorithms)
- [Running the Demo](#running-the-demo)
- [Development Setup](#development-setup)
- [Testing](#testing)
- [Vulnerable Demo Contracts](#vulnerable-demo-contracts)
- [Environment Variables](#environment-variables)
- [Design Decisions](#design-decisions)

---

## System Architecture

```
                           BugBounty.agent
    ┌──────────────────────────────────────────────────────────┐
    │                    Base Sepolia Chain                      │
    │                                                            │
    │  ┌─────────────┐  ┌──────────────┐  ┌─────────────────┐  │
    │  │  Identity    │  │  Reputation  │  │  Validation     │  │
    │  │  Registry    │  │  Registry    │  │  Registry       │  │
    │  │  (ERC-721)   │  │  (feedback)  │  │  (state diffs)  │  │
    │  └──────┬───────┘  └──────┬───────┘  └────────┬────────┘  │
    │         │                 │                    │            │
    │  ┌──────┴─────────────────┴────────────────────┴────────┐  │
    │  │              BountyRegistry (USDC escrow)             │  │
    │  └──────────────────────┬───────────────────────────────┘  │
    │                         │                                  │
    │  ┌──────────────────────┴───────────────────────────────┐  │
    │  │           BugSubmission (commit-reveal + staking)     │  │
    │  └──────────────────────┬───────────────────────────────┘  │
    │                         │                                  │
    │  ┌──────────────────────┴───────────────────────────────┐  │
    │  │        ArbiterContract (jury selection + voting)       │  │
    │  └──────────────────────────────────────────────────────┘  │
    └──────────────────────────────────────────────────────────┘
                              │
         ┌────────────────────┼─────────────────────┐
         ▼                    ▼                      ▼
    ┌─────────┐       ┌──────────────┐       ┌─────────────┐
    │ Protocol │       │   Hunter     │       │  3x Arbiter │
    │  Agent   │       │   Agent      │       │   Agents    │
    │          │       │              │       │             │
    │ Creates  │       │ Scans        │       │ Evaluate    │
    │ bounties │       │ Slither+LLM  │       │ via Venice  │
    │ Receives │       │ Commits PoC  │       │ Blind vote  │
    │ patches  │       │ Stakes USDC  │       │ Consensus   │
    └─────────┘       └──────────────┘       └─────────────┘
                              │
                      ┌───────┴────────┐
                      │   Executor     │
                      │   Service      │
                      │                │
                      │ Forks chain    │
                      │ Runs PoC       │
                      │ State diff     │
                      │ Patch guidance │
                      └────────────────┘
```

Six agents collaborate through on-chain contracts. No agent trusts another — all coordination happens via contract state and cryptographic commitments.

---

## How It Works

### Full Lifecycle (10 steps)

1. **Protocol Agent creates bounty** — Deposits USDC into BountyRegistry with payout tiers (Critical: 25k, High: 10k, Medium: 2k, Low: 500) and a scope URI pointing to in-scope contracts on IPFS.

2. **Hunter Agent scans** — Watches for `BountyCreated` events, downloads target contracts, runs [Slither](https://github.com/crytic/slither) static analysis, filters findings >= Medium.

3. **Hunter reasons with LLM** — Sends Slither findings + contract source to Venice (llama-3.3-70b). Gets structured exploitability analysis.

4. **Hunter generates PoC** — LLM writes a complete Foundry test that demonstrates the exploit. Validates it compiles locally.

5. **Hunter commits** — Encrypts the PoC with the Executor's ECIES public key, uploads to IPFS, computes `commitHash = keccak256(abi.encode(encryptedCID, hunterAgentId, salt))`, stakes USDC, calls `commitBug()`.

6. **Hunter reveals** — After commit confirmation, calls `revealBug(bugId, encryptedCID, salt)`. The contract verifies the hash matches. The 200-block reveal window starts from commit.

7. **Executor runs PoC** — Decrypts the submission, forks the chain at the target block, runs the Foundry PoC, captures pre/post state. Produces a **State Impact JSON** (balance changes, storage changes, impact flags). Registers on-chain via ValidationRegistry and ArbiterContract.

8. **3 Arbiters vote** — Jury selected by reputation ranking. Each arbiter independently evaluates the State Impact JSON (never seeing hunter prose — prompt injection firewall). Blind commit-reveal: commit vote hash, then reveal severity + salt. 50 blocks per phase.

9. **Resolution** — Median of revealed severities determines final verdict. Valid findings trigger USDC payout from escrow. Hunter gets stake back + bounty tier payout. Reputation feedback: hunter +100 (valid) / -100 (invalid), arbiters +10 (consensus) / -5 (deviated).

10. **Patch guidance** — For Critical/High findings, the Executor generates remediation advice via Venice, encrypts it with the Protocol Agent's public key, and emits a `PatchGuidance` event. Only the Protocol Agent can decrypt it.

---

## Repository Structure

```
bugbounty-agent/
├── contracts/                    # Foundry project (Solidity 0.8.24+)
│   ├── src/
│   │   ├── erc8004/
│   │   │   ├── IdentityRegistry.sol       # ERC-721 agent identity + metadata
│   │   │   ├── ReputationRegistry.sol     # Feedback ledger + validity rates
│   │   │   └── ValidationRegistry.sol     # Executor verification records
│   │   ├── BountyRegistry.sol             # Bounty creation + USDC escrow
│   │   ├── BugSubmission.sol              # Commit-reveal + reputation-adjusted staking
│   │   ├── ArbiterContract.sol            # Jury selection + blind voting + resolution
│   │   └── mocks/MockUSDC.sol             # Test ERC-20 (6 decimals)
│   ├── test/                              # 45 tests (unit + integration)
│   ├── script/Deploy.s.sol                # Foundry deploy with cross-contract wiring
│   ├── foundry.toml
│   └── remappings.txt
│
├── agents/                       # Python off-chain agents
│   ├── common/                            # Shared infrastructure
│   │   ├── inference.py                   # Venice/OpenAI LLM wrapper (retry, singleton)
│   │   ├── contracts.py                   # Web3.py bindings from Foundry ABI artifacts
│   │   ├── ipfs.py                        # Pinata upload/download (timeout + retry)
│   │   ├── crypto.py                      # ECIES encrypt/decrypt (secp256k1)
│   │   ├── block_cursor.py               # Persisted last-processed-block per agent
│   │   └── config.py                      # Env var loading + deployments.json reader
│   ├── protocol/                          # Protocol Agent
│   │   ├── agent.py                       # CLI: create-bounty | watch
│   │   ├── risk_model.py                  # Hardcoded tier amounts (demo)
│   │   └── patch_receiver.py              # Decrypt + display patch guidance
│   ├── hunter/                            # Hunter Agent
│   │   ├── agent.py                       # Main loop: poll → scan → submit
│   │   ├── scanner.py                     # Slither integration
│   │   ├── reasoning.py                   # LLM exploitability analysis
│   │   ├── poc_generator.py               # LLM → Foundry PoC test script
│   │   └── submitter.py                   # Encrypt + commit-reveal flow
│   ├── executor/                          # Executor Service
│   │   ├── service.py                     # Event listener + orchestration
│   │   ├── fork_runner.py                 # forge test on chain fork
│   │   ├── state_diff.py                  # State Impact JSON builder
│   │   ├── abi_resolver.py                # Label storage slots from ABIs
│   │   └── patch_guidance.py              # LLM remediation + encrypt + IPFS
│   ├── arbiter/                           # Arbiter Agents (3 instances)
│   │   ├── agent.py                       # JurySelected → evaluate → vote
│   │   ├── evaluator.py                   # State Impact → severity (0-4) via LLM
│   │   └── voter.py                       # Blind commit-reveal voting
│   └── pyproject.toml
│
├── dashboard/                    # React + Vite + TypeScript + Tailwind
│   └── src/
│       ├── App.tsx                        # Router + nav + stat cards
│       ├── pages/
│       │   ├── BountiesPage.tsx           # Bounty list
│       │   ├── BountyDetailPage.tsx       # Bounty detail + submissions
│       │   ├── SubmissionDetailPage.tsx   # Full pipeline view
│       │   ├── AgentsPage.tsx             # Agent registry + reputation
│       │   └── LiveFeedPage.tsx           # Real-time event stream
│       ├── config.ts                      # RPC provider setup
│       └── contracts.ts                   # ABI definitions + addresses
│
├── vulnerable/                   # Intentionally buggy contracts (demo targets)
│   ├── ReentrancyVault.sol                # Classic reentrancy
│   ├── AccessControlToken.sol             # Missing access control on mint()
│   └── OracleManipulation.sol             # Manipulable price feed
│
├── scripts/
│   ├── demo_flow.py                       # Full lifecycle orchestration
│   └── deploy_and_register.py             # Deploy + mint agents + fund wallets
│
├── .env.example                           # Environment variable template
└── deployments.json                       # Contract addresses (written by deploy script)
```

---

## Smart Contracts

### Contract Dependency Graph

```
ArbiterContract ──→ BugSubmission.resolveSubmission()
                ──→ ReputationRegistry.giveFeedback()
                ──→ ValidationRegistry.getValidationStatus()
                ──→ IdentityRegistry.isActive() + ownerOf()

BugSubmission   ──→ BountyRegistry.deductPayout()
                ──→ ReputationRegistry.getReputation()
                ──→ IdentityRegistry.isActive()

BountyRegistry  ──→ IdentityRegistry.ownerOf()
                ──→ BugSubmission.getPendingCount()
```

### ERC-8004 Registries

| Contract | Purpose | Key Functions |
|----------|---------|---------------|
| **IdentityRegistry** | ERC-721 agent IDs with key-value metadata | `mintAgent()`, `setMetadata()`, `getMetadata()`, `isActive()` |
| **ReputationRegistry** | Authorized-caller-only feedback ledger | `giveFeedback()`, `getReputation()`, `getValidityRate()` |
| **ValidationRegistry** | One-write executor verification records | `submitValidation()`, `getValidationStatus()` |

### Core Contracts

| Contract | Purpose | Key Functions |
|----------|---------|---------------|
| **BountyRegistry** | USDC escrow with tier-based payouts | `createBounty()`, `deductPayout()`, `withdrawRemainder()` |
| **BugSubmission** | Commit-reveal submissions with reputation-adjusted staking | `commitBug()`, `revealBug()`, `resolveSubmission()` |
| **ArbiterContract** | Reputation-ranked jury, blind voting, median resolution | `registerStateImpact()`, `commitVote()`, `revealVote()` |

### Stake Schedule (USDC)

Stakes are adjusted based on the hunter's reputation tier:

| Claimed Severity | Unknown (<3 valid) | Established (3+, net positive) | Top-tier (10+, >80% valid) |
|-----------------|-------------------|-------------------------------|---------------------------|
| CRITICAL (4)     | 250                | 100                            | 0                          |
| HIGH (3)         | 100                | 50                             | 0                          |
| MEDIUM (2)       | 25                 | 10                             | 0                          |
| LOW (1)          | 10                 | 5                              | 0                          |

### Severity Rubric

Applied by all arbiters, enforced platform-wide:

| Level | Score | Criteria |
|-------|-------|----------|
| **CRITICAL** | 4 | Direct loss of funds, consensus failure, or permanent bricking. Exploitable with no/minimal prerequisites. |
| **HIGH** | 3 | Indirect fund loss, significant DoS (>1h), unauthorized privilege escalation. Moderate prerequisites. |
| **MEDIUM** | 2 | Limited fund loss (<$10k), temporary DoS (<1h), recoverable state corruption. Specific conditions required. |
| **LOW** | 1 | Informational, gas optimizations, best-practice violations with no direct exploit path. |
| **INVALID** | 0 | Exploit failed, didn't compile, wrong contract, or out of scope. |

---

## Off-Chain Agents

### Agent Overview

| Agent | Wallet | Role | Inference Model |
|-------|--------|------|-----------------|
| Protocol Agent | Own key | Creates bounties, receives patch guidance | — |
| Hunter Agent | Own key | Scans, reasons, generates PoC, submits | llama-3.3-70b |
| Executor Service | Own key | Runs PoC forks, produces state diffs, generates patches | llama-3.3-70b |
| Arbiter 1 | Own key | Evaluates state impact, votes on severity | llama-3.3-70b (temp 0.0) |
| Arbiter 2 | Own key | Evaluates state impact, votes on severity | llama-3.3-70b (temp 0.1) |
| Arbiter 3 | Own key | Evaluates state impact, votes on severity | mistral-large (temp 0.0) |

Each agent has **separate Ethereum and ECIES key pairs**. Ethereum keys sign transactions; ECIES keys encrypt/decrypt sensitive data (PoCs, patches). Public ECIES keys are published on-chain via `IdentityRegistry.setMetadata()`.

### Prompt Injection Firewall

Arbiters **never see hunter-authored text**. They receive only the structured State Impact JSON produced by the trusted Executor. This architectural boundary prevents hunters from injecting prompts to influence severity ratings.

---

## Dashboard

Read-only React dashboard (no wallet connection). Polls Base Sepolia RPC every 5-30 seconds.

| Page | Route | Data Source |
|------|-------|-------------|
| Home | `/` | Stat cards (bounties, submissions, payouts) |
| Bounties | `/bounties` | `BountyRegistry.getBountyCount()` + `getBounty(id)` |
| Bounty Detail | `/bounties/:id` | Bounty params + linked submissions |
| Submission Detail | `/submissions/:id` | Pipeline view: commit → reveal → arbitration → verdict |
| Agents | `/agents` | `IdentityRegistry.totalAgents()` + `ReputationRegistry.getReputation()` |
| Live Feed | `/feed` | Incremental event polling across all contracts |

---

## Algorithms

### Jury Selection (Reputation-Ranked)

When the Executor registers a state impact, the contract selects 3 jurors:

1. **Collect eligible arbiters** — iterate the arbiter pool, excluding any arbiter whose wallet owner matches the hunter or protocol agent (conflict of interest check via `IdentityRegistry.ownerOf()`).

2. **Score each** — call `ReputationRegistry.getFeedbackCount(agentId, "consensus_aligned")` for each eligible arbiter.

3. **Select top 3** — three selection passes over the eligible set. Each pass picks the highest-scoring unselected arbiter. Ties broken by pool order (deterministic).

4. **Revert if < 3 eligible** — ensures minimum quorum.

### Median Resolution

After arbiters reveal their severity votes:

- **3 reveals:** Sort the three values. Take the middle one (median). If all three vote INVALID (0), submission is invalid. Otherwise, payout at the median severity.

- **2 reveals** (1 arbiter timed out): Take `min(severity1, severity2)` — conservative approach favoring the lower rating. Non-revealing arbiter gets -20 reputation.

- **0-1 reveals** (insufficient quorum): Submission marked invalid. Hunter's stake is **returned** (not slashed — this is arbiter failure, not hunter's fault). Non-revealing arbiters get -20 reputation each.

### Reputation Feedback

After resolution:

| Target | Valid Submission | Invalid Submission |
|--------|-----------------|-------------------|
| Hunter | +100 | -100 |
| Aligned arbiter | +10 | +10 |
| Deviated arbiter | -5 | -5 |

An arbiter is "aligned" if their vote matches the final median. "Deviated" if they voted differently.

### Commit-Reveal Protocol

**Hunter submissions:**
```
commitHash = keccak256(abi.encode(encryptedCID, hunterAgentId, salt))
```
- Commit: submit hash + stake USDC
- Reveal: submit plaintext values. Contract verifies hash. 200-block window.

**Arbiter votes:**
```
voteHash = keccak256(abi.encode(severity, salt))
```
- Commit: submit hash. 50-block window.
- Reveal: submit severity + salt. 50-block window.

---

## Running the Demo

### Prerequisites

- [Foundry](https://book.getfoundry.sh/getting-started/installation) (forge, cast, anvil)
- Python 3.11+ with pip
- Node.js 18+ with npm

### Quick Start

```bash
# 1. Clone and install
git clone https://github.com/sneg55/bugbounty-agent.git
cd bugbounty-agent

# Install Solidity dependencies
cd contracts && forge install && forge build && cd ..

# Install Python dependencies
python3 -m venv .venv && source .venv/bin/activate
cd agents && pip install -e ".[dev]" && cd ..

# Install dashboard dependencies
cd dashboard && npm install && cd ..
```

### Run the Full Demo (Local Anvil)

```bash
# Terminal 1: Start local chain (2-second block time)
anvil --block-time 2

# Terminal 2: Run the demo
source .venv/bin/activate
python scripts/demo_flow.py --rpc-url http://localhost:8545
```

### What the Demo Does

The `demo_flow.py` script orchestrates the entire protocol lifecycle using Anvil's pre-funded accounts:

| Step | Action | Accounts Used |
|------|--------|---------------|
| 1 | Deploy 7 contracts with cross-references | Account 0 (deployer) |
| 2 | Mint 6 agent IDs, fund wallets (50k + 1k USDC) | Account 0 |
| 3 | Protocol Agent creates 50,000 USDC bounty | Account 1 (protocol) |
| 4 | Hunter commits CRITICAL bug + reveals | Account 2 (hunter) |
| 5 | Executor registers state impact | Account 3 (executor) |
| 6 | 3 Arbiters blind vote (all CRITICAL) | Accounts 4-6 (arbiters) |
| 7 | Executor emits patch guidance | Account 3 |
| 8 | Protocol withdraws 25,000 USDC remainder | Account 1 |

**Expected output:**
```
Hunter USDC balance:  26,000 (25k payout + 750 original + 250 stake returned)
Protocol remainder:   25,000 USDC
Hunter reputation:    +100
Arbiter reputation:   +10 each
```

### Run the Dashboard

```bash
cd dashboard && npm run dev
# Open http://localhost:5173
```

Point the dashboard at your Anvil instance or Base Sepolia by editing `dashboard/src/config.ts`.

### Deploy to Base Sepolia

```bash
# Copy and fill in environment variables
cp .env.example .env
# Edit .env with your keys, Venice API key, and Pinata credentials

# Deploy contracts
python scripts/deploy_and_register.py \
  --rpc-url https://sepolia.base.org \
  --private-key $DEPLOYER_PRIVATE_KEY

# Run individual agents
cd agents
python -m protocol.agent create-bounty --name "MyProtocol" --scope-uri "ipfs://..."
python -m hunter.agent --watch
python -m executor.service
python -m arbiter.agent --slot 1
python -m arbiter.agent --slot 2
python -m arbiter.agent --slot 3
```

---

## Development Setup

### Build

```bash
# Contracts
cd contracts && forge build

# Agents
cd agents && pip install -e ".[dev]"

# Dashboard
cd dashboard && npm install && npm run build
```

### Lint / Format

```bash
# Solidity
cd contracts && forge fmt

# TypeScript
cd dashboard && npx tsc --noEmit
```

---

## Testing

### Solidity Tests (45 passing)

```bash
cd contracts && forge test -v
```

| Suite | Tests | Coverage |
|-------|-------|----------|
| MockUSDCTest | 4 | name, decimals, mint, anyone-can-mint |
| IdentityRegistryTest | 7 | mint, increments, ownership, metadata, isActive, tokenURI |
| ReputationRegistryTest | 7 | feedback, cumulative, tags, validity rate, authorization |
| ValidationRegistryTest | 5 | submit, get, nonexistent, authorization, no-overwrite |
| BountyRegistryTest | 6 | create, get, ownership, withdraw, deadline, count |
| BountyRegistryPendingTest | 2 | pending-submission guard, withdraw-after-resolve |
| BugSubmissionTest | 7 | commit, stake, reveal, hash check, window, max-3, reputation |
| ArbiterContractTest | 5 | state impact, full voting, invalid slashing, access control, jury ranking |
| FullLifecycleTest | 2 | end-to-end + security guards |

### Python Tests (24 passing)

```bash
cd agents && python -m pytest -v
```

| Module | Tests |
|--------|-------|
| common/inference | 2 (mock responses, retry) |
| common/crypto | 2 (roundtrip, wrong-key rejection) |
| common/ipfs | 3 (upload, download, timeout) |
| common/contracts | 2 (ABI loading, provider) |
| common/block_cursor | 2 (default, persistence) |
| hunter/scanner | 1 (severity filtering) |
| hunter/submitter | 1 (commit hash computation) |
| executor/state_diff | 3 (impact flags, role changes, JSON builder) |
| executor/patch_guidance | 2 (generation, encrypt+upload flow) |
| arbiter/evaluator | 2 (severity parsing, retry on bad output) |

### End-to-End

The `scripts/demo_flow.py` script serves as the E2E test — it runs the full protocol lifecycle with assertions at each step against a local Anvil instance.

---

## Vulnerable Demo Contracts

Three intentionally buggy contracts for demonstration:

### ReentrancyVault.sol
Classic reentrancy — `withdraw()` sends ETH via external call before updating the sender's balance. An attacker contract can re-enter `withdraw()` in its `receive()` callback to drain the vault.

**Expected finding:** CRITICAL. State diff shows vault balance dropping to 0.

### AccessControlToken.sol
Missing access control on `mint()` — anyone can mint unlimited tokens. The `burn()` function correctly requires `msg.sender == admin`, but `mint()` has no such check.

**Expected finding:** HIGH. State diff shows attacker balance and total supply increasing.

### OracleManipulation.sol
A lending contract with a manipulable `SimplePriceOracle`. The `setPrice()` function has no access control. An attacker updates the price, borrows at inflated collateral value, and drains the pool.

**Expected finding:** CRITICAL. State diff shows pool drained and oracle price changed.

---

## Environment Variables

Copy `.env.example` to `.env` and fill in:

| Variable | Purpose | Required |
|----------|---------|----------|
| `RPC_URL` | Base Sepolia RPC endpoint | Yes |
| `CHAIN_ID` | Chain ID (84532 for Base Sepolia) | Yes |
| `PROTOCOL_AGENT_PRIVATE_KEY` | Protocol agent Ethereum key | Yes |
| `HUNTER_AGENT_PRIVATE_KEY` | Hunter agent Ethereum key | Yes |
| `ARBITER_{1,2,3}_PRIVATE_KEY` | Arbiter Ethereum keys (3 required) | Yes |
| `EXECUTOR_PRIVATE_KEY` | Executor Ethereum key | Yes |
| `EXECUTOR_ECIES_PRIVATE_KEY` | Executor ECIES key (for decrypting submissions) | Yes |
| `PROTOCOL_ECIES_PRIVATE_KEY` | Protocol ECIES key (for decrypting patches) | Yes |
| `INFERENCE_BASE_URL` | Venice API endpoint | For agents |
| `INFERENCE_API_KEY` | Venice API key | For agents |
| `INFERENCE_MODEL` | LLM model (default: llama-3.3-70b) | No |
| `PINATA_API_KEY` | Pinata IPFS API key | For agents |
| `PINATA_SECRET_KEY` | Pinata IPFS secret | For agents |

**Note:** For local demo with Anvil, no `.env` is needed — the demo script uses Anvil's pre-funded accounts.

---

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Separate wallets per agent** | No shared keys. Each agent signs independently. Compromising one agent doesn't compromise others. |
| **ECIES keys separate from Ethereum keys** | Encryption keys have different security properties than signing keys. Stored on-chain as metadata. |
| **Arbiters see only State Impact JSON** | Prompt injection firewall. Hunters cannot influence arbiter LLM evaluations through crafted text. |
| **Blind commit-reveal voting** | Prevents arbiters from copying each other's votes. Ensures independent evaluation. |
| **Median resolution (3 arbiters)** | Robust to a single outlier. Conservative 2-arbiter fallback uses min(). |
| **Reputation-adjusted stakes** | Established hunters pay less to participate. Unknown hunters put more skin in the game. |
| **Stake returned on arbiter timeout** | Hunter shouldn't be penalized for arbiter infrastructure failures. |
| **50-block voting windows** | ~100 seconds on Base Sepolia. Long enough for LLM evaluation, short enough for fast resolution. |
| **Patch guidance only for HIGH+** | Venice inference is expensive. Low/Medium findings don't justify automated remediation. |
| **Provider-agnostic inference** | Venice first, any OpenAI-compatible endpoint as fallback. No vendor lock-in. |
| **No wallet in dashboard** | Read-only data visualization. Reduces attack surface and simplifies UX. |

---

## License

MIT

---

> **Synthesis Hackathon 2026** | Team: bot55 + Nick Sawinyh
