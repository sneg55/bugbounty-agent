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
