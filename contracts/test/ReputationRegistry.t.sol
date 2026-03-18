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
