// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "./erc8004/IdentityRegistry.sol";

interface IBugSubmission {
    function getPendingCount(uint256 bountyId) external view returns (uint256);
}

contract BountyRegistry {
    using SafeERC20 for IERC20;

    struct Tiers {
        uint256 critical;
        uint256 high;
        uint256 medium;
        uint256 low;
    }

    struct Bounty {
        uint256 protocolAgentId;
        string name;
        string scopeURI;
        Tiers tiers;
        uint256 totalFunding;
        uint256 totalPaid;
        uint256 deadline;
        int256 minHunterReputation;
        bool active;
        uint256 submissionCount;
    }

    IERC20 public immutable usdc;
    IdentityRegistry public immutable identityRegistry;
    address public bugSubmissionContract;

    uint256 public constant GRACE_PERIOD = 1800;
    uint256 private _nextBountyId;
    mapping(uint256 => Bounty) private _bounties;

    event BountyCreated(
        uint256 indexed bountyId,
        uint256 indexed protocolAgentId,
        string name,
        uint256 totalFunding,
        uint256 deadline
    );
    event PayoutDeducted(uint256 indexed bountyId, address indexed recipient, uint256 amount);
    event RemainderWithdrawn(uint256 indexed bountyId, uint256 amount);

    address public immutable deployer;

    constructor(address _usdc, address _identityRegistry) {
        usdc = IERC20(_usdc);
        identityRegistry = IdentityRegistry(_identityRegistry);
        deployer = msg.sender;
    }

    function setBugSubmissionContract(address _bugSubmission) external {
        require(msg.sender == deployer, "Only deployer");
        require(bugSubmissionContract == address(0), "Already set");
        bugSubmissionContract = _bugSubmission;
    }

    function createBounty(
        uint256 protocolAgentId,
        string calldata name,
        string calldata scopeURI,
        Tiers calldata tiers,
        uint256 funding,
        uint256 deadline,
        int256 minHunterReputation
    ) external returns (uint256) {
        require(identityRegistry.ownerOf(protocolAgentId) == msg.sender, "Not agent owner");
        require(deadline > block.timestamp, "Deadline must be in the future");
        require(funding > 0, "Funding must be > 0");
        require(tiers.low > 0, "Low tier must be > 0");
        require(tiers.medium >= tiers.low, "Tiers must be ordered: medium >= low");
        require(tiers.high >= tiers.medium, "Tiers must be ordered: high >= medium");
        require(tiers.critical >= tiers.high, "Tiers must be ordered: critical >= high");
        require(funding >= tiers.critical, "Funding must cover at least one critical payout");

        _nextBountyId++;
        uint256 bountyId = _nextBountyId;

        _bounties[bountyId] = Bounty({
            protocolAgentId: protocolAgentId,
            name: name,
            scopeURI: scopeURI,
            tiers: tiers,
            totalFunding: funding,
            totalPaid: 0,
            deadline: deadline,
            minHunterReputation: minHunterReputation,
            active: true,
            submissionCount: 0
        });

        usdc.safeTransferFrom(msg.sender, address(this), funding);

        emit BountyCreated(bountyId, protocolAgentId, name, funding, deadline);
        return bountyId;
    }

    function deductPayout(uint256 bountyId, uint256 amount, address recipient) external {
        require(msg.sender == bugSubmissionContract, "Only BugSubmission");
        Bounty storage b = _bounties[bountyId];
        require(b.active, "Bounty not active");
        require(b.totalPaid + amount <= b.totalFunding, "Insufficient funds");

        b.totalPaid += amount;
        usdc.safeTransfer(recipient, amount);

        emit PayoutDeducted(bountyId, recipient, amount);
    }

    function incrementSubmissionCount(uint256 bountyId) external {
        require(msg.sender == bugSubmissionContract, "Only BugSubmission");
        _bounties[bountyId].submissionCount++;
    }

    function withdrawRemainder(uint256 bountyId) external {
        Bounty storage b = _bounties[bountyId];
        require(identityRegistry.ownerOf(b.protocolAgentId) == msg.sender, "Not agent owner");
        require(block.timestamp > b.deadline + GRACE_PERIOD, "Deadline + grace not passed");
        require(b.active, "Already withdrawn");
        require(
            bugSubmissionContract == address(0) ||
            IBugSubmission(bugSubmissionContract).getPendingCount(bountyId) == 0,
            "Pending submissions exist"
        );

        uint256 remainder = b.totalFunding - b.totalPaid;
        require(remainder > 0, "No remainder");

        b.active = false;
        usdc.safeTransfer(msg.sender, remainder);

        emit RemainderWithdrawn(bountyId, remainder);
    }

    function getBounty(uint256 bountyId) external view returns (Bounty memory) {
        return _bounties[bountyId];
    }

    function getRemainingFunds(uint256 bountyId) external view returns (uint256) {
        Bounty storage b = _bounties[bountyId];
        return b.totalFunding - b.totalPaid;
    }

    function getBountyCount() external view returns (uint256) {
        return _nextBountyId;
    }

    function getTierPayout(uint256 bountyId, uint8 severity) external view returns (uint256) {
        Bounty storage b = _bounties[bountyId];
        if (severity == 4) return b.tiers.critical;
        if (severity == 3) return b.tiers.high;
        if (severity == 2) return b.tiers.medium;
        if (severity == 1) return b.tiers.low;
        return 0;
    }
}
