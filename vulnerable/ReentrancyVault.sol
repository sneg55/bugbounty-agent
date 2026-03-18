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
