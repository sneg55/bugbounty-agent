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
