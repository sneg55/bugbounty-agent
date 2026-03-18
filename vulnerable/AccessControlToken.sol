// vulnerable/AccessControlToken.sol
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";

/**
 * @title AccessControlToken
 * @notice INTENTIONALLY VULNERABLE - for demo/testing only.
 * @dev Missing access control on mint function.
 */
contract AccessControlToken is ERC20 {
    address public admin;

    constructor() ERC20("VulnToken", "VULN") {
        admin = msg.sender;
        _mint(msg.sender, 1_000_000e18);
    }

    // BUG: No access control! Should be `require(msg.sender == admin)`
    function mint(address to, uint256 amount) external {
        _mint(to, amount);
    }

    function burn(address from, uint256 amount) external {
        require(msg.sender == admin, "Only admin");
        _burn(from, amount);
    }
}
