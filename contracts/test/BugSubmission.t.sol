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

    function test_insufficient_reputation_rejected() public {
        // Create a bounty that requires minHunterReputation > 0
        usdc.mint(protocolOwner, 50_000e6);
        vm.prank(protocolOwner);
        usdc.approve(address(bountyRegistry), type(uint256).max);
        vm.prank(protocolOwner);
        uint256 restrictedBountyId = bountyRegistry.createBounty(
            protocolAgentId,
            "RestrictedProtocol",
            "ipfs://scope2",
            BountyRegistry.Tiers(25_000e6, 10_000e6, 2_000e6, 500e6),
            50_000e6,
            block.timestamp + 30 days,
            100 // minHunterReputation = 100
        );

        // Hunter has 0 reputation — commit should revert
        bytes32 commitHash = keccak256(abi.encode("ipfs://enc", hunterAgentId, bytes32("salt")));
        vm.prank(hunterOwner);
        vm.expectRevert("Insufficient reputation");
        submission.commitBug(restrictedBountyId, commitHash, hunterAgentId, 4);
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

    // --- 72-hour dispute window tests ---

    function _commitAndReveal(uint8 severity) internal returns (uint256) {
        string memory cid = "ipfs://accept-test";
        bytes32 salt = bytes32("acceptsalt");
        bytes32 commitHash = keccak256(abi.encode(cid, hunterAgentId, salt));
        vm.prank(hunterOwner);
        uint256 id = submission.commitBug(bountyId, commitHash, hunterAgentId, severity);
        vm.prank(hunterOwner);
        submission.revealBug(id, cid, salt);
        return id;
    }

    function test_accept_submission() public {
        uint256 id = _commitAndReveal(3); // HIGH
        uint256 hunterBefore = usdc.balanceOf(hunterOwner);

        vm.prank(protocolOwner);
        submission.acceptSubmission(id);

        BugSubmission.Submission memory sub = submission.getSubmission(id);
        assertTrue(sub.isValid);
        assertEq(sub.finalSeverity, 3);
        assertEq(uint8(sub.protocolResponse), 1); // Accepted

        // Hunter got stake back + HIGH payout (10,000e6)
        uint256 hunterAfter = usdc.balanceOf(hunterOwner);
        uint256 stake = hunterBefore > hunterAfter ? 0 : hunterAfter - hunterBefore; // stake was taken at commit
        // Check: got 100e6 stake + 10_000e6 payout
        assertEq(hunterAfter, hunterBefore + 100e6 + 10_000e6);
    }

    function test_dispute_submission() public {
        uint256 id = _commitAndReveal(4);

        vm.prank(protocolOwner);
        submission.disputeSubmission(id);

        BugSubmission.Submission memory sub = submission.getSubmission(id);
        assertEq(uint8(sub.protocolResponse), 2); // Disputed
        assertEq(uint8(sub.status), 1); // Still Revealed (awaiting arbitration)
    }

    function test_auto_accept_on_timeout() public {
        uint256 id = _commitAndReveal(4); // CRITICAL
        uint256 hunterBefore = usdc.balanceOf(hunterOwner);

        // Warp past 72-hour dispute window
        vm.warp(block.timestamp + 72 hours + 1);

        // Anyone can call autoAcceptOnTimeout
        address anyone = makeAddr("anyone");
        vm.prank(anyone);
        submission.autoAcceptOnTimeout(id);

        BugSubmission.Submission memory sub = submission.getSubmission(id);
        assertTrue(sub.isValid);
        assertEq(sub.finalSeverity, 4);

        // Hunter got stake back + CRITICAL payout (25,000e6)
        assertEq(usdc.balanceOf(hunterOwner), hunterBefore + 250e6 + 25_000e6);
    }

    function test_cannot_accept_after_dispute() public {
        uint256 id = _commitAndReveal(3);

        vm.prank(protocolOwner);
        submission.disputeSubmission(id);

        vm.prank(protocolOwner);
        vm.expectRevert("Already responded");
        submission.acceptSubmission(id);
    }

    function test_cannot_dispute_after_accept() public {
        uint256 id = _commitAndReveal(3);

        vm.prank(protocolOwner);
        submission.acceptSubmission(id);

        vm.prank(protocolOwner);
        vm.expectRevert(); // Resolved or Already responded
        submission.disputeSubmission(id);
    }

    function test_cannot_accept_after_window_expires() public {
        uint256 id = _commitAndReveal(3);

        vm.warp(block.timestamp + 72 hours + 1);

        vm.prank(protocolOwner);
        vm.expectRevert("Dispute window expired");
        submission.acceptSubmission(id);
    }

    function test_non_protocol_owner_cannot_accept() public {
        uint256 id = _commitAndReveal(3);

        vm.prank(hunterOwner);
        vm.expectRevert("Not protocol owner");
        submission.acceptSubmission(id);
    }

    function test_auto_accept_reverts_before_window() public {
        uint256 id = _commitAndReveal(3);

        vm.prank(makeAddr("anyone"));
        vm.expectRevert("Dispute window not expired");
        submission.autoAcceptOnTimeout(id);
    }
}
