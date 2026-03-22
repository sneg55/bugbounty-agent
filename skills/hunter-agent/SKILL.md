---
name: hunter-agent
description: Operates the Hunter Agent — scans bounty scopes with Slither, reasons about exploitability via Venice AI, generates PoCs, and submits findings via commit-reveal. Use when working with vulnerability scanning, PoC generation, or the hunter submission flow.
---

# Hunter Agent

Scans bounties for vulnerabilities, generates PoCs, and submits findings on-chain.

## Quick Start

```bash
# Scan a specific bounty
python -m hunter.agent --bounty-id 1

# Watch for new bounties and scan automatically
python -m hunter.agent --watch
```

## Pipeline

```
BountyCreated event
  │
  ├─ Fetch scope from IPFS (contract sources + addresses)
  ├─ Run Slither static analysis
  ├─ Venice AI: filter exploitable findings
  ├─ Generate PoC for each finding
  │
  └─ For each exploitable finding:
     ├─ Encrypt {report, poc} for executor AND protocol (dual ECIES)
     ├─ Upload to IPFS
     ├─ Compute commitHash = keccak256(abi.encode(CID, agentId, salt))
     ├─ commitBug(bountyId, commitHash, agentId, severity)
     └─ revealBug(bugId, CID, salt)
```

## Key Files

| File | Purpose |
|------|---------|
| `agents/hunter/agent.py` | Main agent: scan bounties, watch mode |
| `agents/hunter/scanner.py` | Slither integration: run and parse findings |
| `agents/hunter/reasoning.py` | Venice AI: analyze exploitability |
| `agents/hunter/poc_generator.py` | Generate Solidity PoC from finding |
| `agents/hunter/submitter.py` | Dual-encrypt, IPFS upload, commit-reveal |

## Dual Encryption

The hunter encrypts the report for both executor and protocol:

```python
# submitter.py
encrypted = encrypt(executor_pubkey, payload)        # executor can run PoC
protocol_encrypted = encrypt(protocol_pubkey, payload)  # protocol can triage
# Both stored in single IPFS payload
```

Both public keys are fetched from `IdentityRegistry.getMetadata(agentId, "eciesPubKey")`.

## Commit-Reveal Scheme

```
commitHash = keccak256(abi.encode(encryptedCID, hunterAgentId, salt))
```

Uses `abi.encode` (NOT `abi.encodePacked`). Including `hunterAgentId` prevents cross-hunter commit hash theft.

## Stake Calculation

Stakes are calculated on-chain based on hunter reputation:

| Tier | Unknown | Established (3+ valid, rep > 0) | Top (10+ valid, >80% rate) |
|------|---------|--------------------------------|---------------------------|
| CRITICAL | 250 USDC | 100 USDC | 0 |
| HIGH | 100 USDC | 50 USDC | 0 |
| MEDIUM | 25 USDC | 10 USDC | 0 |
| LOW | 10 USDC | 5 USDC | 0 |

## Environment Variables

```
HUNTER_AGENT_PRIVATE_KEY=0x...   # Ethereum wallet (for staking + tx)
```

## Workflow: Adding a New Scanner

1. Create a new scanner function in `hunter/scanner.py`
2. Call it from `scan_bounty()` in `hunter/agent.py`
3. Ensure findings match the expected format: `{finding, severity, strategy}`
4. Test with `pytest hunter/test_scanner.py`
