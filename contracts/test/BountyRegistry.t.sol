// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Test.sol";
import "../src/BountyRegistry.sol";
import "../src/BugSubmission.sol";
import "../src/ArbiterContract.sol";
import "../src/mocks/MockUSDC.sol";
import "../src/erc8004/IdentityRegistry.sol";
import "../src/erc8004/ReputationRegistry.sol";
import "../src/erc8004/ValidationRegistry.sol";

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

// Separate test contract to avoid stack-too-deep in the pending-submissions test
contract BountyRegistryPendingTest is Test {
    BountyRegistry public bountyRegistry;
    BugSubmission public submission;
    ArbiterContract public arbiter;
    MockUSDC public usdc;
    IdentityRegistry public identity;
    ReputationRegistry public reputation;
    ValidationRegistry public validation;

    address public owner = makeAddr("owner");
    address public protocolOwner = makeAddr("protocolOwner2");
    address public hunterOwner = makeAddr("hunterOwner2");
    address public executor = makeAddr("executor2");
    address public arbiterOwner1 = makeAddr("arb1wb");
    address public arbiterOwner2 = makeAddr("arb2wb");
    address public arbiterOwner3 = makeAddr("arb3wb");

    uint256 public protocolAgentId;
    uint256 public hunterAgentId;
    uint256 public executorAgentId;
    uint256 public arbiterAgentId1;
    uint256 public arbiterAgentId2;
    uint256 public arbiterAgentId3;
    uint256 public bountyId;
    uint256 public bugId;
    uint256 public bountyDeadline;

    function setUp() public {
        vm.startPrank(owner);
        usdc = new MockUSDC();
        identity = new IdentityRegistry();
        reputation = new ReputationRegistry();
        validation = new ValidationRegistry();
        bountyRegistry = new BountyRegistry(address(usdc), address(identity));
        submission = new BugSubmission(address(usdc), address(identity), address(reputation), address(bountyRegistry));
        arbiter = new ArbiterContract(address(identity), address(reputation), address(validation), address(submission));

        bountyRegistry.setBugSubmissionContract(address(submission));
        submission.setArbiterContract(address(arbiter));
        reputation.addAuthorizedCaller(address(arbiter));
        validation.addAuthorizedCaller(executor);

        protocolAgentId = identity.mintAgent(protocolOwner, "ipfs://protocol2");
        hunterAgentId = identity.mintAgent(hunterOwner, "ipfs://hunter2");
        executorAgentId = identity.mintAgent(executor, "ipfs://executor2");
        arbiterAgentId1 = identity.mintAgent(arbiterOwner1, "ipfs://arb1wb");
        arbiterAgentId2 = identity.mintAgent(arbiterOwner2, "ipfs://arb2wb");
        arbiterAgentId3 = identity.mintAgent(arbiterOwner3, "ipfs://arb3wb");
        vm.stopPrank();

        vm.prank(arbiterOwner1);
        arbiter.registerArbiter(arbiterAgentId1);
        vm.prank(arbiterOwner2);
        arbiter.registerArbiter(arbiterAgentId2);
        vm.prank(arbiterOwner3);
        arbiter.registerArbiter(arbiterAgentId3);

        usdc.mint(protocolOwner, 50_000e6);
        vm.startPrank(protocolOwner);
        usdc.approve(address(bountyRegistry), type(uint256).max);
        bountyDeadline = block.timestamp + 1 days;
        bountyId = bountyRegistry.createBounty(
            protocolAgentId, "PendingTest", "ipfs://scope",
            BountyRegistry.Tiers(25_000e6, 10_000e6, 2_000e6, 500e6),
            50_000e6, bountyDeadline, 0
        );
        vm.stopPrank();

        usdc.mint(hunterOwner, 1_000e6);
        vm.prank(hunterOwner);
        usdc.approve(address(submission), type(uint256).max);

        bytes32 commitHash = keccak256(abi.encode("ipfs://enc2", hunterAgentId, bytes32("hsalt2")));
        vm.prank(hunterOwner);
        bugId = submission.commitBug(bountyId, commitHash, hunterAgentId, 4);
        vm.prank(hunterOwner);
        submission.revealBug(bugId, "ipfs://enc2", bytes32("hsalt2"));
    }

    function test_withdraw_reverts_with_pending_submissions() public {
        vm.warp(bountyDeadline + bountyRegistry.GRACE_PERIOD() + 1);

        vm.prank(protocolOwner);
        vm.expectRevert("Pending submissions exist");
        bountyRegistry.withdrawRemainder(bountyId);
    }

    function test_withdraw_succeeds_after_submission_resolved() public {
        vm.warp(bountyDeadline + bountyRegistry.GRACE_PERIOD() + 1);

        // Resolve via arbiter voting
        bytes32 reqHash = keccak256("statehash_wb2");
        vm.prank(executor);
        validation.submitValidation(executorAgentId, reqHash, "ipfs://statediff_wb2");
        vm.prank(owner);
        arbiter.setExecutor(executor);
        vm.prank(executor);
        arbiter.registerStateImpact(bugId, reqHash, "ipfs://statediff_wb2");

        _doVotes(uint8(4));

        // Pending count now 0 — withdraw should succeed
        // Remaining = 50,000 - 25,000 (critical payout) = 25,000
        vm.prank(protocolOwner);
        bountyRegistry.withdrawRemainder(bountyId);
        assertEq(usdc.balanceOf(protocolOwner), 25_000e6);
    }

    function _doVotes(uint8 severity) internal {
        bytes32 s1 = bytes32("s1wb2");
        bytes32 s2 = bytes32("s2wb2");
        bytes32 s3 = bytes32("s3wb2");
        vm.prank(arbiterOwner1);
        arbiter.commitVote(bugId, keccak256(abi.encode(severity, s1)));
        vm.prank(arbiterOwner2);
        arbiter.commitVote(bugId, keccak256(abi.encode(severity, s2)));
        vm.prank(arbiterOwner3);
        arbiter.commitVote(bugId, keccak256(abi.encode(severity, s3)));
        vm.prank(arbiterOwner1);
        arbiter.revealVote(bugId, severity, s1);
        vm.prank(arbiterOwner2);
        arbiter.revealVote(bugId, severity, s2);
        vm.prank(arbiterOwner3);
        arbiter.revealVote(bugId, severity, s3);
    }
}
