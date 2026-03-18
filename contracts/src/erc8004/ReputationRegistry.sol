// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/access/Ownable.sol";

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
