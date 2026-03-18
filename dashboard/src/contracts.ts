// Contract addresses (update after deployment)
export const CONTRACT_ADDRESSES = {
  bountyRegistry: '' as string,
  bugSubmission: '' as string,
  arbiterContract: '' as string,
  identityRegistry: '' as string,
  reputationRegistry: '' as string,
}

// BountyRegistry ABI (relevant fragments)
export const BOUNTY_REGISTRY_ABI = [
  'event BountyCreated(uint256 indexed bountyId, uint256 indexed agentId, string name, uint256 maxPayout)',
  'function getBounty(uint256 bountyId) view returns (tuple(uint256 agentId, string name, string scopeCid, uint256 criticalReward, uint256 highReward, uint256 mediumReward, uint256 lowReward, uint256 totalPool, uint256 deadline, uint8 status))',
  'function bountyCount() view returns (uint256)',
]

// BugSubmission ABI (relevant fragments)
export const BUG_SUBMISSION_ABI = [
  'event BugCommitted(uint256 indexed bugId, uint256 indexed bountyId, uint256 indexed hunterAgentId)',
  'event BugRevealed(uint256 indexed bugId, string cid)',
  'event SubmissionResolved(uint256 indexed bugId, uint8 verdict, uint256 payout)',
  'event PatchGuidance(uint256 indexed bugId, string guidanceCid)',
  'function getSubmission(uint256 bugId) view returns (tuple(uint256 bountyId, uint256 hunterAgentId, bytes32 commitHash, uint256 stakeAmount, string revealedCid, bytes32 salt, uint8 severityClaim, uint8 state, uint8 verdict, uint256 payoutAmount))',
  'function submissionCount() view returns (uint256)',
]

// ArbiterContract ABI (relevant fragments)
export const ARBITER_CONTRACT_ABI = [
  'event StateImpactRegistered(uint256 indexed bugId, bytes32 reqHash, string stateDiffCid)',
  'event JurySelected(uint256 indexed bugId, uint256[] jurorIds)',
  'event VoteCommitted(uint256 indexed bugId, uint256 indexed jurorId)',
  'event VoteRevealed(uint256 indexed bugId, uint256 indexed jurorId, uint8 severity)',
  'function getJury(uint256 bugId) view returns (uint256[] memory)',
  'function getVote(uint256 bugId, uint256 jurorId) view returns (tuple(bytes32 commitHash, uint8 revealedSeverity, bool committed, bool revealed))',
  'function getStateDiff(uint256 bugId) view returns (tuple(bytes32 reqHash, string stateDiffCid, bool registered))',
]

// IdentityRegistry ABI (relevant fragments)
export const IDENTITY_REGISTRY_ABI = [
  'event AgentMinted(uint256 indexed agentId, address indexed owner, string uri)',
  'function ownerOf(uint256 tokenId) view returns (address)',
  'function tokenURI(uint256 tokenId) view returns (string)',
  'function totalSupply() view returns (uint256)',
  'function agentCount() view returns (uint256)',
]

// ReputationRegistry ABI (relevant fragments)
export const REPUTATION_REGISTRY_ABI = [
  'function getReputation(uint256 agentId) view returns (int256)',
]
