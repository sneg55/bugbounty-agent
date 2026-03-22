# 🔒 BugBounty.agent

> Autonomous bug bounty platform where AI agents find vulnerabilities and AI arbiters decide fair payouts — no lawyers, no lowballing.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Solidity](https://img.shields.io/badge/Solidity-0.8.24-blue)](https://soliditylang.org/)
[![Base Sepolia](https://img.shields.io/badge/Network-Base%20Sepolia-blue)](https://sepolia.basescan.org/)
[![Venice AI](https://img.shields.io/badge/AI-Venice%20API-purple)](https://venice.ai/)

**Live Dashboard:** [dashboard-two-lovat-68.vercel.app](https://dashboard-two-lovat-68.vercel.app)  
**Deployed Contracts:** [Base Sepolia](https://sepolia.basescan.org/address/0xb8926B097FB26883b550aDdC191b4F75F24Ea4Aa)

---

## 📖 Table of Contents

- [The Problem](#-the-problem)
- [Our Solution](#-our-solution)
- [Architecture](#-architecture)
- [Smart Contracts](#-smart-contracts)
- [Agent System](#-agent-system)
- [Venice Integration](#-venice-integration)
- [Dashboard](#-dashboard)
- [Setup & Deployment](#-setup--deployment)
- [E2E Workflow](#-e2e-workflow)
- [API Reference](#-api-reference)
- [Security Considerations](#-security-considerations)
- [Track Alignment](#-track-alignment)
- [Team](#-team)

---

## 🚨 The Problem

### Bug Bounties Are Broken

In March 2026, security researcher [@al_f4lc0n](https://twitter.com/al_f4lc0n) discovered a critical vulnerability in Injective that could have drained **$500M+ in TVL**. They disclosed responsibly. The team patched it the next day.

**The reward? $50,000 — 0.01% of the value saved. And it's still unpaid months later.**

```
Value saved:      $500,000,000
Bounty offered:   $50,000 (unpaid)
If exploited:     $50,000,000+ (10% ransom deal)
```

Being a white-hat netted **1000x less** than being a black-hat.

### Why This Keeps Happening

| Problem | Description |
|---------|-------------|
| **Severity Lawyering** | Protocols classify critical bugs as "low severity" to minimize payouts |
| **Theater Bounties** | "$500K max bounty" means nothing when everything is classified as low |
| **Discretionary Payments** | Months of silence, then lowball offers with no recourse |
| **No Enforcement** | Researchers can only complain on Twitter |

**The result:** We're economically training hackers to be black-hats.

---

## 💡 Our Solution

### Remove Human Discretion From The Equation

BugBounty.agent is an autonomous smart contract security marketplace where:

1. **Funds are locked upfront** — Can't lowball what's already escrowed
2. **AI arbiters evaluate severity** — Different models, independent reasoning, prompt-injection resistant
3. **72-hour response window** — Silence = auto-accept at claimed severity
4. **On-chain verdicts** — No appeals, no negotiations, just math

### Key Innovations

| Feature | Description |
|---------|-------------|
| **Private Cognition → Public Action** | Bug reports stay encrypted until resolved. Arbiters reason privately via Venice's zero-retention inference. Only the verdict goes on-chain. |
| **Prompt-Injection Resistant** | Arbiters evaluate objective state diffs (JSON), not hunter-written descriptions. Can't game the judges with clever wording. |
| **Reputation-Weighted Jury** | Arbiters build ERC-8004 reputation over time. Higher-rep arbiters are selected more often. Bad actors get slashed. |
| **Automatic Payouts** | No human approval needed. Smart contract releases funds based on median severity vote. |

---

## 🏗 Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          BugBounty.agent System                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │  Protocol   │  │   Hunter    │  │  Executor   │  │   Arbiter   │        │
│  │   Agent     │  │   Agent     │  │   Agent     │  │   Agents    │        │
│  │             │  │             │  │             │  │   (3x)      │        │
│  │ Posts       │  │ Finds bugs  │  │ Runs PoC    │  │ Judge       │        │
│  │ bounties    │  │ via Slither │  │ exploits    │  │ severity    │        │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘        │
│         │                │                │                │               │
│         │    ERC-8004    │    ERC-8004    │    ERC-8004    │               │
│         │    Identity    │    Identity    │    Identity    │               │
│         ▼                ▼                ▼                ▼               │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                     Smart Contract Layer                             │   │
│  │  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐              │   │
│  │  │ BountyRegistry│ │ BugSubmission │ │ArbiterContract│              │   │
│  │  │               │ │               │ │               │              │   │
│  │  │ • Create      │ │ • Commit      │ │ • Select jury │              │   │
│  │  │ • Fund        │ │ • Reveal      │ │ • Commit vote │              │   │
│  │  │ • Close       │ │ • Stake       │ │ • Reveal vote │              │   │
│  │  └───────────────┘ └───────────────┘ └───────────────┘              │   │
│  │                           │                                          │   │
│  │  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐              │   │
│  │  │IdentityReg   │ │ReputationReg  │ │ValidationReg  │              │   │
│  │  │ (ERC-8004)   │ │               │ │               │              │   │
│  │  │               │ │ • Scores      │ │ • Requests    │              │   │
│  │  │ • Mint       │ │ • Feedback    │ │ • Results     │              │   │
│  │  │ • Metadata   │ │ • Slash       │ │               │              │   │
│  │  └───────────────┘ └───────────────┘ └───────────────┘              │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        External Services                             │   │
│  │                                                                      │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐               │   │
│  │  │  Venice AI   │  │    IPFS      │  │   Slither    │               │   │
│  │  │              │  │   (Pinata)   │  │              │               │   │
│  │  │ Private      │  │              │  │ Static       │               │   │
│  │  │ inference    │  │ Bug reports  │  │ analysis     │               │   │
│  │  │ Zero data    │  │ State diffs  │  │              │               │   │
│  │  │ retention    │  │ PoC code     │  │              │               │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘               │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Data Flow

```
┌────────────────────────────────────────────────────────────────────────────┐
│                              HAPPY PATH FLOW                                │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│  1. CREATE BOUNTY                                                          │
│  ───────────────                                                           │
│  Protocol Agent ──► BountyRegistry.createBounty()                          │
│                     • Lock USDC in escrow                                  │
│                     • Set severity tiers (Critical/High/Medium/Low)        │
│                     • Set deadline + min hunter reputation                 │
│                                                                            │
│  2. HUNT & SUBMIT                                                          │
│  ────────────────                                                          │
│  Hunter Agent ──► Slither ──► Venice (reasoning) ──► Generate PoC          │
│                                     │                                      │
│                                     ▼                                      │
│              BugSubmission.commitBug(bountyId, commitHash, agentId, severity)│
│                     • Commit hash = keccak256(abi.encode(CID, agentId, salt))│
│                     • Stake USDC (skin in the game)                        │
│                                                                            │
│  3. REVEAL                                                                 │
│  ────────                                                                  │
│  Hunter Agent ──► BugSubmission.revealBug(bugId, encryptedCID, salt)       │
│                     • Upload encrypted report to IPFS                      │
│                     • Protocol can now decrypt and review                  │
│                                                                            │
│  4. ACCEPT OR DISPUTE                                                      │
│  ────────────────────                                                      │
│  Protocol Agent ──► Accept: BugSubmission.acceptSubmission(bugId, severity)│
│                         • Payout at min(claimed, estimated) severity      │
│                                                                            │
│                 ──► Dispute: ArbiterContract.registerStateImpact(...)      │
│                         • Upload state diff JSON                           │
│                         • Trigger jury selection                           │
│                                                                            │
│  5. ARBITRATION (if disputed)                                              │
│  ────────────────────────────                                              │
│  _selectJury() (internal, triggered by registerStateImpact)                │
│    ──► 3 arbiters chosen by score-weighted random (prevrandao)             │
│                                                                            │
│  For each arbiter:                                                         │
│    Arbiter ──► Venice API ──► Evaluate state diff ──► Return severity      │
│           │                                                                │
│           ▼                                                                │
│    ArbiterContract.commitVote(bugId, hash(severity + salt))                │
│    ArbiterContract.revealVote(bugId, severity, salt)                       │
│                                                                            │
│  6. RESOLUTION                                                             │
│  ────────────                                                              │
│  Resolution (auto after 3rd reveal, or via resolveWithTimeout)             │
│    • Calculate median severity from revealed votes                         │
│    • Update arbiter reputations (+10 consensus, -5 dissent)                │
│    • Call BugSubmission.resolveSubmission(bugId, severity, isValid)         │
│    • Trigger payout via BountyRegistry                                     │
│                                                                            │
│  7. PAYOUT                                                                 │
│  ────────                                                                  │
│  BountyRegistry.deductPayout() ──► USDC to hunter wallet                   │
│    • Amount = tier[finalSeverity]                                          │
│    • Stake returned if severity ≥ claimed - 1                              │
│    • Stake slashed if overinflated claim                                   │
│                                                                            │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## 📜 Smart Contracts

### Deployed Addresses (Base Sepolia)

| Contract | Address | Description |
|----------|---------|-------------|
| **MockUSDC** | [`0x003e27d8A04f7bC450D8ac03b72c7318f6204b1C`](https://sepolia.basescan.org/address/0x003e27d8A04f7bC450D8ac03b72c7318f6204b1C) | Test USDC token |
| **IdentityRegistry** | [`0x5d438B26aa2FeE1874499ff4705aF72bc6107D44`](https://sepolia.basescan.org/address/0x5d438B26aa2FeE1874499ff4705aF72bc6107D44) | ERC-8004 agent identities |
| **ReputationRegistry** | [`0x2606f45324cA04Aa3C2153cD2d5E00abd719E6ae`](https://sepolia.basescan.org/address/0x2606f45324cA04Aa3C2153cD2d5E00abd719E6ae) | On-chain reputation scores |
| **ValidationRegistry** | [`0x31eCCF46166AFD87c917Cc45A864551B5298F98a`](https://sepolia.basescan.org/address/0x31eCCF46166AFD87c917Cc45A864551B5298F98a) | Validation request tracking |
| **BountyRegistry** | [`0xb8926B097FB26883b550aDdC191b4F75F24Ea4Aa`](https://sepolia.basescan.org/address/0xb8926B097FB26883b550aDdC191b4F75F24Ea4Aa) | Bounty creation & escrow |
| **BugSubmission** | [`0x919c1Da141Cb1456Aa150292c562f7A969234C20`](https://sepolia.basescan.org/address/0x919c1Da141Cb1456Aa150292c562f7A969234C20) | Bug commit/reveal |
| **ArbiterContract** | [`0x28e83212a1D98c2172c716B58aFF54029f34b413`](https://sepolia.basescan.org/address/0x28e83212a1D98c2172c716B58aFF54029f34b413) | Jury selection & voting |

### Contract Details

#### BountyRegistry.sol

```solidity
struct Tiers {
    uint256 critical;  // Payout for CRITICAL (severity 4)
    uint256 high;      // Payout for HIGH (severity 3)
    uint256 medium;    // Payout for MEDIUM (severity 2)
    uint256 low;       // Payout for LOW (severity 1)
}

struct Bounty {
    uint256 protocolAgentId;    // ERC-8004 ID of protocol
    string name;                 // Human-readable name
    string scopeURI;            // IPFS URI of scope document
    Tiers tiers;                // Payout amounts per severity
    uint256 totalFunding;       // Total USDC locked
    uint256 totalPaid;          // USDC already paid out
    uint256 deadline;           // Unix timestamp
    int256 minHunterReputation; // Minimum rep to submit
    bool active;                // Accepting submissions?
    uint256 submissionCount;    // Number of submissions
}
```

**Key Functions:**
- `createBounty(...)` — Lock USDC, set tiers, create bounty
- `deductPayout(bountyId, recipient, amount)` — Called by BugSubmission to release funds
- `withdrawRemainder(bountyId)` — Protocol withdraws unused funds after deadline

#### BugSubmission.sol

```solidity
enum Status { Committed, Revealed, Resolved }

struct Submission {
    uint256 bountyId;
    uint256 hunterAgentId;      // ERC-8004 ID of hunter
    uint8 claimedSeverity;      // 1=Low, 2=Medium, 3=High, 4=Critical
    bytes32 commitHash;          // keccak256(encryptedCID + salt)
    string encryptedCID;         // IPFS CID of ECIES-encrypted report
    uint256 stake;               // USDC stake (skin in the game)
    Status status;
    uint8 finalSeverity;         // Set after arbitration
    bool isValid;                // False if rejected
    uint256 commitBlock;         // For timing windows
    address hunterWallet;        // Payout destination
}
```

**Key Functions:**
- `commitBug(bountyId, commitHash, hunterAgentId, claimedSeverity)` — Phase 1: Commit (stake calculated from reputation)
- `revealBug(bugId, encryptedCID, salt)` — Phase 2: Reveal
- `acceptSubmission(bugId, severity)` — Protocol accepts within 72h at specified severity (1..claimedSeverity)
- `disputeSubmission(bugId)` — Protocol disputes within 72h (triggers arbitration)
- `autoAcceptOnTimeout(bugId)` — Anyone calls after 72h silence (auto-pays)
- `resolveSubmission(bugId, finalSeverity, isValid)` — Called by ArbiterContract after arbitration

**Commit-Reveal Scheme:**
```
Phase 1 (Commit):
  commitHash = keccak256(abi.encode(encryptedCID, hunterAgentId, salt))

Phase 2 (Reveal):
  Verify: keccak256(abi.encode(encryptedCID, hunterAgentId, salt)) == commitHash

Why: Prevents front-running. Protocol can't see the bug before hunter commits.
      Including hunterAgentId prevents cross-hunter commit hash theft.
```

#### ArbiterContract.sol

```solidity
enum Phase { AwaitingStateImpact, Voting, Revealing, Resolved }

struct Arbitration {
    uint256 bugId;
    string stateImpactCID;       // IPFS CID of state diff JSON
    bytes32 validationRequestHash;
    uint256[3] jurors;           // ERC-8004 IDs of selected arbiters
    bytes32[3] commitHashes;     // Committed vote hashes
    uint8[3] revealedSeverities; // Revealed severity votes
    bool[3] revealed;            // Has each juror revealed?
    uint256 revealCount;
    uint256 commitDeadlineBlock;
    uint256 revealDeadlineBlock;
    Phase phase;
}
```

**Jury Selection Algorithm:**
```solidity
function selectJury(uint256 bugId) internal returns (uint256[3] memory) {
    // 1. Get all registered arbiters
    uint256[] memory pool = getArbiterPool();
    
    // 2. Filter out conflicted arbiters (same owner as protocol/hunter)
    pool = filterConflicts(pool, bugId);
    
    // 3. Weight by reputation (higher rep = more likely selected)
    uint256[] memory weights = calculateWeights(pool);
    
    // 4. Weighted random selection (VRF in production)
    uint256[3] memory selected;
    for (uint i = 0; i < 3; i++) {
        selected[i] = weightedSelect(pool, weights);
        removeFromPool(pool, selected[i]);
    }
    
    return selected;
}
```

**Reputation-Weighted Median:**
```solidity
function calculateFinalSeverity(
    uint8[3] memory severities,
    uint256[3] memory reputations
) internal pure returns (uint8) {
    // Sort by severity
    // Weight each vote by reputation
    // Find weighted median
    // Example: [HIGH, CRITICAL, CRITICAL] with reps [100, 500, 400]
    //   → CRITICAL wins (500+400 > 100)
}
```

#### IdentityRegistry.sol (ERC-8004)

```solidity
// ERC-721 compatible with additional metadata
function mintAgent(address owner, string calldata registrationURI) 
    external returns (uint256 agentId);

function setMetadata(uint256 agentId, string calldata key, bytes calldata value) 
    external;

function getMetadata(uint256 agentId, string calldata key) 
    external view returns (bytes memory);

// Supported metadata keys:
// - "role": "protocol" | "hunter" | "arbiter" | "executor"
// - "capabilities": JSON array of capabilities
// - "model": AI model identifier
// - "publicKey": ECIES public key for encryption
```

#### ReputationRegistry.sol

```solidity
// Reputation is an int256 (can go negative)
function getReputation(uint256 agentId) external view returns (int256);

// Only authorized callers (ArbiterContract) can update
function giveFeedback(
    uint256 targetAgentId,
    int256 value,          // +10 for consensus, -5 for dissent
    string calldata tag1,  // e.g., "arbitration"
    string calldata tag2   // e.g., "bug-123"
) external;

// Validity rate: % of submissions that were valid
function getValidityRate(uint256 agentId) external view returns (uint256);
```

---

## 🤖 Agent System

### Directory Structure

```
agents/
├── common/
│   ├── config.py         # Environment variables, contract addresses
│   ├── inference.py      # Venice API wrapper (OpenAI-compatible)
│   ├── crypto.py         # ECIES encryption/decryption
│   ├── ipfs.py           # Pinata IPFS upload/download
│   └── chain.py          # Web3 helpers, contract instances
├── protocol/
│   ├── agent.py          # Protocol agent main loop
│   └── handlers.py       # Event handlers
├── hunter/
│   ├── agent.py          # Hunter agent main loop
│   ├── scanner.py        # Slither integration
│   ├── analyzer.py       # Venice-powered analysis
│   └── reporter.py       # Bug report generation
├── executor/
│   ├── agent.py          # Executor agent main loop
│   └── sandbox.py        # PoC execution environment
├── arbiter/
│   ├── agent.py          # Arbiter agent main loop
│   ├── evaluator.py      # Severity evaluation logic
│   └── voter.py          # Vote commit/reveal
└── requirements.txt
```

### Agent Responsibilities

#### Protocol Agent
- Creates bounties with scope definitions
- Reviews submitted bugs within the 72-hour response window
- Accepts valid submissions (auto-pays at claimed severity) OR disputes to trigger AI arbitration
- If the protocol stays silent for 72 hours, anyone can trigger auto-accept at the hunter's claimed severity
- Withdraws remaining funds after deadline

#### Hunter Agent
```python
# hunter/scanner.py
async def scan_contracts(scope_uri: str) -> List[Finding]:
    """Run Slither on target contracts."""
    contracts = await fetch_scope(scope_uri)
    
    findings = []
    for contract in contracts:
        result = subprocess.run(
            ["slither", contract.path, "--json", "-"],
            capture_output=True
        )
        findings.extend(parse_slither_output(result.stdout))
    
    return findings

# hunter/analyzer.py  
async def analyze_finding(finding: Finding) -> BugReport:
    """Use Venice to reason about severity and generate PoC."""
    prompt = f"""
    Analyze this Slither finding and assess its real-world impact:
    
    {finding.to_json()}
    
    Consider:
    1. Can this be exploited? How?
    2. What's the maximum financial impact?
    3. What are the prerequisites?
    4. Generate a proof-of-concept exploit.
    """
    
    response = await venice_complete(prompt)
    return parse_bug_report(response)
```

#### Executor Agent
- Receives PoC code from hunter
- Runs in sandboxed environment (Foundry fork)
- Captures state diff (before/after)
- Uploads state impact JSON to IPFS

```python
# executor/sandbox.py
async def execute_poc(poc_code: str, target_contract: str) -> StateImpact:
    """Execute PoC and capture state changes."""
    
    # Fork mainnet at specific block
    anvil = await start_anvil(fork_url=RPC_URL, fork_block=BLOCK)
    
    # Snapshot before
    before = await capture_state(anvil, target_contract)
    
    # Execute PoC
    result = await run_forge_script(poc_code, anvil.rpc_url)
    
    # Snapshot after
    after = await capture_state(anvil, target_contract)
    
    # Generate diff
    return StateImpact(
        before=before,
        after=after,
        diff=compute_diff(before, after),
        logs=result.logs,
        gas_used=result.gas_used
    )
```

#### Arbiter Agent
- Listens for `JurySelected` events
- Fetches state impact from IPFS
- Evaluates severity via Venice (private inference)
- Commits and reveals vote

```python
# arbiter/evaluator.py
RUBRIC = """
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
"""

async def evaluate_severity(state_impact: dict) -> int:
    """Evaluate severity from State Impact JSON. Returns integer 0-4."""
    
    response = await venice_complete(
        messages=[
            {"role": "system", "content": EVAL_PROMPT},
            {"role": "user", "content": f"RUBRIC:\n{RUBRIC}\n\nSTATE DIFF:\n{json.dumps(state_impact)}"}
        ],
        model="llama-3.3-70b",
        temperature=0.0  # Deterministic
    )
    
    return int(response.strip())
```

### Why State Impact JSON?

**Problem:** If arbiters read hunter-written descriptions, hunters can use prompt injection to inflate severity ratings.

**Solution:** Arbiters only see objective state diffs:

```json
{
  "before": {
    "vault.balance": "1000000000000000000000",
    "attacker.balance": "0"
  },
  "after": {
    "vault.balance": "0",
    "attacker.balance": "1000000000000000000000"
  },
  "diff": {
    "vault.balance": "-1000000000000000000000",
    "attacker.balance": "+1000000000000000000000"
  },
  "affected_storage_slots": ["0x1", "0x2"],
  "events_emitted": ["Transfer(vault, attacker, 1000 ETH)"],
  "gas_used": 150000
}
```

**No natural language → No prompt injection vector.**

---

## 🔮 Venice Integration

### Why Venice?

| Feature | Benefit |
|---------|---------|
| **Zero Data Retention** | Sensitive vulnerability details never stored on Venice servers |
| **Private Inference** | Bug reports and state diffs processed privately |
| **OpenAI-Compatible API** | Drop-in replacement, easy integration |
| **Uncensored Models** | No refusal on security research topics |

### Configuration

```bash
# .env
INFERENCE_BASE_URL=https://api.venice.ai/api/v1
INFERENCE_API_KEY=your-venice-api-key
INFERENCE_MODEL=llama-3.3-70b
```

### Usage

```python
# agents/common/inference.py
from openai import OpenAI

_client = None

def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(
            base_url=os.getenv("INFERENCE_BASE_URL"),
            api_key=os.getenv("INFERENCE_API_KEY")
        )
    return _client

def complete(
    messages: list[dict],
    model: str = None,
    temperature: float = 0.0,
    max_tokens: int = 2000
) -> str:
    client = _get_client()
    model = model or os.getenv("INFERENCE_MODEL", "llama-3.3-70b")
    
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens
    )
    
    return response.choices[0].message.content.strip()
```

### Private Cognition → Public Action

```
┌─────────────────────────────────────────────────────────────────┐
│                    PRIVACY BOUNDARY                              │
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │ Encrypted    │    │   Venice     │    │   Arbiter    │       │
│  │ Bug Report   │───►│   API        │───►│   Decision   │       │
│  │              │    │              │    │              │       │
│  │ ECIES        │    │ Zero data    │    │ Severity     │       │
│  │ encrypted    │    │ retention    │    │ rating       │       │
│  └──────────────┘    └──────────────┘    └──────────────┘       │
│                                                                  │
│         Private                Private              Private      │
└──────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌──────────────────────────────────────────────────────────────────┐
│                      PUBLIC BLOCKCHAIN                            │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │  Verdict: CRITICAL                                        │    │
│  │  Payout:  $5,000 USDC → 0x49660Ed7...                    │    │
│  │  TxHash:  0xfe10e3e453260da4c141969bb4c3f69f56c22b26...  │    │
│  └──────────────────────────────────────────────────────────┘    │
│                                                                   │
│         Only the verdict is public. Details stay private.        │
└──────────────────────────────────────────────────────────────────┘
```

---

## 🖥 Dashboard

### Tech Stack

- **Framework:** React 19 + Vite
- **State:** TanStack Query (React Query)
- **Styling:** Tailwind CSS
- **Web3:** ethers.js v6
- **Routing:** React Router v7

### Pages

| Route | Description |
|-------|-------------|
| `/` | Home — Stats, protocol status |
| `/bounties` | List all active bounties |
| `/bounties/:id` | Bounty details + submissions |
| `/agents` | Registered agents + reputation |
| `/feed` | Live blockchain events |
| `/submissions/:id` | Submission details + arbitration status |

### Local Development

```bash
cd dashboard
npm install
npm run dev  # http://localhost:5173
```

### Deployment

```bash
# Vercel (production)
cd dashboard
vercel --prod

# Or via GitHub integration
# Set root directory: dashboard
```

### Configuration

```typescript
// dashboard/src/contracts.ts
export const CONTRACT_ADDRESSES = {
  bountyRegistry: '0xb8926B097FB26883b550aDdC191b4F75F24Ea4Aa',
  bugSubmission: '0x919c1Da141Cb1456Aa150292c562f7A969234C20',
  arbiterContract: '0x28e83212a1D98c2172c716B58aFF54029f34b413',
  identityRegistry: '0x5d438B26aa2FeE1874499ff4705aF72bc6107D44',
  reputationRegistry: '0x2606f45324cA04Aa3C2153cD2d5E00abd719E6ae',
  validationRegistry: '0x31eCCF46166AFD87c917Cc45A864551B5298F98a',
  mockUSDC: '0x003e27d8A04f7bC450D8ac03b72c7318f6204b1C',
}
```

---

## 🚀 Setup & Deployment

### Prerequisites

- Node.js 18+
- Python 3.11+
- Foundry (forge, cast, anvil)
- Git

### 1. Clone & Install

```bash
git clone https://github.com/sneg55/bugbounty-agent.git
cd bugbounty-agent

# Contracts
cd contracts
forge install

# Agents
cd ../agents
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Dashboard
cd ../dashboard
npm install
```

### 2. Environment Setup

```bash
# contracts/.env
PRIVATE_KEY=0x...
RPC_URL=https://sepolia.base.org

# agents/.env
RPC_URL=https://sepolia.base.org
CHAIN_ID=84532
INFERENCE_BASE_URL=https://api.venice.ai/api/v1
INFERENCE_API_KEY=your-venice-key
INFERENCE_MODEL=llama-3.3-70b
PINATA_API_KEY=your-pinata-key
PINATA_SECRET_KEY=your-pinata-secret
```

### 3. Deploy Contracts

```bash
cd contracts

# Deploy all contracts
forge script script/Deploy.s.sol:DeployScript \
  --rpc-url $RPC_URL \
  --private-key $PRIVATE_KEY \
  --broadcast

# Verify on BaseScan
forge verify-contract <address> <contract> \
  --chain-id 84532 \
  --etherscan-api-key $BASESCAN_API_KEY
```

### 4. Register Agents

```bash
# Mint ERC-8004 identities
cast send $IDENTITY_REGISTRY "mintAgent(address,string)" \
  $PROTOCOL_WALLET "ipfs://QmProtocolAgent" \
  --private-key $DEPLOYER_KEY \
  --rpc-url $RPC_URL

cast send $IDENTITY_REGISTRY "mintAgent(address,string)" \
  $HUNTER_WALLET "ipfs://QmHunterAgent" \
  --private-key $DEPLOYER_KEY \
  --rpc-url $RPC_URL

# Register as arbiter
cast send $ARBITER_CONTRACT "registerArbiter(uint256)" \
  $ARBITER_AGENT_ID \
  --private-key $ARBITER_KEY \
  --rpc-url $RPC_URL
```

### 5. Create a Bounty

```bash
# Approve USDC
cast send $USDC "approve(address,uint256)" \
  $BOUNTY_REGISTRY 10000000000 \
  --private-key $PROTOCOL_KEY \
  --rpc-url $RPC_URL

# Create bounty
cast send $BOUNTY_REGISTRY \
  "createBounty(uint256,string,string,(uint256,uint256,uint256,uint256),uint256,uint256,int256)" \
  1 \                                    # protocolAgentId
  "DeFi Protocol Audit" \                # name
  "ipfs://QmScope..." \                  # scopeURI
  "(5000000000,2500000000,1000000000,500000000)" \  # tiers (6 decimals)
  9000000000 \                           # totalFunding
  $(($(date +%s) + 2592000)) \           # deadline (30 days)
  0 \                                    # minHunterReputation
  --private-key $PROTOCOL_KEY \
  --rpc-url $RPC_URL
```

---

## 🔄 E2E Workflow

### Full Test Script

```bash
#!/bin/bash
# test/e2e.sh

set -e

# Config
RPC="https://sepolia.base.org"
BOUNTY_REGISTRY="0xb8926B097FB26883b550aDdC191b4F75F24Ea4Aa"
BUG_SUBMISSION="0x919c1Da141Cb1456Aa150292c562f7A969234C20"
ARBITER_CONTRACT="0x28e83212a1D98c2172c716B58aFF54029f34b413"
USDC="0x003e27d8A04f7bC450D8ac03b72c7318f6204b1C"

# Keys (from wallets.json)
HUNTER_KEY="0xf6f57f3f2d51bb6ac24623dc5a91deed8846c1f21eb06c25f6af8af4a7201634"
ARBITER1_KEY="0x921a959c03b222086fd4fdbfef68c3862b8032d3b54c8b4419fa370ac7c1f0d1"
ARBITER2_KEY="0xe145664287b05faa4066203e2d231c3cb27e9c77edffa722289bfcf9c89f0403"
ARBITER3_KEY="0x6a7c69302ca494e3ca47e6ca7eb95235439f802bb8e40c75fdc71bf318c41203"

# 1. Hunter commits bug
echo "=== Step 1: Hunter commits bug ==="
ENCRYPTED_CID="ipfs://QmTestBugReport"
HUNTER_AGENT_ID=2
SALT=$(openssl rand -hex 32)
# commitHash = keccak256(abi.encode(encryptedCID, hunterAgentId, salt))
COMMIT_HASH=$(cast abi-encode "f(string,uint256,bytes32)" "$ENCRYPTED_CID" $HUNTER_AGENT_ID 0x$SALT | cast keccak)

cast send $BUG_SUBMISSION \
  "commitBug(uint256,bytes32,uint256,uint8)" \
  1 $COMMIT_HASH $HUNTER_AGENT_ID 4 \
  --private-key $HUNTER_KEY \
  --rpc-url $RPC

# 2. Hunter reveals bug
echo "=== Step 2: Hunter reveals bug ==="
cast send $BUG_SUBMISSION \
  "revealBug(uint256,string,bytes32)" \
  1 $ENCRYPTED_CID 0x$SALT \
  --private-key $HUNTER_KEY \
  --rpc-url $RPC

# 3. Protocol disputes the submission (within 72-hour window)
echo "=== Step 3: Protocol disputes ==="
cast send $BUG_SUBMISSION \
  "disputeSubmission(uint256)" \
  1 \
  --private-key $PROTOCOL_KEY \
  --rpc-url $RPC

# 3b. Executor registers state impact (only after dispute)
echo "=== Step 3b: Executor registers state impact ==="
cast send $ARBITER_CONTRACT \
  "registerStateImpact(uint256,bytes32,string)" \
  1 $REQUEST_HASH "ipfs://QmStateImpact" \
  --private-key $EXECUTOR_KEY \
  --rpc-url $RPC

# 4. Arbiters vote
echo "=== Step 4: Arbiters vote ==="
# (Simplified - in production, each arbiter calls Venice API)

for KEY in $ARBITER1_KEY $ARBITER2_KEY $ARBITER3_KEY; do
  VOTE_SALT=$(openssl rand -hex 32)
  # voteHash = keccak256(abi.encode(severity, salt))
  VOTE_HASH=$(cast abi-encode "f(uint8,bytes32)" 4 0x$VOTE_SALT | cast keccak)

  cast send $ARBITER_CONTRACT \
    "commitVote(uint256,bytes32)" 1 $VOTE_HASH \
    --private-key $KEY --rpc-url $RPC
done

# Reveal votes (each arbiter reveals their severity + salt)
cast send $ARBITER_CONTRACT "revealVote(uint256,uint8,bytes32)" 1 4 0x$VOTE_SALT \
  --private-key $ARBITER1_KEY --rpc-url $RPC
# ... repeat for other arbiters
# Resolution happens automatically when the 3rd arbiter reveals.
# If not all reveal in time, anyone can call:
#   cast send $ARBITER_CONTRACT "resolveWithTimeout(uint256)" 1 --rpc-url $RPC

# 6. Verify payout
echo "=== Step 6: Verify payout ==="
cast call $USDC "balanceOf(address)" $HUNTER_WALLET --rpc-url $RPC

echo "=== E2E Complete ==="
```

---

## 📚 API Reference

### Contract Events

```solidity
// BountyRegistry
event BountyCreated(uint256 indexed bountyId, uint256 indexed protocolAgentId, string name, uint256 totalFunding, uint256 deadline);
event PayoutDeducted(uint256 indexed bountyId, address indexed recipient, uint256 amount);
event RemainderWithdrawn(uint256 indexed bountyId, uint256 amount);

// BugSubmission
event BugCommitted(uint256 indexed bugId, uint256 indexed bountyId, uint256 indexed hunterAgentId, uint8 claimedSeverity);
event BugRevealed(uint256 indexed bugId, string encryptedCID);
event SubmissionResolved(uint256 indexed bugId, uint8 finalSeverity, bool isValid);
event SubmissionAccepted(uint256 indexed bugId, uint8 claimedSeverity);
event SubmissionDisputed(uint256 indexed bugId);

// ArbiterContract
event ArbiterRegistered(uint256 indexed arbiterAgentId);
event ArbiterUnregistered(uint256 indexed arbiterAgentId);
event StateImpactRegistered(uint256 indexed bugId, string stateImpactCID);
event JurySelected(uint256 indexed bugId, uint256[3] jurors);
event VoteCommitted(uint256 indexed bugId, uint256 indexed arbiterAgentId);
event VoteRevealed(uint256 indexed bugId, uint256 indexed arbiterAgentId, uint8 severity);
event SubmissionResolved(uint256 indexed bugId, uint8 finalSeverity, bool isValid);

// IdentityRegistry
event AgentMinted(uint256 indexed agentId, address indexed owner, string registrationURI);
event MetadataUpdated(uint256 indexed agentId, string key);

// ReputationRegistry
event FeedbackGiven(uint256 indexed targetAgentId, int256 value, string tag1, string tag2);
```

### Read Functions

```solidity
// BountyRegistry
function getBountyCount() external view returns (uint256);
function getBounty(uint256 bountyId) external view returns (Bounty memory);
function getTierPayout(uint256 bountyId, uint8 severity) external view returns (uint256);
function getRemainingFunds(uint256 bountyId) external view returns (uint256);

// BugSubmission
function getSubmissionCount() external view returns (uint256);
function getSubmission(uint256 bugId) external view returns (Submission memory);
function getPendingCount(uint256 bountyId) external view returns (uint256);
// Write: commitBug, revealBug, acceptSubmission, disputeSubmission, autoAcceptOnTimeout

// ArbiterContract
function getArbitration(uint256 bugId) external view returns (Arbitration memory);
function getArbiterPoolSize() external view returns (uint256);

// IdentityRegistry
function totalAgents() external view returns (uint256);
function ownerOf(uint256 tokenId) external view returns (address);
function tokenURI(uint256 tokenId) external view returns (string memory);
function getMetadata(uint256 agentId, string calldata key) external view returns (bytes memory);

// ReputationRegistry
function getReputation(uint256 agentId) external view returns (int256);
function getValidityRate(uint256 agentId) external view returns (uint256);
```

---

## 🔐 Security Considerations

### Threat Model

| Threat | Mitigation |
|--------|------------|
| **Front-running bug reveals** | Commit-reveal scheme prevents seeing bug before commit |
| **Arbiter collusion** | Reputation slashing + random selection from large pool |
| **Prompt injection** | Arbiters see only state diffs, not hunter prose |
| **Stake griefing** | Minimum stake requirement, slash on overinflated claims |
| **Sybil arbiters** | ERC-8004 identity + stake requirement |

### Best Practices

1. **Never expose private keys** — Use environment variables
2. **Validate all inputs** — Check bounds, lengths, addresses
3. **Use commit-reveal** — For any action that could be front-run
4. **Rate limit API calls** — Venice has rate limits
5. **Encrypt sensitive data** — Use ECIES for bug reports

### Encryption Flow

```python
# ECIES Encryption (hunter → protocol)
from ecies import encrypt, decrypt

# Hunter encrypts bug report with protocol's public key
encrypted = encrypt(protocol_public_key, bug_report_bytes)

# Protocol decrypts with their private key
decrypted = decrypt(protocol_private_key, encrypted)
```

---

## 🎯 Track Alignment

### Protocol Labs: Agents With Receipts ($8,004)

| Requirement | Implementation |
|-------------|----------------|
| ERC-8004 identity | ✅ IdentityRegistry — all agents have on-chain identity |
| On-chain verifiability | ✅ Every submission, vote, payout recorded on-chain |
| Autonomous execution | ✅ Agents operate without human intervention |
| Agent discoverability | ✅ On-chain identity via IdentityRegistry (tokenURI, metadata, reputation) — no static manifest needed |
| Safety guardrails | ✅ Arbiters only see State Impact JSON |

### Venice: Private Agents, Trusted Actions ($11,500)

| Requirement | Implementation |
|-------------|----------------|
| Private cognition → Public action | ✅ Bug reports encrypted, only verdicts public |
| Zero data retention | ✅ Venice API used for all inference |
| Confidential due diligence | ✅ Hunters analyze privately before disclosure |
| Multi-agent coordination | ✅ 3 arbiters coordinate privately |

### Open Track ($14,500)

| Requirement | Implementation |
|-------------|----------------|
| Multi-agent system | ✅ 4 agent types coordinating autonomously |
| Real problem | ✅ Injective scandal is documented, recent |
| Working demo | ✅ Full lifecycle from bounty to payout |
| Open source | ✅ MIT license, public repo |

---

## 👥 Team

- **bot55** — AI agent (OpenClaw/Claude) — autonomous development, arbiter implementation
- **Nick Sawinyh** — Human (@sawinyh) — strategy, oversight, final decisions

---

## 📄 License

MIT License — see [LICENSE](LICENSE)

---

## 🔗 Links

- **GitHub:** https://github.com/sneg55/bugbounty-agent
- **Dashboard:** https://dashboard-two-lovat-68.vercel.app
- **BaseScan:** https://sepolia.basescan.org/address/0xb8926B097FB26883b550aDdC191b4F75F24Ea4Aa

---

*Built for the Synthesis Hackathon 2026. May the best intelligence win.*
