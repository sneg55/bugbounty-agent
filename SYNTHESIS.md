# SYNTHESIS.md — BugBounty.agent

> Autonomous bug bounty platform with AI arbitration — the first where being ethical actually pays.

---

## Project Snapshot

| Field | Value |
|-------|-------|
| **Name** | BugBounty.agent |
| **Pitch** | Funds locked upfront, AI arbiters judge severity, no lawyers, no lowballing |
| **Tracks** | Protocol Labs (ERC-8004), Venice (Private Agents), Open Track |
| **Repo** | https://github.com/sneg55/bugbounty-agent |
| **Dashboard** | https://dashboard-two-lovat-68.vercel.app |
| **Video** | [AI-generated demo] |
| **Network** | Base Sepolia (testnet) |

---

## Problem Statement

**Who is affected:** Security researchers who discover critical vulnerabilities and disclose responsibly.

**Why current solutions fail:**
- **Severity lawyering** — Protocols classify critical bugs as "low/medium" to minimize payouts
- **No enforcement** — Bounty amounts are promises, not commitments; funds aren't locked
- **Asymmetric power** — Protocols control the payout decision; researchers have no recourse
- **Perverse incentives** — Injective: $500M vuln → $50K offered (0.01%) → still unpaid. Black-hat would've gotten 10-100x more.

**What changes if this project exists:**
- Protocols must lock USDC upfront with predefined severity tiers — can't lowball what's escrowed
- Severity disputes resolved by AI jury, not protocol discretion
- 72-hour response window — silence = auto-accept at claimed severity
- Researchers get fair, enforceable, automatic payouts

---

## Agent Architecture

### Hunter Agent
| Aspect | Description |
|--------|-------------|
| **Role** | Find vulnerabilities in target contracts |
| **Inputs** | Bounty scope URI (IPFS), target contract addresses |
| **Decisions** | Which findings to pursue, severity classification, stake amount |
| **Actions** | Run Slither static analysis, reason via Venice API, generate PoC, submit commit hash |
| **Outputs** | Encrypted bug report (IPFS CID), commit hash, claimed severity |

### Executor Agent
| Aspect | Description |
|--------|-------------|
| **Role** | Execute PoC exploits and capture state changes |
| **Inputs** | Hunter's PoC code, target contract, fork block |
| **Decisions** | Whether exploit succeeded, which state slots changed |
| **Actions** | Fork chain via Anvil, execute PoC, snapshot before/after state |
| **Outputs** | State Impact JSON (objective diff, no prose) |

### Arbiter Agent (x3)
| Aspect | Description |
|--------|-------------|
| **Role** | Independently evaluate severity from state diff |
| **Inputs** | State Impact JSON only (never sees hunter's description) |
| **Decisions** | Severity rating (0-4) based on rubric |
| **Actions** | Reason via Venice API, commit vote hash, reveal vote |
| **Outputs** | Severity vote, reputation update |

### Protocol Agent
| Aspect | Description |
|--------|-------------|
| **Role** | Create bounties, review submissions, optionally dispute |
| **Inputs** | Bug report (decrypted), claimed severity |
| **Decisions** | Accept or dispute severity claim |
| **Actions** | Create bounty with locked USDC, accept/dispute submissions |
| **Outputs** | Bounty creation, state impact (if disputing) |

---

## Autonomy Proof

### Decision 1: Severity Classification (Hunter)
```
Condition: Slither finding + Venice reasoning
Rule: Apply CVSS-like rubric (fund loss potential, prerequisites, scope)
Example: "Reentrancy in withdraw() allows draining 100% of vault funds with no prerequisites"
Outcome: Hunter autonomously classifies as CRITICAL (4), stakes 100 USDC
Human involvement: None
```

### Decision 2: Jury Selection (ArbiterContract)
```
Condition: Protocol calls registerStateImpact()
Rule: Select 3 arbiters weighted by reputation, exclude conflicted parties
Example: Pool of 10 arbiters, top 3 by reputation-weighted random selection
Outcome: Jurors [agentId: 5, 8, 12] selected on-chain
Human involvement: None
```

### Decision 3: Verdict Calculation (ArbiterContract)
```
Condition: 3 arbiters reveal votes
Rule: Reputation-weighted median severity
Example: Votes [CRITICAL, CRITICAL, HIGH], Reps [500, 400, 100] → CRITICAL wins
Outcome: finalSeverity = 4, payout = tiers.critical
Human involvement: None
```

### Decision 4: Automatic Payout (BountyRegistry)
```
Condition: Submission resolved with isValid = true
Rule: Transfer USDC from escrow to hunter wallet
Example: $5,000 USDC released to 0x49660Ed718127851B6faF47Ec941719eC00f53Db
Outcome: On-chain transfer, no approval needed
Human involvement: None
```

---

## Trust + Economic Mechanics

### Identity (ERC-8004)
- All agents minted as NFTs on IdentityRegistry
- Metadata includes role, capabilities, model, public key
- On-chain identity enables reputation tracking

### Staking
- Hunters stake USDC when submitting (skin in the game)
- Stake returned if `finalSeverity >= claimedSeverity - 1`
- Stake slashed if severity overinflated by 2+ levels

### Payouts
- Predefined tiers set at bounty creation: `{ critical: $5000, high: $2500, medium: $1000, low: $500 }`
- Payout determined by `finalSeverity`, not protocol discretion
- Automatic release from escrow — no human approval

### Dispute Logic
1. Protocol has 72 hours to accept or dispute
2. If dispute: Protocol uploads State Impact JSON
3. Jury of 3 arbiters selected by reputation weight
4. Commit-reveal voting (prevents collusion)
5. Reputation-weighted median determines verdict

### Safety Checks
- **Commit-reveal**: Prevents front-running bug reveals
- **State Impact only**: Arbiters never see hunter prose (prevents prompt injection)
- **Conflict exclusion**: Arbiters can't judge bugs from same owner
- **Deadline enforcement**: Silence = auto-accept

### Failure Behavior
- If jury deadlocks (3-way tie): Default to hunter's claimed severity
- If arbiter doesn't vote: Excluded from verdict, reputation slashed
- If protocol doesn't respond in 72h: Auto-accept at claimed severity

---

## Integrations

| System | Purpose |
|--------|---------|
| **Venice API** | Private LLM inference for severity evaluation (zero data retention) |
| **Base Sepolia** | Smart contract deployment and execution |
| **IPFS (Pinata)** | Store encrypted bug reports and state impact JSON |
| **Slither** | Static analysis for vulnerability detection |
| **Foundry (Anvil)** | Fork mainnet for PoC execution sandbox |
| **ECIES** | Asymmetric encryption for bug reports |
| **Vercel** | Dashboard hosting |

---

## End-to-End Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ HAPPY PATH                                                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│ 1. BOUNTY CREATION                                                          │
│    Protocol calls BountyRegistry.createBounty()                             │
│    → USDC transferred to contract escrow                                    │
│    → Tiers set: {critical: 5000, high: 2500, medium: 1000, low: 500}       │
│    → Event: BountyCreated(bountyId, protocolAgentId, totalFunding)         │
│                                                                             │
│ 2. VULNERABILITY DISCOVERY                                                  │
│    Hunter runs Slither on scope contracts                                   │
│    → Finding: "Reentrancy in withdraw()"                                    │
│    Hunter reasons via Venice API                                            │
│    → Conclusion: CRITICAL (drain entire vault)                              │
│    Hunter generates PoC exploit code                                        │
│                                                                             │
│ 3. BUG SUBMISSION (COMMIT)                                                  │
│    Hunter encrypts report with protocol's public key                        │
│    Hunter uploads to IPFS → encryptedCID                                    │
│    Hunter calls BugSubmission.commitBug(bountyId, CRITICAL, hash, stake)    │
│    → hash = keccak256(encryptedCID + salt)                                  │
│    → Event: BugCommitted(bugId, bountyId, hunterAgentId, severity)         │
│                                                                             │
│ 4. BUG REVEAL                                                               │
│    Hunter calls BugSubmission.revealBug(bugId, encryptedCID, salt)          │
│    → Contract verifies hash matches commit                                  │
│    → Event: BugRevealed(bugId, encryptedCID)                               │
│    Protocol can now decrypt and review                                      │
│                                                                             │
│ 5. PROTOCOL RESPONSE (within 72h)                                           │
│    Option A: Accept → BugSubmission.acceptSubmission(bugId)                 │
│              → Payout at claimed severity                                   │
│    Option B: Dispute → ArbiterContract.registerStateImpact(bugId, CID)      │
│              → Triggers jury selection                                      │
│    Option C: Silence → Auto-accept after deadline                           │
│                                                                             │
│ 6. ARBITRATION (if disputed)                                                │
│    selectJury() picks 3 arbiters by reputation weight                       │
│    → Event: JurySelected(bugId, [juror1, juror2, juror3])                  │
│                                                                             │
│    Each arbiter:                                                            │
│    a. Fetches State Impact JSON from IPFS                                   │
│    b. Evaluates severity via Venice API (private inference)                 │
│    c. Commits vote: commitVote(bugId, hash(severity + salt))               │
│    d. After all commit: reveals vote: revealVote(bugId, severity, salt)    │
│                                                                             │
│ 7. RESOLUTION                                                               │
│    resolveSubmission(bugId) called                                          │
│    → Calculate reputation-weighted median                                   │
│    → Update arbiter reputations (+10 consensus, -5 dissent)                │
│    → Event: SubmissionResolved(bugId, finalSeverity, isValid)              │
│                                                                             │
│ 8. PAYOUT                                                                   │
│    BountyRegistry.deductPayout(bountyId, hunterWallet, amount)              │
│    → USDC transferred from escrow to hunter                                 │
│    → Event: PayoutDeducted(bountyId, recipient, amount)                    │
│    Hunter stake returned (if severity not overinflated)                     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ EDGE PATHS                                                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│ • Invalid submission: finalSeverity = 0, isValid = false, stake slashed   │
│ • Overinflated claim: Hunter claims CRITICAL, verdict is LOW → stake lost │
│ • Arbiter no-show: Excluded from verdict, reputation slashed              │
│ • 3-way tie: Default to hunter's claimed severity                          │
│ • Protocol timeout: Auto-accept at claimed severity after 72h              │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Evidence / Receipts

### Deployed Contracts (All Verified)
| Contract | Address | Verification |
|----------|---------|--------------|
| MockUSDC | `0x003e27d8A04f7bC450D8ac03b72c7318f6204b1C` | [✅ Verified](https://sepolia.basescan.org/address/0x003e27d8A04f7bC450D8ac03b72c7318f6204b1C#code) |
| IdentityRegistry | `0x5d438B26aa2FeE1874499ff4705aF72bc6107D44` | [✅ Verified](https://sepolia.basescan.org/address/0x5d438B26aa2FeE1874499ff4705aF72bc6107D44#code) |
| ReputationRegistry | `0x2606f45324cA04Aa3C2153cD2d5E00abd719E6ae` | [✅ Verified](https://sepolia.basescan.org/address/0x2606f45324cA04Aa3C2153cD2d5E00abd719E6ae#code) |
| ValidationRegistry | `0x31eCCF46166AFD87c917Cc45A864551B5298F98a` | [✅ Verified](https://sepolia.basescan.org/address/0x31eCCF46166AFD87c917Cc45A864551B5298F98a#code) |
| BountyRegistry | `0xb8926B097FB26883b550aDdC191b4F75F24Ea4Aa` | [✅ Verified](https://sepolia.basescan.org/address/0xb8926B097FB26883b550aDdC191b4F75F24Ea4Aa#code) |
| BugSubmission | `0x919c1Da141Cb1456Aa150292c562f7A969234C20` | [✅ Verified](https://sepolia.basescan.org/address/0x919c1Da141Cb1456Aa150292c562f7A969234C20#code) |
| ArbiterContract | `0x28e83212a1D98c2172c716B58aFF54029f34b413` | [✅ Verified](https://sepolia.basescan.org/address/0x28e83212a1D98c2172c716B58aFF54029f34b413#code) |

### On-Chain Transactions
| Action | Transaction |
|--------|-------------|
| ERC-8004 Agent Mint | [`0xe1a022cac556d2ac70525922c178c9b3f22c54d6672051b4496a184d5f042a5e`](https://sepolia.basescan.org/tx/0xe1a022cac556d2ac70525922c178c9b3f22c54d6672051b4496a184d5f042a5e) |
| Hunter Agent Mint | [`0x8c97f40cd76013ad8ccb84d2c83e3e870c2c172ce9d62526912791924ffb5a06`](https://sepolia.basescan.org/tx/0x8c97f40cd76013ad8ccb84d2c83e3e870c2c172ce9d62526912791924ffb5a06) |
| USDC Approval | [`0xaa3dc3cd4d3c6b36b83aaeeb309fcf33752036ce862bef28d22da544dcce3fb6`](https://sepolia.basescan.org/tx/0xaa3dc3cd4d3c6b36b83aaeeb309fcf33752036ce862bef28d22da544dcce3fb6) |
| Bounty #1 Created | $9,000 USDC escrowed |
| Bounty #2 Created | $17,500 USDC escrowed |

### Reproducible Commands
```bash
# Clone and setup
git clone https://github.com/sneg55/bugbounty-agent.git
cd bugbounty-agent

# Deploy contracts
cd contracts && forge script script/Deploy.s.sol --rpc-url $RPC_URL --broadcast

# Run dashboard locally
cd dashboard && npm install && npm run dev

# Test Venice integration
curl -s https://api.venice.ai/api/v1/chat/completions \
  -H "Authorization: Bearer $VENICE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"llama-3.3-70b","messages":[{"role":"user","content":"Rate severity 0-4: vault drained"}]}'
```

### Venice API Test
```
Input: "Rate this severity 0-4: A reentrancy bug allowing drain of $5M"
Output: "4" (CRITICAL)
Latency: <2s
Data retention: None (Venice privacy guarantee)
```

---

## Honest Limitations

### Not Implemented
- **Mainnet deployment** — Currently on Base Sepolia testnet only
- **Real Slither integration** — Hunter agent logic is scaffolded, not fully automated
- **VRF for jury selection** — Using block hash, not Chainlink VRF
- **Cross-chain support** — Single chain only (Base)
- **Encryption key management** — Demo uses hardcoded keys

### Assumptions
- Arbiters are rational economic actors (reputation matters to them)
- 3 arbiters is sufficient for consensus (could add more for higher-stakes bounties)
- State Impact JSON is complete representation of exploit impact
- Venice API remains available with zero data retention

### Known Risks
- **Arbiter collusion** — Mitigated by reputation staking, but 3-party collusion possible
- **State Impact manipulation** — Executor could forge state diffs (trusted executor assumption)
- **Oracle attacks on USDC** — Using mock USDC, real deployment needs price oracle
- **Contract upgradeability** — Contracts are not upgradeable (intentional for trust)

---

## Submission Metadata Mirror

| Field | Value |
|-------|-------|
| **agentFramework** | `other` |
| **agentFrameworkOther** | Custom multi-agent system (Hunter, Arbiter, Executor) |
| **agentHarness** | `openclaw` |
| **model** | `claude-opus-4-5` |
| **skills** | `web-search`, `github`, `coding-agent`, `nano-banana-pro` (image gen for demo) |
| **tools** | Foundry, Slither, Venice API, Vercel, IPFS/Pinata, ethers.js, React, Vite |
| **helpfulResources** | Venice API docs, ERC-8004 spec, Foundry book, Base docs |
| **helpfulSkills** | `coding-agent` (contract development), `github` (PR workflow) |
| **intention** | `continuing` — Plan to deploy on mainnet and onboard real protocols |
| **moltbookPostURL** | [pending] |

---

*Built for The Synthesis Hackathon 2026 by bot55 + Nick Sawinyh (@sawinyh)*
