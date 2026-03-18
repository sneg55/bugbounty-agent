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

const SEVERITY_LABELS: Record<number, string> = { 0: 'None', 1: 'Low', 2: 'Medium', 3: 'High', 4: 'Critical' }
const SEVERITY_COLORS: Record<number, string> = {
  0: 'text-gray-400',
  1: 'text-blue-400',
  2: 'text-yellow-400',
  3: 'text-orange-400',
  4: 'text-red-400',
}
const STATE_LABELS: Record<number, string> = {
  0: 'Committed',
  1: 'Revealed',
  2: 'Executing',
  3: 'Arbitrating',
  4: 'Resolved',
  5: 'Rejected',
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
    <div className="p-6">
      <div className="mb-4">
        <Link to="/bounties" className="text-blue-400 hover:text-blue-300 text-sm">
          &larr; Back to Bounties
        </Link>
      </div>

      {!enabled && (
        <div className="rounded-lg border border-yellow-700 bg-yellow-900/20 p-4 text-yellow-300 text-sm mb-4">
          Contract address not configured.
        </div>
      )}

      {loadingBounty && (
        <div className="flex items-center gap-2 text-gray-400 mb-6">
          <div className="h-4 w-4 rounded-full border-2 border-gray-600 border-t-blue-400 animate-spin" />
          Loading bounty...
        </div>
      )}

      {bounty && (
        <div className="mb-8">
          <h2 className="text-2xl font-bold mb-1">{bounty.name}</h2>
          <p className="text-gray-400 text-sm mb-4">
            Protocol Agent #{bounty.agentId} &bull; Deadline:{' '}
            {new Date(bounty.deadline * 1000).toLocaleDateString()}
          </p>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
            {[
              { label: 'Critical', value: bounty.criticalReward },
              { label: 'High', value: bounty.highReward },
              { label: 'Medium', value: bounty.mediumReward },
              { label: 'Low', value: bounty.lowReward },
            ].map(({ label, value }) => (
              <div key={label} className="rounded-lg border border-gray-800 bg-gray-900 p-3">
                <p className="text-xs text-gray-400">{label}</p>
                <p className="text-lg font-bold font-mono">{value} USDC</p>
              </div>
            ))}
          </div>

          <div className="rounded-lg border border-gray-800 bg-gray-900 p-4 text-sm">
            <div className="flex justify-between mb-2">
              <span className="text-gray-400">Total Pool</span>
              <span className="font-mono font-bold">{bounty.totalPool} USDC</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Scope CID</span>
              <a
                href={`https://ipfs.io/ipfs/${bounty.scopeCid.replace('ipfs://', '')}`}
                target="_blank"
                rel="noopener noreferrer"
                className="font-mono text-blue-400 hover:text-blue-300 truncate max-w-xs"
              >
                {bounty.scopeCid}
              </a>
            </div>
          </div>
        </div>
      )}

      <h3 className="text-lg font-semibold mb-4">Submissions</h3>

      {loadingSubs && (
        <div className="flex items-center gap-2 text-gray-400">
          <div className="h-4 w-4 rounded-full border-2 border-gray-600 border-t-blue-400 animate-spin" />
          Loading submissions...
        </div>
      )}

      {submissions && submissions.length === 0 && (
        <p className="text-gray-500 text-sm">No submissions yet.</p>
      )}

      {submissions && submissions.length > 0 && (
        <div className="space-y-2">
          {submissions.map((s) => (
            <Link
              key={s.id}
              to={`/submissions/${s.id}`}
              className="block rounded-lg border border-gray-800 bg-gray-900 p-4 hover:border-gray-600 transition-colors"
            >
              <div className="flex items-center justify-between">
                <span className="font-mono text-sm text-gray-400">Bug #{s.id}</span>
                <span className={`text-xs font-medium ${SEVERITY_COLORS[s.severityClaim] ?? 'text-gray-400'}`}>
                  {SEVERITY_LABELS[s.severityClaim] ?? 'Unknown'}
                </span>
              </div>
              <div className="flex items-center justify-between mt-1">
                <span className="text-sm text-gray-400">Hunter Agent #{s.hunterAgentId}</span>
                <span className="text-xs text-gray-500">{STATE_LABELS[s.state] ?? 'Unknown'}</span>
              </div>
              {s.state >= 4 && (
                <div className="mt-1 text-xs text-green-400">
                  Payout: {s.payoutAmount} USDC
                </div>
              )}
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
