// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "./erc8004/IdentityRegistry.sol";
import "./erc8004/ReputationRegistry.sol";
import "./BountyRegistry.sol";

contract BugSubmission {
    using SafeERC20 for IERC20;

    enum Status { Committed, Revealed, Resolved }
    enum ProtocolResponse { None, Accepted, Disputed }

    struct Submission {
        uint256 bountyId;
        uint256 hunterAgentId;
        uint8 claimedSeverity;
        bytes32 commitHash;
        string encryptedCID;
        uint256 stake;
        Status status;
        uint8 finalSeverity;
        bool isValid;
        uint256 commitBlock;
        address hunterWallet;
        uint256 revealedAt;
        ProtocolResponse protocolResponse;
    }

    uint256 public constant REVEAL_WINDOW = 200; // blocks
    uint256 public constant DISPUTE_WINDOW = 72 hours;
    uint256 public constant MAX_SUBMISSIONS_PER_HUNTER = 3;

    IERC20 public immutable usdc;
    IdentityRegistry public immutable identityRegistry;
    ReputationRegistry public immutable reputationRegistry;
    BountyRegistry public immutable bountyRegistry;
    address public arbiterContract;

    uint256 private _nextBugId;
    mapping(uint256 => Submission) private _submissions;
    mapping(uint256 => mapping(uint256 => uint256)) private _activeSubmissionCount; // bountyId => hunterAgentId => count
    mapping(uint256 => uint256) private _pendingCountPerBounty; // bountyId => pending submission count

    event BugCommitted(uint256 indexed bugId, uint256 indexed bountyId, uint256 indexed hunterAgentId, uint8 claimedSeverity);
    event BugRevealed(uint256 indexed bugId, string encryptedCID);
    event SubmissionResolved(uint256 indexed bugId, uint8 finalSeverity, bool isValid);
    event SubmissionAccepted(uint256 indexed bugId, uint8 claimedSeverity);
    event SubmissionDisputed(uint256 indexed bugId);

    address public immutable deployer;

    constructor(address _usdc, address _identity, address _reputation, address _bountyRegistry) {
        usdc = IERC20(_usdc);
        identityRegistry = IdentityRegistry(_identity);
        reputationRegistry = ReputationRegistry(_reputation);
        bountyRegistry = BountyRegistry(_bountyRegistry);
        deployer = msg.sender;
    }

    function setArbiterContract(address _arbiter) external {
        require(msg.sender == deployer, "Only deployer");
        require(arbiterContract == address(0), "Already set");
        arbiterContract = _arbiter;
    }

    function commitBug(
        uint256 bountyId,
        bytes32 commitHash,
        uint256 hunterAgentId,
        uint8 claimedSeverity
    ) external returns (uint256) {
        require(identityRegistry.isActive(hunterAgentId), "Invalid agent");
        require(identityRegistry.ownerOf(hunterAgentId) == msg.sender, "Not agent owner");
        require(claimedSeverity >= 1 && claimedSeverity <= 4, "Invalid severity");
        require(
            _activeSubmissionCount[bountyId][hunterAgentId] < MAX_SUBMISSIONS_PER_HUNTER,
            "Max submissions reached"
        );

        BountyRegistry.Bounty memory bounty = bountyRegistry.getBounty(bountyId);
        require(bounty.active, "Bounty not active");
        require(block.timestamp < bounty.deadline, "Bounty expired");

        if (bounty.minHunterReputation > 0) {
            require(
                reputationRegistry.getReputation(hunterAgentId) >= bounty.minHunterReputation,
                "Insufficient reputation"
            );
        }

        uint256 stake = _calculateStake(hunterAgentId, claimedSeverity);

        _nextBugId++;
        uint256 bugId = _nextBugId;

        _submissions[bugId] = Submission({
            bountyId: bountyId,
            hunterAgentId: hunterAgentId,
            claimedSeverity: claimedSeverity,
            commitHash: commitHash,
            encryptedCID: "",
            stake: stake,
            status: Status.Committed,
            finalSeverity: 0,
            isValid: false,
            commitBlock: block.number,
            hunterWallet: msg.sender,
            revealedAt: 0,
            protocolResponse: ProtocolResponse.None
        });

        _activeSubmissionCount[bountyId][hunterAgentId]++;
        _pendingCountPerBounty[bountyId]++;
        usdc.safeTransferFrom(msg.sender, address(this), stake);
        bountyRegistry.incrementSubmissionCount(bountyId);

        emit BugCommitted(bugId, bountyId, hunterAgentId, claimedSeverity);
        return bugId;
    }

    function revealBug(uint256 bugId, string calldata encryptedCID, bytes32 salt) external {
        Submission storage sub = _submissions[bugId];
        require(sub.status == Status.Committed, "Not in commit phase");
        require(identityRegistry.ownerOf(sub.hunterAgentId) == msg.sender, "Not agent owner");
        require(block.number <= sub.commitBlock + REVEAL_WINDOW, "Reveal window expired");

        bytes32 expected = keccak256(abi.encode(encryptedCID, sub.hunterAgentId, salt));
        require(expected == sub.commitHash, "Hash mismatch");

        sub.encryptedCID = encryptedCID;
        sub.status = Status.Revealed;
        sub.revealedAt = block.timestamp;

        emit BugRevealed(bugId, encryptedCID);
    }

    function resolveSubmission(uint256 bugId, uint8 finalSeverity, bool isValid) external {
        require(msg.sender == arbiterContract, "Only ArbiterContract");
        Submission storage sub = _submissions[bugId];
        require(sub.status == Status.Revealed, "Not revealed");

        sub.status = Status.Resolved;
        sub.finalSeverity = finalSeverity;
        sub.isValid = isValid;

        _activeSubmissionCount[sub.bountyId][sub.hunterAgentId]--;
        _pendingCountPerBounty[sub.bountyId]--;

        if (isValid && finalSeverity > 0) {
            // Return stake
            usdc.safeTransfer(sub.hunterWallet, sub.stake);
            // Trigger payout from bounty escrow
            uint256 payout = bountyRegistry.getTierPayout(sub.bountyId, finalSeverity);
            bountyRegistry.deductPayout(sub.bountyId, payout, sub.hunterWallet);
        }
        // If invalid, stake stays in contract (slashed)

        emit SubmissionResolved(bugId, finalSeverity, isValid);
    }

    function resolveSubmissionTimeout(uint256 bugId) external {
        require(msg.sender == arbiterContract, "Only ArbiterContract");
        Submission storage sub = _submissions[bugId];
        require(sub.status == Status.Revealed, "Not revealed");

        sub.status = Status.Resolved;
        sub.finalSeverity = 0;
        sub.isValid = false;

        _activeSubmissionCount[sub.bountyId][sub.hunterAgentId]--;
        _pendingCountPerBounty[sub.bountyId]--;

        // Return stake (not slashed — arbiter failure, not hunter's fault)
        usdc.safeTransfer(sub.hunterWallet, sub.stake);

        emit SubmissionResolved(bugId, 0, false);
    }

    function acceptSubmission(uint256 bugId, uint8 severity) external {
        Submission storage sub = _submissions[bugId];
        require(sub.status == Status.Revealed, "Not revealed");
        require(sub.protocolResponse == ProtocolResponse.None, "Already responded");
        require(block.timestamp <= sub.revealedAt + DISPUTE_WINDOW, "Dispute window expired");
        require(severity >= 1 && severity <= sub.claimedSeverity, "Severity must be 1..claimedSeverity");

        // Only the protocol owner for this bounty can accept
        BountyRegistry.Bounty memory bounty = bountyRegistry.getBounty(sub.bountyId);
        require(identityRegistry.ownerOf(bounty.protocolAgentId) == msg.sender, "Not protocol owner");

        sub.protocolResponse = ProtocolResponse.Accepted;
        sub.status = Status.Resolved;
        sub.finalSeverity = severity;
        sub.isValid = true;

        _activeSubmissionCount[sub.bountyId][sub.hunterAgentId]--;
        _pendingCountPerBounty[sub.bountyId]--;

        // Return stake + pay at accepted severity
        usdc.safeTransfer(sub.hunterWallet, sub.stake);
        uint256 payout = bountyRegistry.getTierPayout(sub.bountyId, severity);
        bountyRegistry.deductPayout(sub.bountyId, payout, sub.hunterWallet);

        emit SubmissionAccepted(bugId, severity);
        emit SubmissionResolved(bugId, sub.claimedSeverity, true);
    }

    function disputeSubmission(uint256 bugId) external {
        Submission storage sub = _submissions[bugId];
        require(sub.status == Status.Revealed, "Not revealed");
        require(sub.protocolResponse == ProtocolResponse.None, "Already responded");
        require(block.timestamp <= sub.revealedAt + DISPUTE_WINDOW, "Dispute window expired");

        BountyRegistry.Bounty memory bounty = bountyRegistry.getBounty(sub.bountyId);
        require(identityRegistry.ownerOf(bounty.protocolAgentId) == msg.sender, "Not protocol owner");

        sub.protocolResponse = ProtocolResponse.Disputed;

        emit SubmissionDisputed(bugId);
    }

    function autoAcceptOnTimeout(uint256 bugId) external {
        Submission storage sub = _submissions[bugId];
        require(sub.status == Status.Revealed, "Not revealed");
        require(sub.protocolResponse == ProtocolResponse.None, "Already responded");
        require(block.timestamp > sub.revealedAt + DISPUTE_WINDOW, "Dispute window not expired");

        sub.protocolResponse = ProtocolResponse.Accepted;
        sub.status = Status.Resolved;
        sub.finalSeverity = sub.claimedSeverity;
        sub.isValid = true;

        _activeSubmissionCount[sub.bountyId][sub.hunterAgentId]--;
        _pendingCountPerBounty[sub.bountyId]--;

        // Return stake + pay at claimed severity
        usdc.safeTransfer(sub.hunterWallet, sub.stake);
        uint256 payout = bountyRegistry.getTierPayout(sub.bountyId, sub.claimedSeverity);
        bountyRegistry.deductPayout(sub.bountyId, payout, sub.hunterWallet);

        emit SubmissionAccepted(bugId, sub.claimedSeverity);
        emit SubmissionResolved(bugId, sub.claimedSeverity, true);
    }

    function reclaimExpiredCommit(uint256 bugId) external {
        Submission storage sub = _submissions[bugId];
        require(sub.status == Status.Committed, "Not in commit phase");
        require(block.number > sub.commitBlock + REVEAL_WINDOW, "Window not expired");

        sub.status = Status.Resolved;
        sub.isValid = false;
        _activeSubmissionCount[sub.bountyId][sub.hunterAgentId]--;
        _pendingCountPerBounty[sub.bountyId]--;

        usdc.safeTransfer(sub.hunterWallet, sub.stake);
    }

    function getPendingCount(uint256 bountyId) external view returns (uint256) {
        return _pendingCountPerBounty[bountyId];
    }

    function getSubmission(uint256 bugId) external view returns (Submission memory) {
        return _submissions[bugId];
    }

    function getSubmissionCount() external view returns (uint256) {
        return _nextBugId;
    }

    function _calculateStake(uint256 hunterAgentId, uint8 severity) internal view returns (uint256) {
        uint256 validCount = reputationRegistry.getFeedbackCount(hunterAgentId, "submission_valid");
        uint256 validityRate = reputationRegistry.getValidityRate(hunterAgentId);

        // Top-tier: 10+ valid, >80% rate
        if (validCount >= 10 && validityRate > 80) return 0;

        // Established: 3+ valid, net positive reputation
        if (validCount >= 3 && reputationRegistry.getReputation(hunterAgentId) > 0) {
            if (severity == 4) return 100e6;
            if (severity == 3) return 50e6;
            if (severity == 2) return 10e6;
            return 5e6;
        }

        // Unknown
        if (severity == 4) return 250e6;
        if (severity == 3) return 100e6;
        if (severity == 2) return 25e6;
        return 10e6;
    }
}
