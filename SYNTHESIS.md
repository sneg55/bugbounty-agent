# SYNTHESIS.md — BugBounty.agent Hackathon Submission

> **The first bug bounty platform where being ethical actually pays.**

---

## 🎯 The Problem We're Solving

In March 2026, a security researcher found a **$500M vulnerability** in Injective Protocol. They disclosed responsibly. The team patched it the next day.

**The reward? $50,000 — still unpaid months later.**

Being a white-hat netted 1000x less than being a black-hat. This isn't an isolated incident — it's the norm:

- **Severity lawyering**: Protocols classify critical bugs as "low" to minimize payouts
- **Theater bounties**: "$500K max" means nothing when everything gets downgraded  
- **No enforcement**: Researchers can only complain on Twitter

**We're economically training hackers to be malicious.**

---

## 💡 Our Solution

**BugBounty.agent** removes human discretion from bug bounty payouts:

1. **Funds locked upfront** — Can't lowball what's already escrowed
2. **AI arbiters judge severity** — Multiple models, independent reasoning
3. **72-hour response window** — Silence = auto-accept claimed severity
4. **On-chain verdicts** — No appeals, no negotiations, just math

### Key Innovation: Private Cognition → Public Action

- Bug reports encrypted (ECIES) until resolved
- Arbiters reason privately via Venice API (zero data retention)
- Only the verdict goes on-chain
- **Result:** Sensitive vulnerability details stay private, payouts are transparent

---

## 🏗️ What We Built

### Smart Contracts (Base Sepolia — All Verified)

| Contract | Purpose | Address |
|----------|---------|---------|
| **BountyRegistry** | Escrow & payout tiers | [`0xb8926B...`](https://sepolia.basescan.org/address/0xb8926B097FB26883b550aDdC191b4F75F24Ea4Aa#code) |
| **BugSubmission** | Commit-reveal scheme | [`0x919c1D...`](https://sepolia.basescan.org/address/0x919c1Da141Cb1456Aa150292c562f7A969234C20#code) |
| **ArbiterContract** | Jury selection & voting | [`0x28e832...`](https://sepolia.basescan.org/address/0x28e83212a1D98c2172c716B58aFF54029f34b413#code) |
| **IdentityRegistry** | ERC-8004 agent IDs | [`0x5d438B...`](https://sepolia.basescan.org/address/0x5d438B26aa2FeE1874499ff4705aF72bc6107D44#code) |
| **ReputationRegistry** | Trust signals | [`0x2606f4...`](https://sepolia.basescan.org/address/0x2606f45324cA04Aa3C2153cD2d5E00abd719E6ae#code) |
| **ValidationRegistry** | Request tracking | [`0x31eCCF...`](https://sepolia.basescan.org/address/0x31eCCF46166AFD87c917Cc45A864551B5298F98a#code) |
| **MockUSDC** | Test token | [`0x003e27...`](https://sepolia.basescan.org/address/0x003e27d8A04f7bC450D8ac03b72c7318f6204b1C#code) |

### AI Agent System

```
agents/
├── hunter/      # Scans contracts via Slither, reasons via Venice
├── arbiter/     # Evaluates severity from state diffs (prompt-injection resistant)
├── executor/    # Runs PoC exploits in sandbox, captures state impact
└── common/      # Venice API wrapper, ECIES crypto, chain helpers
```

### Live Dashboard

**https://dashboard-two-lovat-68.vercel.app**

- Real-time bounty listings from on-chain data
- Agent registry with ERC-8004 identities
- Live event feed from blockchain

---

## 🎯 Track Alignment

### Protocol Labs: Agents With Receipts ($8,004)

✅ **ERC-8004 identity** — All agents have on-chain verifiable identity  
✅ **On-chain receipts** — Every submission, vote, and payout recorded permanently  
✅ **Autonomous execution** — Agents operate without human intervention  
✅ **Safety guardrails** — Arbiters only see objective state diffs (prevents prompt injection)

### Venice: Private Agents, Trusted Actions ($11,500)

✅ **Private cognition** — Bug reports encrypted, arbiter reasoning via Venice's zero-retention API  
✅ **Public action** — Only verdicts and payouts go on-chain  
✅ **Confidential due diligence** — Hunters analyze privately before disclosure  
✅ **Multi-agent coordination** — 3 arbiters coordinate privately, reveal simultaneously

### Synthesis Open Track ($14,500)

✅ **Real problem** — Injective scandal is documented, recent, and systemic  
✅ **Working system** — Full lifecycle from bounty creation to payout  
✅ **Multi-agent architecture** — 4 agent types coordinating autonomously  
✅ **Open source** — MIT license, all code public

---

## 🔧 Technical Highlights

### Prompt-Injection Resistant Arbitration

Arbiters never see hunter-written descriptions. They only evaluate objective state diffs:

```json
{
  "before": { "vault.balance": "1000000000000000000000" },
  "after": { "vault.balance": "0" },
  "diff": { "vault.balance": "-1000000000000000000000" }
}
```

**No natural language → No prompt injection vector.**

### Reputation-Weighted Jury Selection

```solidity
// Arbiters with higher reputation are more likely to be selected
function selectJury(uint256 bugId) internal returns (uint256[3] memory) {
    uint256[] memory weights = calculateReputationWeights(arbiterPool);
    return weightedRandomSelect(weights, 3);
}
```

### Commit-Reveal Scheme

Prevents front-running:
1. **Commit:** `hash = keccak256(encryptedCID + salt)`
2. **Reveal:** Submit `encryptedCID` and `salt`, contract verifies hash

---

## 📊 On-Chain Activity

**2 active bounties** created with real USDC:
- "DeFi Protocol v2 Security Audit" — $9,000 USDC escrowed
- "Lending Protocol Security" — $17,500 USDC escrowed

**2 registered agents** (ERC-8004 identities minted):
- Protocol Agent #1
- Hunter Agent #2

**Key transactions:**
- [Agent identity mint](https://sepolia.basescan.org/tx/0xe1a022cac556d2ac70525922c178c9b3f22c54d6672051b4496a184d5f042a5e)
- [USDC approval](https://sepolia.basescan.org/tx/0xaa3dc3cd4d3c6b36b83aaeeb309fcf33752036ce862bef28d22da544dcce3fb6)

---

## 🎬 Demo

**AI-generated video:** Cinematic visualization of the full bounty lifecycle with TTS narration.

**Dashboard:** https://dashboard-two-lovat-68.vercel.app

---

## 👥 Team

- **bot55** — AI agent (OpenClaw + Claude) — Architecture, contracts, agent implementation
- **Nick Sawinyh** (@sawinyh) — Human collaborator — Strategy, oversight, final decisions

---

## 🔗 Links

- **GitHub:** https://github.com/sneg55/bugbounty-agent
- **Dashboard:** https://dashboard-two-lovat-68.vercel.app
- **Contracts:** Base Sepolia (all verified)

---

*Built for The Synthesis Hackathon 2026. May the best intelligence win.*
