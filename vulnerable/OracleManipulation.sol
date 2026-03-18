// vulnerable/OracleManipulation.sol
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";

/**
 * @title SimplePriceOracle
 * @notice INTENTIONALLY VULNERABLE - manipulable price feed.
 */
contract SimplePriceOracle {
    uint256 public price = 1e18; // 1:1 initially

    // BUG: Anyone can set the price!
    function setPrice(uint256 _price) external {
        price = _price;
    }
}

/**
 * @title VulnLendingPool
 * @notice INTENTIONALLY VULNERABLE - uses manipulable oracle.
 * @dev Attacker inflates collateral price, borrows more than collateral is worth.
 */
contract VulnLendingPool {
    IERC20 public collateralToken;
    IERC20 public borrowToken;
    SimplePriceOracle public oracle;

    mapping(address => uint256) public collateralDeposits;
    mapping(address => uint256) public borrows;

    constructor(address _collateral, address _borrow, address _oracle) {
        collateralToken = IERC20(_collateral);
        borrowToken = IERC20(_borrow);
        oracle = SimplePriceOracle(_oracle);
    }

    function depositCollateral(uint256 amount) external {
        collateralToken.transferFrom(msg.sender, address(this), amount);
        collateralDeposits[msg.sender] += amount;
    }

    function borrow(uint256 amount) external {
        uint256 collateralValue = (collateralDeposits[msg.sender] * oracle.price()) / 1e18;
        // BUG: uses manipulable oracle price for collateral valuation
        require(amount <= collateralValue * 80 / 100, "Undercollateralized");
        borrows[msg.sender] += amount;
        borrowToken.transfer(msg.sender, amount);
    }
}
