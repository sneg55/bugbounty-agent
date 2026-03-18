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
