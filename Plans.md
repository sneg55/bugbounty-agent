# Plans

## Current Phase: Complete

Source plan: `docs/superpowers/plans/2026-03-17-bugbounty-agent.md`

### Slice 1: Project Scaffolding + ERC-8004 Registries
- [x] `cc:完了` Initialize Foundry project + OpenZeppelin
- [x] `cc:完了` MockUSDC contract + tests
- [x] `cc:完了` IdentityRegistry contract + tests
- [x] `cc:完了` ReputationRegistry contract + tests
- [x] `cc:完了` ValidationRegistry contract + tests

### Slice 2: Bounty Creation
- [x] `cc:完了` BountyRegistry contract + tests
- [x] `cc:完了` Python common layer (inference, contracts, ipfs, crypto)
- [x] `cc:完了` Protocol Agent
- [x] `cc:完了` Dashboard — bounties page

### Slice 3: Submission Flow
- [x] `cc:完了` BugSubmission contract + tests
- [x] `cc:完了` Hunter Agent (scanner, reasoning, PoC, submitter)
- [x] `cc:完了` Dashboard — submission view

### Slice 4: Execution + Arbitration
- [x] `cc:完了` ArbiterContract + tests
- [x] `cc:完了` Executor service (fork runner, state diff, ABI resolver)
- [x] `cc:完了` Arbiter agents (3x, evaluator, voter)
- [x] `cc:完了` Dashboard — votes + payout view

### Slice 5: Patch Guidance
- [x] `cc:完了` Patch guidance (Venice remediation + encrypted delivery)
- [x] `cc:完了` Dashboard — patch status
- [x] `cc:完了` Demo flow script (full lifecycle)

---

## Test Suite

Ref: Design Spec Section 10 — Testing Strategy

### Contract Tests (Foundry) — `contracts/test/`

**Unit tests** — each contract in isolation, TDD (write failing test → implement → pass):

| Contract | Test file | Key cases |
|----------|-----------|-----------|
| MockUSDC | `MockUSDC.t.sol` | name, decimals, mint, anyone-can-mint |
| IdentityRegistry | `IdentityRegistry.t.sol` | mint agent, increments IDs, only-owner-mint, set/get metadata, only-token-owner metadata, isActive, registrationURI |
| ReputationRegistry | `ReputationRegistry.t.sol` | give feedback, cumulative reputation, feedback count by tag, validity rate, zero-submissions rate, only-authorized caller, add/remove authorized |
| ValidationRegistry | `ValidationRegistry.t.sol` | submit validation, get status, get validation, only-authorized caller |
| BountyRegistry | `BountyRegistry.t.sol` | create bounty + escrow, withdraw remainder (after deadline + grace), deductPayout (only BugSubmission), remaining funds, invalid agent revert, insufficient funding revert |
| BugSubmission | `BugSubmission.t.sol` | commitBug (stake transfer, hash storage), revealBug (hash verification, window check), resolveSubmission (valid payout, invalid slash), reclaimExpiredCommit, max 3 active per hunter, reputation-adjusted stakes |
| ArbiterContract | `ArbiterContract.t.sol` | register/unregister arbiter, registerStateImpact + jury selection, conflict-of-interest exclusion, commit/reveal vote, median resolution, timeout scenarios (0/1/2/3 reveals), reputation feedback, patch guidance registration |

**Integration test** — `FullLifecycle.t.sol`:
- Create bounty → commit → reveal → state impact → 3 arbiter votes → resolve → verify payout + reputation updates
- Single test covering the entire contract interaction graph

### Agent Tests (pytest) — `agents/tests/`

| Module | Test file | Key cases |
|--------|-----------|-----------|
| `common/inference.py` | `test_inference.py` | Mock responses, retry logic (max 2), parse failure detection |
| `common/crypto.py` | `test_crypto.py` | ECIES encrypt/decrypt roundtrip, key generation |
| `common/ipfs.py` | `test_ipfs.py` | Upload/download mock, CID handling |
| `common/contracts.py` | `test_contracts.py` | ABI loading from Foundry artifacts, typed wrapper generation |
| `hunter/scanner.py` | `test_scanner.py` | Slither against vulnerable contracts, assert reentrancy + access control findings |
| `hunter/submitter.py` | `test_submitter.py` | Encrypt/decrypt roundtrip, commit hash generation (`keccak256(abi.encode(encryptedCID, hunterAgentId, salt))`) |
| `executor/state_diff.py` | `test_state_diff.py` | State Impact JSON generation from known fork output |
| `arbiter/evaluator.py` | `test_evaluator.py` | Known State Impact JSONs → assert correct severity (0-4) |

All agent tests touching the chain run against **local Anvil** with deployed contracts. No contract mocking in Python.

### End-to-End

`scripts/demo_flow.py` doubles as the E2E test with assertions at each step:
1. Deploy all contracts
2. Mint agent IDs + register metadata + fund wallets
3. Protocol Agent creates bounty
4. Hunter scans → reasons → generates PoC → commit → reveal
5. Executor forks → runs PoC → state diff → registers on-chain
6. 3 Arbiters selected → evaluate → blind vote → median resolution → payout
7. Patch guidance generated → encrypted → delivered
8. Protocol Agent withdraws remainder

---

## Phase 2: Code Review Fixes

Created: 2026-03-18 | Source: Post-implementation code review

### P1 — Security (Critical)

| Task | Description | DoD | Depends | Status |
|------|------------|-----|---------|--------|
| 2.1 | **Fix `setExecutor` access control** | `forge test` passes; test proves non-deployer reverts on `setExecutor()` | - | `cc:完了` |
| 2.2 | **Wire executor setup into deployment scripts** | Both scripts call `setExecutor(executorAddress)` on ArbiterContract | 2.1 | `cc:完了` |
| 2.3 | **Prevent ValidationRegistry overwrite** | Test proves second `submitValidation()` with same hash reverts | - | `cc:完了` |
| 2.4 | **Enforce `minHunterReputation` in `commitBug()`** | Test proves hunter below threshold reverts on `commitBug()` | - | `cc:完了` |
| 2.5 | **Add pending-submission guard to `withdrawRemainder()`** | Test proves `withdrawRemainder()` reverts when pending submissions exist | - | `cc:完了` |

### P2 — Dashboard ABI Sync

| Task | Description | DoD | Depends | Status |
|------|------------|-----|---------|--------|
| 2.6 | **Regenerate `contracts.ts` ABIs from Foundry artifacts** | `npm run build` passes; every ABI function exists in `.sol` | - | `cc:完了` |
| 2.7 | **Fix BountiesPage to use actual contract methods** | `npm run build` clean | 2.6 | `cc:完了` |
| 2.8 | **Fix SubmissionDetailPage** | `npm run build` clean | 2.6 | `cc:完了` |
| 2.9 | **Fix AgentsPage** | `npm run build` clean | 2.6 | `cc:完了` |
| 2.10 | **Clean up frontend template remnants** | No dead files; `npm run build` clean | - | `cc:完了` |

### P3 — Architectural Completeness

| Task | Description | DoD | Depends | Status |
|------|------------|-----|---------|--------|
| 2.11 | **Wire patch guidance into executor service** | `service.py` calls patch guidance for HIGH/CRITICAL | - | `cc:完了` |
| 2.12 | **Implement Protocol Agent watch mode** | `agent.py watch` polls events and decrypts patch guidance | - | `cc:完了` |
| 2.13 | **Implement reputation-ranked jury selection** | Test proves higher-rep arbiters selected; `forge test` passes | - | `cc:完了` |
| 2.14 | **Fix ECIES metadata registration** | Real keypairs generated; `bytes` signature used | - | `cc:完了` |

### P4 — Technical Debt

| Task | Description | DoD | Depends | Status |
|------|------------|-----|---------|--------|
| 2.15 | **Fix executor state impact construction** | chain_id from config; trace parser for balance/storage | - | `cc:完了` |
| 2.16 | **Fix fork runner** | Copies libs; JSON output parsing with fallback | - | `cc:完了` |
| 2.17 | **Fix always-true test assertion** | Meaningful provider assertion; no `or True` | - | `cc:完了` |
| 2.18 | **Add IPFS timeout/retry** | timeout=30; retry with backoff on transient failures | - | `cc:完了` |

### P5 — Optimization

| Task | Description | DoD | Depends | Status |
|------|------------|-----|---------|--------|
| 2.19 | **Add event cursoring to agent polling loops** | BlockCursor utility; all agents use incremental ranges | - | `cc:完了` |
| 2.20 | **Optimize LiveFeedPage to incremental block windows** | Incremental polling with dedup | - | `cc:完了` |

### P6 — Test Coverage for New Fixes

| Task | Description | DoD | Depends | Status |
|------|------------|-----|---------|--------|
| 2.21 | **Solidity tests for security fixes** | 9 new tests: setExecutor, overwrite, reputation, pending, jury ranking | 2.1, 2.3, 2.4, 2.5, 2.13 | `cc:完了` |
| 2.22 | **Python tests for completeness fixes** | IPFS timeout, block cursor, patch guidance encrypt+upload | 2.11, 2.18, 2.19 | `cc:完了` |
| 2.23 | **Update FullLifecycle.t.sol** | test_security_guards: minRep + pending withdrawal | 2.1, 2.4, 2.5, 2.13 | `cc:完了` |

---

## Phase 3: Feedback Round — Bug Fixes & 72-Hour Auto-Accept

Created: 2026-03-21 | Source: External review feedback

### P1 — Critical Event-Field Bugs (silent data loss)

| Task | 内容 | DoD | Depends | Status |
|------|------|-----|---------|--------|
| 3.1 | Fix event field names in `executor/service.py:108` — `severity`→`finalSeverity`, `valid`→`isValid` | Executor reads correct SubmissionResolved fields; patch guidance triggers on HIGH+ | - | cc:完了 |
| 3.2 | Fix event field names in `protocol/agent.py:102` — same rename | Protocol watcher logs correct severity/validity | - | cc:完了 |
| 3.3 | Fix `LiveFeedPage.tsx:49` — treats `bool isValid` as payout amount via `formatUnits()` | Dashboard shows "severity HIGH, valid" not garbled USDC | - | cc:完了 |

### P2 — Correctness & Realism

| Task | 内容 | DoD | Depends | Status |
|------|------|-----|---------|--------|
| 3.4 | Fix deltaUSD suppression in `state_diff.py` — use `deltaWei` directly for fund-loss detection instead of always-zero deltaUSD | `compute_impact_flags()` detects fund loss when deltaWei < 0 | - | cc:完了 |
| 3.5 | Fix PoC zero-address in `hunter/agent.py:55` — inject actual `contract_address` from bounty scope into PoC generation | Generated PoC targets real contract address | - | cc:完了 |

### P3 — Jury Randomization

| Task | 内容 | DoD | Depends | Status |
|------|------|-----|---------|--------|
| 3.6 | Replace deterministic top-3 jury selection in `ArbiterContract.sol:140` with score-weighted random via `block.prevrandao` | Jury selection non-deterministic; existing tests pass; new test shows different juries across blocks | - | cc:完了 |
| 3.7 | Add doc comment above `selectJury()` noting prevrandao is accepted hackathon trade-off (miner-influenceable; commit-reveal would be stronger for production) | Comment present | 3.6 | cc:完了 |

### P4 — 72-Hour Auto-Accept Protocol Flow

The original design promised a dispute window where protocols can accept or dispute submissions. Implementation went straight to mandatory arbitration. This phase adds the accept/dispute window.

**Flow after this phase:**
```
reveal → 72h window → protocol accepts (auto-pay) OR disputes (→ arbitration) OR silence (→ auto-accept at claimed severity)
```

| Task | 内容 | DoD | Depends | Status |
|------|------|-----|---------|--------|
| 3.8 | Add dispute window to `BugSubmission.sol`: `revealedAt` timestamp, `DISPUTE_WINDOW = 72 hours`, `ProtocolResponse` enum (None/Accepted/Disputed) in Submission struct | Contract compiles with new fields | - | cc:完了 |
| 3.9 | Add `acceptSubmission(bugId)` — protocol owner calls within 72h, pays at claimed severity via `BountyRegistry.deductPayout` | Function works; emits `SubmissionAccepted`; test covers happy path + only-protocol-owner + window check | 3.8 | cc:完了 |
| 3.10 | Add `disputeSubmission(bugId)` — protocol owner calls within 72h, sets Disputed status, enables arbitration path | Function works; emits `SubmissionDisputed`; test covers happy path | 3.8 | cc:完了 |
| 3.11 | Add `autoAcceptOnTimeout(bugId)` — anyone calls after 72h with no response, pays at claimed severity | Function works; test covers timeout scenario | 3.8 | cc:完了 |
| 3.12 | Gate `registerStateImpact()` in `ArbiterContract.sol` — require submission is Disputed before allowing state impact | Can't register impact on non-disputed submissions; existing tests updated | 3.10 | cc:完了 |
| 3.13 | Update `executor/service.py` — handle accept/dispute/timeout paths before arbitration | Executor skips arbitration on accept, proceeds on dispute, auto-accepts on timeout | 3.9, 3.10, 3.11 | cc:完了 |
| 3.14 | Update `protocol/agent.py` — add accept/dispute decision logic for revealed submissions | Protocol agent responds within window | 3.9, 3.10 | cc:完了 |
| 3.15 | Update `FullLifecycle.t.sol` — add test for accept path and timeout path alongside existing dispute path | 3 lifecycle variants pass | 3.9, 3.10, 3.11 | cc:完了 |

### P5 — Documentation Alignment

| Task | 内容 | DoD | Depends | Status |
|------|------|-----|---------|--------|
| 3.16 | Fix README Protocol Agent description (~line 421) to match accept/dispute/timeout flow | Description matches implementation | 3.14 | cc:完了 |
| 3.17 | Fix README E2E signatures (~line 851) — `registerStateImpact(uint256,string)` → correct 3-param signature; add accept/dispute cast examples | Cast commands match contract signatures | 3.12 | cc:完了 |
| 3.18 | README line ~70 — 72-hour claim now accurate post-implementation | Claim matches reality | 3.11 | cc:完了 |

---

## Phase 4: Evidence-Based Protocol Agent (Severity-Aware Accept/Dispute)

Created: 2026-03-21 | Source: Feedback — agent autonomy is reactive, not adaptive

The protocol agent currently disputes everything blindly. This phase makes it decrypt the bug report, ask Venice to assess validity and severity, and decide accept vs dispute based on evidence.

**Decision logic after this phase:**
```
1. Decrypt hunter's bug report from IPFS
2. Venice inference: "Is this valid? What severity?"
3. If LLM says valid AND estimated severity within 1 tier of claim → ACCEPT
4. If LLM says invalid OR severity mismatch ≥ 2 tiers → DISPUTE
```

### P1 — Enable Protocol to Read Bug Reports

Currently the hunter encrypts reports only for the executor. The protocol agent needs access too.

| Task | 内容 | DoD | Depends | Status |
|------|------|-----|---------|--------|
| 4.1 | Update `hunter/submitter.py` — dual-encrypt: produce two IPFS payloads, one for executor (existing), one for protocol. Store both CIDs in the encrypted payload or add `protocolEncryptedCID` to the upload. Simplest: encrypt the same `{report, poc}` payload with protocol's ECIES pubkey and include it as a second field in the IPFS JSON | Hunter fetches both executor and protocol pubkeys from chain; IPFS JSON has `encrypted` (for executor) and `protocolEncrypted` (for protocol) fields | - | cc:完了 |
| 4.2 | Update `executor/service.py` — ignore the new `protocolEncrypted` field (read `encrypted` as before) | Executor still works unchanged; test passes | 4.1 | cc:完了 |

### P2 — Protocol Triage Module

| Task | 内容 | DoD | Depends | Status |
|------|------|-----|---------|--------|
| 4.3 | Create `protocol/triage.py` — `triage_submission(report, scope_source, claimed_severity) -> {"valid": bool, "estimated_severity": str, "confidence": float, "reasoning": str}`. Calls Venice via `common.inference.complete()` with a structured prompt. Returns parsed JSON | Unit test with mocked inference returns valid JSON with all fields | - | cc:完了 |
| 4.4 | Add triage prompt template — system prompt instructs the LLM: given a bug report (finding, severity, strategy) and the in-scope contract source, assess (1) is this a real exploitable vulnerability, (2) what severity (LOW/MEDIUM/HIGH/CRITICAL), (3) confidence 0-1. Output JSON | Prompt template produces valid assessments for known test cases (mocked) | 4.3 | cc:完了 |

### P3 — Wire Into Protocol Agent

| Task | 内容 | DoD | Depends | Status |
|------|------|-----|---------|--------|
| 4.5 | Update `protocol/agent.py` `dispute_revealed_submissions()` → rename to `respond_to_submissions()`. For each revealed submission: (a) download + decrypt payload with protocol ECIES key, (b) fetch bounty scope from IPFS, (c) call `triage_submission()`, (d) if valid + severity within 1 tier → `acceptSubmission`, else → `disputeSubmission`. Log reasoning | Protocol agent accepts or disputes based on triage; prints reasoning for each decision | 4.1, 4.3 | cc:完了 |
| 4.6 | Add decision logging — write each triage decision to stdout with: bugId, claimed severity, estimated severity, valid, confidence, action taken (ACCEPT/DISPUTE) | Log output shows evidence-based reasoning, not blind dispute | 4.5 | cc:完了 |

### P4 — Tests

| Task | 内容 | DoD | Depends | Status |
|------|------|-----|---------|--------|
| 4.7 | Unit test for `protocol/triage.py` — mock Venice response, verify JSON parsing, verify accept/dispute decision logic for: (a) valid + matching severity → accept, (b) valid + severity mismatch ≥ 2 → dispute, (c) invalid → dispute, (d) malformed LLM response → dispute (safe fallback) | `pytest agents/protocol/test_triage.py` passes with 4+ test cases | 4.3 | cc:完了 |
| 4.8 | Update `test_submitter.py` if needed — verify dual-encryption payload structure | Existing tests pass; new test confirms `protocolEncrypted` field present | 4.1 | cc:完了 |

---

## Archive
<!-- Completed tasks move here -->
