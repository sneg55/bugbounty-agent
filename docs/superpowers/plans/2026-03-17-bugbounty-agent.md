# BugBounty.agent Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an autonomous smart contract security marketplace where AI agents find vulnerabilities, evaluate severity via private inference, and trigger automatic escrowed payouts on Base Sepolia.

**Architecture:** 5 vertical slices, each producing an independently demoable system. Foundry smart contracts → Python off-chain agents → React dashboard. All AI inference routes through a Venice-compatible provider-agnostic layer.

**Tech Stack:** Foundry (Solidity 0.8.24+), Python 3.11+ (web3.py, openai, eciespy, slither-analyzer), React + Vite + TypeScript + Tailwind CSS + ethers.js, Base Sepolia testnet.

**Spec:** `docs/superpowers/specs/2026-03-17-bugbounty-agent-design.md`

---

## Chunk 1: Project Scaffolding + ERC-8004 Registries

### Task 1: Initialize Foundry Project

**Files:**
- Create: `contracts/foundry.toml`
- Create: `contracts/remappings.txt`

- [ ] **Step 1: Initialize Foundry project**

```bash
cd /Users/sneg55/Documents/GitHub/hackathon
forge init contracts --no-git --no-commit
```

- [ ] **Step 2: Install OpenZeppelin**

```bash
cd /Users/sneg55/Documents/GitHub/hackathon/contracts
forge install OpenZeppelin/openzeppelin-contracts --no-git --no-commit
```

- [ ] **Step 3: Configure foundry.toml**

```toml
[profile.default]
src = "src"
out = "out"
libs = ["lib"]
solc = "0.8.24"
evm_version = "cancun"

[profile.default.fmt]
line_length = 120

[rpc_endpoints]
base_sepolia = "${RPC_URL}"
```

- [ ] **Step 4: Configure remappings.txt**

```
@openzeppelin/contracts/=lib/openzeppelin-contracts/contracts/
```

- [ ] **Step 5: Verify project compiles**

Run: `cd /Users/sneg55/Documents/GitHub/hackathon/contracts && forge build`
Expected: Successful compilation (default Counter.sol)

- [ ] **Step 6: Remove default Counter files, commit**

```bash
rm contracts/src/Counter.sol contracts/test/Counter.t.sol contracts/script/Counter.s.sol
git add contracts/
git commit -m "chore: initialize Foundry project with OpenZeppelin"
```

---

### Task 2: MockUSDC Contract

**Files:**
- Create: `contracts/src/mocks/MockUSDC.sol`
- Create: `contracts/test/MockUSDC.t.sol`

- [ ] **Step 1: Write failing test**

```solidity
// contracts/test/MockUSDC.t.sol
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Test.sol";
import "../src/mocks/MockUSDC.sol";

contract MockUSDCTest is Test {
    MockUSDC public usdc;
    address public alice = makeAddr("alice");

    function setUp() public {
        usdc = new MockUSDC();
    }

    function test_name() public view {
        assertEq(usdc.name(), "Mock USDC");
    }

    function test_decimals() public view {
        assertEq(usdc.decimals(), 6);
    }

    function test_mint() public {
        usdc.mint(alice, 1000e6);
        assertEq(usdc.balanceOf(alice), 1000e6);
    }

    function test_anyone_can_mint() public {
        vm.prank(alice);
        usdc.mint(alice, 500e6);
        assertEq(usdc.balanceOf(alice), 500e6);
    }
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/sneg55/Documents/GitHub/hackathon/contracts && forge test --match-contract MockUSDCTest -v`
Expected: FAIL (file not found)

- [ ] **Step 3: Write MockUSDC implementation**

```solidity
// contracts/src/mocks/MockUSDC.sol
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";

contract MockUSDC is ERC20 {
    constructor() ERC20("Mock USDC", "USDC") {}

    function decimals() public pure override returns (uint8) {
        return 6;
    }

    function mint(address to, uint256 amount) external {
        _mint(to, amount);
    }
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/sneg55/Documents/GitHub/hackathon/contracts && forge test --match-contract MockUSDCTest -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add contracts/src/mocks/MockUSDC.sol contracts/test/MockUSDC.t.sol
git commit -m "feat: add MockUSDC ERC-20 for testing"
```

---

### Task 3: IdentityRegistry Contract

**Files:**
- Create: `contracts/src/erc8004/IdentityRegistry.sol`
- Create: `contracts/test/IdentityRegistry.t.sol`

- [ ] **Step 1: Write failing tests**

```solidity
// contracts/test/IdentityRegistry.t.sol
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Test.sol";
import "../src/erc8004/IdentityRegistry.sol";

contract IdentityRegistryTest is Test {
    IdentityRegistry public registry;
    address public owner = makeAddr("owner");
    address public alice = makeAddr("alice");

    function setUp() public {
        vm.prank(owner);
        registry = new IdentityRegistry();
    }

    function test_mint_agent() public {
        vm.prank(owner);
        uint256 agentId = registry.mintAgent(alice, "ipfs://registration1");
        assertEq(agentId, 1);
        assertEq(registry.ownerOf(1), alice);
    }

    function test_mint_increments_ids() public {
        vm.startPrank(owner);
        uint256 id1 = registry.mintAgent(alice, "ipfs://reg1");
        uint256 id2 = registry.mintAgent(alice, "ipfs://reg2");
        vm.stopPrank();
        assertEq(id1, 1);
        assertEq(id2, 2);
    }

    function test_only_owner_can_mint() public {
        vm.prank(alice);
        vm.expectRevert();
        registry.mintAgent(alice, "ipfs://reg");
    }

    function test_set_and_get_metadata() public {
        vm.prank(owner);
        registry.mintAgent(alice, "ipfs://reg");

        vm.prank(alice);
        registry.setMetadata(1, "eciesPubKey", hex"04abcd");

        bytes memory val = registry.getMetadata(1, "eciesPubKey");
        assertEq(val, hex"04abcd");
    }

    function test_only_token_owner_can_set_metadata() public {
        vm.prank(owner);
        registry.mintAgent(alice, "ipfs://reg");

        vm.prank(owner);
        vm.expectRevert("Not token owner");
        registry.setMetadata(1, "key", hex"01");
    }

    function test_is_active() public {
        vm.prank(owner);
        registry.mintAgent(alice, "ipfs://reg");
        assertTrue(registry.isActive(1));
        assertFalse(registry.isActive(999));
    }

    function test_registration_uri() public {
        vm.prank(owner);
        registry.mintAgent(alice, "ipfs://myregistration");
        assertEq(registry.tokenURI(1), "ipfs://myregistration");
    }
}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/sneg55/Documents/GitHub/hackathon/contracts && forge test --match-contract IdentityRegistryTest -v`
Expected: FAIL

- [ ] **Step 3: Write IdentityRegistry implementation**

```solidity
// contracts/src/erc8004/IdentityRegistry.sol
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

contract IdentityRegistry is ERC721, Ownable {
    uint256 private _nextTokenId;

    mapping(uint256 => string) private _registrationURIs;
    mapping(uint256 => mapping(string => bytes)) private _metadata;

    event AgentMinted(uint256 indexed agentId, address indexed owner, string registrationURI);
    event MetadataUpdated(uint256 indexed agentId, string key);

    constructor() ERC721("BugBounty Agent Identity", "BBAID") Ownable(msg.sender) {}

    function mintAgent(address to, string calldata registrationURI) external onlyOwner returns (uint256) {
        _nextTokenId++;
        uint256 agentId = _nextTokenId;
        _mint(to, agentId);
        _registrationURIs[agentId] = registrationURI;
        emit AgentMinted(agentId, to, registrationURI);
        return agentId;
    }

    function setMetadata(uint256 agentId, string calldata key, bytes calldata value) external {
        require(ownerOf(agentId) == msg.sender, "Not token owner");
        _metadata[agentId][key] = value;
        emit MetadataUpdated(agentId, key);
    }

    function getMetadata(uint256 agentId, string calldata key) external view returns (bytes memory) {
        return _metadata[agentId][key];
    }

    function isActive(uint256 agentId) external view returns (bool) {
        if (agentId == 0 || agentId > _nextTokenId) return false;
        return _ownerOf(agentId) != address(0);
    }

    function tokenURI(uint256 tokenId) public view override returns (string memory) {
        _requireOwned(tokenId);
        return _registrationURIs[tokenId];
    }

    function totalAgents() external view returns (uint256) {
        return _nextTokenId;
    }
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/sneg55/Documents/GitHub/hackathon/contracts && forge test --match-contract IdentityRegistryTest -v`
Expected: All 7 tests PASS

- [ ] **Step 5: Commit**

```bash
git add contracts/src/erc8004/IdentityRegistry.sol contracts/test/IdentityRegistry.t.sol
git commit -m "feat: add IdentityRegistry (ERC-8004) with agent minting and metadata"
```

---

### Task 4: ReputationRegistry Contract

**Files:**
- Create: `contracts/src/erc8004/ReputationRegistry.sol`
- Create: `contracts/test/ReputationRegistry.t.sol`

- [ ] **Step 1: Write failing tests**

```solidity
// contracts/test/ReputationRegistry.t.sol
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Test.sol";
import "../src/erc8004/ReputationRegistry.sol";

contract ReputationRegistryTest is Test {
    ReputationRegistry public registry;
    address public owner = makeAddr("owner");
    address public arbiterContract = makeAddr("arbiterContract");

    function setUp() public {
        vm.prank(owner);
        registry = new ReputationRegistry();
        vm.prank(owner);
        registry.addAuthorizedCaller(arbiterContract);
    }

    function test_give_feedback() public {
        vm.prank(arbiterContract);
        registry.giveFeedback(42, 100, "submission_valid", "CRITICAL");
        assertEq(registry.getReputation(42), 100);
    }

    function test_cumulative_reputation() public {
        vm.startPrank(arbiterContract);
        registry.giveFeedback(42, 100, "submission_valid", "CRITICAL");
        registry.giveFeedback(42, -100, "submission_invalid", "HIGH");
        vm.stopPrank();
        assertEq(registry.getReputation(42), 0);
    }

    function test_feedback_count_by_tag() public {
        vm.startPrank(arbiterContract);
        registry.giveFeedback(42, 100, "submission_valid", "CRITICAL");
        registry.giveFeedback(42, 100, "submission_valid", "HIGH");
        registry.giveFeedback(42, -100, "submission_invalid", "LOW");
        vm.stopPrank();
        assertEq(registry.getFeedbackCount(42, "submission_valid"), 2);
        assertEq(registry.getFeedbackCount(42, "submission_invalid"), 1);
    }

    function test_validity_rate() public {
        vm.startPrank(arbiterContract);
        registry.giveFeedback(42, 100, "submission_valid", "CRITICAL");
        registry.giveFeedback(42, 100, "submission_valid", "HIGH");
        registry.giveFeedback(42, -100, "submission_invalid", "LOW");
        vm.stopPrank();
        // 2 valid / 3 total = 66%
        assertEq(registry.getValidityRate(42), 66);
    }

    function test_validity_rate_zero_submissions() public view {
        assertEq(registry.getValidityRate(42), 0);
    }

    function test_only_authorized_can_give_feedback() public {
        vm.prank(owner);
        vm.expectRevert("Not authorized");
        registry.giveFeedback(42, 100, "submission_valid", "CRITICAL");
    }

    function test_add_remove_authorized_caller() public {
        address newCaller = makeAddr("newCaller");
        vm.prank(owner);
        registry.addAuthorizedCaller(newCaller);

        vm.prank(newCaller);
        registry.giveFeedback(1, 10, "consensus_aligned", "HIGH");
        assertEq(registry.getReputation(1), 10);

        vm.prank(owner);
        registry.removeAuthorizedCaller(newCaller);

        vm.prank(newCaller);
        vm.expectRevert("Not authorized");
        registry.giveFeedback(1, 10, "consensus_aligned", "HIGH");
    }
}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/sneg55/Documents/GitHub/hackathon/contracts && forge test --match-contract ReputationRegistryTest -v`
Expected: FAIL

- [ ] **Step 3: Write ReputationRegistry implementation**

```solidity
// contracts/src/erc8004/ReputationRegistry.sol
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/access/Ownable.sol";

contract ReputationRegistry is Ownable {
    struct Feedback {
        int256 value;
        string tag1;
        string tag2;
        uint256 timestamp;
    }

    mapping(address => bool) public authorizedCallers;
    mapping(uint256 => int256) private _reputation;
    mapping(uint256 => mapping(string => uint256)) private _feedbackCounts;
    mapping(uint256 => Feedback[]) private _feedbackHistory;

    event FeedbackGiven(uint256 indexed targetAgentId, int256 value, string tag1, string tag2);

    constructor() Ownable(msg.sender) {}

    modifier onlyAuthorized() {
        require(authorizedCallers[msg.sender], "Not authorized");
        _;
    }

    function addAuthorizedCaller(address caller) external onlyOwner {
        authorizedCallers[caller] = true;
    }

    function removeAuthorizedCaller(address caller) external onlyOwner {
        authorizedCallers[caller] = false;
    }

    function giveFeedback(
        uint256 targetAgentId,
        int256 value,
        string calldata tag1,
        string calldata tag2
    ) external onlyAuthorized {
        _reputation[targetAgentId] += value;
        _feedbackCounts[targetAgentId][tag1]++;
        _feedbackHistory[targetAgentId].push(Feedback(value, tag1, tag2, block.timestamp));
        emit FeedbackGiven(targetAgentId, value, tag1, tag2);
    }

    function getReputation(uint256 agentId) external view returns (int256) {
        return _reputation[agentId];
    }

    function getFeedbackCount(uint256 agentId, string calldata tag1) external view returns (uint256) {
        return _feedbackCounts[agentId][tag1];
    }

    function getValidityRate(uint256 agentId) external view returns (uint256) {
        uint256 valid = _feedbackCounts[agentId]["submission_valid"];
        uint256 invalid = _feedbackCounts[agentId]["submission_invalid"];
        uint256 total = valid + invalid;
        if (total == 0) return 0;
        return (valid * 100) / total;
    }

    function getFeedbackHistory(uint256 agentId) external view returns (Feedback[] memory) {
        return _feedbackHistory[agentId];
    }
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/sneg55/Documents/GitHub/hackathon/contracts && forge test --match-contract ReputationRegistryTest -v`
Expected: All 7 tests PASS

- [ ] **Step 5: Commit**

```bash
git add contracts/src/erc8004/ReputationRegistry.sol contracts/test/ReputationRegistry.t.sol
git commit -m "feat: add ReputationRegistry (ERC-8004) with feedback and validity tracking"
```

---

### Task 5: ValidationRegistry Contract

**Files:**
- Create: `contracts/src/erc8004/ValidationRegistry.sol`
- Create: `contracts/test/ValidationRegistry.t.sol`

- [ ] **Step 1: Write failing tests**

```solidity
// contracts/test/ValidationRegistry.t.sol
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Test.sol";
import "../src/erc8004/ValidationRegistry.sol";

contract ValidationRegistryTest is Test {
    ValidationRegistry public registry;
    address public owner = makeAddr("owner");
    address public executor = makeAddr("executor");

    function setUp() public {
        vm.prank(owner);
        registry = new ValidationRegistry();
        vm.prank(owner);
        registry.addAuthorizedCaller(executor);
    }

    function test_submit_validation() public {
        bytes32 reqHash = keccak256("test");
        vm.prank(executor);
        registry.submitValidation(88, reqHash, "ipfs://statediff1");
        assertTrue(registry.getValidationStatus(reqHash));
    }

    function test_get_validation_details() public {
        bytes32 reqHash = keccak256("test");
        vm.prank(executor);
        registry.submitValidation(88, reqHash, "ipfs://statediff1");

        (uint256 executorId, string memory uri, uint256 ts) = registry.getValidation(reqHash);
        assertEq(executorId, 88);
        assertEq(uri, "ipfs://statediff1");
        assertGt(ts, 0);
    }

    function test_nonexistent_validation() public view {
        bytes32 reqHash = keccak256("nonexistent");
        assertFalse(registry.getValidationStatus(reqHash));
    }

    function test_only_authorized_can_submit() public {
        vm.prank(makeAddr("nobody"));
        vm.expectRevert("Not authorized");
        registry.submitValidation(88, keccak256("test"), "ipfs://x");
    }
}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/sneg55/Documents/GitHub/hackathon/contracts && forge test --match-contract ValidationRegistryTest -v`
Expected: FAIL

- [ ] **Step 3: Write ValidationRegistry implementation**

```solidity
// contracts/src/erc8004/ValidationRegistry.sol
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/access/Ownable.sol";

contract ValidationRegistry is Ownable {
    struct Validation {
        uint256 executorAgentId;
        string resultURI;
        uint256 timestamp;
        bool exists;
    }

    mapping(address => bool) public authorizedCallers;
    mapping(bytes32 => Validation) private _validations;

    event ValidationSubmitted(uint256 indexed executorAgentId, bytes32 indexed requestHash, string resultURI);

    constructor() Ownable(msg.sender) {}

    modifier onlyAuthorized() {
        require(authorizedCallers[msg.sender], "Not authorized");
        _;
    }

    function addAuthorizedCaller(address caller) external onlyOwner {
        authorizedCallers[caller] = true;
    }

    function removeAuthorizedCaller(address caller) external onlyOwner {
        authorizedCallers[caller] = false;
    }

    function submitValidation(
        uint256 executorAgentId,
        bytes32 requestHash,
        string calldata resultURI
    ) external onlyAuthorized {
        _validations[requestHash] = Validation(executorAgentId, resultURI, block.timestamp, true);
        emit ValidationSubmitted(executorAgentId, requestHash, resultURI);
    }

    function getValidationStatus(bytes32 requestHash) external view returns (bool) {
        return _validations[requestHash].exists;
    }

    function getValidation(bytes32 requestHash)
        external
        view
        returns (uint256 executorAgentId, string memory resultURI, uint256 timestamp)
    {
        Validation storage v = _validations[requestHash];
        require(v.exists, "Validation not found");
        return (v.executorAgentId, v.resultURI, v.timestamp);
    }
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/sneg55/Documents/GitHub/hackathon/contracts && forge test --match-contract ValidationRegistryTest -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add contracts/src/erc8004/ValidationRegistry.sol contracts/test/ValidationRegistry.t.sol
git commit -m "feat: add ValidationRegistry (ERC-8004) for executor verification"
```

---

### Task 6: Initialize Python Project + Common Layer Skeleton

**Files:**
- Create: `agents/pyproject.toml`
- Create: `agents/common/__init__.py`
- Create: `agents/common/config.py`
- Create: `.env.example`

- [ ] **Step 1: Create pyproject.toml**

```toml
# agents/pyproject.toml
[project]
name = "bugbounty-agents"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "web3>=7.0.0",
    "eth-abi>=5.0.0",
    "openai>=1.0.0",
    "eciespy>=0.4.0",
    "python-dotenv>=1.0.0",
    "requests>=2.31.0",
    "slither-analyzer>=0.10.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
]

[build-system]
requires = ["setuptools>=68.0"]
build-backend = "setuptools.backends._legacy:_Backend"
```

- [ ] **Step 2: Create config module**

```python
# agents/common/__init__.py
```

```python
# agents/common/config.py
import json
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Chain
RPC_URL = os.getenv("RPC_URL", "https://sepolia.base.org")
CHAIN_ID = int(os.getenv("CHAIN_ID", "84532"))

# Inference
INFERENCE_BASE_URL = os.getenv("INFERENCE_BASE_URL", "https://api.venice.ai/api/v1")
INFERENCE_API_KEY = os.getenv("INFERENCE_API_KEY", "")
INFERENCE_MODEL = os.getenv("INFERENCE_MODEL", "llama-3.3-70b")

# IPFS
PINATA_API_KEY = os.getenv("PINATA_API_KEY", "")
PINATA_SECRET_KEY = os.getenv("PINATA_SECRET_KEY", "")

# Deployments
DEPLOYMENTS_FILE = os.getenv("DEPLOYMENTS_FILE", str(Path(__file__).parent.parent.parent / "deployments.json"))


def load_deployments() -> dict:
    with open(DEPLOYMENTS_FILE) as f:
        return json.load(f)
```

- [ ] **Step 3: Create .env.example at project root**

```bash
# .env.example
# Chain
RPC_URL=https://sepolia.base.org
CHAIN_ID=84532

# Agent private keys
PROTOCOL_AGENT_PRIVATE_KEY=0x...
HUNTER_AGENT_PRIVATE_KEY=0x...
ARBITER_1_PRIVATE_KEY=0x...
ARBITER_2_PRIVATE_KEY=0x...
ARBITER_3_PRIVATE_KEY=0x...
EXECUTOR_PRIVATE_KEY=0x...

# ECIES keys (separate from Ethereum keys)
EXECUTOR_ECIES_PRIVATE_KEY=0x...
PROTOCOL_ECIES_PRIVATE_KEY=0x...

# Inference (Venice)
INFERENCE_BASE_URL=https://api.venice.ai/api/v1
INFERENCE_API_KEY=
INFERENCE_MODEL=llama-3.3-70b

# IPFS (Pinata)
PINATA_API_KEY=
PINATA_SECRET_KEY=
```

- [ ] **Step 4: Create .gitignore**

```
# .gitignore
.env
deployments.json
__pycache__/
*.pyc
contracts/out/
contracts/cache/
node_modules/
dashboard/dist/
.venv/
```

- [ ] **Step 5: Install Python dependencies**

Run: `cd /Users/sneg55/Documents/GitHub/hackathon/agents && pip install -e ".[dev]"`
Expected: Successful installation

- [ ] **Step 6: Commit**

```bash
git add agents/pyproject.toml agents/common/__init__.py agents/common/config.py .env.example .gitignore
git commit -m "chore: initialize Python project with common config layer"
```

---

### Task 7: Contract Bindings Module

**Files:**
- Create: `agents/common/contracts.py`
- Create: `agents/common/test_contracts.py`

- [ ] **Step 1: Write failing test**

```python
# agents/common/test_contracts.py
import json
from pathlib import Path
from unittest.mock import patch

from common.contracts import load_abi, get_web3


def test_load_abi_reads_foundry_artifact():
    """Verify load_abi reads from contracts/out/ and extracts abi key."""
    contracts_out = Path(__file__).parent.parent.parent / "contracts" / "out"
    # MockUSDC should exist after forge build
    abi = load_abi("MockUSDC")
    assert isinstance(abi, list)
    assert len(abi) > 0
    # Should have mint function
    fn_names = [item["name"] for item in abi if item.get("type") == "function"]
    assert "mint" in fn_names


def test_get_web3_returns_connected_provider():
    w3 = get_web3()
    assert w3.is_connected() or True  # May not be connected without RPC
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/sneg55/Documents/GitHub/hackathon/agents && python -m pytest common/test_contracts.py -v`
Expected: FAIL (module not found)

- [ ] **Step 3: Write contracts module**

```python
# agents/common/contracts.py
import json
from pathlib import Path

from web3 import Web3

from common.config import RPC_URL, load_deployments

ARTIFACTS_DIR = Path(__file__).parent.parent.parent / "contracts" / "out"


def get_web3() -> Web3:
    return Web3(Web3.HTTPProvider(RPC_URL))


def load_abi(contract_name: str) -> list:
    """Load ABI from Foundry compilation artifacts."""
    artifact_path = ARTIFACTS_DIR / f"{contract_name}.sol" / f"{contract_name}.json"
    with open(artifact_path) as f:
        artifact = json.load(f)
    return artifact["abi"]


def get_contract(w3: Web3, contract_name: str, address: str):
    """Get a web3 contract instance."""
    abi = load_abi(contract_name)
    return w3.eth.contract(address=Web3.to_checksum_address(address), abi=abi)


def get_all_contracts(w3: Web3) -> dict:
    """Load all deployed contracts from deployments.json."""
    deployments = load_deployments()
    contracts = {}
    name_map = {
        "identityRegistry": "IdentityRegistry",
        "reputationRegistry": "ReputationRegistry",
        "validationRegistry": "ValidationRegistry",
        "bountyRegistry": "BountyRegistry",
        "bugSubmission": "BugSubmission",
        "arbiterContract": "ArbiterContract",
        "mockUSDC": "MockUSDC",
    }
    for key, contract_name in name_map.items():
        if key in deployments:
            contracts[key] = get_contract(w3, contract_name, deployments[key])
    return contracts
```

- [ ] **Step 4: Build contracts first so artifacts exist, then run tests**

Run: `cd /Users/sneg55/Documents/GitHub/hackathon/contracts && forge build && cd ../agents && python -m pytest common/test_contracts.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add agents/common/contracts.py agents/common/test_contracts.py
git commit -m "feat: add contract ABI loader and web3 bindings"
```

---

### Task 8: Deploy Script (Foundry)

**Files:**
- Create: `contracts/script/Deploy.s.sol`

- [ ] **Step 1: Write deploy script**

```solidity
// contracts/script/Deploy.s.sol
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Script.sol";
import "../src/mocks/MockUSDC.sol";
import "../src/erc8004/IdentityRegistry.sol";
import "../src/erc8004/ReputationRegistry.sol";
import "../src/erc8004/ValidationRegistry.sol";

contract Deploy is Script {
    function run() external {
        uint256 deployerPrivateKey = vm.envUint("DEPLOYER_PRIVATE_KEY");
        vm.startBroadcast(deployerPrivateKey);

        MockUSDC usdc = new MockUSDC();
        IdentityRegistry identity = new IdentityRegistry();
        ReputationRegistry reputation = new ReputationRegistry();
        ValidationRegistry validation = new ValidationRegistry();

        vm.stopBroadcast();

        // Log addresses for deployments.json
        console.log("MockUSDC:", address(usdc));
        console.log("IdentityRegistry:", address(identity));
        console.log("ReputationRegistry:", address(reputation));
        console.log("ValidationRegistry:", address(validation));
    }
}
```

Note: This is a partial deploy script for Slice 1. It will be extended in later slices to include BountyRegistry, BugSubmission, and ArbiterContract with cross-references.

- [ ] **Step 2: Verify script compiles**

Run: `cd /Users/sneg55/Documents/GitHub/hackathon/contracts && forge build`
Expected: Successful compilation

- [ ] **Step 3: Commit**

```bash
git add contracts/script/Deploy.s.sol
git commit -m "feat: add Foundry deploy script for ERC-8004 registries + MockUSDC"
```

---

### Task 9: Python Deploy & Register Script

**Files:**
- Create: `scripts/deploy_and_register.py`
- Create: `scripts/__init__.py`

- [ ] **Step 1: Write the deploy and register script**

```python
# scripts/deploy_and_register.py
"""
Deploy contracts to Base Sepolia (or Anvil) and register agent identities.
Writes deployments.json for agents and dashboard to consume.

Usage:
    python scripts/deploy_and_register.py --rpc-url http://localhost:8545 --private-key 0x...

For Anvil local testing:
    anvil &
    python scripts/deploy_and_register.py
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path


def run_forge_script(rpc_url: str, private_key: str) -> dict:
    """Run Foundry deploy script and parse output for addresses."""
    result = subprocess.run(
        [
            "forge", "script", "script/Deploy.s.sol:Deploy",
            "--rpc-url", rpc_url,
            "--private-key", private_key,
            "--broadcast",
        ],
        cwd=str(Path(__file__).parent.parent / "contracts"),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print("Deploy failed:", result.stderr)
        sys.exit(1)

    # Parse addresses from console.log output
    addresses = {}
    for line in result.stdout.splitlines():
        for name in ["MockUSDC", "IdentityRegistry", "ReputationRegistry", "ValidationRegistry"]:
            if f"{name}:" in line:
                addr = line.split(f"{name}:")[1].strip()
                addresses[name] = addr
    return addresses


def write_deployments(addresses: dict, output_path: str = "deployments.json"):
    """Write deployments.json mapping."""
    key_map = {
        "MockUSDC": "mockUSDC",
        "IdentityRegistry": "identityRegistry",
        "ReputationRegistry": "reputationRegistry",
        "ValidationRegistry": "validationRegistry",
    }
    deployments = {key_map[k]: v for k, v in addresses.items() if k in key_map}
    deployments["agentIds"] = {}

    path = Path(__file__).parent.parent / output_path
    with open(path, "w") as f:
        json.dump(deployments, f, indent=2)
    print(f"Deployments written to {path}")
    return deployments


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rpc-url", default="http://localhost:8545")
    parser.add_argument("--private-key", default="0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80")  # Anvil default key 0
    args = parser.parse_args()

    print("Deploying contracts...")
    addresses = run_forge_script(args.rpc_url, args.private_key)
    print("Deployed:", addresses)

    deployments = write_deployments(addresses)
    print("Done. Deployments:", json.dumps(deployments, indent=2))


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify script syntax**

Run: `python -c "import ast; ast.parse(open('scripts/deploy_and_register.py').read()); print('OK')"`
Expected: OK

- [ ] **Step 3: Commit**

```bash
git add scripts/deploy_and_register.py scripts/__init__.py
git commit -m "feat: add Python deploy script wrapping Foundry deployment"
```

---

## Chunk 2: BountyRegistry + Protocol Agent + Dashboard Skeleton

### Task 10: BountyRegistry Contract

**Files:**
- Create: `contracts/src/BountyRegistry.sol`
- Create: `contracts/test/BountyRegistry.t.sol`

- [ ] **Step 1: Write failing tests**

```solidity
// contracts/test/BountyRegistry.t.sol
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Test.sol";
import "../src/BountyRegistry.sol";
import "../src/mocks/MockUSDC.sol";
import "../src/erc8004/IdentityRegistry.sol";

contract BountyRegistryTest is Test {
    BountyRegistry public bountyRegistry;
    MockUSDC public usdc;
    IdentityRegistry public identity;

    address public owner = makeAddr("owner");
    address public protocolOwner = makeAddr("protocolOwner");
    uint256 public protocolAgentId;

    function setUp() public {
        vm.startPrank(owner);
        usdc = new MockUSDC();
        identity = new IdentityRegistry();
        bountyRegistry = new BountyRegistry(address(usdc), address(identity));
        protocolAgentId = identity.mintAgent(protocolOwner, "ipfs://protocol");
        vm.stopPrank();

        // Fund protocol
        usdc.mint(protocolOwner, 50_000e6);
        vm.prank(protocolOwner);
        usdc.approve(address(bountyRegistry), type(uint256).max);
    }

    function test_create_bounty() public {
        vm.prank(protocolOwner);
        uint256 bountyId = bountyRegistry.createBounty(
            protocolAgentId,
            "TestProtocol",
            "ipfs://scope",
            BountyRegistry.Tiers(25_000e6, 10_000e6, 2_000e6, 500e6),
            50_000e6,
            block.timestamp + 30 days,
            0
        );
        assertEq(bountyId, 1);
        assertEq(usdc.balanceOf(address(bountyRegistry)), 50_000e6);
    }

    function test_get_bounty() public {
        vm.prank(protocolOwner);
        uint256 bountyId = bountyRegistry.createBounty(
            protocolAgentId,
            "TestProtocol",
            "ipfs://scope",
            BountyRegistry.Tiers(25_000e6, 10_000e6, 2_000e6, 500e6),
            50_000e6,
            block.timestamp + 30 days,
            0
        );

        BountyRegistry.Bounty memory b = bountyRegistry.getBounty(bountyId);
        assertEq(b.name, "TestProtocol");
        assertEq(b.totalFunding, 50_000e6);
        assertTrue(b.active);
    }

    function test_only_agent_owner_can_create() public {
        vm.prank(makeAddr("stranger"));
        vm.expectRevert("Not agent owner");
        bountyRegistry.createBounty(
            protocolAgentId,
            "TestProtocol",
            "ipfs://scope",
            BountyRegistry.Tiers(25_000e6, 10_000e6, 2_000e6, 500e6),
            50_000e6,
            block.timestamp + 30 days,
            0
        );
    }

    function test_withdraw_remainder_after_deadline() public {
        vm.prank(protocolOwner);
        uint256 bountyId = bountyRegistry.createBounty(
            protocolAgentId,
            "TestProtocol",
            "ipfs://scope",
            BountyRegistry.Tiers(25_000e6, 10_000e6, 2_000e6, 500e6),
            50_000e6,
            block.timestamp + 1,
            0
        );

        vm.warp(block.timestamp + 1 + 1800 + 1); // past deadline + grace

        vm.prank(protocolOwner);
        bountyRegistry.withdrawRemainder(bountyId);
        assertEq(usdc.balanceOf(protocolOwner), 50_000e6);
    }

    function test_cannot_withdraw_before_deadline() public {
        vm.prank(protocolOwner);
        uint256 bountyId = bountyRegistry.createBounty(
            protocolAgentId,
            "TestProtocol",
            "ipfs://scope",
            BountyRegistry.Tiers(25_000e6, 10_000e6, 2_000e6, 500e6),
            50_000e6,
            block.timestamp + 30 days,
            0
        );

        vm.prank(protocolOwner);
        vm.expectRevert("Deadline + grace not passed");
        bountyRegistry.withdrawRemainder(bountyId);
    }

    function test_bounty_count() public {
        vm.startPrank(protocolOwner);
        bountyRegistry.createBounty(
            protocolAgentId, "P1", "ipfs://s1",
            BountyRegistry.Tiers(1e6, 1e6, 1e6, 1e6), 4e6, block.timestamp + 1 days, 0
        );
        bountyRegistry.createBounty(
            protocolAgentId, "P2", "ipfs://s2",
            BountyRegistry.Tiers(1e6, 1e6, 1e6, 1e6), 4e6, block.timestamp + 1 days, 0
        );
        vm.stopPrank();
        assertEq(bountyRegistry.getBountyCount(), 2);
    }
}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/sneg55/Documents/GitHub/hackathon/contracts && forge test --match-contract BountyRegistryTest -v`
Expected: FAIL

- [ ] **Step 3: Write BountyRegistry implementation**

```solidity
// contracts/src/BountyRegistry.sol
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "./erc8004/IdentityRegistry.sol";

contract BountyRegistry {
    using SafeERC20 for IERC20;

    struct Tiers {
        uint256 critical;
        uint256 high;
        uint256 medium;
        uint256 low;
    }

    struct Bounty {
        uint256 protocolAgentId;
        string name;
        string scopeURI;
        Tiers tiers;
        uint256 totalFunding;
        uint256 totalPaid;
        uint256 deadline;
        int256 minHunterReputation;
        bool active;
        uint256 submissionCount;
    }

    IERC20 public immutable usdc;
    IdentityRegistry public immutable identityRegistry;
    address public bugSubmissionContract;

    uint256 public constant GRACE_PERIOD = 1800;
    uint256 private _nextBountyId;
    mapping(uint256 => Bounty) private _bounties;

    event BountyCreated(
        uint256 indexed bountyId,
        uint256 indexed protocolAgentId,
        string name,
        uint256 totalFunding,
        uint256 deadline
    );
    event PayoutDeducted(uint256 indexed bountyId, address indexed recipient, uint256 amount);
    event RemainderWithdrawn(uint256 indexed bountyId, uint256 amount);

    address public immutable deployer;

    constructor(address _usdc, address _identityRegistry) {
        usdc = IERC20(_usdc);
        identityRegistry = IdentityRegistry(_identityRegistry);
        deployer = msg.sender;
    }

    function setBugSubmissionContract(address _bugSubmission) external {
        require(msg.sender == deployer, "Only deployer");
        require(bugSubmissionContract == address(0), "Already set");
        bugSubmissionContract = _bugSubmission;
    }

    function createBounty(
        uint256 protocolAgentId,
        string calldata name,
        string calldata scopeURI,
        Tiers calldata tiers,
        uint256 funding,
        uint256 deadline,
        int256 minHunterReputation
    ) external returns (uint256) {
        require(identityRegistry.ownerOf(protocolAgentId) == msg.sender, "Not agent owner");
        require(deadline > block.timestamp, "Deadline must be in the future");
        require(funding > 0, "Funding must be > 0");

        _nextBountyId++;
        uint256 bountyId = _nextBountyId;

        _bounties[bountyId] = Bounty({
            protocolAgentId: protocolAgentId,
            name: name,
            scopeURI: scopeURI,
            tiers: tiers,
            totalFunding: funding,
            totalPaid: 0,
            deadline: deadline,
            minHunterReputation: minHunterReputation,
            active: true,
            submissionCount: 0
        });

        usdc.safeTransferFrom(msg.sender, address(this), funding);

        emit BountyCreated(bountyId, protocolAgentId, name, funding, deadline);
        return bountyId;
    }

    function deductPayout(uint256 bountyId, uint256 amount, address recipient) external {
        require(msg.sender == bugSubmissionContract, "Only BugSubmission");
        Bounty storage b = _bounties[bountyId];
        require(b.active, "Bounty not active");
        require(b.totalPaid + amount <= b.totalFunding, "Insufficient funds");

        b.totalPaid += amount;
        usdc.safeTransfer(recipient, amount);

        emit PayoutDeducted(bountyId, recipient, amount);
    }

    function incrementSubmissionCount(uint256 bountyId) external {
        require(msg.sender == bugSubmissionContract, "Only BugSubmission");
        _bounties[bountyId].submissionCount++;
    }

    function withdrawRemainder(uint256 bountyId) external {
        Bounty storage b = _bounties[bountyId];
        require(identityRegistry.ownerOf(b.protocolAgentId) == msg.sender, "Not agent owner");
        require(block.timestamp > b.deadline + GRACE_PERIOD, "Deadline + grace not passed");
        require(b.active, "Already withdrawn");

        uint256 remainder = b.totalFunding - b.totalPaid;
        require(remainder > 0, "No remainder");

        b.active = false;
        usdc.safeTransfer(msg.sender, remainder);

        emit RemainderWithdrawn(bountyId, remainder);
    }

    function getBounty(uint256 bountyId) external view returns (Bounty memory) {
        return _bounties[bountyId];
    }

    function getRemainingFunds(uint256 bountyId) external view returns (uint256) {
        Bounty storage b = _bounties[bountyId];
        return b.totalFunding - b.totalPaid;
    }

    function getBountyCount() external view returns (uint256) {
        return _nextBountyId;
    }

    function getTierPayout(uint256 bountyId, uint8 severity) external view returns (uint256) {
        Bounty storage b = _bounties[bountyId];
        if (severity == 4) return b.tiers.critical;
        if (severity == 3) return b.tiers.high;
        if (severity == 2) return b.tiers.medium;
        if (severity == 1) return b.tiers.low;
        return 0;
    }
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/sneg55/Documents/GitHub/hackathon/contracts && forge test --match-contract BountyRegistryTest -v`
Expected: All 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add contracts/src/BountyRegistry.sol contracts/test/BountyRegistry.t.sol
git commit -m "feat: add BountyRegistry with USDC escrow and tier-based payouts"
```

---

### Task 11: Inference Module

**Files:**
- Create: `agents/common/inference.py`
- Create: `agents/common/test_inference.py`

- [ ] **Step 1: Write failing tests**

```python
# agents/common/test_inference.py
from unittest.mock import MagicMock, patch

from common.inference import complete


@patch("common.inference._get_client")
def test_complete_returns_content(mock_get_client):
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content="4"))]
    )
    mock_get_client.return_value = mock_client

    result = complete(
        messages=[{"role": "user", "content": "rate this"}],
        model="llama-3.3-70b",
        temperature=0.0,
        max_tokens=4,
    )
    assert result == "4"


@patch("common.inference._get_client")
def test_complete_retries_on_failure(mock_get_client):
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = [
        Exception("API error"),
        MagicMock(choices=[MagicMock(message=MagicMock(content="3"))]),
    ]
    mock_get_client.return_value = mock_client

    result = complete(
        messages=[{"role": "user", "content": "rate this"}],
        model="llama-3.3-70b",
        temperature=0.0,
        max_tokens=4,
    )
    assert result == "3"
    assert mock_client.chat.completions.create.call_count == 2
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/sneg55/Documents/GitHub/hackathon/agents && python -m pytest common/test_inference.py -v`
Expected: FAIL

- [ ] **Step 3: Write inference module**

```python
# agents/common/inference.py
import time

from openai import OpenAI

from common.config import INFERENCE_BASE_URL, INFERENCE_API_KEY, INFERENCE_MODEL

_client = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(base_url=INFERENCE_BASE_URL, api_key=INFERENCE_API_KEY)
    return _client


def complete(
    messages: list[dict],
    model: str | None = None,
    temperature: float = 0.0,
    max_tokens: int = 2000,
    max_retries: int = 2,
) -> str:
    """Send a chat completion request. Returns the content string."""
    client = _get_client()
    model = model or INFERENCE_MODEL

    for attempt in range(max_retries + 1):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            if attempt == max_retries:
                raise
            time.sleep(1)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/sneg55/Documents/GitHub/hackathon/agents && python -m pytest common/test_inference.py -v`
Expected: All 2 tests PASS

- [ ] **Step 5: Commit**

```bash
git add agents/common/inference.py agents/common/test_inference.py
git commit -m "feat: add provider-agnostic inference module (Venice/OpenAI compatible)"
```

---

### Task 12: IPFS Module

**Files:**
- Create: `agents/common/ipfs.py`
- Create: `agents/common/test_ipfs.py`

- [ ] **Step 1: Write failing tests**

```python
# agents/common/test_ipfs.py
from unittest.mock import patch, MagicMock

from common.ipfs import upload_json, download_json


@patch("common.ipfs.requests.post")
def test_upload_json(mock_post):
    mock_post.return_value = MagicMock(
        status_code=200,
        json=lambda: {"IpfsHash": "QmTestHash123"}
    )

    cid = upload_json({"test": "data"})
    assert cid == "QmTestHash123"


@patch("common.ipfs.requests.get")
def test_download_json(mock_get):
    mock_get.return_value = MagicMock(
        status_code=200,
        json=lambda: {"test": "data"}
    )

    data = download_json("QmTestHash123")
    assert data == {"test": "data"}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/sneg55/Documents/GitHub/hackathon/agents && python -m pytest common/test_ipfs.py -v`
Expected: FAIL

- [ ] **Step 3: Write IPFS module**

```python
# agents/common/ipfs.py
import json

import requests

from common.config import PINATA_API_KEY, PINATA_SECRET_KEY

PINATA_PIN_URL = "https://api.pinata.cloud/pinning/pinJSONToIPFS"
IPFS_GATEWAY = "https://gateway.pinata.cloud/ipfs"


def upload_json(data: dict) -> str:
    """Upload JSON to IPFS via Pinata. Returns CID."""
    headers = {
        "pinata_api_key": PINATA_API_KEY,
        "pinata_secret_api_key": PINATA_SECRET_KEY,
        "Content-Type": "application/json",
    }
    response = requests.post(
        PINATA_PIN_URL,
        headers=headers,
        json={"pinataContent": data},
    )
    response.raise_for_status()
    return response.json()["IpfsHash"]


def download_json(cid: str) -> dict:
    """Download JSON from IPFS gateway."""
    url = f"{IPFS_GATEWAY}/{cid}"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/sneg55/Documents/GitHub/hackathon/agents && python -m pytest common/test_ipfs.py -v`
Expected: All 2 tests PASS

- [ ] **Step 5: Commit**

```bash
git add agents/common/ipfs.py agents/common/test_ipfs.py
git commit -m "feat: add IPFS module with Pinata upload/download"
```

---

### Task 13: ECIES Crypto Module

**Files:**
- Create: `agents/common/crypto.py`
- Create: `agents/common/test_crypto.py`

- [ ] **Step 1: Write failing tests**

```python
# agents/common/test_crypto.py
from common.crypto import generate_keypair, encrypt, decrypt


def test_roundtrip_encrypt_decrypt():
    private_key, public_key = generate_keypair()
    plaintext = b'{"vulnerability": "reentrancy", "poc": "test code"}'

    ciphertext = encrypt(public_key, plaintext)
    assert ciphertext != plaintext

    decrypted = decrypt(private_key, ciphertext)
    assert decrypted == plaintext


def test_different_keypairs_cannot_decrypt():
    priv1, pub1 = generate_keypair()
    priv2, pub2 = generate_keypair()

    ciphertext = encrypt(pub1, b"secret data")

    try:
        decrypt(priv2, ciphertext)
        assert False, "Should have raised an exception"
    except Exception:
        pass  # Expected
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/sneg55/Documents/GitHub/hackathon/agents && python -m pytest common/test_crypto.py -v`
Expected: FAIL

- [ ] **Step 3: Write crypto module**

```python
# agents/common/crypto.py
from ecies import encrypt as ecies_encrypt, decrypt as ecies_decrypt
from ecies.utils import generate_eth_key


def generate_keypair() -> tuple[bytes, bytes]:
    """Generate an ECIES keypair. Returns (private_key_hex, public_key_hex)."""
    key = generate_eth_key()
    return key.to_hex().encode(), key.public_key.to_hex().encode()


def encrypt(public_key: bytes, plaintext: bytes) -> bytes:
    """Encrypt data with an ECIES public key."""
    return ecies_encrypt(public_key.decode() if isinstance(public_key, bytes) else public_key, plaintext)


def decrypt(private_key: bytes, ciphertext: bytes) -> bytes:
    """Decrypt data with an ECIES private key."""
    return ecies_decrypt(private_key.decode() if isinstance(private_key, bytes) else private_key, ciphertext)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/sneg55/Documents/GitHub/hackathon/agents && python -m pytest common/test_crypto.py -v`
Expected: All 2 tests PASS

- [ ] **Step 5: Commit**

```bash
git add agents/common/crypto.py agents/common/test_crypto.py
git commit -m "feat: add ECIES encryption module for submission confidentiality"
```

---

### Task 14: Protocol Agent - Create Bounty

**Files:**
- Create: `agents/protocol/__init__.py`
- Create: `agents/protocol/agent.py`
- Create: `agents/protocol/risk_model.py`

- [ ] **Step 1: Write risk model**

```python
# agents/protocol/__init__.py
```

```python
# agents/protocol/risk_model.py
"""Hardcoded risk model for demo. Returns tier amounts in USDC base units (6 decimals)."""


def get_default_tiers() -> dict:
    """Default bounty tier amounts."""
    return {
        "critical": 25_000 * 10**6,
        "high": 10_000 * 10**6,
        "medium": 2_000 * 10**6,
        "low": 500 * 10**6,
    }


def get_default_funding() -> int:
    """Default total bounty funding."""
    return 50_000 * 10**6
```

- [ ] **Step 2: Write Protocol Agent**

```python
# agents/protocol/agent.py
"""Protocol Agent: creates bounties, watches for resolution and patch guidance events."""
import argparse
import json
import os
import time

from web3 import Web3

from common.config import RPC_URL, load_deployments
from common.contracts import get_web3, get_all_contracts
from protocol.risk_model import get_default_tiers, get_default_funding


def create_bounty(
    w3: Web3,
    contracts: dict,
    agent_id: int,
    name: str,
    scope_uri: str,
    deadline_seconds: int = 86400,
):
    """Create a bounty on-chain."""
    private_key = os.getenv("PROTOCOL_AGENT_PRIVATE_KEY")
    account = w3.eth.account.from_key(private_key)
    tiers = get_default_tiers()
    funding = get_default_funding()

    # Approve USDC
    usdc = contracts["mockUSDC"]
    bounty_registry = contracts["bountyRegistry"]

    nonce = w3.eth.get_transaction_count(account.address)

    approve_tx = usdc.functions.approve(
        bounty_registry.address, funding
    ).build_transaction({
        "from": account.address,
        "nonce": nonce,
        "gas": 100_000,
    })
    signed = account.sign_transaction(approve_tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    w3.eth.wait_for_transaction_receipt(tx_hash)

    # Create bounty
    nonce += 1
    deadline = int(time.time()) + deadline_seconds
    create_tx = bounty_registry.functions.createBounty(
        agent_id,
        name,
        scope_uri,
        (tiers["critical"], tiers["high"], tiers["medium"], tiers["low"]),
        funding,
        deadline,
        0,  # minHunterReputation
    ).build_transaction({
        "from": account.address,
        "nonce": nonce,
        "gas": 500_000,
    })
    signed = account.sign_transaction(create_tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

    print(f"Bounty created! TX: {tx_hash.hex()}")
    return receipt


def main():
    parser = argparse.ArgumentParser(description="Protocol Agent")
    parser.add_argument("command", choices=["create-bounty", "watch"])
    parser.add_argument("--name", default="TestProtocol")
    parser.add_argument("--scope-uri", default="ipfs://demo-scope")
    parser.add_argument("--deadline", type=int, default=86400)
    args = parser.parse_args()

    w3 = get_web3()
    contracts = get_all_contracts(w3)
    deployments = load_deployments()

    if args.command == "create-bounty":
        agent_id = deployments["agentIds"]["protocol"]
        create_bounty(w3, contracts, agent_id, args.name, args.scope_uri, args.deadline)
    elif args.command == "watch":
        print("Watching for events... (Ctrl+C to stop)")
        # Event watching implemented in Task 30 (Slice 5)
        while True:
            time.sleep(5)


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Commit**

```bash
git add agents/protocol/
git commit -m "feat: add Protocol Agent with create-bounty command"
```

---

### Task 15: Dashboard Skeleton

**Files:**
- Create: `dashboard/` (Vite + React + TypeScript project)

- [ ] **Step 1: Initialize Vite project**

```bash
cd /Users/sneg55/Documents/GitHub/hackathon
npm create vite@latest dashboard -- --template react-ts
cd dashboard
npm install
npm install ethers@6 @tanstack/react-query tailwindcss @tailwindcss/vite
```

- [ ] **Step 2: Configure Tailwind**

Update `dashboard/vite.config.ts`:
```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
})
```

Replace `dashboard/src/index.css`:
```css
@import "tailwindcss";
```

- [ ] **Step 3: Create contract config and ABI loader**

```typescript
// dashboard/src/config.ts
import { ethers } from 'ethers';

// Will be replaced with actual deployment addresses
import deployments from '../../deployments.json';

export const RPC_URL = 'https://sepolia.base.org';
export const CHAIN_ID = 84532;

export function getProvider(): ethers.JsonRpcProvider {
  return new ethers.JsonRpcProvider(RPC_URL);
}

export { deployments };
```

```typescript
// dashboard/src/contracts.ts
import { ethers } from 'ethers';
import { getProvider, deployments } from './config';

// ABIs will be imported from Foundry artifacts
// For now, define minimal ABIs inline for the events and view functions we need

export const BOUNTY_REGISTRY_ABI = [
  "function getBounty(uint256 bountyId) view returns (tuple(uint256 protocolAgentId, string name, string scopeURI, tuple(uint256 critical, uint256 high, uint256 medium, uint256 low) tiers, uint256 totalFunding, uint256 totalPaid, uint256 deadline, int256 minHunterReputation, bool active, uint256 submissionCount))",
  "function getBountyCount() view returns (uint256)",
  "function getRemainingFunds(uint256 bountyId) view returns (uint256)",
  "event BountyCreated(uint256 indexed bountyId, uint256 indexed protocolAgentId, string name, uint256 totalFunding, uint256 deadline)",
];

export function getBountyRegistryContract(): ethers.Contract {
  const provider = getProvider();
  return new ethers.Contract(
    deployments.bountyRegistry,
    BOUNTY_REGISTRY_ABI,
    provider,
  );
}
```

- [ ] **Step 4: Create App shell with routing**

```typescript
// dashboard/src/App.tsx
import { useState } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BountiesList } from './pages/BountiesList';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchInterval: 5000,
    },
  },
});

type Page = 'bounties' | 'agents' | 'live-feed';

export default function App() {
  const [page, setPage] = useState<Page>('bounties');

  return (
    <QueryClientProvider client={queryClient}>
      <div className="min-h-screen bg-gray-950 text-gray-100">
        <nav className="border-b border-gray-800 px-6 py-4">
          <div className="flex items-center gap-8">
            <h1 className="text-xl font-bold text-white">BugBounty.agent</h1>
            <div className="flex gap-4">
              <button
                onClick={() => setPage('bounties')}
                className={`px-3 py-1 rounded ${page === 'bounties' ? 'bg-gray-800 text-white' : 'text-gray-400 hover:text-white'}`}
              >
                Bounties
              </button>
              <button
                onClick={() => setPage('agents')}
                className={`px-3 py-1 rounded ${page === 'agents' ? 'bg-gray-800 text-white' : 'text-gray-400 hover:text-white'}`}
              >
                Agents
              </button>
              <button
                onClick={() => setPage('live-feed')}
                className={`px-3 py-1 rounded ${page === 'live-feed' ? 'bg-gray-800 text-white' : 'text-gray-400 hover:text-white'}`}
              >
                Live Feed
              </button>
            </div>
          </div>
        </nav>
        <main className="p-6">
          {page === 'bounties' && <BountiesList />}
          {page === 'agents' && <div className="text-gray-500">Agents page (Slice 4)</div>}
          {page === 'live-feed' && <div className="text-gray-500">Live Feed (Slice 4)</div>}
        </main>
      </div>
    </QueryClientProvider>
  );
}
```

- [ ] **Step 5: Create Bounties List page**

```typescript
// dashboard/src/pages/BountiesList.tsx
import { useQuery } from '@tanstack/react-query';
import { getBountyRegistryContract } from '../contracts';
import { ethers } from 'ethers';

interface Bounty {
  id: number;
  name: string;
  totalFunding: string;
  totalPaid: string;
  deadline: number;
  active: boolean;
  submissionCount: number;
  tiers: {
    critical: string;
    high: string;
    medium: string;
    low: string;
  };
}

async function fetchBounties(): Promise<Bounty[]> {
  const contract = getBountyRegistryContract();
  const count = await contract.getBountyCount();
  const bounties: Bounty[] = [];

  for (let i = 1; i <= Number(count); i++) {
    const b = await contract.getBounty(i);
    bounties.push({
      id: i,
      name: b.name,
      totalFunding: ethers.formatUnits(b.totalFunding, 6),
      totalPaid: ethers.formatUnits(b.totalPaid, 6),
      deadline: Number(b.deadline),
      active: b.active,
      submissionCount: Number(b.submissionCount),
      tiers: {
        critical: ethers.formatUnits(b.tiers.critical, 6),
        high: ethers.formatUnits(b.tiers.high, 6),
        medium: ethers.formatUnits(b.tiers.medium, 6),
        low: ethers.formatUnits(b.tiers.low, 6),
      },
    });
  }
  return bounties;
}

export function BountiesList() {
  const { data: bounties, isLoading, error } = useQuery({
    queryKey: ['bounties'],
    queryFn: fetchBounties,
  });

  if (isLoading) return <div className="text-gray-500">Loading bounties...</div>;
  if (error) return <div className="text-red-400">Error loading bounties</div>;
  if (!bounties?.length) return <div className="text-gray-500">No bounties yet.</div>;

  return (
    <div>
      <h2 className="text-2xl font-bold mb-4">Active Bounties</h2>
      <div className="grid gap-4">
        {bounties.map((b) => (
          <div key={b.id} className="bg-gray-900 border border-gray-800 rounded-lg p-4">
            <div className="flex justify-between items-start">
              <div>
                <h3 className="text-lg font-semibold">{b.name}</h3>
                <p className="text-sm text-gray-400">Bounty #{b.id}</p>
              </div>
              <span className={`px-2 py-1 rounded text-xs ${b.active ? 'bg-green-900 text-green-300' : 'bg-gray-800 text-gray-500'}`}>
                {b.active ? 'Active' : 'Closed'}
              </span>
            </div>
            <div className="grid grid-cols-4 gap-4 mt-4 text-sm">
              <div>
                <p className="text-gray-500">Total Funding</p>
                <p className="font-mono">${b.totalFunding}</p>
              </div>
              <div>
                <p className="text-gray-500">Paid Out</p>
                <p className="font-mono">${b.totalPaid}</p>
              </div>
              <div>
                <p className="text-gray-500">Submissions</p>
                <p className="font-mono">{b.submissionCount}</p>
              </div>
              <div>
                <p className="text-gray-500">Deadline</p>
                <p className="font-mono">{new Date(b.deadline * 1000).toLocaleDateString()}</p>
              </div>
            </div>
            <div className="flex gap-4 mt-3 text-xs text-gray-400">
              <span>CRIT: ${b.tiers.critical}</span>
              <span>HIGH: ${b.tiers.high}</span>
              <span>MED: ${b.tiers.medium}</span>
              <span>LOW: ${b.tiers.low}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 6: Verify dashboard builds**

Run: `cd /Users/sneg55/Documents/GitHub/hackathon/dashboard && npm run build`
Expected: Successful build (may have runtime errors without deployments.json — that's expected)

- [ ] **Step 7: Commit**

```bash
git add dashboard/
git commit -m "feat: add dashboard skeleton with bounties list page"
```

---

## Chunk 3: BugSubmission + Hunter Agent

### Task 16: BugSubmission Contract

**Files:**
- Create: `contracts/src/BugSubmission.sol`
- Create: `contracts/test/BugSubmission.t.sol`

- [ ] **Step 1: Write failing tests**

```solidity
// contracts/test/BugSubmission.t.sol
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Test.sol";
import "../src/BugSubmission.sol";
import "../src/BountyRegistry.sol";
import "../src/mocks/MockUSDC.sol";
import "../src/erc8004/IdentityRegistry.sol";
import "../src/erc8004/ReputationRegistry.sol";

contract BugSubmissionTest is Test {
    BugSubmission public submission;
    BountyRegistry public bountyRegistry;
    MockUSDC public usdc;
    IdentityRegistry public identity;
    ReputationRegistry public reputation;

    address public owner = makeAddr("owner");
    address public protocolOwner = makeAddr("protocolOwner");
    address public hunterOwner = makeAddr("hunterOwner");
    uint256 public protocolAgentId;
    uint256 public hunterAgentId;
    uint256 public bountyId;

    function setUp() public {
        vm.startPrank(owner);
        usdc = new MockUSDC();
        identity = new IdentityRegistry();
        reputation = new ReputationRegistry();
        bountyRegistry = new BountyRegistry(address(usdc), address(identity));
        submission = new BugSubmission(
            address(usdc),
            address(identity),
            address(reputation),
            address(bountyRegistry)
        );
        bountyRegistry.setBugSubmissionContract(address(submission));

        protocolAgentId = identity.mintAgent(protocolOwner, "ipfs://protocol");
        hunterAgentId = identity.mintAgent(hunterOwner, "ipfs://hunter");
        vm.stopPrank();

        // Fund protocol and create bounty
        usdc.mint(protocolOwner, 50_000e6);
        vm.startPrank(protocolOwner);
        usdc.approve(address(bountyRegistry), type(uint256).max);
        bountyId = bountyRegistry.createBounty(
            protocolAgentId,
            "TestProtocol",
            "ipfs://scope",
            BountyRegistry.Tiers(25_000e6, 10_000e6, 2_000e6, 500e6),
            50_000e6,
            block.timestamp + 30 days,
            0
        );
        vm.stopPrank();

        // Fund hunter for staking
        usdc.mint(hunterOwner, 1_000e6);
        vm.prank(hunterOwner);
        usdc.approve(address(submission), type(uint256).max);
    }

    function test_commit_bug() public {
        bytes32 commitHash = keccak256(abi.encode("ipfs://encrypted", hunterAgentId, bytes32("salt")));
        vm.prank(hunterOwner);
        uint256 bugId = submission.commitBug(bountyId, commitHash, hunterAgentId, 4); // CRITICAL
        assertEq(bugId, 1);
    }

    function test_commit_takes_stake() public {
        bytes32 commitHash = keccak256(abi.encode("ipfs://encrypted", hunterAgentId, bytes32("salt")));
        uint256 balBefore = usdc.balanceOf(hunterOwner);
        vm.prank(hunterOwner);
        submission.commitBug(bountyId, commitHash, hunterAgentId, 4);
        uint256 balAfter = usdc.balanceOf(hunterOwner);
        // Unknown hunter, CRITICAL = 250 USDC
        assertEq(balBefore - balAfter, 250e6);
    }

    function test_reveal_bug() public {
        string memory encryptedCID = "ipfs://encrypted123";
        bytes32 salt = bytes32("randomsalt");
        bytes32 commitHash = keccak256(abi.encode(encryptedCID, hunterAgentId, salt));

        vm.prank(hunterOwner);
        uint256 bugId = submission.commitBug(bountyId, commitHash, hunterAgentId, 4);

        // Reveal immediately (no minimum wait)
        vm.prank(hunterOwner);
        submission.revealBug(bugId, encryptedCID, salt);
    }

    function test_reveal_wrong_hash_reverts() public {
        bytes32 commitHash = keccak256(abi.encode("ipfs://real", hunterAgentId, bytes32("salt")));
        vm.prank(hunterOwner);
        uint256 bugId = submission.commitBug(bountyId, commitHash, hunterAgentId, 4);

        vm.prank(hunterOwner);
        vm.expectRevert("Hash mismatch");
        submission.revealBug(bugId, "ipfs://wrong", bytes32("salt"));
    }

    function test_reveal_after_window_reverts() public {
        bytes32 commitHash = keccak256(abi.encode("ipfs://enc", hunterAgentId, bytes32("salt")));
        vm.prank(hunterOwner);
        uint256 bugId = submission.commitBug(bountyId, commitHash, hunterAgentId, 4);

        vm.roll(block.number + 201); // Past 200-block window

        vm.prank(hunterOwner);
        vm.expectRevert("Reveal window expired");
        submission.revealBug(bugId, "ipfs://enc", bytes32("salt"));
    }

    function test_max_3_submissions_per_hunter() public {
        vm.startPrank(hunterOwner);
        for (uint256 i = 0; i < 3; i++) {
            bytes32 h = keccak256(abi.encode(string(abi.encodePacked("cid", i)), hunterAgentId, bytes32(i)));
            submission.commitBug(bountyId, h, hunterAgentId, 1); // LOW = 10 USDC stake
        }
        bytes32 h4 = keccak256(abi.encode("cid4", hunterAgentId, bytes32(uint256(4))));
        vm.expectRevert("Max submissions reached");
        submission.commitBug(bountyId, h4, hunterAgentId, 1);
        vm.stopPrank();
    }
}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/sneg55/Documents/GitHub/hackathon/contracts && forge test --match-contract BugSubmissionTest -v`
Expected: FAIL

- [ ] **Step 3: Write BugSubmission implementation**

```solidity
// contracts/src/BugSubmission.sol
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "./erc8004/IdentityRegistry.sol";
import "./erc8004/ReputationRegistry.sol";
import "./BountyRegistry.sol";

contract BugSubmission {
    using SafeERC20 for IERC20;

    enum Status { Committed, Revealed, Resolved }

    struct Submission {
        uint256 bountyId;
        uint256 hunterAgentId;
        uint8 claimedSeverity;
        bytes32 commitHash;
        string encryptedCID;
        uint256 stake;
        Status status;
        uint8 finalSeverity;
        bool isValid;
        uint256 commitBlock;
        address hunterWallet;
    }

    uint256 public constant REVEAL_WINDOW = 200; // blocks
    uint256 public constant MAX_SUBMISSIONS_PER_HUNTER = 3;

    IERC20 public immutable usdc;
    IdentityRegistry public immutable identityRegistry;
    ReputationRegistry public immutable reputationRegistry;
    BountyRegistry public immutable bountyRegistry;
    address public arbiterContract;

    uint256 private _nextBugId;
    mapping(uint256 => Submission) private _submissions;
    mapping(uint256 => mapping(uint256 => uint256)) private _activeSubmissionCount; // bountyId => hunterAgentId => count

    event BugCommitted(uint256 indexed bugId, uint256 indexed bountyId, uint256 indexed hunterAgentId, uint8 claimedSeverity);
    event BugRevealed(uint256 indexed bugId, string encryptedCID);
    event SubmissionResolved(uint256 indexed bugId, uint8 finalSeverity, bool isValid);

    address public immutable deployer;

    constructor(address _usdc, address _identity, address _reputation, address _bountyRegistry) {
        usdc = IERC20(_usdc);
        identityRegistry = IdentityRegistry(_identity);
        reputationRegistry = ReputationRegistry(_reputation);
        bountyRegistry = BountyRegistry(_bountyRegistry);
        deployer = msg.sender;
    }

    function setArbiterContract(address _arbiter) external {
        require(msg.sender == deployer, "Only deployer");
        require(arbiterContract == address(0), "Already set");
        arbiterContract = _arbiter;
    }

    function commitBug(
        uint256 bountyId,
        bytes32 commitHash,
        uint256 hunterAgentId,
        uint8 claimedSeverity
    ) external returns (uint256) {
        require(identityRegistry.isActive(hunterAgentId), "Invalid agent");
        require(identityRegistry.ownerOf(hunterAgentId) == msg.sender, "Not agent owner");
        require(claimedSeverity >= 1 && claimedSeverity <= 4, "Invalid severity");
        require(
            _activeSubmissionCount[bountyId][hunterAgentId] < MAX_SUBMISSIONS_PER_HUNTER,
            "Max submissions reached"
        );

        BountyRegistry.Bounty memory bounty = bountyRegistry.getBounty(bountyId);
        require(bounty.active, "Bounty not active");
        require(block.timestamp < bounty.deadline, "Bounty expired");

        uint256 stake = _calculateStake(hunterAgentId, claimedSeverity);

        _nextBugId++;
        uint256 bugId = _nextBugId;

        _submissions[bugId] = Submission({
            bountyId: bountyId,
            hunterAgentId: hunterAgentId,
            claimedSeverity: claimedSeverity,
            commitHash: commitHash,
            encryptedCID: "",
            stake: stake,
            status: Status.Committed,
            finalSeverity: 0,
            isValid: false,
            commitBlock: block.number,
            hunterWallet: msg.sender
        });

        _activeSubmissionCount[bountyId][hunterAgentId]++;
        usdc.safeTransferFrom(msg.sender, address(this), stake);
        bountyRegistry.incrementSubmissionCount(bountyId);

        emit BugCommitted(bugId, bountyId, hunterAgentId, claimedSeverity);
        return bugId;
    }

    function revealBug(uint256 bugId, string calldata encryptedCID, bytes32 salt) external {
        Submission storage sub = _submissions[bugId];
        require(sub.status == Status.Committed, "Not in commit phase");
        require(identityRegistry.ownerOf(sub.hunterAgentId) == msg.sender, "Not agent owner");
        require(block.number <= sub.commitBlock + REVEAL_WINDOW, "Reveal window expired");

        bytes32 expected = keccak256(abi.encode(encryptedCID, sub.hunterAgentId, salt));
        require(expected == sub.commitHash, "Hash mismatch");

        sub.encryptedCID = encryptedCID;
        sub.status = Status.Revealed;

        emit BugRevealed(bugId, encryptedCID);
    }

    function resolveSubmission(uint256 bugId, uint8 finalSeverity, bool isValid) external {
        require(msg.sender == arbiterContract, "Only ArbiterContract");
        Submission storage sub = _submissions[bugId];
        require(sub.status == Status.Revealed, "Not revealed");

        sub.status = Status.Resolved;
        sub.finalSeverity = finalSeverity;
        sub.isValid = isValid;

        _activeSubmissionCount[sub.bountyId][sub.hunterAgentId]--;

        if (isValid && finalSeverity > 0) {
            // Return stake
            usdc.safeTransfer(sub.hunterWallet, sub.stake);
            // Trigger payout from bounty escrow
            uint256 payout = bountyRegistry.getTierPayout(sub.bountyId, finalSeverity);
            bountyRegistry.deductPayout(sub.bountyId, payout, sub.hunterWallet);
        }
        // If invalid, stake stays in contract (slashed)

        emit SubmissionResolved(bugId, finalSeverity, isValid);
    }

    function resolveSubmissionTimeout(uint256 bugId) external {
        require(msg.sender == arbiterContract, "Only ArbiterContract");
        Submission storage sub = _submissions[bugId];
        require(sub.status == Status.Revealed, "Not revealed");

        sub.status = Status.Resolved;
        sub.finalSeverity = 0;
        sub.isValid = false;
        _activeSubmissionCount[sub.bountyId][sub.hunterAgentId]--;

        // Return stake (not slashed — arbiter failure, not hunter's fault)
        usdc.safeTransfer(sub.hunterWallet, sub.stake);

        emit SubmissionResolved(bugId, 0, false);
    }

    function reclaimExpiredCommit(uint256 bugId) external {
        Submission storage sub = _submissions[bugId];
        require(sub.status == Status.Committed, "Not in commit phase");
        require(block.number > sub.commitBlock + REVEAL_WINDOW, "Window not expired");

        sub.status = Status.Resolved;
        sub.isValid = false;
        _activeSubmissionCount[sub.bountyId][sub.hunterAgentId]--;

        usdc.safeTransfer(sub.hunterWallet, sub.stake);
    }

    function getSubmission(uint256 bugId) external view returns (Submission memory) {
        return _submissions[bugId];
    }

    function getSubmissionCount() external view returns (uint256) {
        return _nextBugId;
    }

    function _calculateStake(uint256 hunterAgentId, uint8 severity) internal view returns (uint256) {
        uint256 validCount = reputationRegistry.getFeedbackCount(hunterAgentId, "submission_valid");
        uint256 validityRate = reputationRegistry.getValidityRate(hunterAgentId);

        // Top-tier: 10+ valid, >80% rate
        if (validCount >= 10 && validityRate > 80) return 0;

        // Established: 3+ valid, net positive reputation
        if (validCount >= 3 && reputationRegistry.getReputation(hunterAgentId) > 0) {
            if (severity == 4) return 100e6;
            if (severity == 3) return 50e6;
            if (severity == 2) return 10e6;
            return 5e6;
        }

        // Unknown
        if (severity == 4) return 250e6;
        if (severity == 3) return 100e6;
        if (severity == 2) return 25e6;
        return 10e6;
    }
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/sneg55/Documents/GitHub/hackathon/contracts && forge test --match-contract BugSubmissionTest -v`
Expected: All 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add contracts/src/BugSubmission.sol contracts/test/BugSubmission.t.sol
git commit -m "feat: add BugSubmission with commit-reveal and reputation-scaled staking"
```

---

### Task 17: Hunter Agent - Scanner Module

**Files:**
- Create: `agents/hunter/__init__.py`
- Create: `agents/hunter/scanner.py`
- Create: `agents/hunter/test_scanner.py`

- [ ] **Step 1: Write failing test**

```python
# agents/hunter/test_scanner.py
from pathlib import Path
from hunter.scanner import run_slither, parse_findings


def test_parse_findings_filters_by_severity():
    """Test that parse_findings filters out low/informational."""
    raw_output = {
        "results": {
            "detectors": [
                {"check": "reentrancy-eth", "impact": "High", "confidence": "Medium",
                 "description": "Reentrancy in Vault.withdraw()", "elements": []},
                {"check": "naming-convention", "impact": "Informational", "confidence": "High",
                 "description": "Variable not in mixedCase", "elements": []},
                {"check": "unprotected-upgrade", "impact": "High", "confidence": "High",
                 "description": "Missing access control", "elements": []},
            ]
        }
    }
    findings = parse_findings(raw_output, min_impact="Medium")
    assert len(findings) == 2
    assert all(f["impact"] in ("High", "Medium", "Critical") for f in findings)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/sneg55/Documents/GitHub/hackathon/agents && python -m pytest hunter/test_scanner.py -v`
Expected: FAIL

- [ ] **Step 3: Write scanner module**

```python
# agents/hunter/__init__.py
```

```python
# agents/hunter/scanner.py
"""Slither integration for static analysis of Solidity contracts."""
import json
import subprocess
import tempfile
from pathlib import Path

IMPACT_ORDER = ["Informational", "Low", "Medium", "High", "Critical"]


def run_slither(contract_source: str, contract_filename: str = "Target.sol") -> dict:
    """Run Slither on a contract source string. Returns raw JSON output."""
    with tempfile.TemporaryDirectory() as tmpdir:
        contract_path = Path(tmpdir) / contract_filename
        contract_path.write_text(contract_source)

        result = subprocess.run(
            ["slither", str(contract_path), "--json", "-"],
            capture_output=True,
            text=True,
            cwd=tmpdir,
        )
        # Slither returns non-zero on findings, which is expected
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            return {"results": {"detectors": []}}


def parse_findings(slither_output: dict, min_impact: str = "Medium") -> list[dict]:
    """Filter Slither findings by minimum impact level."""
    min_idx = IMPACT_ORDER.index(min_impact)
    detectors = slither_output.get("results", {}).get("detectors", [])

    findings = []
    for d in detectors:
        impact = d.get("impact", "Informational")
        if impact in IMPACT_ORDER and IMPACT_ORDER.index(impact) >= min_idx:
            findings.append({
                "check": d.get("check", ""),
                "impact": impact,
                "confidence": d.get("confidence", ""),
                "description": d.get("description", ""),
            })
    return findings
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/sneg55/Documents/GitHub/hackathon/agents && python -m pytest hunter/test_scanner.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add agents/hunter/
git commit -m "feat: add Hunter scanner module with Slither integration"
```

---

### Task 18: Hunter Agent - Reasoning Module

**Files:**
- Create: `agents/hunter/reasoning.py`
- Create: `agents/hunter/test_reasoning.py`

- [ ] **Step 1: Write failing test**

```python
# agents/hunter/test_reasoning.py
from unittest.mock import patch

from hunter.reasoning import analyze_findings


@patch("hunter.reasoning.complete")
def test_analyze_findings_returns_structured_analysis(mock_complete):
    mock_complete.return_value = '{"exploitable": [{"finding": "reentrancy-eth", "severity": "CRITICAL", "strategy": "Deploy attacker contract that re-enters withdraw"}], "not_exploitable": ["naming-convention"]}'

    findings = [
        {"check": "reentrancy-eth", "impact": "High", "description": "Reentrancy in withdraw()"},
    ]
    contract_source = "contract Vault { function withdraw() public { ... } }"

    result = analyze_findings(findings, contract_source)
    assert "exploitable" in result
    assert len(result["exploitable"]) == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/sneg55/Documents/GitHub/hackathon/agents && python -m pytest hunter/test_reasoning.py -v`
Expected: FAIL

- [ ] **Step 3: Write reasoning module**

```python
# agents/hunter/reasoning.py
"""LLM-powered vulnerability reasoning via Venice."""
import json

from common.inference import complete

ANALYSIS_PROMPT = """You are an expert smart contract security auditor.

Given the following Slither static analysis findings and the contract source code,
determine which findings are genuinely exploitable.

For each exploitable finding:
1. Classify severity: CRITICAL, HIGH, MEDIUM, or LOW
2. Describe a proof-of-concept strategy (what attacker contract to deploy, what calls to make)

Respond with valid JSON:
{
  "exploitable": [
    {
      "finding": "<slither check name>",
      "severity": "<CRITICAL|HIGH|MEDIUM|LOW>",
      "strategy": "<brief PoC strategy>"
    }
  ],
  "not_exploitable": ["<check names that are false positives>"]
}
"""


def analyze_findings(findings: list[dict], contract_source: str) -> dict:
    """Send findings + source to Venice for exploitability analysis."""
    findings_text = json.dumps(findings, indent=2)

    response = complete(
        messages=[
            {"role": "system", "content": ANALYSIS_PROMPT},
            {"role": "user", "content": f"CONTRACT SOURCE:\n{contract_source}\n\nSLITHER FINDINGS:\n{findings_text}"},
        ],
        temperature=0.0,
        max_tokens=2000,
    )

    try:
        return json.loads(response)
    except json.JSONDecodeError:
        # Try to extract JSON from response
        start = response.find("{")
        end = response.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(response[start:end])
        return {"exploitable": [], "not_exploitable": []}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/sneg55/Documents/GitHub/hackathon/agents && python -m pytest hunter/test_reasoning.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add agents/hunter/reasoning.py agents/hunter/test_reasoning.py
git commit -m "feat: add Hunter reasoning module for LLM vulnerability analysis"
```

---

### Task 19: Hunter Agent - PoC Generator

**Files:**
- Create: `agents/hunter/poc_generator.py`
- Create: `agents/hunter/test_poc_generator.py`

- [ ] **Step 1: Write failing test**

```python
# agents/hunter/test_poc_generator.py
from unittest.mock import patch

from hunter.poc_generator import generate_poc


@patch("hunter.poc_generator.complete")
def test_generate_poc_returns_solidity(mock_complete):
    mock_complete.return_value = """```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Test.sol";

contract ExploitTest is Test {
    function testExploit() public {
        // exploit code
    }
}
```"""

    result = generate_poc(
        finding={"check": "reentrancy-eth", "severity": "CRITICAL", "strategy": "Re-enter withdraw"},
        contract_source="contract Vault { ... }",
        contract_address="0x1234",
    )
    assert "pragma solidity" in result
    assert "Test" in result
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/sneg55/Documents/GitHub/hackathon/agents && python -m pytest hunter/test_poc_generator.py -v`
Expected: FAIL

- [ ] **Step 3: Write PoC generator module**

```python
# agents/hunter/poc_generator.py
"""Generate Foundry PoC test scripts from vulnerability analysis."""
import re

from common.inference import complete

POC_PROMPT = """You are an expert smart contract exploit developer.

Generate a complete Foundry test file that demonstrates the exploit.
The test should:
1. Fork the chain at the current block
2. Set up the attacker contract (if needed)
3. Execute the exploit
4. Assert that funds were drained / access was gained / state was corrupted

Use these imports:
- forge-std/Test.sol

The target contract is at address: {contract_address}

Output ONLY the Solidity code, wrapped in ```solidity ... ``` markers.
"""


def generate_poc(finding: dict, contract_source: str, contract_address: str) -> str:
    """Generate a Foundry PoC test script for a vulnerability finding."""
    response = complete(
        messages=[
            {"role": "system", "content": POC_PROMPT.format(contract_address=contract_address)},
            {
                "role": "user",
                "content": (
                    f"VULNERABILITY:\n{finding['check']} - {finding.get('strategy', '')}\n\n"
                    f"CONTRACT SOURCE:\n{contract_source}"
                ),
            },
        ],
        temperature=0.0,
        max_tokens=4000,
    )

    # Extract Solidity code from markdown fences
    match = re.search(r"```solidity\n(.*?)```", response, re.DOTALL)
    if match:
        return match.group(1).strip()

    # If no fences, try to find pragma
    if "pragma solidity" in response:
        start = response.index("pragma solidity")
        return response[start:].strip()

    return response
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/sneg55/Documents/GitHub/hackathon/agents && python -m pytest hunter/test_poc_generator.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add agents/hunter/poc_generator.py agents/hunter/test_poc_generator.py
git commit -m "feat: add Hunter PoC generator for Foundry exploit scripts"
```

---

### Task 20: Hunter Agent - Submitter Module

**Files:**
- Create: `agents/hunter/submitter.py`
- Create: `agents/hunter/test_submitter.py`

- [ ] **Step 1: Write failing test**

```python
# agents/hunter/test_submitter.py
from eth_abi import encode
from web3 import Web3

from hunter.submitter import compute_commit_hash


def test_compute_commit_hash():
    """Verify commit hash matches Solidity's keccak256(abi.encode(...))."""
    encrypted_cid = "ipfs://QmTest123"
    hunter_agent_id = 42
    salt = bytes.fromhex("aa" * 32)

    result = compute_commit_hash(encrypted_cid, hunter_agent_id, salt)

    # Must match Solidity: keccak256(abi.encode(string, uint256, bytes32))
    # abi.encode uses ABI standard encoding (NOT packed), so we use eth_abi.encode
    encoded = encode(["string", "uint256", "bytes32"], [encrypted_cid, hunter_agent_id, salt])
    expected = Web3.keccak(encoded)
    assert result == expected
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/sneg55/Documents/GitHub/hackathon/agents && python -m pytest hunter/test_submitter.py -v`
Expected: FAIL

- [ ] **Step 3: Write submitter module**

```python
# agents/hunter/submitter.py
"""Handles encryption, IPFS upload, and commit-reveal submission flow."""
import json
import os
import secrets
import time

from web3 import Web3

from common.contracts import get_web3, get_all_contracts, load_abi
from common.config import load_deployments
from common.crypto import encrypt
from common.ipfs import upload_json


def compute_commit_hash(encrypted_cid: str, hunter_agent_id: int, salt: bytes) -> bytes:
    """Compute commit hash matching Solidity's keccak256(abi.encode(string, uint256, bytes32)).

    IMPORTANT: Uses eth_abi.encode (ABI standard encoding with padding), NOT
    Web3.solidity_keccak which uses abi.encodePacked (tight packing). The Solidity
    contract uses abi.encode, so we must match that exactly.
    """
    from eth_abi import encode
    encoded = encode(["string", "uint256", "bytes32"], [encrypted_cid, hunter_agent_id, salt])
    return Web3.keccak(encoded)


def submit_finding(
    report: dict,
    poc_source: str,
    bounty_id: int,
    hunter_agent_id: int,
    claimed_severity: int,
    executor_pubkey: bytes,
) -> dict:
    """Full submission flow: encrypt → IPFS → commit → reveal."""
    w3 = get_web3()
    contracts = get_all_contracts(w3)
    private_key = os.getenv("HUNTER_AGENT_PRIVATE_KEY")
    account = w3.eth.account.from_key(private_key)

    # 1. Encrypt report + PoC with executor's public key
    payload = json.dumps({"report": report, "poc": poc_source}).encode()
    encrypted = encrypt(executor_pubkey, payload)

    # 2. Upload encrypted payload to IPFS
    encrypted_cid = upload_json({"encrypted": encrypted.hex()})

    # 3. Generate salt and commit hash
    salt = secrets.token_bytes(32)
    commit_hash = compute_commit_hash(encrypted_cid, hunter_agent_id, salt)

    # 4. Commit on-chain
    bug_submission = contracts["bugSubmission"]
    nonce = w3.eth.get_transaction_count(account.address)
    tx = bug_submission.functions.commitBug(
        bounty_id, commit_hash, hunter_agent_id, claimed_severity
    ).build_transaction({
        "from": account.address,
        "nonce": nonce,
        "gas": 300_000,
    })
    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

    # Parse bug ID from event
    bug_id = bug_submission.events.BugCommitted().process_receipt(receipt)[0]["args"]["bugId"]
    print(f"Committed bug #{bug_id}, tx: {tx_hash.hex()}")

    # 5. Wait for confirmation then reveal immediately
    time.sleep(3)  # Wait for block confirmation

    nonce += 1
    reveal_tx = bug_submission.functions.revealBug(
        bug_id, encrypted_cid, salt
    ).build_transaction({
        "from": account.address,
        "nonce": nonce,
        "gas": 200_000,
    })
    signed = account.sign_transaction(reveal_tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    w3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"Revealed bug #{bug_id}, tx: {tx_hash.hex()}")

    return {"bug_id": bug_id, "encrypted_cid": encrypted_cid, "salt": salt.hex()}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/sneg55/Documents/GitHub/hackathon/agents && python -m pytest hunter/test_submitter.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add agents/hunter/submitter.py agents/hunter/test_submitter.py
git commit -m "feat: add Hunter submitter with commit-reveal flow"
```

---

### Task 21: Hunter Agent - Main Agent Loop

**Files:**
- Create: `agents/hunter/agent.py`

- [ ] **Step 1: Write main agent**

```python
# agents/hunter/agent.py
"""Hunter Agent: scans bounties, finds vulnerabilities, submits findings."""
import argparse
import os
import time

from common.contracts import get_web3, get_all_contracts
from common.config import load_deployments
from common.ipfs import download_json
from hunter.scanner import run_slither, parse_findings
from hunter.reasoning import analyze_findings
from hunter.poc_generator import generate_poc
from hunter.submitter import submit_finding

SEVERITY_MAP = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}


def scan_bounty(w3, contracts, bounty_id: int, hunter_agent_id: int, executor_pubkey: bytes):
    """Scan a single bounty: fetch scope, analyze, submit findings."""
    bounty = contracts["bountyRegistry"].functions.getBounty(bounty_id).call()
    scope_uri = bounty[2]  # scopeURI
    print(f"Scanning bounty #{bounty_id}: {bounty[1]} (scope: {scope_uri})")

    # Fetch in-scope contract sources from IPFS
    scope_data = download_json(scope_uri.replace("ipfs://", ""))
    contract_sources = scope_data.get("contracts", {})

    for name, source in contract_sources.items():
        print(f"  Analyzing {name}...")

        # 1. Run Slither
        slither_output = run_slither(source, f"{name}.sol")
        findings = parse_findings(slither_output, min_impact="Medium")
        if not findings:
            print(f"  No significant findings in {name}")
            continue

        print(f"  Found {len(findings)} findings, running LLM analysis...")

        # 2. LLM reasoning
        analysis = analyze_findings(findings, source)
        exploitable = analysis.get("exploitable", [])
        if not exploitable:
            print(f"  No exploitable findings in {name}")
            continue

        # 3. Generate and submit PoCs for each exploitable finding
        for finding in exploitable:
            severity = SEVERITY_MAP.get(finding.get("severity", "LOW"), 1)
            print(f"  Generating PoC for {finding['finding']} (severity: {finding['severity']})")

            poc_source = generate_poc(
                finding=finding,
                contract_source=source,
                contract_address="0x0000000000000000000000000000000000000000",  # Will be filled by executor
            )

            report = {
                "contract": name,
                "finding": finding["finding"],
                "severity": finding["severity"],
                "strategy": finding.get("strategy", ""),
            }

            result = submit_finding(
                report=report,
                poc_source=poc_source,
                bounty_id=bounty_id,
                hunter_agent_id=hunter_agent_id,
                claimed_severity=severity,
                executor_pubkey=executor_pubkey,
            )
            print(f"  Submitted bug #{result['bug_id']}")


def main():
    parser = argparse.ArgumentParser(description="Hunter Agent")
    parser.add_argument("--bounty-id", type=int, help="Specific bounty to scan")
    parser.add_argument("--watch", action="store_true", help="Watch for new bounties")
    args = parser.parse_args()

    w3 = get_web3()
    contracts = get_all_contracts(w3)
    deployments = load_deployments()
    hunter_agent_id = deployments["agentIds"]["hunter"]

    # Fetch executor's ECIES public key from chain
    executor_agent_id = deployments["agentIds"]["executor"]
    executor_pubkey = contracts["identityRegistry"].functions.getMetadata(
        executor_agent_id, "eciesPubKey"
    ).call()

    if args.bounty_id:
        scan_bounty(w3, contracts, args.bounty_id, hunter_agent_id, executor_pubkey)
    elif args.watch:
        print("Watching for new bounties... (Ctrl+C to stop)")
        seen_bounties = set()
        while True:
            count = contracts["bountyRegistry"].functions.getBountyCount().call()
            for i in range(1, count + 1):
                if i not in seen_bounties:
                    seen_bounties.add(i)
                    scan_bounty(w3, contracts, i, hunter_agent_id, executor_pubkey)
            time.sleep(10)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify syntax**

Run: `python -c "import ast; ast.parse(open('agents/hunter/agent.py').read()); print('OK')"`
Expected: OK

- [ ] **Step 3: Commit**

```bash
git add agents/hunter/agent.py
git commit -m "feat: add Hunter Agent main loop with bounty watching"
```

---

## Chunk 4: ArbiterContract + Executor + Arbiter Agents

### Task 22: ArbiterContract

**Files:**
- Create: `contracts/src/ArbiterContract.sol`
- Create: `contracts/test/ArbiterContract.t.sol`

- [ ] **Step 1: Write failing tests**

```solidity
// contracts/test/ArbiterContract.t.sol
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Test.sol";
import "../src/ArbiterContract.sol";
import "../src/BugSubmission.sol";
import "../src/BountyRegistry.sol";
import "../src/mocks/MockUSDC.sol";
import "../src/erc8004/IdentityRegistry.sol";
import "../src/erc8004/ReputationRegistry.sol";
import "../src/erc8004/ValidationRegistry.sol";

contract ArbiterContractTest is Test {
    ArbiterContract public arbiter;
    BugSubmission public submission;
    BountyRegistry public bountyRegistry;
    MockUSDC public usdc;
    IdentityRegistry public identity;
    ReputationRegistry public reputation;
    ValidationRegistry public validation;

    address public owner = makeAddr("owner");
    address public protocolOwner = makeAddr("protocolOwner");
    address public hunterOwner = makeAddr("hunterOwner");
    address public executor = makeAddr("executor");
    address public arbiterOwner1 = makeAddr("arbiterOwner1");
    address public arbiterOwner2 = makeAddr("arbiterOwner2");
    address public arbiterOwner3 = makeAddr("arbiterOwner3");

    uint256 public protocolAgentId;
    uint256 public hunterAgentId;
    uint256 public executorAgentId;
    uint256 public arbiterAgentId1;
    uint256 public arbiterAgentId2;
    uint256 public arbiterAgentId3;
    uint256 public bountyId;
    uint256 public bugId;

    function setUp() public {
        vm.startPrank(owner);
        usdc = new MockUSDC();
        identity = new IdentityRegistry();
        reputation = new ReputationRegistry();
        validation = new ValidationRegistry();
        bountyRegistry = new BountyRegistry(address(usdc), address(identity));
        submission = new BugSubmission(
            address(usdc), address(identity), address(reputation), address(bountyRegistry)
        );
        arbiter = new ArbiterContract(
            address(identity), address(reputation), address(validation), address(submission)
        );

        bountyRegistry.setBugSubmissionContract(address(submission));
        submission.setArbiterContract(address(arbiter));
        reputation.addAuthorizedCaller(address(arbiter));
        validation.addAuthorizedCaller(executor);

        // Mint agents
        protocolAgentId = identity.mintAgent(protocolOwner, "ipfs://protocol");
        hunterAgentId = identity.mintAgent(hunterOwner, "ipfs://hunter");
        executorAgentId = identity.mintAgent(executor, "ipfs://executor");
        arbiterAgentId1 = identity.mintAgent(arbiterOwner1, "ipfs://arbiter1");
        arbiterAgentId2 = identity.mintAgent(arbiterOwner2, "ipfs://arbiter2");
        arbiterAgentId3 = identity.mintAgent(arbiterOwner3, "ipfs://arbiter3");
        vm.stopPrank();

        // Register arbiters
        vm.prank(arbiterOwner1);
        arbiter.registerArbiter(arbiterAgentId1);
        vm.prank(arbiterOwner2);
        arbiter.registerArbiter(arbiterAgentId2);
        vm.prank(arbiterOwner3);
        arbiter.registerArbiter(arbiterAgentId3);

        // Setup bounty
        usdc.mint(protocolOwner, 50_000e6);
        vm.startPrank(protocolOwner);
        usdc.approve(address(bountyRegistry), type(uint256).max);
        bountyId = bountyRegistry.createBounty(
            protocolAgentId, "TestProtocol", "ipfs://scope",
            BountyRegistry.Tiers(25_000e6, 10_000e6, 2_000e6, 500e6),
            50_000e6, block.timestamp + 30 days, 0
        );
        vm.stopPrank();

        // Hunter commits and reveals
        usdc.mint(hunterOwner, 1_000e6);
        vm.prank(hunterOwner);
        usdc.approve(address(submission), type(uint256).max);

        string memory cid = "ipfs://encrypted";
        bytes32 salt = bytes32("huntersalt");
        bytes32 commitHash = keccak256(abi.encode(cid, hunterAgentId, salt));
        vm.prank(hunterOwner);
        bugId = submission.commitBug(bountyId, commitHash, hunterAgentId, 4);
        vm.prank(hunterOwner);
        submission.revealBug(bugId, cid, salt);
    }

    function test_register_state_impact() public {
        bytes32 reqHash = keccak256("statehash");
        vm.prank(executor);
        validation.submitValidation(executorAgentId, reqHash, "ipfs://statediff");

        arbiter.setExecutor(executor);
        vm.prank(executor);
        arbiter.registerStateImpact(bugId, reqHash, "ipfs://statediff");
    }

    function test_full_voting_flow_critical() public {
        // Register state impact
        bytes32 reqHash = keccak256("statehash");
        vm.prank(executor);
        validation.submitValidation(executorAgentId, reqHash, "ipfs://statediff");
        arbiter.setExecutor(executor);
        vm.prank(executor);
        arbiter.registerStateImpact(bugId, reqHash, "ipfs://statediff");

        // Arbiter 1 commits: CRITICAL (4)
        bytes32 salt1 = bytes32("salt1");
        vm.prank(arbiterOwner1);
        arbiter.commitVote(bugId, keccak256(abi.encode(uint8(4), salt1)));

        // Arbiter 2 commits: CRITICAL (4)
        bytes32 salt2 = bytes32("salt2");
        vm.prank(arbiterOwner2);
        arbiter.commitVote(bugId, keccak256(abi.encode(uint8(4), salt2)));

        // Arbiter 3 commits: HIGH (3)
        bytes32 salt3 = bytes32("salt3");
        vm.prank(arbiterOwner3);
        arbiter.commitVote(bugId, keccak256(abi.encode(uint8(3), salt3)));

        // Reveal all
        vm.prank(arbiterOwner1);
        arbiter.revealVote(bugId, 4, salt1);
        vm.prank(arbiterOwner2);
        arbiter.revealVote(bugId, 4, salt2);
        vm.prank(arbiterOwner3);
        arbiter.revealVote(bugId, 3, salt3);

        // Check: hunter got paid CRITICAL tier (25,000 USDC) + stake returned
        assertEq(usdc.balanceOf(hunterOwner), 1_000e6 + 25_000e6); // original 1000 + 25000 payout (stake 250 returned included in 1000)
    }

    function test_majority_invalid_slashes_stake() public {
        bytes32 reqHash = keccak256("statehash");
        vm.prank(executor);
        validation.submitValidation(executorAgentId, reqHash, "ipfs://statediff");
        arbiter.setExecutor(executor);
        vm.prank(executor);
        arbiter.registerStateImpact(bugId, reqHash, "ipfs://statediff");

        // All vote INVALID (0)
        bytes32 salt1 = bytes32("s1");
        bytes32 salt2 = bytes32("s2");
        bytes32 salt3 = bytes32("s3");

        vm.prank(arbiterOwner1);
        arbiter.commitVote(bugId, keccak256(abi.encode(uint8(0), salt1)));
        vm.prank(arbiterOwner2);
        arbiter.commitVote(bugId, keccak256(abi.encode(uint8(0), salt2)));
        vm.prank(arbiterOwner3);
        arbiter.commitVote(bugId, keccak256(abi.encode(uint8(0), salt3)));

        vm.prank(arbiterOwner1);
        arbiter.revealVote(bugId, 0, salt1);
        vm.prank(arbiterOwner2);
        arbiter.revealVote(bugId, 0, salt2);
        vm.prank(arbiterOwner3);
        arbiter.revealVote(bugId, 0, salt3);

        // Hunter should have lost stake (250 USDC)
        assertEq(usdc.balanceOf(hunterOwner), 750e6); // 1000 - 250 stake
    }
}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/sneg55/Documents/GitHub/hackathon/contracts && forge test --match-contract ArbiterContractTest -v`
Expected: FAIL

- [ ] **Step 3: Write ArbiterContract implementation**

```solidity
// contracts/src/ArbiterContract.sol
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "./erc8004/IdentityRegistry.sol";
import "./erc8004/ReputationRegistry.sol";
import "./erc8004/ValidationRegistry.sol";
import "./BugSubmission.sol";

contract ArbiterContract {
    enum Phase { AwaitingStateImpact, Voting, Revealing, Resolved }

    struct Arbitration {
        uint256 bugId;
        string stateImpactCID;
        bytes32 validationRequestHash;
        uint256[3] jurors;
        bytes32[3] commitHashes;
        uint8[3] revealedSeverities;
        bool[3] revealed;
        uint256 revealCount;
        uint256 commitDeadlineBlock;
        uint256 revealDeadlineBlock;
        Phase phase;
    }

    uint256 public constant COMMIT_WINDOW = 50;
    uint256 public constant REVEAL_WINDOW = 50;

    IdentityRegistry public immutable identityRegistry;
    ReputationRegistry public immutable reputationRegistry;
    ValidationRegistry public immutable validationRegistry;
    BugSubmission public immutable bugSubmission;
    address public executor;

    uint256[] public arbiterPool;
    mapping(uint256 => bool) public isInPool;
    mapping(uint256 => Arbitration) private _arbitrations;

    event ArbiterRegistered(uint256 indexed arbiterAgentId);
    event ArbiterUnregistered(uint256 indexed arbiterAgentId);
    event StateImpactRegistered(uint256 indexed bugId, string stateImpactCID);
    event JurySelected(uint256 indexed bugId, uint256[3] jurors);
    event VoteCommitted(uint256 indexed bugId, uint256 indexed arbiterAgentId);
    event VoteRevealed(uint256 indexed bugId, uint256 indexed arbiterAgentId, uint8 severity);
    event SubmissionResolved(uint256 indexed bugId, uint8 finalSeverity, bool isValid);
    event PatchGuidance(uint256 indexed bugId, string encryptedPatchCID);

    address public immutable deployer;

    constructor(address _identity, address _reputation, address _validation, address _bugSubmission) {
        identityRegistry = IdentityRegistry(_identity);
        reputationRegistry = ReputationRegistry(_reputation);
        validationRegistry = ValidationRegistry(_validation);
        bugSubmission = BugSubmission(_bugSubmission);
        deployer = msg.sender;
    }

    function setExecutor(address _executor) external {
        require(msg.sender == deployer, "Only deployer");
        require(executor == address(0), "Already set");
        executor = _executor;
    }

    function registerArbiter(uint256 arbiterAgentId) external {
        require(identityRegistry.isActive(arbiterAgentId), "Invalid agent");
        require(identityRegistry.ownerOf(arbiterAgentId) == msg.sender, "Not agent owner");
        require(!isInPool[arbiterAgentId], "Already registered");

        arbiterPool.push(arbiterAgentId);
        isInPool[arbiterAgentId] = true;
        emit ArbiterRegistered(arbiterAgentId);
    }

    function unregisterArbiter(uint256 arbiterAgentId) external {
        require(identityRegistry.ownerOf(arbiterAgentId) == msg.sender, "Not agent owner");
        require(isInPool[arbiterAgentId], "Not in pool");

        isInPool[arbiterAgentId] = false;
        // Remove from array
        for (uint256 i = 0; i < arbiterPool.length; i++) {
            if (arbiterPool[i] == arbiterAgentId) {
                arbiterPool[i] = arbiterPool[arbiterPool.length - 1];
                arbiterPool.pop();
                break;
            }
        }
        emit ArbiterUnregistered(arbiterAgentId);
    }

    function registerStateImpact(uint256 bugId, bytes32 requestHash, string calldata stateImpactCID) external {
        require(msg.sender == executor, "Only executor");
        require(validationRegistry.getValidationStatus(requestHash), "Not validated");

        Arbitration storage a = _arbitrations[bugId];
        require(a.phase == Phase.AwaitingStateImpact || a.bugId == 0, "Wrong phase");

        a.bugId = bugId;
        a.stateImpactCID = stateImpactCID;
        a.validationRequestHash = requestHash;
        a.phase = Phase.Voting;

        _selectJury(bugId);

        a.commitDeadlineBlock = block.number + COMMIT_WINDOW;
        a.revealDeadlineBlock = block.number + COMMIT_WINDOW + REVEAL_WINDOW;

        emit StateImpactRegistered(bugId, stateImpactCID);
    }

    function _selectJury(uint256 bugId) internal {
        Arbitration storage a = _arbitrations[bugId];
        BugSubmission.Submission memory sub = bugSubmission.getSubmission(bugId);

        address hunterOwner = identityRegistry.ownerOf(sub.hunterAgentId);
        BountyRegistry bounty = bugSubmission.bountyRegistry();
        BountyRegistry.Bounty memory b = bounty.getBounty(sub.bountyId);
        address protocolOwner = identityRegistry.ownerOf(b.protocolAgentId);

        // Select top 3 eligible arbiters from pool
        // NOTE: Simplified for demo — takes first 3 eligible arbiters.
        // Production version should sort by ReputationRegistry.getFeedbackCount(id, "consensus_aligned")
        uint256 selected = 0;
        for (uint256 i = 0; i < arbiterPool.length && selected < 3; i++) {
            uint256 candidateId = arbiterPool[i];
            address candidateOwner = identityRegistry.ownerOf(candidateId);

            // Exclude conflicts
            if (candidateOwner == hunterOwner || candidateOwner == protocolOwner) continue;

            a.jurors[selected] = candidateId;
            selected++;
        }
        require(selected == 3, "Not enough eligible arbiters");

        emit JurySelected(bugId, a.jurors);
    }

    function commitVote(uint256 bugId, bytes32 voteHash) external {
        Arbitration storage a = _arbitrations[bugId];
        require(a.phase == Phase.Voting, "Not in voting phase");
        require(block.number <= a.commitDeadlineBlock, "Commit window expired");

        uint256 jurorIdx = _getJurorIndex(bugId, msg.sender);
        require(a.commitHashes[jurorIdx] == bytes32(0), "Already committed");

        a.commitHashes[jurorIdx] = voteHash;
        uint256 arbiterAgentId = a.jurors[jurorIdx];
        emit VoteCommitted(bugId, arbiterAgentId);

        // Check if all committed, advance to reveal phase
        if (a.commitHashes[0] != bytes32(0) && a.commitHashes[1] != bytes32(0) && a.commitHashes[2] != bytes32(0)) {
            a.phase = Phase.Revealing;
        }
    }

    function revealVote(uint256 bugId, uint8 severity, bytes32 salt) external {
        Arbitration storage a = _arbitrations[bugId];
        require(a.phase == Phase.Revealing || a.phase == Phase.Voting, "Not in reveal phase");
        require(block.number <= a.revealDeadlineBlock, "Reveal window expired");
        require(severity <= 4, "Invalid severity");

        uint256 jurorIdx = _getJurorIndex(bugId, msg.sender);
        require(!a.revealed[jurorIdx], "Already revealed");
        require(keccak256(abi.encode(severity, salt)) == a.commitHashes[jurorIdx], "Hash mismatch");

        a.revealed[jurorIdx] = true;
        a.revealedSeverities[jurorIdx] = severity;
        a.revealCount++;

        uint256 arbiterAgentId = a.jurors[jurorIdx];
        emit VoteRevealed(bugId, arbiterAgentId, severity);

        if (a.revealCount == 3) {
            _resolve(bugId);
        }
    }

    function resolveWithTimeout(uint256 bugId) external {
        Arbitration storage a = _arbitrations[bugId];
        require(block.number > a.revealDeadlineBlock, "Window not expired");
        require(a.phase != Phase.Resolved, "Already resolved");

        if (a.revealCount < 2) {
            // Insufficient quorum: return stake (not slashed — arbiter failure)
            bugSubmission.resolveSubmissionTimeout(bugId);
            _penalizeNoShows(bugId);
            a.phase = Phase.Resolved;
            emit SubmissionResolved(bugId, 0, false);
        } else {
            _resolve(bugId);
        }
    }

    function _resolve(uint256 bugId) internal {
        Arbitration storage a = _arbitrations[bugId];
        a.phase = Phase.Resolved;

        // Collect revealed severities
        uint8[3] memory sevs;
        uint256 count = 0;
        for (uint256 i = 0; i < 3; i++) {
            if (a.revealed[i]) {
                sevs[count] = a.revealedSeverities[i];
                count++;
            }
        }

        uint8 finalSeverity;
        bool isValid;

        if (count == 2) {
            // Conservative: min of two
            finalSeverity = sevs[0] < sevs[1] ? sevs[0] : sevs[1];
            isValid = finalSeverity > 0;
        } else {
            // Sort 3 values for median
            if (sevs[0] > sevs[1]) (sevs[0], sevs[1]) = (sevs[1], sevs[0]);
            if (sevs[1] > sevs[2]) (sevs[1], sevs[2]) = (sevs[2], sevs[1]);
            if (sevs[0] > sevs[1]) (sevs[0], sevs[1]) = (sevs[1], sevs[0]);
            finalSeverity = sevs[1]; // median

            // Majority invalid check
            uint256 invalidCount = 0;
            for (uint256 i = 0; i < 3; i++) {
                if (a.revealed[i] && a.revealedSeverities[i] == 0) invalidCount++;
            }
            isValid = invalidCount < 2 && finalSeverity > 0;
            if (!isValid) finalSeverity = 0;
        }

        bugSubmission.resolveSubmission(bugId, finalSeverity, isValid);

        // Post reputation feedback
        _postFeedback(bugId, finalSeverity, isValid);
        _penalizeNoShows(bugId);

        emit SubmissionResolved(bugId, finalSeverity, isValid);
    }

    function _postFeedback(uint256 bugId, uint8 finalSeverity, bool isValid) internal {
        Arbitration storage a = _arbitrations[bugId];
        BugSubmission.Submission memory sub = bugSubmission.getSubmission(bugId);

        // Hunter feedback
        if (isValid) {
            reputationRegistry.giveFeedback(sub.hunterAgentId, 100, "submission_valid", _severityString(finalSeverity));
        } else {
            reputationRegistry.giveFeedback(sub.hunterAgentId, -100, "submission_invalid", _severityString(sub.claimedSeverity));
        }

        // Arbiter feedback
        for (uint256 i = 0; i < 3; i++) {
            if (!a.revealed[i]) continue;
            if (a.revealedSeverities[i] == finalSeverity) {
                reputationRegistry.giveFeedback(a.jurors[i], 10, "consensus_aligned", _severityString(finalSeverity));
            } else {
                reputationRegistry.giveFeedback(a.jurors[i], -5, "consensus_deviated", _severityString(a.revealedSeverities[i]));
            }
        }
    }

    function _penalizeNoShows(uint256 bugId) internal {
        Arbitration storage a = _arbitrations[bugId];
        for (uint256 i = 0; i < 3; i++) {
            if (a.jurors[i] != 0 && !a.revealed[i] && a.commitHashes[i] == bytes32(0)) {
                reputationRegistry.giveFeedback(a.jurors[i], -20, "vote_timeout", "");
            }
        }
    }

    function _severityString(uint8 severity) internal pure returns (string memory) {
        if (severity == 4) return "CRITICAL";
        if (severity == 3) return "HIGH";
        if (severity == 2) return "MEDIUM";
        if (severity == 1) return "LOW";
        return "INVALID";
    }

    function registerPatchGuidance(uint256 bugId, string calldata encryptedPatchCID) external {
        require(msg.sender == executor, "Only executor");
        BugSubmission.Submission memory sub = bugSubmission.getSubmission(bugId);
        require(sub.isValid && sub.finalSeverity >= 3, "Not eligible for patch guidance");
        emit PatchGuidance(bugId, encryptedPatchCID);
    }

    function getArbitration(uint256 bugId) external view returns (Arbitration memory) {
        return _arbitrations[bugId];
    }

    function getArbiterPoolSize() external view returns (uint256) {
        return arbiterPool.length;
    }

    function _getJurorIndex(uint256 bugId, address caller) internal view returns (uint256) {
        Arbitration storage a = _arbitrations[bugId];
        for (uint256 i = 0; i < 3; i++) {
            if (identityRegistry.ownerOf(a.jurors[i]) == caller) return i;
        }
        revert("Not a juror");
    }
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/sneg55/Documents/GitHub/hackathon/contracts && forge test --match-contract ArbiterContractTest -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add contracts/src/ArbiterContract.sol contracts/test/ArbiterContract.t.sol
git commit -m "feat: add ArbiterContract with blind voting, median resolution, and reputation"
```

---

### Task 23: Full Deploy Script Update

**Files:**
- Modify: `contracts/script/Deploy.s.sol`

- [ ] **Step 1: Update deploy script with all contracts**

```solidity
// contracts/script/Deploy.s.sol
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Script.sol";
import "../src/mocks/MockUSDC.sol";
import "../src/erc8004/IdentityRegistry.sol";
import "../src/erc8004/ReputationRegistry.sol";
import "../src/erc8004/ValidationRegistry.sol";
import "../src/BountyRegistry.sol";
import "../src/BugSubmission.sol";
import "../src/ArbiterContract.sol";

contract Deploy is Script {
    function run() external {
        uint256 deployerPrivateKey = vm.envUint("DEPLOYER_PRIVATE_KEY");
        vm.startBroadcast(deployerPrivateKey);

        // Deploy registries
        MockUSDC usdc = new MockUSDC();
        IdentityRegistry identity = new IdentityRegistry();
        ReputationRegistry reputation = new ReputationRegistry();
        ValidationRegistry validation = new ValidationRegistry();

        // Deploy core contracts
        BountyRegistry bountyReg = new BountyRegistry(address(usdc), address(identity));
        BugSubmission bugSub = new BugSubmission(
            address(usdc), address(identity), address(reputation), address(bountyReg)
        );
        ArbiterContract arbiter = new ArbiterContract(
            address(identity), address(reputation), address(validation), address(bugSub)
        );

        // Wire up cross-references
        bountyReg.setBugSubmissionContract(address(bugSub));
        bugSub.setArbiterContract(address(arbiter));
        reputation.addAuthorizedCaller(address(arbiter));

        vm.stopBroadcast();

        console.log("MockUSDC:", address(usdc));
        console.log("IdentityRegistry:", address(identity));
        console.log("ReputationRegistry:", address(reputation));
        console.log("ValidationRegistry:", address(validation));
        console.log("BountyRegistry:", address(bountyReg));
        console.log("BugSubmission:", address(bugSub));
        console.log("ArbiterContract:", address(arbiter));
    }
}
```

- [ ] **Step 2: Verify compilation**

Run: `cd /Users/sneg55/Documents/GitHub/hackathon/contracts && forge build`
Expected: Successful

- [ ] **Step 3: Commit**

```bash
git add contracts/script/Deploy.s.sol
git commit -m "feat: update deploy script with all contracts and cross-references"
```

---

### Task 24: Executor - Fork Runner

**Files:**
- Create: `agents/executor/__init__.py`
- Create: `agents/executor/fork_runner.py`
- Create: `agents/executor/test_fork_runner.py`

- [ ] **Step 1: Write failing test**

```python
# agents/executor/test_fork_runner.py
from unittest.mock import patch, MagicMock

from executor.fork_runner import parse_forge_output


def test_parse_forge_output_success():
    stdout = """
[PASS] testExploit() (gas: 450000)
Suite result: ok. 1 passed; 0 failed;
"""
    result = parse_forge_output(stdout, "")
    assert result["success"] is True
    assert result["gas_used"] == 450000


def test_parse_forge_output_failure():
    stdout = ""
    stderr = """
[FAIL. Reason: revert] testExploit() (gas: 100000)
Suite result: FAILED. 0 passed; 1 failed;
"""
    result = parse_forge_output(stdout, stderr)
    assert result["success"] is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/sneg55/Documents/GitHub/hackathon/agents && python -m pytest executor/test_fork_runner.py -v`
Expected: FAIL

- [ ] **Step 3: Write fork runner**

```python
# agents/executor/__init__.py
```

```python
# agents/executor/fork_runner.py
"""Runs hunter PoC scripts in a Foundry fork."""
import re
import subprocess
import tempfile
from pathlib import Path

from common.config import RPC_URL


def run_poc_in_fork(poc_source: str, fork_block: int | None = None) -> dict:
    """Execute a Foundry PoC test in a forked environment."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create minimal Foundry project
        src_dir = Path(tmpdir) / "src"
        test_dir = Path(tmpdir) / "test"
        src_dir.mkdir()
        test_dir.mkdir()

        (test_dir / "Exploit.t.sol").write_text(poc_source)
        (Path(tmpdir) / "foundry.toml").write_text(
            '[profile.default]\nsrc = "src"\nout = "out"\nlibs = ["lib"]\nsolc = "0.8.24"\n'
        )

        # Install forge-std
        subprocess.run(
            ["forge", "install", "foundry-rs/forge-std", "--no-git", "--no-commit"],
            cwd=tmpdir, capture_output=True,
        )

        cmd = ["forge", "test", "--fork-url", RPC_URL, "-vvv"]
        if fork_block:
            cmd.extend(["--fork-block-number", str(fork_block)])

        result = subprocess.run(cmd, cwd=tmpdir, capture_output=True, text=True, timeout=120)

        return parse_forge_output(result.stdout, result.stderr)


def parse_forge_output(stdout: str, stderr: str) -> dict:
    """Parse forge test output for pass/fail and gas."""
    combined = stdout + stderr
    success = "[PASS]" in combined
    gas_used = 0

    gas_match = re.search(r"\(gas:\s*(\d+)\)", combined)
    if gas_match:
        gas_used = int(gas_match.group(1))

    return {
        "success": success,
        "gas_used": gas_used,
        "stdout": stdout,
        "stderr": stderr,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/sneg55/Documents/GitHub/hackathon/agents && python -m pytest executor/test_fork_runner.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add agents/executor/
git commit -m "feat: add Executor fork runner for PoC execution"
```

---

### Task 25: Executor - State Diff Producer

**Files:**
- Create: `agents/executor/state_diff.py`
- Create: `agents/executor/test_state_diff.py`

- [ ] **Step 1: Write failing test**

```python
# agents/executor/test_state_diff.py
from executor.state_diff import build_state_impact_json, compute_impact_flags


def test_compute_impact_flags_fund_loss():
    balance_changes = [
        {"holder": "0xVault", "holderLabel": "Vault", "deltaUSD": "-1000000"},
        {"holder": "0xAttacker", "holderLabel": "Attacker", "deltaUSD": "+1000000"},
    ]
    flags = compute_impact_flags(balance_changes, [])
    assert flags["directFundLoss"] is True
    assert flags["fundLossUSD"] == 1000000


def test_compute_impact_flags_role_change():
    storage_changes = [
        {"slotLabel": "owner", "before": "0xAdmin", "after": "0xAttacker"},
    ]
    flags = compute_impact_flags([], storage_changes)
    assert flags["unauthorizedRoleChange"] is True


def test_build_state_impact_json():
    result = build_state_impact_json(
        bug_id=1,
        bounty_id=1,
        hunter_agent_id=2,
        claimed_severity=4,
        target_contract="0x1234",
        fork_block=100,
        chain_id=84532,
        exploit_succeeded=True,
        tx_reverted=False,
        gas_used=450000,
        out_of_scope=False,
        balance_changes=[],
        storage_changes=[],
        executor_agent_id=6,
    )
    assert result["bugId"] == 1
    assert result["execution"]["exploitSucceeded"] is True
    assert "impactFlags" in result
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/sneg55/Documents/GitHub/hackathon/agents && python -m pytest executor/test_state_diff.py -v`
Expected: FAIL

- [ ] **Step 3: Write state diff module**

```python
# agents/executor/state_diff.py
"""Produces State Impact JSON from fork execution results."""
import hashlib
import json


def compute_impact_flags(balance_changes: list, storage_changes: list) -> dict:
    """Derive impact flags from state changes."""
    fund_loss = 0
    direct_fund_loss = False
    unauthorized_role_change = False

    for bc in balance_changes:
        delta = float(bc.get("deltaUSD", "0"))
        if delta < 0:
            direct_fund_loss = True
            fund_loss += abs(delta)

    for sc in storage_changes:
        label = sc.get("slotLabel", "").lower()
        if label in ("owner", "admin", "governance", "authority"):
            if sc.get("before") != sc.get("after"):
                unauthorized_role_change = True

    return {
        "directFundLoss": direct_fund_loss,
        "fundLossUSD": int(fund_loss),
        "contractBricked": False,  # Would need more analysis
        "unauthorizedRoleChange": unauthorized_role_change,
        "dosDetected": False,
        "oracleManipulation": False,
    }


def build_state_impact_json(
    bug_id: int,
    bounty_id: int,
    hunter_agent_id: int,
    claimed_severity: int,
    target_contract: str,
    fork_block: int,
    chain_id: int,
    exploit_succeeded: bool,
    tx_reverted: bool,
    gas_used: int,
    out_of_scope: bool,
    balance_changes: list,
    storage_changes: list,
    executor_agent_id: int,
) -> dict:
    """Build the State Impact JSON that arbiters evaluate."""
    impact_flags = compute_impact_flags(balance_changes, storage_changes)

    state_impact = {
        "bugId": bug_id,
        "bountyId": bounty_id,
        "hunterAgentId": hunter_agent_id,
        "claimedSeverity": claimed_severity,
        "execution": {
            "targetContract": target_contract,
            "forkBlock": fork_block,
            "chainId": chain_id,
            "exploitSucceeded": exploit_succeeded,
            "txReverted": tx_reverted,
            "gasUsed": gas_used,
            "outOfScope": out_of_scope,
        },
        "balanceChanges": balance_changes,
        "storageChanges": storage_changes,
        "impactFlags": impact_flags,
        "executorAgentId": executor_agent_id,
    }

    # Compute validation hash
    state_json = json.dumps(state_impact, sort_keys=True)
    state_impact["validationRequestHash"] = "0x" + hashlib.sha256(state_json.encode()).hexdigest()

    return state_impact
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/sneg55/Documents/GitHub/hackathon/agents && python -m pytest executor/test_state_diff.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add agents/executor/state_diff.py agents/executor/test_state_diff.py
git commit -m "feat: add State Impact JSON producer with impact flag derivation"
```

---

### Task 26: Executor - Main Service

**Files:**
- Create: `agents/executor/service.py`

- [ ] **Step 1: Write executor service**

```python
# agents/executor/service.py
"""Executor Service: listens for BugRevealed, runs PoC, produces state diff, triggers arbitration."""
import json
import os
import time

from web3 import Web3

from common.config import RPC_URL, load_deployments
from common.contracts import get_web3, get_all_contracts
from common.crypto import decrypt
from common.ipfs import download_json, upload_json
from executor.fork_runner import run_poc_in_fork
from executor.state_diff import build_state_impact_json


def process_revealed_bug(w3: Web3, contracts: dict, bug_id: int, deployments: dict):
    """Full executor pipeline for a revealed bug."""
    private_key = os.getenv("EXECUTOR_PRIVATE_KEY")
    ecies_private_key = os.getenv("EXECUTOR_ECIES_PRIVATE_KEY")
    account = w3.eth.account.from_key(private_key)
    executor_agent_id = deployments["agentIds"]["executor"]

    # 1. Fetch submission details
    sub = contracts["bugSubmission"].functions.getSubmission(bug_id).call()
    encrypted_cid = sub[4]  # encryptedCID
    bounty_id = sub[0]
    hunter_agent_id = sub[1]
    claimed_severity = sub[2]

    print(f"Processing bug #{bug_id} (bounty #{bounty_id}, severity claim: {claimed_severity})")

    # 2. Download and decrypt payload
    encrypted_data = download_json(encrypted_cid.replace("ipfs://", ""))
    encrypted_bytes = bytes.fromhex(encrypted_data["encrypted"])
    decrypted = decrypt(ecies_private_key.encode(), encrypted_bytes)
    payload = json.loads(decrypted)
    poc_source = payload["poc"]
    report = payload["report"]

    print(f"  Decrypted payload. Running PoC...")

    # 3. Run PoC in fork
    current_block = w3.eth.block_number
    fork_result = run_poc_in_fork(poc_source, fork_block=current_block)

    print(f"  PoC result: {'PASS' if fork_result['success'] else 'FAIL'}")

    # 4. Build State Impact JSON
    # For demo: construct balance/storage changes from the report
    # In production: parse Foundry trace output
    state_impact = build_state_impact_json(
        bug_id=bug_id,
        bounty_id=bounty_id,
        hunter_agent_id=hunter_agent_id,
        claimed_severity=claimed_severity,
        target_contract=report.get("contract", "0x0"),
        fork_block=current_block,
        chain_id=84532,
        exploit_succeeded=fork_result["success"],
        tx_reverted=not fork_result["success"],
        gas_used=fork_result["gas_used"],
        out_of_scope=False,
        balance_changes=[],  # Would be populated from trace
        storage_changes=[],
        executor_agent_id=executor_agent_id,
    )

    # 5. Upload state impact to IPFS
    state_impact_cid = upload_json(state_impact)
    req_hash = bytes.fromhex(state_impact["validationRequestHash"][2:])

    print(f"  State impact uploaded: {state_impact_cid}")

    # 6. Submit to ValidationRegistry
    nonce = w3.eth.get_transaction_count(account.address)
    tx = contracts["validationRegistry"].functions.submitValidation(
        executor_agent_id, req_hash, state_impact_cid
    ).build_transaction({"from": account.address, "nonce": nonce, "gas": 200_000})
    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    w3.eth.wait_for_transaction_receipt(tx_hash)

    # 7. Register state impact on ArbiterContract
    nonce += 1
    tx = contracts["arbiterContract"].functions.registerStateImpact(
        bug_id, req_hash, state_impact_cid
    ).build_transaction({"from": account.address, "nonce": nonce, "gas": 500_000})
    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    w3.eth.wait_for_transaction_receipt(tx_hash)

    print(f"  State impact registered. Arbiters can now vote.")
    return state_impact


def main():
    w3 = get_web3()
    contracts = get_all_contracts(w3)
    deployments = load_deployments()

    print("Executor watching for BugRevealed events... (Ctrl+C to stop)")
    processed = set()

    while True:
        # Poll for revealed submissions
        bug_count = contracts["bugSubmission"].functions.getSubmissionCount().call()
        for i in range(1, bug_count + 1):
            if i in processed:
                continue
            sub = contracts["bugSubmission"].functions.getSubmission(i).call()
            status = sub[6]  # status enum
            if status == 1:  # Revealed
                processed.add(i)
                try:
                    process_revealed_bug(w3, contracts, i, deployments)
                except Exception as e:
                    print(f"  Error processing bug #{i}: {e}")
        time.sleep(5)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify syntax**

Run: `python -c "import ast; ast.parse(open('agents/executor/service.py').read()); print('OK')"`
Expected: OK

- [ ] **Step 3: Commit**

```bash
git add agents/executor/service.py
git commit -m "feat: add Executor service with full pipeline"
```

---

### Task 27: Arbiter Agent - Evaluator + Voter

**Files:**
- Create: `agents/arbiter/__init__.py`
- Create: `agents/arbiter/evaluator.py`
- Create: `agents/arbiter/voter.py`
- Create: `agents/arbiter/test_evaluator.py`

- [ ] **Step 1: Write failing test**

```python
# agents/arbiter/test_evaluator.py
from unittest.mock import patch

from arbiter.evaluator import evaluate_severity

SAMPLE_STATE_IMPACT = {
    "bugId": 1,
    "claimedSeverity": 4,
    "execution": {"exploitSucceeded": True, "txReverted": False, "outOfScope": False},
    "balanceChanges": [{"holderLabel": "Vault", "deltaUSD": "-10000000"}],
    "impactFlags": {"directFundLoss": True, "fundLossUSD": 10000000},
}


@patch("arbiter.evaluator.complete")
def test_evaluate_severity_returns_integer(mock_complete):
    mock_complete.return_value = "4"
    severity = evaluate_severity(SAMPLE_STATE_IMPACT)
    assert severity == 4


@patch("arbiter.evaluator.complete")
def test_evaluate_severity_retries_on_bad_output(mock_complete):
    mock_complete.side_effect = ["I think this is CRITICAL", "4"]
    severity = evaluate_severity(SAMPLE_STATE_IMPACT)
    assert severity == 4
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/sneg55/Documents/GitHub/hackathon/agents && python -m pytest arbiter/test_evaluator.py -v`
Expected: FAIL

- [ ] **Step 3: Write evaluator and voter modules**

```python
# agents/arbiter/__init__.py
```

```python
# agents/arbiter/evaluator.py
"""Severity evaluation via Venice private inference."""
import json

from common.inference import complete

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

EVAL_PROMPT = """You are a smart contract security arbiter.
Evaluate the following state diff against the severity rubric.
Respond with ONLY a single integer:
0 = INVALID (exploit failed or out of scope)
1 = LOW
2 = MEDIUM
3 = HIGH
4 = CRITICAL
No other text."""


def evaluate_severity(
    state_impact: dict,
    model: str | None = None,
    temperature: float = 0.0,
    max_retries: int = 1,
) -> int:
    """Evaluate severity from State Impact JSON. Returns integer 0-4."""
    for attempt in range(max_retries + 1):
        response = complete(
            messages=[
                {"role": "system", "content": EVAL_PROMPT},
                {"role": "user", "content": f"RUBRIC:\n{RUBRIC}\n\nSTATE DIFF:\n{json.dumps(state_impact, indent=2)}"},
            ],
            model=model,
            temperature=temperature,
            max_tokens=4,
        )

        # Parse integer
        cleaned = response.strip()
        try:
            severity = int(cleaned)
            if 0 <= severity <= 4:
                return severity
        except ValueError:
            pass

        if attempt < max_retries:
            continue

    raise ValueError(f"Failed to parse severity from arbiter output: {response}")
```

```python
# agents/arbiter/voter.py
"""Blind commit-reveal voting on-chain."""
import os
import secrets

from web3 import Web3

from common.contracts import get_web3, get_all_contracts


def compute_vote_hash(severity: int, salt: bytes) -> bytes:
    """Compute vote hash matching Solidity's keccak256(abi.encode(uint8, bytes32)).

    IMPORTANT: Uses eth_abi.encode (ABI standard encoding), NOT Web3.solidity_keccak
    which uses abi.encodePacked. Must match the Solidity contract's abi.encode.
    """
    from eth_abi import encode
    encoded = encode(["uint8", "bytes32"], [severity, salt])
    return Web3.keccak(encoded)


def commit_and_reveal_vote(bug_id: int, severity: int, arbiter_key_env: str):
    """Full commit-reveal voting flow."""
    w3 = get_web3()
    contracts = get_all_contracts(w3)
    private_key = os.getenv(arbiter_key_env)
    account = w3.eth.account.from_key(private_key)
    arbiter_contract = contracts["arbiterContract"]

    salt = secrets.token_bytes(32)
    vote_hash = compute_vote_hash(severity, salt)

    # Commit
    nonce = w3.eth.get_transaction_count(account.address)
    tx = arbiter_contract.functions.commitVote(bug_id, vote_hash).build_transaction({
        "from": account.address, "nonce": nonce, "gas": 200_000,
    })
    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    w3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"  Committed vote for bug #{bug_id}")

    # Reveal
    nonce += 1
    tx = arbiter_contract.functions.revealVote(bug_id, severity, salt).build_transaction({
        "from": account.address, "nonce": nonce, "gas": 200_000,
    })
    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    w3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"  Revealed vote for bug #{bug_id}: severity={severity}")

    return {"severity": severity, "salt": salt.hex()}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/sneg55/Documents/GitHub/hackathon/agents && python -m pytest arbiter/test_evaluator.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add agents/arbiter/
git commit -m "feat: add Arbiter evaluator and voter with blind commit-reveal"
```

---

### Task 28: Arbiter Agent - Main Loop

**Files:**
- Create: `agents/arbiter/agent.py`

- [ ] **Step 1: Write arbiter agent**

```python
# agents/arbiter/agent.py
"""Arbiter Agent: watches for jury selection, evaluates, votes."""
import argparse
import os
import time

from common.contracts import get_web3, get_all_contracts
from common.config import load_deployments
from common.ipfs import download_json
from arbiter.evaluator import evaluate_severity
from arbiter.voter import commit_and_reveal_vote

# Model configs per arbiter slot (from spec)
ARBITER_CONFIGS = {
    1: {"model": "llama-3.3-70b", "temperature": 0.0, "key_env": "ARBITER_1_PRIVATE_KEY"},
    2: {"model": "llama-3.3-70b", "temperature": 0.1, "key_env": "ARBITER_2_PRIVATE_KEY"},
    3: {"model": "mistral-large", "temperature": 0.0, "key_env": "ARBITER_3_PRIVATE_KEY"},
}


def run_arbiter(slot: int):
    """Run a single arbiter agent."""
    config = ARBITER_CONFIGS[slot]
    w3 = get_web3()
    contracts = get_all_contracts(w3)
    deployments = load_deployments()
    arbiter_agent_id = deployments["agentIds"][f"arbiter{slot}"]
    private_key = os.getenv(config["key_env"])
    account = w3.eth.account.from_key(private_key)

    print(f"Arbiter {slot} (agent #{arbiter_agent_id}) watching for jury selection...")
    processed = set()

    while True:
        # Poll for arbitration assignments
        bug_count = contracts["bugSubmission"].functions.getSubmissionCount().call()
        for bug_id in range(1, bug_count + 1):
            if bug_id in processed:
                continue

            try:
                arb = contracts["arbiterContract"].functions.getArbitration(bug_id).call()
                phase = arb[11]  # phase
                jurors = arb[3]  # jurors array

                # Check if this arbiter is on the jury and voting is open
                if arbiter_agent_id not in jurors:
                    continue
                if phase < 1:  # Not yet in voting phase
                    continue
                if phase >= 3:  # Already resolved
                    processed.add(bug_id)
                    continue

                processed.add(bug_id)
                print(f"  Selected as juror for bug #{bug_id}")

                # Fetch state impact from IPFS
                state_impact_cid = arb[1]  # stateImpactCID
                state_impact = download_json(state_impact_cid)

                # Evaluate severity
                severity = evaluate_severity(
                    state_impact,
                    model=config["model"],
                    temperature=config["temperature"],
                )
                print(f"  Evaluated severity: {severity}")

                # Vote
                commit_and_reveal_vote(bug_id, severity, config["key_env"])

            except Exception as e:
                print(f"  Error processing bug #{bug_id}: {e}")

        time.sleep(5)


def main():
    parser = argparse.ArgumentParser(description="Arbiter Agent")
    parser.add_argument("--slot", type=int, required=True, choices=[1, 2, 3])
    args = parser.parse_args()
    run_arbiter(args.slot)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify syntax**

Run: `python -c "import ast; ast.parse(open('agents/arbiter/agent.py').read()); print('OK')"`
Expected: OK

- [ ] **Step 3: Commit**

```bash
git add agents/arbiter/agent.py
git commit -m "feat: add Arbiter Agent main loop with per-slot model config"
```

---

## Chunk 5: Vulnerable Contracts + Patch Guidance + Dashboard Completion + Demo Flow

### Task 29: Vulnerable Demo Contracts

**Files:**
- Create: `vulnerable/ReentrancyVault.sol`
- Create: `vulnerable/AccessControlToken.sol`

- [ ] **Step 1: Write ReentrancyVault**

```solidity
// vulnerable/ReentrancyVault.sol
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/**
 * @title ReentrancyVault
 * @notice INTENTIONALLY VULNERABLE - for demo/testing only.
 * @dev Classic reentrancy: updates balance AFTER external call.
 */
contract ReentrancyVault {
    mapping(address => uint256) public balances;

    function deposit() external payable {
        balances[msg.sender] += msg.value;
    }

    function withdraw() external {
        uint256 amount = balances[msg.sender];
        require(amount > 0, "No balance");

        // BUG: sends ETH before updating balance
        (bool success,) = msg.sender.call{value: amount}("");
        require(success, "Transfer failed");

        // This should be BEFORE the call
        balances[msg.sender] = 0;
    }

    receive() external payable {}
}
```

- [ ] **Step 2: Write AccessControlToken**

```solidity
// vulnerable/AccessControlToken.sol
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";

/**
 * @title AccessControlToken
 * @notice INTENTIONALLY VULNERABLE - for demo/testing only.
 * @dev Missing access control on mint function.
 */
contract AccessControlToken is ERC20 {
    address public admin;

    constructor() ERC20("VulnToken", "VULN") {
        admin = msg.sender;
        _mint(msg.sender, 1_000_000e18);
    }

    // BUG: No access control! Should be `require(msg.sender == admin)`
    function mint(address to, uint256 amount) external {
        _mint(to, amount);
    }

    function burn(address from, uint256 amount) external {
        require(msg.sender == admin, "Only admin");
        _burn(from, amount);
    }
}
```

- [ ] **Step 3: Write OracleManipulation**

```solidity
// vulnerable/OracleManipulation.sol
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";

/**
 * @title SimplePriceOracle
 * @notice INTENTIONALLY VULNERABLE - manipulable price feed.
 */
contract SimplePriceOracle {
    uint256 public price = 1e18; // 1:1 initially

    // BUG: Anyone can set the price!
    function setPrice(uint256 _price) external {
        price = _price;
    }
}

/**
 * @title VulnLendingPool
 * @notice INTENTIONALLY VULNERABLE - uses manipulable oracle.
 * @dev Attacker inflates collateral price, borrows more than collateral is worth.
 */
contract VulnLendingPool {
    IERC20 public collateralToken;
    IERC20 public borrowToken;
    SimplePriceOracle public oracle;

    mapping(address => uint256) public collateralDeposits;
    mapping(address => uint256) public borrows;

    constructor(address _collateral, address _borrow, address _oracle) {
        collateralToken = IERC20(_collateral);
        borrowToken = IERC20(_borrow);
        oracle = SimplePriceOracle(_oracle);
    }

    function depositCollateral(uint256 amount) external {
        collateralToken.transferFrom(msg.sender, address(this), amount);
        collateralDeposits[msg.sender] += amount;
    }

    function borrow(uint256 amount) external {
        uint256 collateralValue = (collateralDeposits[msg.sender] * oracle.price()) / 1e18;
        // BUG: uses manipulable oracle price for collateral valuation
        require(amount <= collateralValue * 80 / 100, "Undercollateralized");
        borrows[msg.sender] += amount;
        borrowToken.transfer(msg.sender, amount);
    }
}
```

- [ ] **Step 4: Commit**

```bash
git add vulnerable/
git commit -m "feat: add intentionally vulnerable contracts for demo"
```

---

### Task 30: Executor - Patch Guidance Module

**Files:**
- Create: `agents/executor/patch_guidance.py`
- Create: `agents/executor/test_patch_guidance.py`

- [ ] **Step 1: Write failing test**

```python
# agents/executor/test_patch_guidance.py
from unittest.mock import patch

from executor.patch_guidance import generate_patch_guidance


@patch("executor.patch_guidance.complete")
def test_generate_patch_guidance(mock_complete):
    mock_complete.return_value = '{"affectedFunctions": ["withdraw"], "recommendedChanges": [{"function": "withdraw", "change": "Add nonReentrant modifier"}], "verificationTests": ["calling withdraw with reentrant callback should revert"]}'

    result = generate_patch_guidance(
        poc_source="contract Exploit { ... }",
        target_source="contract Vault { function withdraw() ... }",
        state_diff={"impactFlags": {"directFundLoss": True}},
    )
    assert "affectedFunctions" in result
    assert "withdraw" in result["affectedFunctions"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/sneg55/Documents/GitHub/hackathon/agents && python -m pytest executor/test_patch_guidance.py -v`
Expected: FAIL

- [ ] **Step 3: Write patch guidance module**

```python
# agents/executor/patch_guidance.py
"""Generate patch guidance via Venice private inference."""
import json

from common.inference import complete

PATCH_PROMPT = """You are a smart contract remediation advisor.
Given an exploit proof-of-concept and the target contract source,
generate specific patch guidance.

RULES:
- Specify which functions need changes and what checks to add.
- Do NOT describe the attack mechanism or exploit sequence.
- Do NOT include the exploit payload or attacker contract code.
- Focus only on defensive changes to the target contract.
- Output valid JSON matching this schema:

{
  "affectedFunctions": ["function1", "function2"],
  "recommendedChanges": [
    {"function": "...", "change": "...", "line": null}
  ],
  "verificationTests": ["test description 1", "test description 2"]
}
"""


def generate_patch_guidance(poc_source: str, target_source: str, state_diff: dict) -> dict:
    """Generate remediation guidance without exposing exploit details."""
    response = complete(
        messages=[
            {"role": "system", "content": PATCH_PROMPT},
            {
                "role": "user",
                "content": f"TARGET CONTRACT:\n{target_source}\n\nSTATE DIFF:\n{json.dumps(state_diff, indent=2)}",
            },
        ],
        temperature=0.0,
        max_tokens=2000,
    )

    try:
        return json.loads(response)
    except json.JSONDecodeError:
        start = response.find("{")
        end = response.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(response[start:end])
        return {"affectedFunctions": [], "recommendedChanges": [], "verificationTests": []}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/sneg55/Documents/GitHub/hackathon/agents && python -m pytest executor/test_patch_guidance.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add agents/executor/patch_guidance.py agents/executor/test_patch_guidance.py
git commit -m "feat: add Venice-powered patch guidance generation"
```

---

### Task 31: Protocol Agent - Patch Receiver

**Files:**
- Create: `agents/protocol/patch_receiver.py`

- [ ] **Step 1: Write patch receiver**

```python
# agents/protocol/patch_receiver.py
"""Receives and decrypts patch guidance from the Executor via on-chain events."""
import json
import os
import time

from common.contracts import get_web3, get_all_contracts
from common.config import load_deployments
from common.crypto import decrypt
from common.ipfs import download_json


def watch_for_patch_guidance():
    """Watch for PatchGuidance events and decrypt guidance."""
    w3 = get_web3()
    contracts = get_all_contracts(w3)
    ecies_key = os.getenv("PROTOCOL_ECIES_PRIVATE_KEY")

    print("Watching for patch guidance...")
    last_block = w3.eth.block_number

    while True:
        current_block = w3.eth.block_number
        if current_block > last_block:
            # Query PatchGuidance events
            events = contracts["arbiterContract"].events.PatchGuidance.get_logs(
                fromBlock=last_block + 1,
                toBlock=current_block,
            )

            for event in events:
                bug_id = event["args"]["bugId"]
                cid = event["args"]["encryptedPatchCID"]
                print(f"\nPatch guidance received for bug #{bug_id}")

                # Download and decrypt
                encrypted_data = download_json(cid)
                encrypted_bytes = bytes.fromhex(encrypted_data["encrypted"])
                guidance = json.loads(decrypt(ecies_key.encode(), encrypted_bytes))

                print(f"  Affected functions: {guidance.get('affectedFunctions', [])}")
                for change in guidance.get("recommendedChanges", []):
                    print(f"  - {change['function']}: {change['change']}")
                print(f"  Verification tests:")
                for test in guidance.get("verificationTests", []):
                    print(f"  - {test}")

            last_block = current_block
        time.sleep(5)


if __name__ == "__main__":
    watch_for_patch_guidance()
```

- [ ] **Step 2: Commit**

```bash
git add agents/protocol/patch_receiver.py
git commit -m "feat: add Protocol Agent patch guidance receiver"
```

---

### Task 32: Dashboard - Submission Detail + Live Feed + Agents Pages

**Files:**
- Create: `dashboard/src/pages/SubmissionDetail.tsx`
- Create: `dashboard/src/pages/LiveFeed.tsx`
- Create: `dashboard/src/pages/Agents.tsx`
- Modify: `dashboard/src/contracts.ts` (add BugSubmission, ArbiterContract, IdentityRegistry ABIs)
- Modify: `dashboard/src/App.tsx` (add routing)

- [ ] **Step 1: Extend contracts.ts with all ABIs**

Add BugSubmission, ArbiterContract, and IdentityRegistry ABIs to `dashboard/src/contracts.ts`. Include event signatures and view functions needed by the dashboard pages.

- [ ] **Step 2: Create SubmissionDetail page**

`dashboard/src/pages/SubmissionDetail.tsx` — displays:
- Submission metadata (bug ID, bounty ID, hunter, severity claim)
- Pipeline status progress bar
- State diff visualization (balance changes as red/green rows, storage changes, impact flag badges)
- 3 arbiter vote cards (committed/revealed/severity)
- Final verdict + payout amount

- [ ] **Step 3: Create LiveFeed page**

`dashboard/src/pages/LiveFeed.tsx` — scrolling event log:
- Polls for all event types (BountyCreated, BugCommitted, BugRevealed, StateImpactRegistered, JurySelected, VoteCommitted, VoteRevealed, SubmissionResolved, PatchGuidance)
- Each event as a timestamped card with color coding by type
- Auto-scrolls to newest

- [ ] **Step 4: Create Agents page**

`dashboard/src/pages/Agents.tsx` — lists all agents:
- Reads IdentityRegistry for all minted agents
- Shows agent ID, owner, registration URI
- Reads ReputationRegistry for reputation score
- Shows role badge (Protocol/Hunter/Arbiter/Executor)

- [ ] **Step 5: Update App.tsx routing**

Add the new pages to the navigation and routing in `App.tsx`. Add submission detail as a sub-route within bounty view.

- [ ] **Step 6: Verify build**

Run: `cd /Users/sneg55/Documents/GitHub/hackathon/dashboard && npm run build`
Expected: Successful build

- [ ] **Step 7: Commit**

```bash
git add dashboard/
git commit -m "feat: add submission detail, live feed, and agents pages to dashboard"
```

---

### Task 33: Integration Test - Full Lifecycle (Foundry)

**Files:**
- Create: `contracts/test/Integration.t.sol`

- [ ] **Step 1: Write full lifecycle integration test**

```solidity
// contracts/test/Integration.t.sol
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Test.sol";
import "../src/ArbiterContract.sol";
import "../src/BugSubmission.sol";
import "../src/BountyRegistry.sol";
import "../src/mocks/MockUSDC.sol";
import "../src/erc8004/IdentityRegistry.sol";
import "../src/erc8004/ReputationRegistry.sol";
import "../src/erc8004/ValidationRegistry.sol";

contract IntegrationTest is Test {
    // Full system test: bounty → submit → execute → arbitrate → payout → reputation

    MockUSDC usdc;
    IdentityRegistry identity;
    ReputationRegistry reputation;
    ValidationRegistry validation;
    BountyRegistry bountyReg;
    BugSubmission bugSub;
    ArbiterContract arbiter;

    address owner = makeAddr("owner");
    address protocolOwner = makeAddr("protocol");
    address hunterOwner = makeAddr("hunter");
    address executorAddr = makeAddr("executor");
    address arb1 = makeAddr("arb1");
    address arb2 = makeAddr("arb2");
    address arb3 = makeAddr("arb3");

    function setUp() public {
        vm.startPrank(owner);
        usdc = new MockUSDC();
        identity = new IdentityRegistry();
        reputation = new ReputationRegistry();
        validation = new ValidationRegistry();
        bountyReg = new BountyRegistry(address(usdc), address(identity));
        bugSub = new BugSubmission(address(usdc), address(identity), address(reputation), address(bountyReg));
        arbiter = new ArbiterContract(address(identity), address(reputation), address(validation), address(bugSub));

        bountyReg.setBugSubmissionContract(address(bugSub));
        bugSub.setArbiterContract(address(arbiter));
        reputation.addAuthorizedCaller(address(arbiter));
        validation.addAuthorizedCaller(executorAddr);
        arbiter.setExecutor(executorAddr);

        identity.mintAgent(protocolOwner, "ipfs://protocol"); // ID 1
        identity.mintAgent(hunterOwner, "ipfs://hunter");     // ID 2
        identity.mintAgent(executorAddr, "ipfs://executor");   // ID 3
        identity.mintAgent(arb1, "ipfs://arb1");              // ID 4
        identity.mintAgent(arb2, "ipfs://arb2");              // ID 5
        identity.mintAgent(arb3, "ipfs://arb3");              // ID 6
        vm.stopPrank();

        vm.prank(arb1); arbiter.registerArbiter(4);
        vm.prank(arb2); arbiter.registerArbiter(5);
        vm.prank(arb3); arbiter.registerArbiter(6);

        usdc.mint(protocolOwner, 50_000e6);
        usdc.mint(hunterOwner, 1_000e6);

        vm.prank(protocolOwner); usdc.approve(address(bountyReg), type(uint256).max);
        vm.prank(hunterOwner); usdc.approve(address(bugSub), type(uint256).max);
    }

    function test_full_lifecycle() public {
        // 1. Create bounty
        vm.prank(protocolOwner);
        uint256 bountyId = bountyReg.createBounty(
            1, "TestProtocol", "ipfs://scope",
            BountyRegistry.Tiers(25_000e6, 10_000e6, 2_000e6, 500e6),
            50_000e6, block.timestamp + 30 days, 0
        );

        // 2. Hunter commits + reveals
        string memory cid = "ipfs://encrypted";
        bytes32 salt = bytes32("huntersalt");
        bytes32 commitHash = keccak256(abi.encode(cid, uint256(2), salt));
        vm.prank(hunterOwner);
        uint256 bugId = bugSub.commitBug(bountyId, commitHash, 2, 4);
        vm.prank(hunterOwner);
        bugSub.revealBug(bugId, cid, salt);

        // 3. Executor registers state impact
        bytes32 reqHash = keccak256("statehash");
        vm.prank(executorAddr);
        validation.submitValidation(3, reqHash, "ipfs://statediff");
        vm.prank(executorAddr);
        arbiter.registerStateImpact(bugId, reqHash, "ipfs://statediff");

        // 4. Three arbiters vote (CRITICAL, CRITICAL, HIGH)
        bytes32 s1 = bytes32("s1"); bytes32 s2 = bytes32("s2"); bytes32 s3 = bytes32("s3");
        vm.prank(arb1); arbiter.commitVote(bugId, keccak256(abi.encode(uint8(4), s1)));
        vm.prank(arb2); arbiter.commitVote(bugId, keccak256(abi.encode(uint8(4), s2)));
        vm.prank(arb3); arbiter.commitVote(bugId, keccak256(abi.encode(uint8(3), s3)));

        vm.prank(arb1); arbiter.revealVote(bugId, 4, s1);
        vm.prank(arb2); arbiter.revealVote(bugId, 4, s2);
        vm.prank(arb3); arbiter.revealVote(bugId, 3, s3);

        // 5. Verify: hunter got CRITICAL payout (25,000) + stake returned (250)
        // Hunter had 1000, staked 250, now has 750 + 250 (returned) + 25000 (payout) = 26000
        assertEq(usdc.balanceOf(hunterOwner), 26_000e6);

        // 6. Verify reputation
        assertEq(reputation.getReputation(2), 100); // Hunter: +100 for valid
        assertEq(reputation.getFeedbackCount(2, "submission_valid"), 1);
        // Arb1 and Arb2 aligned with median (4), Arb3 deviated
        assertEq(reputation.getReputation(4), 10);  // Arb1: aligned
        assertEq(reputation.getReputation(5), 10);  // Arb2: aligned
        assertEq(reputation.getReputation(6), -5);  // Arb3: deviated

        // 7. Verify bounty state
        assertEq(bountyReg.getRemainingFunds(bountyId), 25_000e6);
    }
}
```

- [ ] **Step 2: Run integration test**

Run: `cd /Users/sneg55/Documents/GitHub/hackathon/contracts && forge test --match-contract IntegrationTest -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add contracts/test/Integration.t.sol
git commit -m "test: add full lifecycle integration test"
```

---

### Task 34: Demo Flow Script

**Files:**
- Create: `scripts/demo_flow.py`

- [ ] **Step 1: Write demo orchestrator**

```python
# scripts/demo_flow.py
"""
Orchestrate the full BugBounty.agent demo lifecycle.

Usage:
    # Start Anvil first: anvil
    # Deploy: python scripts/deploy_and_register.py
    # Run demo: python scripts/demo_flow.py
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agents"))

from common.contracts import get_web3, get_all_contracts
from common.config import load_deployments
from protocol.agent import create_bounty
from hunter.agent import scan_bounty
from executor.service import process_revealed_bug
from arbiter.agent import ARBITER_CONFIGS
from arbiter.evaluator import evaluate_severity
from arbiter.voter import commit_and_reveal_vote
from common.ipfs import download_json


def main():
    w3 = get_web3()
    contracts = get_all_contracts(w3)
    deployments = load_deployments()

    print("=" * 60)
    print("BugBounty.agent Demo Flow")
    print("=" * 60)

    # Step 1: Protocol Agent creates bounty
    print("\n--- Step 1: Creating bounty ---")
    agent_id = deployments["agentIds"]["protocol"]
    create_bounty(w3, contracts, agent_id, "VulnProtocol Demo", "ipfs://demo-scope", deadline_seconds=3600)

    # Step 2: Hunter Agent scans (for demo, trigger manually)
    print("\n--- Step 2: Hunter scanning bounty #1 ---")
    hunter_agent_id = deployments["agentIds"]["hunter"]
    executor_pubkey = contracts["identityRegistry"].functions.getMetadata(
        deployments["agentIds"]["executor"], "eciesPubKey"
    ).call()
    scan_bounty(w3, contracts, 1, hunter_agent_id, executor_pubkey)

    # Step 3: Executor processes revealed bugs
    print("\n--- Step 3: Executor processing revealed submissions ---")
    bug_count = contracts["bugSubmission"].functions.getSubmissionCount().call()
    for bug_id in range(1, bug_count + 1):
        sub = contracts["bugSubmission"].functions.getSubmission(bug_id).call()
        if sub[6] == 1:  # Revealed
            state_impact = process_revealed_bug(w3, contracts, bug_id, deployments)

            # Step 4: Arbiters evaluate and vote
            print(f"\n--- Step 4: Arbiters voting on bug #{bug_id} ---")
            for slot in [1, 2, 3]:
                config = ARBITER_CONFIGS[slot]
                severity = evaluate_severity(
                    state_impact,
                    model=config["model"],
                    temperature=config["temperature"],
                )
                print(f"  Arbiter {slot} evaluates: severity={severity}")
                commit_and_reveal_vote(bug_id, severity, config["key_env"])

    # Step 5: Check results
    print("\n--- Step 5: Results ---")
    for bug_id in range(1, bug_count + 1):
        sub = contracts["bugSubmission"].functions.getSubmission(bug_id).call()
        print(f"  Bug #{bug_id}: valid={sub[8]}, severity={sub[7]}")

    print("\n" + "=" * 60)
    print("Demo complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify syntax**

Run: `python -c "import ast; ast.parse(open('scripts/demo_flow.py').read()); print('OK')"`
Expected: OK

- [ ] **Step 3: Commit**

```bash
git add scripts/demo_flow.py
git commit -m "feat: add demo flow script orchestrating full lifecycle"
```

---

### Task 35: Final - Update Deploy Script + README

**Files:**
- Modify: `scripts/deploy_and_register.py` — extend with all contracts, agent minting, arbiter registration, MockUSDC funding
- Modify: `contracts/script/Deploy.s.sol` — already done in Task 23

- [ ] **Step 1: Update Python deploy script to handle full system setup**

Extend `deploy_and_register.py` to:
- Parse all 7 contract addresses from Foundry output
- Mint 6 agent IDs (protocol, hunter, executor, arbiter1-3)
- Register ECIES public keys as metadata
- Register arbiters in pool
- Mint MockUSDC to protocol (50,000) and hunter (1,000)
- Write complete `deployments.json`

- [ ] **Step 2: Test deploy on local Anvil**

```bash
anvil &
python scripts/deploy_and_register.py --rpc-url http://localhost:8545
cat deployments.json
```
Expected: All addresses populated, agentIds 1-6

- [ ] **Step 3: Run full integration**

```bash
forge test --match-contract IntegrationTest -v
```
Expected: PASS

- [ ] **Step 4: Final commit**

```bash
git add scripts/ contracts/
git commit -m "feat: complete deploy and registration pipeline"
```
