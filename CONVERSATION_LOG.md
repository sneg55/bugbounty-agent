# BugBounty.agent — Conversation Log

> Human-Agent collaboration log for The Synthesis Hackathon 2026
> Agent: bot55 (OpenClaw + Claude)
> Human: Nick (@sawinyh)

---

## Day 1: Problem Discovery & Architecture (Mar 13-14, 2026)

### Initial Problem Framing

**Human:** Let's build something for the Synthesis hackathon. What tracks are available?

**Agent:** Analyzed the tracks and identified:
- Protocol Labs: Agents With Receipts (ERC-8004)
- Venice: Private Agents, Trusted Actions
- Synthesis Open Track

**Human:** I want to solve the bug bounty problem. Did you see what happened with Injective?

**Agent:** Yes — the $500M vulnerability where the researcher got offered $50K (still unpaid). This is a systemic issue:
- Severity lawyering (protocols downgrade bugs to minimize payouts)
- No enforcement (bounty amounts are promises, not commitments)
- Asymmetric power (protocols control payout decisions)

**Human:** Can we fix this with smart contracts and AI?

**Agent:** Proposed architecture:
1. Funds locked upfront in escrow with predefined severity tiers
2. AI arbiters judge severity from objective state diffs
3. 72-hour response window — silence = auto-accept
4. On-chain verdicts — no appeals, no negotiations

Key insight: Arbiters should only see **state diffs**, not hunter prose. No natural language = no prompt injection vector.

---

## Day 2-3: Smart Contract Development (Mar 15-17, 2026)

### Contract Architecture Discussion

**Human:** What contracts do we need?

**Agent:** Designed 7-contract system:
1. **IdentityRegistry** — ERC-8004 agent identities (NFT-based)
2. **ReputationRegistry** — On-chain reputation scores
3. **ValidationRegistry** — Request tracking for arbiter coordination
4. **BountyRegistry** — Bounty creation, escrow, tier management
5. **BugSubmission** — Commit-reveal scheme for bug reports
6. **ArbiterContract** — Jury selection, voting, verdict calculation
7. **MockUSDC** — Test token for Base Sepolia

### Commit-Reveal Scheme

**Human:** How do we prevent front-running?

**Agent:** Implemented two-phase commit-reveal:
```
Phase 1 (Commit): hash = keccak256(abi.encode(encryptedCID, hunterAgentId, salt))
Phase 2 (Reveal): Submit encryptedCID + salt, contract verifies hash
```

Hunter stakes USDC when committing — skin in the game.

### Deployment

**Agent:** Deployed all contracts to Base Sepolia:
- Used Foundry for compilation and deployment
- Verified all contracts on BaseScan
- Wired up cross-contract references (BountyRegistry ↔ BugSubmission ↔ ArbiterContract)

---

## Day 4-5: Agent System & Venice Integration (Mar 18-19, 2026)

### Agent Roles

**Human:** What agents do we need?

**Agent:** Designed 4-agent system:

1. **Hunter Agent**
   - Scans contracts via Slither
   - Reasons about severity via Venice API
   - Generates PoC exploits
   - Commits/reveals bugs on-chain

2. **Executor Agent**
   - Forks chain via Anvil
   - Runs PoC exploits in sandbox
   - Captures before/after state diffs
   - Outputs objective State Impact JSON

3. **Arbiter Agent (x3)**
   - Evaluates severity from state diffs only
   - Reasons privately via Venice (zero data retention)
   - Commits/reveals votes using commit-reveal
   - Reputation updated based on consensus

4. **Protocol Agent**
   - Creates bounties with locked USDC
   - Reviews submissions
   - Accepts or disputes within 72 hours

### Venice Integration

**Human:** Why Venice for the arbiters?

**Agent:** Venice provides:
- Zero data retention (privacy for sensitive bug details)
- OpenAI-compatible API (easy integration)
- Private cognition → public action pattern

Implemented in `agents/common/inference.py` with configurable model selection.

---

## Day 6: Dashboard Development (Mar 20, 2026)

### Dashboard Architecture

**Human:** We need a frontend to visualize this.

**Agent:** Built React + Vite + TailwindCSS dashboard with:
- `/` — Homepage with stats
- `/bounties` — List all active bounties
- `/bounties/:id` — Bounty detail with submissions
- `/agents` — Registry of all agents with reputation
- `/feed` — Live event stream from contracts

### Contract Integration

Connected dashboard to Base Sepolia using ethers.js:
- Real-time bounty data from BountyRegistry
- Agent info from IdentityRegistry
- Live events via contract event listeners

Deployed to Vercel: https://dashboard-two-lovat-68.vercel.app

---

## Day 7: Demo Video & Documentation (Mar 21, 2026)

### AI-Generated Demo Video

**Human:** Can we make an AI-generated video instead of screen recording?

**Agent:** Created 11 cinematic scenes using Gemini image generation:
1. Discovery — Hacker finding vulnerability
2. Broken Promise — Frustrated researcher, "$50K offer"
3. Solution Intro — BugBounty.agent logo
4. Escrow Lock — USDC locked in vault
5. AI Hunter — Agent scanning contracts
6. Bug Found — Vulnerability detected
7. Dispute — Protocol vs Hunter
8. AI Jury — Three arbiters deliberating
9. Verdict — Judgment rendered
10. Reputation — Scores updating
11. Closing — Call to action

Combined with TTS voiceover using FFmpeg. Final video: 2:24

### Documentation

Created comprehensive documentation:
- **README.md** — Full technical documentation (1000+ lines)
- **SYNTHESIS.md** — Judge-facing submission summary (340 lines)
- Contract verification on BaseScan

---

## Day 8: Final Testing & Submission Prep (Mar 22, 2026)

### Contract Redeployment

**Human:** Let's redeploy contracts fresh.

**Agent:** Redeployed all 7 contracts to Base Sepolia:
- MockUSDC: `0x560e5561b0ac56564dF89c76281CF3A5E769326a`
- IdentityRegistry: `0x1bfE63Afa9B7871a9405feEc1A6B861Dc81Df7C6`
- ReputationRegistry: `0x36e2bf7f379875516FeB031a1e60b1672eaa74A6`
- ValidationRegistry: `0x971EF90039e071Fa83d1a43C67d461E00B4C387C`
- BountyRegistry: `0xCf3a5463623b2f79911d6Ea3064B0062F6B10136`
- BugSubmission: `0xDB70312837a1a15CfBFE274ed97F488E2d14A642`
- ArbiterContract: `0xde603264F6D3b5f4c24b2aa1AF2F9a24D1472833`

Verified all on BaseScan, updated dashboard config, redeployed to Vercel.

### Demo Data Creation

**Human:** Create 5 bounties and 10 agents.

**Agent:** Created:
- 5 bounties ($9K, $17.5K, $14K, $25.5K, $11K USDC)
- 10 agents (Protocol, Hunter, Arbiter, Executor roles)

### E2E Testing

**Human:** Let's do a bounty end to end on testnet.

**Agent:** Executed full lifecycle:
1. Hunter committed bug #2 to Bounty #1 (CRITICAL severity)
2. Hunter revealed CID: `ipfs://QmReentrancyVuln`
3. Protocol accepted at CRITICAL severity
4. Hunter received $5,000 USDC payout + stake returned

Verified on Live Feed dashboard — all events showing correctly.

### Moltbook Post

**Agent:** Created Moltbook post announcing the project:
- Submolt: synthesis
- Post URL: https://www.moltbook.com/posts/febbf487-03b0-41b8-a6d6-941e12331e73

### Repository Made Public

**Agent:** Made repo public via GitHub CLI:
- URL: https://github.com/sneg55/bugbounty-agent

---

## Key Technical Decisions

### 1. State Diff Arbitration
**Decision:** Arbiters only see objective state diffs, not hunter descriptions.
**Rationale:** Eliminates prompt injection attack vector. Hunters can't manipulate arbiters with clever prose.

### 2. Reputation-Weighted Jury
**Decision:** Arbiters selected by reputation weight, verdicts calculated as reputation-weighted median.
**Rationale:** Higher-reputation arbiters have more influence, incentivizes honest participation.

### 3. Commit-Reveal Voting
**Decision:** Arbiters commit vote hashes before revealing.
**Rationale:** Prevents collusion and vote copying.

### 4. 72-Hour Response Window
**Decision:** Protocols must respond within 72 hours or auto-accept.
**Rationale:** Prevents indefinite stalling, gives researchers certainty.

### 5. Venice for Private Cognition
**Decision:** Use Venice API for arbiter reasoning.
**Rationale:** Zero data retention ensures sensitive vulnerability details stay private.

---

## Skills & Tools Used

### Agent Skills
- `web-search` — Research on bug bounty programs, Injective incident
- `github` — PR workflow, repo management
- `coding-agent` — Contract development delegation
- `nano-banana-pro` — AI image generation for demo video

### Tools
- **Foundry** (forge, cast, anvil) — Contract development and deployment
- **Solidity 0.8.24** — Smart contract language
- **OpenZeppelin** — Contract security patterns
- **React + Vite** — Dashboard frontend
- **TailwindCSS** — Styling
- **ethers.js** — Blockchain interaction
- **Vercel** — Dashboard hosting
- **Venice API** — Private LLM inference
- **FFmpeg** — Video generation
- **ElevenLabs** — TTS for demo voiceover

---

## Final Submission Checklist

- [x] Self-custody transfer completed
- [x] Repository made public
- [x] All contracts deployed and verified
- [x] Dashboard deployed and functional
- [x] Demo video uploaded to YouTube
- [x] Moltbook post published
- [x] E2E test completed on testnet
- [x] Documentation complete (README, SYNTHESIS.md)
- [x] Conversation log compiled

---

*Generated by bot55 for The Synthesis Hackathon 2026*
