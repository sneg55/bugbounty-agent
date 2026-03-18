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

## Archive
<!-- Completed tasks move here -->
