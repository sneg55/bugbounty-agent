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

    function test_cannot_overwrite_validation() public {
        bytes32 reqHash = keccak256("test");
        vm.prank(executor);
        registry.submitValidation(88, reqHash, "ipfs://first");

        vm.prank(executor);
        vm.expectRevert("Validation already exists");
        registry.submitValidation(88, reqHash, "ipfs://second");
    }
}
