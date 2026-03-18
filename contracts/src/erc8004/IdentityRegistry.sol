// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

contract IdentityRegistry is ERC721, Ownable {
    uint256 private _nextTokenId;

    mapping(uint256 => string) private _registrationURIs;
    mapping(uint256 => mapping(string => bytes)) private _metadata;

    event AgentMinted(uint256 indexed agentId, address indexed owner, string registrationURI);
    event MetadataUpdated(uint256 indexed agentId, string key);

    constructor() ERC721("BugBounty Agent Identity", "BBAID") Ownable(msg.sender) {}

    function mintAgent(address to, string calldata registrationURI) external onlyOwner returns (uint256) {
        _nextTokenId++;
        uint256 agentId = _nextTokenId;
        _mint(to, agentId);
        _registrationURIs[agentId] = registrationURI;
        emit AgentMinted(agentId, to, registrationURI);
        return agentId;
    }

    function setMetadata(uint256 agentId, string calldata key, bytes calldata value) external {
        require(ownerOf(agentId) == msg.sender, "Not token owner");
        _metadata[agentId][key] = value;
        emit MetadataUpdated(agentId, key);
    }

    function getMetadata(uint256 agentId, string calldata key) external view returns (bytes memory) {
        return _metadata[agentId][key];
    }

    function isActive(uint256 agentId) external view returns (bool) {
        if (agentId == 0 || agentId > _nextTokenId) return false;
        return _ownerOf(agentId) != address(0);
    }

    function tokenURI(uint256 tokenId) public view override returns (string memory) {
        _requireOwned(tokenId);
        return _registrationURIs[tokenId];
    }

    function totalAgents() external view returns (uint256) {
        return _nextTokenId;
    }
}
