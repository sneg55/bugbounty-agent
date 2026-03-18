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
