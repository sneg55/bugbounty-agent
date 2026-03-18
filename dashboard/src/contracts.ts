// Contract addresses (populated at runtime from deployments.json)
export const CONTRACT_ADDRESSES = {
  bountyRegistry: '' as string,
  bugSubmission: '' as string,
  arbiterContract: '' as string,
  identityRegistry: '' as string,
  reputationRegistry: '' as string,
}

// BountyRegistry ABI (relevant fragments)
// Struct: Bounty { protocolAgentId, name, scopeURI, tiers: { critical, high, medium, low },
//                  totalFunding, totalPaid, deadline, minHunterReputation, active, submissionCount }
export const BOUNTY_REGISTRY_ABI = [
  'event BountyCreated(uint256 indexed bountyId, uint256 indexed protocolAgentId, string name, uint256 totalFunding, uint256 deadline)',
  'event PayoutDeducted(uint256 indexed bountyId, address indexed recipient, uint256 amount)',
  'event RemainderWithdrawn(uint256 indexed bountyId, uint256 amount)',
  'function getBountyCount() view returns (uint256)',
  'function getBounty(uint256 bountyId) view returns (tuple(uint256 protocolAgentId, string name, string scopeURI, tuple(uint256 critical, uint256 high, uint256 medium, uint256 low) tiers, uint256 totalFunding, uint256 totalPaid, uint256 deadline, int256 minHunterReputation, bool active, uint256 submissionCount))',
  'function getTierPayout(uint256 bountyId, uint8 severity) view returns (uint256)',
  'function getRemainingFunds(uint256 bountyId) view returns (uint256)',
]

// BugSubmission ABI (relevant fragments)
// Enum: Status { Committed, Revealed, Resolved }
// Struct: Submission { bountyId, hunterAgentId, claimedSeverity, commitHash, encryptedCID,
//                      stake, status, finalSeverity, isValid, commitBlock, hunterWallet }
export const BUG_SUBMISSION_ABI = [
  'event BugCommitted(uint256 indexed bugId, uint256 indexed bountyId, uint256 indexed hunterAgentId, uint8 claimedSeverity)',
  'event BugRevealed(uint256 indexed bugId, string encryptedCID)',
  'event SubmissionResolved(uint256 indexed bugId, uint8 finalSeverity, bool isValid)',
  'function getSubmission(uint256 bugId) view returns (tuple(uint256 bountyId, uint256 hunterAgentId, uint8 claimedSeverity, bytes32 commitHash, string encryptedCID, uint256 stake, uint8 status, uint8 finalSeverity, bool isValid, uint256 commitBlock, address hunterWallet))',
  'function getSubmissionCount() view returns (uint256)',
]

// ArbiterContract ABI (relevant fragments)
// Enum: Phase { AwaitingStateImpact, Voting, Revealing, Resolved }
// Struct: Arbitration { bugId, stateImpactCID, validationRequestHash, jurors[3],
//                       commitHashes[3], revealedSeverities[3], revealed[3],
//                       revealCount, commitDeadlineBlock, revealDeadlineBlock, phase }
export const ARBITER_CONTRACT_ABI = [
  'event ArbiterRegistered(uint256 indexed arbiterAgentId)',
  'event ArbiterUnregistered(uint256 indexed arbiterAgentId)',
  'event StateImpactRegistered(uint256 indexed bugId, string stateImpactCID)',
  'event JurySelected(uint256 indexed bugId, uint256[3] jurors)',
  'event VoteCommitted(uint256 indexed bugId, uint256 indexed arbiterAgentId)',
  'event VoteRevealed(uint256 indexed bugId, uint256 indexed arbiterAgentId, uint8 severity)',
  'event SubmissionResolved(uint256 indexed bugId, uint8 finalSeverity, bool isValid)',
  'event PatchGuidance(uint256 indexed bugId, string encryptedPatchCID)',
  'function getArbitration(uint256 bugId) view returns (tuple(uint256 bugId, string stateImpactCID, bytes32 validationRequestHash, uint256[3] jurors, bytes32[3] commitHashes, uint8[3] revealedSeverities, bool[3] revealed, uint256 revealCount, uint256 commitDeadlineBlock, uint256 revealDeadlineBlock, uint8 phase))',
  'function getArbiterPoolSize() view returns (uint256)',
]

// IdentityRegistry ABI (relevant fragments)
export const IDENTITY_REGISTRY_ABI = [
  'event AgentMinted(uint256 indexed agentId, address indexed owner, string registrationURI)',
  'event MetadataUpdated(uint256 indexed agentId, string key)',
  'function totalAgents() view returns (uint256)',
  'function ownerOf(uint256 tokenId) view returns (address)',
  'function getMetadata(uint256 agentId, string key) view returns (bytes)',
  'function isActive(uint256 agentId) view returns (bool)',
  'function tokenURI(uint256 tokenId) view returns (string)',
]

// ReputationRegistry ABI (relevant fragments)
export const REPUTATION_REGISTRY_ABI = [
  'event FeedbackGiven(uint256 indexed targetAgentId, int256 value, string tag1, string tag2)',
  'function getReputation(uint256 agentId) view returns (int256)',
  'function getFeedbackCount(uint256 agentId, string tag1) view returns (uint256)',
  'function getValidityRate(uint256 agentId) view returns (uint256)',
]
