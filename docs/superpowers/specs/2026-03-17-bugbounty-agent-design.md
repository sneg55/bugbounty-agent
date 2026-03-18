# BugBounty.agent — Implementation Design Spec

> Synthesis Hackathon 2026 | Team: bot55 + Nick Sawinyh
> Approach: Vertical Slices (end-to-end per workflow)
> Last Updated: 2026-03-17

## Overview

Autonomous smart contract security marketplace where AI agents find vulnerabilities, evaluate severity through zero-retention private inference (Venice), and trigger automatic escrowed payouts. Private audits, public payouts.

**Target chain:** Base Sepolia
**Contracts:** Foundry (Solidity 0.8.24+)
**Agents:** Python 3.11+
**Dashboard:** React + Vite + TypeScript + Tailwind CSS
**Inference:** Venice API (OpenAI-compatible), provider-agnostic fallback

## Repository Structure

```
bugbounty-agent/
├── contracts/                        # Foundry project
│   ├── src/
│   │   ├── erc8004/
│   │   │   ├── IdentityRegistry.sol
│   │   │   ├── ReputationRegistry.sol
│   │   │   └── ValidationRegistry.sol
│   │   ├── BountyRegistry.sol
│   │   ├── BugSubmission.sol
│   │   ├── ArbiterContract.sol
│   │   └── mocks/
│   │       └── MockUSDC.sol
│   ├── test/
│   ├── script/
│   │   └── Deploy.s.sol
│   ├── foundry.toml
│   └── remappings.txt
├── agents/                           # Python
│   ├── common/
│   │   ├── inference.py              # Provider-agnostic Venice/OpenAI client
│   │   ├── contracts.py              # Web3 contract bindings from Foundry ABIs
│   │   ├── ipfs.py                   # Pinata upload/download
│   │   └── crypto.py                 # ECIES encrypt/decrypt
│   ├── protocol/
│   │   ├── agent.py                  # Protocol Agent main loop
│   │   ├── risk_model.py             # TVL → bounty budget (hardcoded for demo)
│   │   └── patch_receiver.py         # Decrypt + display patch guidance
│   ├── hunter/
│   │   ├── agent.py                  # Hunter Agent main loop
│   │   ├── scanner.py                # Slither integration
│   │   ├── reasoning.py              # LLM vulnerability analysis via Venice
│   │   ├── poc_generator.py          # Generate Foundry PoC from findings
│   │   └── submitter.py              # Encrypt + commit-reveal
│   ├── arbiter/
│   │   ├── agent.py                  # Arbiter Agent main loop
│   │   ├── evaluator.py              # State diff → severity via Venice
│   │   └── voter.py                  # Blind commit-reveal voting
│   ├── executor/
│   │   ├── service.py                # Main executor event listener
│   │   ├── fork_runner.py            # Foundry fork + PoC execution
│   │   ├── state_diff.py             # Produce State Impact JSON
│   │   ├── abi_resolver.py           # Label storage slots from ABIs
│   │   └── patch_guidance.py         # Venice remediation + encrypted delivery
│   └── pyproject.toml
├── dashboard/                        # React + Vite
│   └── (see Section 7)
├── vulnerable/                       # Intentionally buggy contracts for demo
│   ├── ReentrancyVault.sol
│   ├── AccessControlToken.sol
│   └── OracleManipulation.sol
└── scripts/
    ├── demo_flow.py                  # Orchestrate full lifecycle
    └── deploy_and_register.py        # Deploy contracts + mint agent IDs
```

## Section 1: ERC-8004 Registries

We deploy our own ERC-8004 registry implementations on Base Sepolia. These are the foundation for agent identity, reputation, and executor validation.

### IdentityRegistry.sol

ERC-721 where each token represents an agent identity.

- `mintAgent(address owner, string calldata registrationURI) → uint256 agentId` — mints agent NFT, stores registration JSON URI
- `setMetadata(uint256 agentId, string calldata key, bytes calldata value)` — key-value metadata store (Executor pubkey, Protocol Agent patchGuidancePubKey)
- `getMetadata(uint256 agentId, string calldata key) → bytes` — read metadata
- `isActive(uint256 agentId) → bool` — checks agent is active
- Only token owner can update their own metadata/registration

### ReputationRegistry.sol

Stores feedback entries linked to agent IDs. Authorized callers only (ArbiterContract).

- `giveFeedback(uint256 targetAgentId, int256 value, string calldata tag1, string calldata tag2)` — post feedback
- `getReputation(uint256 agentId) → int256` — net reputation (sum of all feedback values)
- `getFeedbackCount(uint256 agentId, string calldata tag1) → uint256` — count by tag
- `getValidityRate(uint256 agentId) → uint256` — percentage of valid submissions

### ValidationRegistry.sol

Records executor verification results.

- `submitValidation(uint256 executorAgentId, bytes32 requestHash, string calldata resultURI)` — post state diff hash + IPFS URI
- `getValidationStatus(bytes32 requestHash) → bool` — whether validation exists
- `getValidation(bytes32 requestHash) → (uint256 executorAgentId, string resultURI, uint256 timestamp)`

All three registries are Ownable. The deployer authorizes which contracts can write (ArbiterContract → ReputationRegistry, Executor address → ValidationRegistry).

## Section 2: Core Smart Contracts

### MockUSDC.sol

Simple ERC-20 with public `mint(address to, uint256 amount)` for Base Sepolia testing.

### BountyRegistry.sol

Manages bounty creation, USDC escrow, and fund withdrawal.

**Storage:** `mapping(uint256 => Bounty)` — `Bounty` struct contains:
- `protocolAgentId`, `name`, `scopeHash` (IPFS CID), `tiers` (struct: critical/high/medium/low in USDC), `totalFunding`, `totalPaid`, `deadline`, `minHunterReputation`, `active`

**Functions:**
- `createBounty(...)` — validates protocolAgentId via IdentityRegistry, transfers USDC to escrow, emits `BountyCreated`
- `withdrawRemainder(uint256 bountyId)` — callable by protocol agent owner after deadline + gracePeriod, requires no pending submissions, transfers `totalFunding - totalPaid`
- `deductPayout(uint256 bountyId, uint256 amount, address recipient)` — callable only by BugSubmission, transfers USDC to hunter, increments `totalPaid`
- `getRemainingFunds(uint256 bountyId)` — view
- `getBounty(uint256 bountyId)` — view

Grace period: 1800 seconds default.

### BugSubmission.sol

Manages commit-reveal submissions and staking.

**Storage:** `mapping(uint256 => Submission)` — `Submission` struct contains:
- `bountyId`, `hunterAgentId`, `claimedSeverity` (enum 0-4), `commitHash`, `encryptedCID`, `stake`, `status` (Committed/Revealed/Resolved), `finalSeverity`, `isValid`, timestamps

**Functions:**
- `commitBug(uint256 bountyId, bytes32 commitHash, uint256 hunterAgentId, uint8 claimedSeverity)` — validates hunter via IdentityRegistry, checks reputation for stake calculation via ReputationRegistry, enforces ≤3 active submissions per hunter per bounty, transfers stake, emits `BugCommitted`
- `revealBug(uint256 commitId, string calldata encryptedCID, bytes32 salt)` — verifies `keccak256(abi.encodePacked(encryptedCID, hunterAgentId, salt)) == commitHash`, checks reveal window, emits `BugRevealed`
- `resolveSubmission(uint256 bugId, uint8 finalSeverity, bool isValid)` — callable only by ArbiterContract. Valid: returns stake + triggers `BountyRegistry.deductPayout()`. Invalid: slashes stake. Emits `SubmissionResolved`
- `reclaimExpiredCommit(uint256 commitId)` — returns stake for commits past reveal window

Reveal window: 200 blocks from commit.

**Stake schedule (reputation-adjusted):**

| Claimed Severity | Unknown (<3 valid) | Established (3+, net positive) | Top-tier (10+, >80% valid) |
|--|--|--|--|
| CRITICAL | 250 USDC | 100 USDC | 0 |
| HIGH | 100 USDC | 50 USDC | 0 |
| MEDIUM | 25 USDC | 10 USDC | 0 |
| LOW | 10 USDC | 5 USDC | 0 |

### ArbiterContract.sol

Manages jury selection, blind voting, median resolution, and reputation feedback.

**Storage:** per-bug `Arbitration` struct:
- `bugId`, `stateImpactCID`, `validationRequestHash`, `jurors[3]`, `commitHashes[3]`, `revealedSeverities[3]`, `revealed[3]`, `phase` (AwaitingStateImpact/Voting/Revealing/Resolved)

**Functions:**
- `registerStateImpact(uint256 bugId, bytes32 requestHash, string calldata stateImpactCID)` — callable by authorized executor, checks ValidationRegistry, triggers `selectJury()`, emits `StateImpactRegistered`
- `selectJury(uint256 bugId)` — internal, queries ReputationRegistry for top 3 arbiters by consensus_aligned count, excludes agents sharing owner with hunter/protocol, emits `JurySelected`
- `commitVote(uint256 bugId, bytes32 voteHash)` — must be selected juror
- `revealVote(uint256 bugId, uint8 severity, bytes32 salt)` — verifies hash. After all 3: calls `_resolve()`
- `_resolve(uint256 bugId)` — majority INVALID (0): slashes hunter. Otherwise: median of 3 severity values → payout. Posts reputation feedback for hunter (+100/-100) and each arbiter (+10 aligned, -5 deviated). Emits `SubmissionResolved`

Voting windows: 50 blocks for commits, 50 blocks for reveals. Simplified backup: resolve with 2 votes if one arbiter misses window.

**Contract-to-contract dependencies:**
```
ArbiterContract → BugSubmission.resolveSubmission()
ArbiterContract → ReputationRegistry.giveFeedback()
ArbiterContract → ValidationRegistry.getValidationStatus()
ArbiterContract → IdentityRegistry.isActive() + ownerOf()
BugSubmission   → BountyRegistry.deductPayout()
BugSubmission   → ReputationRegistry.getReputation()
BugSubmission   → IdentityRegistry.isActive()
```

## Section 3: Inference Layer

Provider-agnostic wrapper around the OpenAI SDK. Venice-first, any OpenAI-compatible endpoint as fallback.

```python
# agents/common/inference.py
# Configurable via env vars:
#   INFERENCE_BASE_URL (default: https://api.venice.ai/api/v1)
#   INFERENCE_API_KEY
#   INFERENCE_MODEL (default: llama-3.3-70b)
```

Single function interface: `complete(messages, model, temperature, max_tokens) → str`

Handles retries (max 2) and parse failure detection.

**Usage points:**
- Hunter reasoning: Slither findings + contract source → exploitability analysis + PoC strategy
- Arbiter evaluation: State Impact JSON + standard rubric → severity integer (0-4)
- Patch guidance: PoC + target source + state diff → remediation JSON

Venice free tier (10 prompts/day) sufficient for integration testing. Pro ($18/mo) for heavier development. Production: VVV staking for capacity.

## Section 4: Off-Chain Agents

### Common Layer (`agents/common/`)

- `inference.py` — Venice/OpenAI wrapper (see Section 3)
- `contracts.py` — Loads Foundry ABI artifacts from `contracts/out/`, typed Python wrappers via web3.py. Each agent has its own wallet (private key from env).
- `ipfs.py` — Upload/download via Pinata HTTP API (free tier). Returns CIDs.
- `crypto.py` — ECIES encrypt/decrypt via `eciespy`. Hunter encrypts with Executor pubkey (from IdentityRegistry metadata). Executor decrypts with its private key.

### Protocol Agent (`agents/protocol/`)

Simplest agent. Runs once to create bounty, then watches for resolution events.

- `agent.py` — CLI entrypoint. Modes: `create-bounty` (config-driven) and `watch` (event listener)
- `risk_model.py` — Hardcoded tier amounts for demo. Interface for future TVL-based calculation.
- `patch_receiver.py` — Listens for `PatchGuidance` event, fetches from IPFS, decrypts, displays remediation.

### Hunter Agent (`agents/hunter/`)

Event-driven: watches `BountyCreated`, runs analysis pipeline, submits findings.

- `agent.py` — Main loop: poll bounties → filter → analyze → submit
- `scanner.py` — Runs Slither on target contracts (from IPFS scopeHash). Parses JSON output for findings ≥ medium.
- `reasoning.py` — Sends Slither findings + contract source to Venice. Returns structured analysis with exploit feasibility.
- `poc_generator.py` — LLM generates full Foundry test script from analysis. Validates compilation before submitting.
- `submitter.py` — Encrypt (Executor pubkey) → IPFS upload → commitBug → wait 50 blocks → revealBug.

### Executor Service (`agents/executor/`)

Triggered by `BugRevealed` events. Trusted infrastructure.

- `service.py` — Event listener. On reveal: decrypt → run PoC → state diff → register → trigger arbiters
- `fork_runner.py` — `forge test --fork-url <rpc> --fork-block-number <N>` with hunter's PoC. Captures pass/fail + gas.
- `state_diff.py` — Compares pre/post state from fork execution. Produces State Impact JSON (balance changes, storage changes, impact flags).
- `abi_resolver.py` — Labels storage slots/addresses from known ABIs. For demo: our own deployed contract ABIs.
- `patch_guidance.py` — For valid CRITICAL/HIGH: sends PoC + source + diff to Venice with remediation prompt. Encrypts output with Protocol Agent pubkey. Uploads to IPFS. Emits `PatchGuidance` event.

### Arbiter Agents (3x) (`agents/arbiter/`)

Three instances, each with own wallet, agent ID, and model config:
- Slot 1: llama-3.3-70b, temperature 0.0
- Slot 2: llama-3.3-70b, temperature 0.1
- Slot 3: mistral-large, temperature 0.0

- `agent.py` — Listens for `JurySelected`. If selected: fetch state diff → evaluate → commit → reveal.
- `evaluator.py` — State Impact JSON + rubric → Venice → severity integer 0-4. Strict parsing, retry once on failure.
- `voter.py` — Random salt → keccak256(severity + salt) → commitVote → wait → revealVote.

All agents poll for events via web3.py HTTP RPC (no WebSocket needed).

## Section 5: Standard Severity Rubric

Applied by all arbiters, enforced platform-wide. Protocol Agents cannot define custom rubrics.

```
CRITICAL (4): Direct loss of funds, consensus failure, or permanent bricking
              of core contracts. Exploitable with no or minimal prerequisites.

HIGH (3):     Indirect fund loss, significant DoS (>1 hour), unauthorized
              privilege escalation to admin-equivalent roles. Exploitable
              with moderate prerequisites.

MEDIUM (2):   Limited fund loss (<$10k), temporary DoS (<1 hour), state
              corruption recoverable by admin action. Requires specific
              conditions.

LOW (1):      Informational findings, gas optimizations, best-practice
              violations with no direct exploit path.

INVALID (0):  Exploit failed, didn't compile, targeted wrong contract,
              or out of scope.
```

## Section 6: State Impact JSON Schema

The only input arbiters receive. Produced by the Executor from fork execution.

```json
{
  "bugId": 804,
  "bountyId": 12,
  "hunterAgentId": 42,
  "claimedSeverity": "CRITICAL",
  "execution": {
    "targetContract": "0x...",
    "forkBlock": 19234567,
    "chainId": 84532,
    "exploitSucceeded": true,
    "txReverted": false,
    "gasUsed": 450000,
    "outOfScope": false
  },
  "balanceChanges": [
    {
      "token": "USDC",
      "tokenAddress": "0x...",
      "holder": "0x...",
      "holderLabel": "Protocol Main Vault",
      "before": "10000000000000",
      "after": "0",
      "deltaUSD": "-10000000"
    }
  ],
  "storageChanges": [
    {
      "contract": "0x...",
      "contractLabel": "ProtocolX Router",
      "slot": "0x0",
      "slotLabel": "owner",
      "before": "0xProtocolMultisig",
      "after": "0xAttackerContract"
    }
  ],
  "impactFlags": {
    "directFundLoss": true,
    "fundLossUSD": 10000000,
    "contractBricked": false,
    "unauthorizedRoleChange": true,
    "dosDetected": false,
    "oracleManipulation": false
  },
  "executorAgentId": 88,
  "validationRequestHash": "0x...",
  "stateImpactCID": "Qm..."
}
```

Arbiters never see hunter prose, PoC source, or any hunter-authored text. This is the prompt-injection firewall.

## Section 7: Web Dashboard

React + Vite + TypeScript + ethers.js + Tailwind CSS. Read-only, no wallet connection. Polls Base Sepolia RPC every 5 seconds.

### Pages

**Bounties List** — Table of active bounties from `BountyCreated` events. Name, funding, tiers, deadline countdown, remaining funds, submission count.

**Bounty Detail** — Bounty parameters + submissions list. Each submission: hunter agent ID, claimed severity, status (Committed → Revealed → Evaluating → Resolved), final severity, payout.

**Submission Detail** — Full pipeline view:
- Commit hash + block
- Reveal status + encrypted CID
- State diff rendered as readable diff (balance changes red/green, storage changes with labels, impact flags as badges)
- 3 arbiter vote cards (commit status → revealed severity), median calculation
- Final verdict + payout tx hash
- Patch guidance status

**Agents** — All registered agents from IdentityRegistry. Type, reputation score, feedback history.

**Live Feed** — Scrolling event log. Every on-chain event as a timestamped card. This is the demo-mode view.

### Tech

- ethers.js provider + React Query for caching
- Contract ABIs copied from Foundry artifacts at build time
- No backend, no Redux, no wallet connection

## Section 8: Vulnerable Demo Contracts

Three intentionally buggy contracts deployed on Base Sepolia.

**ReentrancyVault.sol** — Classic reentrancy. Vault with deposit/withdraw that updates balances after external call. Expected: CRITICAL. State diff: vault drained, attacker balance increases.

**AccessControlToken.sol** — Missing access control on `mint()`. Anyone can mint unlimited tokens. Expected: HIGH. State diff: attacker balance increases, total supply inflates.

**OracleManipulation.sol** — Lending contract with manipulable on-chain price feed. Attacker updates price, borrows at inflated collateral value, drains pool. Expected: CRITICAL. State diff: pool drained, oracle price changed.

## Section 9: Demo Flow

`scripts/demo_flow.py` orchestrates the full lifecycle:

1. Deploy all contracts (ERC-8004 registries, core contracts, MockUSDC, vulnerable contracts)
2. Mint agent IDs (1 protocol, 1 hunter, 3 arbiters, 1 executor) + register metadata
3. Protocol Agent creates bounty — 50,000 MockUSDC targeting the 3 vulnerable contracts
4. Hunter Agent scans → Slither finds reentrancy + access control → LLM reasons → generates PoCs
5. Hunter commits first finding (ReentrancyVault), waits 50 blocks, reveals
6. Executor forks → runs PoC → vault drained → State Impact JSON → registers on-chain
7. 3 Arbiters selected → evaluate via Venice → blind commit → reveal → median = CRITICAL → 25,000 MockUSDC payout
8. Executor generates patch guidance via Venice → encrypted to Protocol Agent → "Add nonReentrant modifier"
9. Repeat for AccessControlToken (HIGH, smaller payout)
10. Protocol Agent withdraws remainder after deadline

**Timing:** ~2-3 minutes per finding on Base Sepolia (~2s blocks). Full demo with 2 findings: ~10 minutes.

## Section 10: Testing Strategy

### Contract Tests (Foundry)

- **Unit:** Each contract in isolation — BountyRegistry, BugSubmission, ArbiterContract, all 3 registries
- **Integration:** Full lifecycle in single test — create bounty → commit → reveal → state impact → 3 votes → resolve → verify payout + reputation

### Agent Tests (pytest)

- `inference.py` — Mock responses, retry logic, parse failures
- `scanner.py` — Slither against vulnerable contracts, assert expected findings
- `evaluator.py` — Known State Impact JSONs → assert correct severity
- `submitter.py` — Encrypt/decrypt roundtrip, commit hash generation
- `state_diff.py` — State Impact JSON generation from known fork output

### End-to-End

`demo_flow.py` is the E2E test. Assertions at each step. All agent tests touching the chain run against local Anvil with deployed contracts. No contract mocking in Python.

## Build Order (Vertical Slices)

1. **Slice 1:** ERC-8004 registries + identity minting (contracts + Python scripts)
2. **Slice 2:** Bounty creation (BountyRegistry + Protocol Agent + dashboard bounties page)
3. **Slice 3:** Submission flow (BugSubmission + Hunter Agent + dashboard submission view)
4. **Slice 4:** Execution + Arbitration (Executor + ArbiterContract + 3 arbiters + dashboard votes + payout)
5. **Slice 5:** Patch guidance (Venice remediation + encrypted delivery + dashboard status)

Each slice is independently demoable. If stopped at any slice, there's a working demo of everything built so far.
