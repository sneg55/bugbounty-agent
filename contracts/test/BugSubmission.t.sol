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
