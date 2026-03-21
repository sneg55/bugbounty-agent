import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import { ethers } from 'ethers'
import { getProvider } from '../config'
import { CONTRACT_ADDRESSES, BOUNTY_REGISTRY_ABI, BUG_SUBMISSION_ABI } from '../contracts'

interface BountyDetail {
  protocolAgentId: string
  name: string
  scopeURI: string
  criticalReward: string
  highReward: string
  mediumReward: string
  lowReward: string
  totalFunding: string
  totalPaid: string
  deadline: number
  minHunterReputation: string
  active: boolean
  submissionCount: number
}

interface Submission {
  id: number
  hunterAgentId: string
  claimedSeverity: number
  status: number
  finalSeverity: number
  isValid: boolean
}

const SEVERITY_LABELS: Record<number, string> = { 0: 'NONE', 1: 'LOW', 2: 'MEDIUM', 3: 'HIGH', 4: 'CRITICAL' }
const SEVERITY_COLORS: Record<number, string> = {
  0: '#6b7280',
  1: '#06b6d4',
  2: '#f59e0b',
  3: '#f97316',
  4: '#ef4444',
}
const STATUS_LABELS: Record<number, string> = {
  0: 'COMMITTED',
  1: 'REVEALED',
  2: 'RESOLVED',
}

async function fetchBountyDetail(bountyId: number): Promise<BountyDetail> {
  const provider = getProvider()
  const contract = new ethers.Contract(
    CONTRACT_ADDRESSES.bountyRegistry,
    BOUNTY_REGISTRY_ABI,
    provider,
  )
  const b = await contract.getBounty(bountyId)
  // Bounty struct: protocolAgentId, name, scopeURI, tiers(critical,high,medium,low), totalFunding, totalPaid, deadline, minHunterReputation, active, submissionCount
  return {
    protocolAgentId: b[0].toString(),
    name: b[1],
    scopeURI: b[2],
    criticalReward: ethers.formatUnits(b[3][0], 6),
    highReward: ethers.formatUnits(b[3][1], 6),
    mediumReward: ethers.formatUnits(b[3][2], 6),
    lowReward: ethers.formatUnits(b[3][3], 6),
    totalFunding: ethers.formatUnits(b[4], 6),
    totalPaid: ethers.formatUnits(b[5], 6),
    deadline: Number(b[6]),
    minHunterReputation: b[7].toString(),
    active: b[8],
    submissionCount: Number(b[9]),
  }
}

async function fetchSubmissionsForBounty(bountyId: number): Promise<Submission[]> {
  const provider = getProvider()
  const subContract = new ethers.Contract(
    CONTRACT_ADDRESSES.bugSubmission,
    BUG_SUBMISSION_ABI,
    provider,
  )
  const count = await subContract.getSubmissionCount()
  const total = Number(count)
  const results: Submission[] = []

  for (let i = 1; i <= total; i++) {
    const s = await subContract.getSubmission(i)
    // Submission struct: bountyId, hunterAgentId, claimedSeverity, commitHash, encryptedCID, stake, status, finalSeverity, isValid, commitBlock, hunterWallet
    if (Number(s[0]) === bountyId) {
      results.push({
        id: i,
        hunterAgentId: s[1].toString(),
        claimedSeverity: Number(s[2]),
        status: Number(s[6]),
        finalSeverity: Number(s[7]),
        isValid: s[8],
      })
    }
  }
  return results
}

export default function BountyDetailPage() {
  const { bountyId } = useParams<{ bountyId: string }>()
  const id = Number(bountyId)

  const enabled = Boolean(CONTRACT_ADDRESSES.bountyRegistry) && !isNaN(id)

  const { data: bounty, isLoading: loadingBounty, error: bountyError } = useQuery({
    queryKey: ['bounty', id],
    queryFn: () => fetchBountyDetail(id),
    enabled,
  })

  const { data: submissions, isLoading: loadingSubs } = useQuery({
    queryKey: ['bounty-submissions', id],
    queryFn: () => fetchSubmissionsForBounty(id),
    enabled: enabled && Boolean(CONTRACT_ADDRESSES.bugSubmission),
    refetchInterval: 15_000,
  })

  return (
    <div className="max-w-6xl mx-auto px-6 py-8">
      <div className="mb-6">
        <Link to="/bounties" className="text-xs text-[#06b6d4] hover:text-white transition-colors duration-150 uppercase tracking-tight">
          &larr; BACK TO BOUNTIES
        </Link>
      </div>

      {!enabled && (
        <div className="border border-[#f59e0b] p-4 text-[#f59e0b] text-xs mb-6" style={{ borderRadius: 0 }}>
          CONTRACT ADDRESS NOT CONFIGURED.
        </div>
      )}

      {loadingBounty && (
        <div className="flex items-center gap-2 text-[#6b7280] text-xs mb-6">
          <span className="inline-block w-2 h-2 bg-[#10b981] animate-pulse" style={{ borderRadius: 0 }} />
          LOADING BOUNTY...
        </div>
      )}

      {bountyError && (
        <div className="border border-[#ef4444] p-4 text-[#ef4444] text-xs mb-6" style={{ borderRadius: 0 }}>
          FAILED TO LOAD BOUNTY: {String(bountyError)}
        </div>
      )}

      {bounty && (
        <div className="mb-10">
          <div className="flex items-center gap-4 mb-6">
            <h1
              className="font-extrabold uppercase text-white"
              style={{ fontSize: 'clamp(1.5rem, 3vw, 2.5rem)', letterSpacing: '-0.05em' }}
            >
              {bounty.name}
            </h1>
            <span
              className={`text-xs font-extrabold px-2 py-1 ${bounty.active ? 'text-[#10b981] border border-[#10b981]' : 'text-[#6b7280] border border-[#6b7280]'}`}
              style={{ borderRadius: 0 }}
            >
              {bounty.active ? 'ACTIVE' : 'CLOSED'}
            </span>
          </div>

          {/* Reward tiers */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-px bg-[#333] mb-8">
            {[
              { label: 'CRITICAL', value: bounty.criticalReward, color: '#ef4444' },
              { label: 'HIGH', value: bounty.highReward, color: '#f97316' },
              { label: 'MEDIUM', value: bounty.mediumReward, color: '#f59e0b' },
              { label: 'LOW', value: bounty.lowReward, color: '#06b6d4' },
            ].map(({ label, value, color }) => (
              <div key={label} className="bg-black p-4" style={{ borderRadius: 0 }}>
                <p className="text-xs uppercase tracking-tight mb-2" style={{ color }}>{label}</p>
                <p className="text-xl font-extrabold text-white">{value}</p>
                <p className="text-xs text-[#6b7280] mt-0.5">USDC</p>
              </div>
            ))}
          </div>

          {/* Metadata key-value grid */}
          <div className="border border-[#333]" style={{ borderRadius: 0 }}>
            <div className="border-b border-[#333] px-4 py-2">
              <span className="text-xs font-extrabold uppercase tracking-tight text-[#6b7280]">METADATA</span>
            </div>
            {[
              { key: 'PROTOCOL AGENT', val: `#${bounty.protocolAgentId}` },
              { key: 'TOTAL FUNDING', val: `${bounty.totalFunding} USDC` },
              { key: 'TOTAL PAID', val: `${bounty.totalPaid} USDC` },
              { key: 'DEADLINE', val: new Date(bounty.deadline * 1000).toLocaleDateString() },
              { key: 'MIN HUNTER REP', val: bounty.minHunterReputation },
              { key: 'SUBMISSIONS', val: bounty.submissionCount.toString() },
              { key: 'SCOPE URI', val: bounty.scopeURI, isLink: bounty.scopeURI.startsWith('ipfs://'), href: `https://ipfs.io/ipfs/${bounty.scopeURI.replace('ipfs://', '')}` },
            ].map(({ key, val, isLink, href }) => (
              <div key={key} className="flex justify-between items-start px-4 py-3 border-b border-dotted border-[#333] last:border-b-0">
                <span className="text-xs text-[#6b7280] uppercase tracking-tight">{key}</span>
                {isLink && href ? (
                  <a
                    href={href}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs text-[#06b6d4] hover:text-white transition-colors duration-150 truncate max-w-xs"
                  >
                    {val}
                  </a>
                ) : (
                  <span className="text-xs text-white font-extrabold">{val}</span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Submissions */}
      <div>
        <div className="mb-4">
          <span
            className="text-sm font-extrabold uppercase text-white"
            style={{ letterSpacing: '-0.05em' }}
          >
            SUBMISSIONS
          </span>
        </div>

        {loadingSubs && (
          <div className="flex items-center gap-2 text-[#6b7280] text-xs">
            <span className="inline-block w-2 h-2 bg-[#10b981] animate-pulse" style={{ borderRadius: 0 }} />
            LOADING SUBMISSIONS...
          </div>
        )}

        {submissions && submissions.length === 0 && (
          <p className="text-[#6b7280] text-xs uppercase tracking-tight py-8 text-center">
            NO SUBMISSIONS YET
          </p>
        )}

        {submissions && submissions.length > 0 && (
          <div className="border border-[#333]" style={{ borderRadius: 0 }}>
            {submissions.map((s) => (
              <Link
                key={s.id}
                to={`/submissions/${s.id}`}
                className="flex items-center justify-between px-4 py-3 border-b border-[#333] last:border-b-0 hover:border-l-2 hover:border-l-[#06b6d4] transition-all duration-150 block"
              >
                <div className="flex items-center gap-4">
                  <span className="text-xs text-[#6b7280]">BUG #{s.id}</span>
                  <span className="text-xs text-[#6b7280]">HUNTER #{s.hunterAgentId}</span>
                </div>
                <div className="flex items-center gap-4">
                  <div className="flex items-center gap-1.5">
                    <span
                      className="inline-block w-2 h-2"
                      style={{ borderRadius: 0, backgroundColor: SEVERITY_COLORS[s.claimedSeverity] ?? '#6b7280' }}
                    />
                    <span className="text-xs" style={{ color: SEVERITY_COLORS[s.claimedSeverity] ?? '#6b7280' }}>
                      {SEVERITY_LABELS[s.claimedSeverity] ?? 'UNKNOWN'}
                    </span>
                  </div>
                  <span className="text-xs text-[#6b7280]">{STATUS_LABELS[s.status] ?? 'UNKNOWN'}</span>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
