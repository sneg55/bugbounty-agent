// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20 ^0.8.24;

// lib/openzeppelin-contracts/contracts/utils/Context.sol

// OpenZeppelin Contracts (last updated v5.0.1) (utils/Context.sol)

/**
 * @dev Provides information about the current execution context, including the
 * sender of the transaction and its data. While these are generally available
 * via msg.sender and msg.data, they should not be accessed in such a direct
 * manner, since when dealing with meta-transactions the account sending and
 * paying for execution may not be the actual sender (as far as an application
 * is concerned).
 *
 * This contract is only required for intermediate, library-like contracts.
 */
abstract contract Context {
    function _msgSender() internal view virtual returns (address) {
        return msg.sender;
    }

    function _msgData() internal view virtual returns (bytes calldata) {
        return msg.data;
    }

    function _contextSuffixLength() internal view virtual returns (uint256) {
        return 0;
    }
}

// lib/openzeppelin-contracts/contracts/access/Ownable.sol

// OpenZeppelin Contracts (last updated v5.0.0) (access/Ownable.sol)

/**
 * @dev Contract module which provides a basic access control mechanism, where
 * there is an account (an owner) that can be granted exclusive access to
 * specific functions.
 *
 * The initial owner is set to the address provided by the deployer. This can
 * later be changed with {transferOwnership}.
 *
 * This module is used through inheritance. It will make available the modifier
 * `onlyOwner`, which can be applied to your functions to restrict their use to
 * the owner.
 */
abstract contract Ownable is Context {
    address private _owner;

    /**
     * @dev The caller account is not authorized to perform an operation.
     */
    error OwnableUnauthorizedAccount(address account);

    /**
     * @dev The owner is not a valid owner account. (eg. `address(0)`)
     */
    error OwnableInvalidOwner(address owner);

    event OwnershipTransferred(address indexed previousOwner, address indexed newOwner);

    /**
     * @dev Initializes the contract setting the address provided by the deployer as the initial owner.
     */
    constructor(address initialOwner) {
        if (initialOwner == address(0)) {
            revert OwnableInvalidOwner(address(0));
        }
        _transferOwnership(initialOwner);
    }

    /**
     * @dev Throws if called by any account other than the owner.
     */
    modifier onlyOwner() {
        _checkOwner();
        _;
    }

    /**
     * @dev Returns the address of the current owner.
     */
    function owner() public view virtual returns (address) {
        return _owner;
    }

    /**
     * @dev Throws if the sender is not the owner.
     */
    function _checkOwner() internal view virtual {
        if (owner() != _msgSender()) {
            revert OwnableUnauthorizedAccount(_msgSender());
        }
    }

    /**
     * @dev Leaves the contract without owner. It will not be possible to call
     * `onlyOwner` functions. Can only be called by the current owner.
     *
     * NOTE: Renouncing ownership will leave the contract without an owner,
     * thereby disabling any functionality that is only available to the owner.
     */
    function renounceOwnership() public virtual onlyOwner {
        _transferOwnership(address(0));
    }

    /**
     * @dev Transfers ownership of the contract to a new account (`newOwner`).
     * Can only be called by the current owner.
     */
    function transferOwnership(address newOwner) public virtual onlyOwner {
        if (newOwner == address(0)) {
            revert OwnableInvalidOwner(address(0));
        }
        _transferOwnership(newOwner);
    }

    /**
     * @dev Transfers ownership of the contract to a new account (`newOwner`).
     * Internal function without access restriction.
     */
    function _transferOwnership(address newOwner) internal virtual {
        address oldOwner = _owner;
        _owner = newOwner;
        emit OwnershipTransferred(oldOwner, newOwner);
    }
}

// src/erc8004/ReputationRegistry.sol

contract ReputationRegistry is Ownable {
    struct Feedback {
        int256 value;
        string tag1;
        string tag2;
        uint256 timestamp;
    }

    mapping(address => bool) public authorizedCallers;
    mapping(uint256 => int256) private _reputation;
    mapping(uint256 => mapping(string => uint256)) private _feedbackCounts;
    mapping(uint256 => Feedback[]) private _feedbackHistory;

    event FeedbackGiven(uint256 indexed targetAgentId, int256 value, string tag1, string tag2);

    constructor() Ownable(msg.sender) {}

    modifier onlyAuthorized() {
        require(authorizedCallers[msg.sender], "Not authorized");
        _;
    }

    function addAuthorizedCaller(address caller) external onlyOwner {
        authorizedCallers[caller] = true;
    }

    function removeAuthorizedCaller(address caller) external onlyOwner {
        authorizedCallers[caller] = false;
    }

    function giveFeedback(
        uint256 targetAgentId,
        int256 value,
        string calldata tag1,
        string calldata tag2
    ) external onlyAuthorized {
        _reputation[targetAgentId] += value;
        _feedbackCounts[targetAgentId][tag1]++;
        _feedbackHistory[targetAgentId].push(Feedback(value, tag1, tag2, block.timestamp));
        emit FeedbackGiven(targetAgentId, value, tag1, tag2);
    }

    function getReputation(uint256 agentId) external view returns (int256) {
        return _reputation[agentId];
    }

    function getFeedbackCount(uint256 agentId, string calldata tag1) external view returns (uint256) {
        return _feedbackCounts[agentId][tag1];
    }

    function getValidityRate(uint256 agentId) external view returns (uint256) {
        uint256 valid = _feedbackCounts[agentId]["submission_valid"];
        uint256 invalid = _feedbackCounts[agentId]["submission_invalid"];
        uint256 total = valid + invalid;
        if (total == 0) return 0;
        return (valid * 100) / total;
    }

    function getFeedbackHistory(uint256 agentId) external view returns (Feedback[] memory) {
        return _feedbackHistory[agentId];
    }
}
