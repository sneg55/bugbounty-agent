import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import { ethers } from 'ethers'
import { getProvider } from '../config'
import { CONTRACT_ADDRESSES, BOUNTY_REGISTRY_ABI, BUG_SUBMISSION_ABI } from '../contracts'

interface BountyDetail {
  agentId: string
  name: string
  scopeCid: string
  criticalReward: string
  highReward: string
  mediumReward: string
  lowReward: string
  totalPool: string
  deadline: number
  status: number
}

interface Submission {
  id: number
  hunterAgentId: string
  severityClaim: number
  state: number
  verdict: number
  payoutAmount: string
}

const SEVERITY_LABELS: Record<number, string> = { 0: 'NONE', 1: 'LOW', 2: 'MEDIUM', 3: 'HIGH', 4: 'CRITICAL' }
const SEVERITY_COLORS: Record<number, string> = {
  0: '#6b7280',
  1: '#06b6d4',
  2: '#f59e0b',
  3: '#f97316',
  4: '#ef4444',
}
const STATE_LABELS: Record<number, string> = {
  0: 'COMMITTED',
  1: 'REVEALED',
  2: 'EXECUTING',
  3: 'ARBITRATING',
  4: 'RESOLVED',
  5: 'REJECTED',
}

async function fetchBountyDetail(bountyId: number): Promise<BountyDetail> {
  const provider = getProvider()
  const contract = new ethers.Contract(
    CONTRACT_ADDRESSES.bountyRegistry,
    BOUNTY_REGISTRY_ABI,
    provider,
  )
  const b = await contract.getBounty(bountyId)
  return {
    agentId: b.agentId.toString(),
    name: b.name,
    scopeCid: b.scopeCid,
    criticalReward: ethers.formatUnits(b.criticalReward, 6),
    highReward: ethers.formatUnits(b.highReward, 6),
    mediumReward: ethers.formatUnits(b.mediumReward, 6),
    lowReward: ethers.formatUnits(b.lowReward, 6),
    totalPool: ethers.formatUnits(b.totalPool, 6),
    deadline: Number(b.deadline),
    status: Number(b.status),
  }
}

async function fetchSubmissionsForBounty(bountyId: number): Promise<Submission[]> {
  const provider = getProvider()
  const subContract = new ethers.Contract(
    CONTRACT_ADDRESSES.bugSubmission,
    BUG_SUBMISSION_ABI,
    provider,
  )
  const count = await subContract.submissionCount()
  const total = Number(count)
  const results: Submission[] = []

  for (let i = 1; i <= total; i++) {
    const s = await subContract.getSubmission(i)
    if (Number(s.bountyId) === bountyId) {
      results.push({
        id: i,
        hunterAgentId: s.hunterAgentId.toString(),
        severityClaim: Number(s.severityClaim),
        state: Number(s.state),
        verdict: Number(s.verdict),
        payoutAmount: ethers.formatUnits(s.payoutAmount, 6),
      })
    }
  }
  return results
}

export default function BountyDetailPage() {
  const { bountyId } = useParams<{ bountyId: string }>()
  const id = Number(bountyId)

  const enabled = Boolean(CONTRACT_ADDRESSES.bountyRegistry) && !isNaN(id)

  const { data: bounty, isLoading: loadingBounty } = useQuery({
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

      {bounty && (
        <div className="mb-10">
          <h1
            className="font-extrabold uppercase text-white mb-6"
            style={{ fontSize: 'clamp(1.5rem, 3vw, 2.5rem)', letterSpacing: '-0.05em' }}
          >
            {bounty.name}
          </h1>

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
              { key: 'PROTOCOL AGENT', val: `#${bounty.agentId}` },
              { key: 'TOTAL POOL', val: `${bounty.totalPool} USDC` },
              { key: 'DEADLINE', val: new Date(bounty.deadline * 1000).toLocaleDateString() },
              { key: 'SCOPE CID', val: bounty.scopeCid, isLink: true, href: `https://ipfs.io/ipfs/${bounty.scopeCid.replace('ipfs://', '')}` },
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
            {submissions.map((s, idx) => (
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
                      style={{ borderRadius: 0, backgroundColor: SEVERITY_COLORS[s.severityClaim] ?? '#6b7280' }}
                    />
                    <span className="text-xs" style={{ color: SEVERITY_COLORS[s.severityClaim] ?? '#6b7280' }}>
                      {SEVERITY_LABELS[s.severityClaim] ?? 'UNKNOWN'}
                    </span>
                  </div>
                  <span className="text-xs text-[#6b7280]">{STATE_LABELS[s.state] ?? 'UNKNOWN'}</span>
                  {s.state >= 4 && (
                    <span className="text-xs text-[#10b981] font-extrabold">{s.payoutAmount} USDC</span>
                  )}
                </div>
                <span className="text-xs text-[#333]">{idx}</span>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
