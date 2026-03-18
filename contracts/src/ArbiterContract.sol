// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "./erc8004/IdentityRegistry.sol";
import "./erc8004/ReputationRegistry.sol";
import "./erc8004/ValidationRegistry.sol";
import "./BugSubmission.sol";

contract ArbiterContract {
    enum Phase { AwaitingStateImpact, Voting, Revealing, Resolved }

    struct Arbitration {
        uint256 bugId;
        string stateImpactCID;
        bytes32 validationRequestHash;
        uint256[3] jurors;
        bytes32[3] commitHashes;
        uint8[3] revealedSeverities;
        bool[3] revealed;
        uint256 revealCount;
        uint256 commitDeadlineBlock;
        uint256 revealDeadlineBlock;
        Phase phase;
    }

    uint256 public constant COMMIT_WINDOW = 50;
    uint256 public constant REVEAL_WINDOW = 50;

    IdentityRegistry public immutable identityRegistry;
    ReputationRegistry public immutable reputationRegistry;
    ValidationRegistry public immutable validationRegistry;
    BugSubmission public immutable bugSubmission;
    address public executor;

    uint256[] public arbiterPool;
    mapping(uint256 => bool) public isInPool;
    mapping(uint256 => Arbitration) private _arbitrations;

    event ArbiterRegistered(uint256 indexed arbiterAgentId);
    event ArbiterUnregistered(uint256 indexed arbiterAgentId);
    event StateImpactRegistered(uint256 indexed bugId, string stateImpactCID);
    event JurySelected(uint256 indexed bugId, uint256[3] jurors);
    event VoteCommitted(uint256 indexed bugId, uint256 indexed arbiterAgentId);
    event VoteRevealed(uint256 indexed bugId, uint256 indexed arbiterAgentId, uint8 severity);
    event SubmissionResolved(uint256 indexed bugId, uint8 finalSeverity, bool isValid);
    event PatchGuidance(uint256 indexed bugId, string encryptedPatchCID);

    address public immutable deployer;

    constructor(address _identity, address _reputation, address _validation, address _bugSubmission) {
        identityRegistry = IdentityRegistry(_identity);
        reputationRegistry = ReputationRegistry(_reputation);
        validationRegistry = ValidationRegistry(_validation);
        bugSubmission = BugSubmission(_bugSubmission);
        deployer = msg.sender;
    }

    function setExecutor(address _executor) external {
        require(msg.sender == deployer, "Only deployer");
        require(executor == address(0), "Already set");
        executor = _executor;
    }

    function registerArbiter(uint256 arbiterAgentId) external {
        require(identityRegistry.isActive(arbiterAgentId), "Invalid agent");
        require(identityRegistry.ownerOf(arbiterAgentId) == msg.sender, "Not agent owner");
        require(!isInPool[arbiterAgentId], "Already registered");

        arbiterPool.push(arbiterAgentId);
        isInPool[arbiterAgentId] = true;
        emit ArbiterRegistered(arbiterAgentId);
    }

    function unregisterArbiter(uint256 arbiterAgentId) external {
        require(identityRegistry.ownerOf(arbiterAgentId) == msg.sender, "Not agent owner");
        require(isInPool[arbiterAgentId], "Not in pool");

        isInPool[arbiterAgentId] = false;
        // Remove from array
        for (uint256 i = 0; i < arbiterPool.length; i++) {
            if (arbiterPool[i] == arbiterAgentId) {
                arbiterPool[i] = arbiterPool[arbiterPool.length - 1];
                arbiterPool.pop();
                break;
            }
        }
        emit ArbiterUnregistered(arbiterAgentId);
    }

    function registerStateImpact(uint256 bugId, bytes32 requestHash, string calldata stateImpactCID) external {
        require(msg.sender == executor, "Only executor");
        require(validationRegistry.getValidationStatus(requestHash), "Not validated");

        Arbitration storage a = _arbitrations[bugId];
        require(a.phase == Phase.AwaitingStateImpact || a.bugId == 0, "Wrong phase");

        a.bugId = bugId;
        a.stateImpactCID = stateImpactCID;
        a.validationRequestHash = requestHash;
        a.phase = Phase.Voting;

        _selectJury(bugId);

        a.commitDeadlineBlock = block.number + COMMIT_WINDOW;
        a.revealDeadlineBlock = block.number + COMMIT_WINDOW + REVEAL_WINDOW;

        emit StateImpactRegistered(bugId, stateImpactCID);
    }

    function _selectJury(uint256 bugId) internal {
        Arbitration storage a = _arbitrations[bugId];
        BugSubmission.Submission memory sub = bugSubmission.getSubmission(bugId);

        address hunterOwner = identityRegistry.ownerOf(sub.hunterAgentId);
        BountyRegistry bounty = bugSubmission.bountyRegistry();
        BountyRegistry.Bounty memory b = bounty.getBounty(sub.bountyId);
        address protocolOwner = identityRegistry.ownerOf(b.protocolAgentId);

        // Collect eligible arbiters into memory arrays
        uint256 poolLen = arbiterPool.length;
        uint256[] memory eligibleIds = new uint256[](poolLen);
        uint256[] memory eligibleScores = new uint256[](poolLen);
        uint256 eligibleCount = 0;

        for (uint256 i = 0; i < poolLen; i++) {
            uint256 candidateId = arbiterPool[i];
            address candidateOwner = identityRegistry.ownerOf(candidateId);

            // Exclude conflicts
            if (candidateOwner == hunterOwner || candidateOwner == protocolOwner) continue;

            uint256 score = reputationRegistry.getFeedbackCount(candidateId, "consensus_aligned");
            eligibleIds[eligibleCount] = candidateId;
            eligibleScores[eligibleCount] = score;
            eligibleCount++;
        }

        require(eligibleCount >= 3, "Not enough eligible arbiters");

        // Select top 3 by score (3 passes: find max, mark selected, repeat)
        bool[] memory picked = new bool[](eligibleCount);
        for (uint256 pick = 0; pick < 3; pick++) {
            uint256 bestIdx = type(uint256).max;
            uint256 bestScore = 0;
            for (uint256 j = 0; j < eligibleCount; j++) {
                if (picked[j]) continue;
                if (bestIdx == type(uint256).max || eligibleScores[j] > bestScore) {
                    bestIdx = j;
                    bestScore = eligibleScores[j];
                }
            }
            picked[bestIdx] = true;
            a.jurors[pick] = eligibleIds[bestIdx];
        }

        emit JurySelected(bugId, a.jurors);
    }

    function commitVote(uint256 bugId, bytes32 voteHash) external {
        Arbitration storage a = _arbitrations[bugId];
        require(a.phase == Phase.Voting, "Not in voting phase");
        require(block.number <= a.commitDeadlineBlock, "Commit window expired");

        uint256 jurorIdx = _getJurorIndex(bugId, msg.sender);
        require(a.commitHashes[jurorIdx] == bytes32(0), "Already committed");

        a.commitHashes[jurorIdx] = voteHash;
        uint256 arbiterAgentId = a.jurors[jurorIdx];
        emit VoteCommitted(bugId, arbiterAgentId);

        // Check if all committed, advance to reveal phase
        if (a.commitHashes[0] != bytes32(0) && a.commitHashes[1] != bytes32(0) && a.commitHashes[2] != bytes32(0)) {
            a.phase = Phase.Revealing;
        }
    }

    function revealVote(uint256 bugId, uint8 severity, bytes32 salt) external {
        Arbitration storage a = _arbitrations[bugId];
        require(a.phase == Phase.Revealing || a.phase == Phase.Voting, "Not in reveal phase");
        require(block.number <= a.revealDeadlineBlock, "Reveal window expired");
        require(severity <= 4, "Invalid severity");

        uint256 jurorIdx = _getJurorIndex(bugId, msg.sender);
        require(!a.revealed[jurorIdx], "Already revealed");
        require(keccak256(abi.encode(severity, salt)) == a.commitHashes[jurorIdx], "Hash mismatch");

        a.revealed[jurorIdx] = true;
        a.revealedSeverities[jurorIdx] = severity;
        a.revealCount++;

        uint256 arbiterAgentId = a.jurors[jurorIdx];
        emit VoteRevealed(bugId, arbiterAgentId, severity);

        if (a.revealCount == 3) {
            _resolve(bugId);
        }
    }

    function resolveWithTimeout(uint256 bugId) external {
        Arbitration storage a = _arbitrations[bugId];
        require(block.number > a.revealDeadlineBlock, "Window not expired");
        require(a.phase != Phase.Resolved, "Already resolved");

        if (a.revealCount < 2) {
            // Insufficient quorum: return stake (not slashed — arbiter failure)
            bugSubmission.resolveSubmissionTimeout(bugId);
            _penalizeNoShows(bugId);
            a.phase = Phase.Resolved;
            emit SubmissionResolved(bugId, 0, false);
        } else {
            _resolve(bugId);
        }
    }

    function _resolve(uint256 bugId) internal {
        Arbitration storage a = _arbitrations[bugId];
        a.phase = Phase.Resolved;

        // Collect revealed severities
        uint8[3] memory sevs;
        uint256 count = 0;
        for (uint256 i = 0; i < 3; i++) {
            if (a.revealed[i]) {
                sevs[count] = a.revealedSeverities[i];
                count++;
            }
        }

        uint8 finalSeverity;
        bool isValid;

        if (count == 2) {
            // Conservative: min of two
            finalSeverity = sevs[0] < sevs[1] ? sevs[0] : sevs[1];
            isValid = finalSeverity > 0;
        } else {
            // Sort 3 values for median
            if (sevs[0] > sevs[1]) (sevs[0], sevs[1]) = (sevs[1], sevs[0]);
            if (sevs[1] > sevs[2]) (sevs[1], sevs[2]) = (sevs[2], sevs[1]);
            if (sevs[0] > sevs[1]) (sevs[0], sevs[1]) = (sevs[1], sevs[0]);
            finalSeverity = sevs[1]; // median

            // Majority invalid check
            uint256 invalidCount = 0;
            for (uint256 i = 0; i < 3; i++) {
                if (a.revealed[i] && a.revealedSeverities[i] == 0) invalidCount++;
            }
            isValid = invalidCount < 2 && finalSeverity > 0;
            if (!isValid) finalSeverity = 0;
        }

        bugSubmission.resolveSubmission(bugId, finalSeverity, isValid);

        // Post reputation feedback
        _postFeedback(bugId, finalSeverity, isValid);
        _penalizeNoShows(bugId);

        emit SubmissionResolved(bugId, finalSeverity, isValid);
    }

    function _postFeedback(uint256 bugId, uint8 finalSeverity, bool isValid) internal {
        Arbitration storage a = _arbitrations[bugId];
        BugSubmission.Submission memory sub = bugSubmission.getSubmission(bugId);

        // Hunter feedback
        if (isValid) {
            reputationRegistry.giveFeedback(sub.hunterAgentId, 100, "submission_valid", _severityString(finalSeverity));
        } else {
            reputationRegistry.giveFeedback(sub.hunterAgentId, -100, "submission_invalid", _severityString(sub.claimedSeverity));
        }

        // Arbiter feedback
        for (uint256 i = 0; i < 3; i++) {
            if (!a.revealed[i]) continue;
            if (a.revealedSeverities[i] == finalSeverity) {
                reputationRegistry.giveFeedback(a.jurors[i], 10, "consensus_aligned", _severityString(finalSeverity));
            } else {
                reputationRegistry.giveFeedback(a.jurors[i], -5, "consensus_deviated", _severityString(a.revealedSeverities[i]));
            }
        }
    }

    function _penalizeNoShows(uint256 bugId) internal {
        Arbitration storage a = _arbitrations[bugId];
        for (uint256 i = 0; i < 3; i++) {
            if (a.jurors[i] != 0 && !a.revealed[i]) {
                reputationRegistry.giveFeedback(a.jurors[i], -20, "vote_timeout", "");
            }
        }
    }

    function _severityString(uint8 severity) internal pure returns (string memory) {
        if (severity == 4) return "CRITICAL";
        if (severity == 3) return "HIGH";
        if (severity == 2) return "MEDIUM";
        if (severity == 1) return "LOW";
        return "INVALID";
    }

    function registerPatchGuidance(uint256 bugId, string calldata encryptedPatchCID) external {
        require(msg.sender == executor, "Only executor");
        BugSubmission.Submission memory sub = bugSubmission.getSubmission(bugId);
        require(sub.isValid && sub.finalSeverity >= 3, "Not eligible for patch guidance");
        emit PatchGuidance(bugId, encryptedPatchCID);
    }

    function getArbitration(uint256 bugId) external view returns (Arbitration memory) {
        return _arbitrations[bugId];
    }

    function getArbiterPoolSize() external view returns (uint256) {
        return arbiterPool.length;
    }

    function _getJurorIndex(uint256 bugId, address caller) internal view returns (uint256) {
        Arbitration storage a = _arbitrations[bugId];
        for (uint256 i = 0; i < 3; i++) {
            if (identityRegistry.ownerOf(a.jurors[i]) == caller) return i;
        }
        revert("Not a juror");
    }
}
