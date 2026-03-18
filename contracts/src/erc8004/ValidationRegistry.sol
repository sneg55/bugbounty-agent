// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/access/Ownable.sol";

contract ValidationRegistry is Ownable {
    struct Validation {
        uint256 executorAgentId;
        string resultURI;
        uint256 timestamp;
        bool exists;
    }

    mapping(address => bool) public authorizedCallers;
    mapping(bytes32 => Validation) private _validations;

    event ValidationSubmitted(uint256 indexed executorAgentId, bytes32 indexed requestHash, string resultURI);

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

    function submitValidation(
        uint256 executorAgentId,
        bytes32 requestHash,
        string calldata resultURI
    ) external onlyAuthorized {
        require(!_validations[requestHash].exists, "Validation already exists");
        _validations[requestHash] = Validation(executorAgentId, resultURI, block.timestamp, true);
        emit ValidationSubmitted(executorAgentId, requestHash, resultURI);
    }

    function getValidationStatus(bytes32 requestHash) external view returns (bool) {
        return _validations[requestHash].exists;
    }

    function getValidation(bytes32 requestHash)
        external
        view
        returns (uint256 executorAgentId, string memory resultURI, uint256 timestamp)
    {
        Validation storage v = _validations[requestHash];
        require(v.exists, "Validation not found");
        return (v.executorAgentId, v.resultURI, v.timestamp);
    }
}
