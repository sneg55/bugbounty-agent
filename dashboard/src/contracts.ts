// Contract addresses on Base Sepolia (deployed 2026-03-20)
export const CONTRACT_ADDRESSES = {
  bountyRegistry: '0xb8926B097FB26883b550aDdC191b4F75F24Ea4Aa',
  bugSubmission: '0x919c1Da141Cb1456Aa150292c562f7A969234C20',
  arbiterContract: '0x28e83212a1D98c2172c716B58aFF54029f34b413',
  identityRegistry: '0x5d438B26aa2FeE1874499ff4705aF72bc6107D44',
  reputationRegistry: '0x2606f45324cA04Aa3C2153cD2d5E00abd719E6ae',
  validationRegistry: '0x31eCCF46166AFD87c917Cc45A864551B5298F98a',
  mockUSDC: '0x003e27d8A04f7bC450D8ac03b72c7318f6204b1C',
}

// BountyRegistry ABI (relevant fragments)
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
export const BUG_SUBMISSION_ABI = [
  'event BugCommitted(uint256 indexed bugId, uint256 indexed bountyId, uint256 indexed hunterAgentId, uint8 claimedSeverity)',
  'event BugRevealed(uint256 indexed bugId, string encryptedCID)',
  'event SubmissionResolved(uint256 indexed bugId, uint8 finalSeverity, bool isValid)',
  'function getSubmission(uint256 bugId) view returns (tuple(uint256 bountyId, uint256 hunterAgentId, uint8 claimedSeverity, bytes32 commitHash, string encryptedCID, uint256 stake, uint8 status, uint8 finalSeverity, bool isValid, uint256 commitBlock, address hunterWallet))',
  'function getSubmissionCount() view returns (uint256)',
]

// ArbiterContract ABI (relevant fragments)
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
