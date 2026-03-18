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

## Archive
<!-- Completed tasks move here -->
