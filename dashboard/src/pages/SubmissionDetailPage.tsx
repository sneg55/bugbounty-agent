import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import { ethers } from 'ethers'
import { getProvider } from '../config'
import { CONTRACT_ADDRESSES, BUG_SUBMISSION_ABI, ARBITER_CONTRACT_ABI } from '../contracts'

interface SubmissionData {
  bountyId: number
  hunterAgentId: string
  stakeAmount: string
  revealedCid: string
  severityClaim: number
  state: number
  verdict: number
  payoutAmount: string
}

interface StateDiff {
  reqHash: string
  stateDiffCid: string
  registered: boolean
}

interface JurorVote {
  jurorId: string
  committed: boolean
  revealed: boolean
  revealedSeverity: number
}

const SEVERITY_LABELS: Record<number, string> = { 0: 'None', 1: 'Low', 2: 'Medium', 3: 'High', 4: 'Critical' }
const SEVERITY_COLORS: Record<number, string> = {
  0: 'bg-gray-700 text-gray-300',
  1: 'bg-blue-900 text-blue-300',
  2: 'bg-yellow-900 text-yellow-300',
  3: 'bg-orange-900 text-orange-300',
  4: 'bg-red-900 text-red-300',
}

const PIPELINE_STAGES = ['Committed', 'Revealed', 'Executing', 'Arbitrating', 'Resolved']

async function fetchSubmission(bugId: number): Promise<SubmissionData> {
  const provider = getProvider()
  const contract = new ethers.Contract(
    CONTRACT_ADDRESSES.bugSubmission,
    BUG_SUBMISSION_ABI,
    provider,
  )
  const s = await contract.getSubmission(bugId)
  return {
    bountyId: Number(s.bountyId),
    hunterAgentId: s.hunterAgentId.toString(),
    stakeAmount: ethers.formatUnits(s.stakeAmount, 6),
    revealedCid: s.revealedCid,
    severityClaim: Number(s.severityClaim),
    state: Number(s.state),
    verdict: Number(s.verdict),
    payoutAmount: ethers.formatUnits(s.payoutAmount, 6),
  }
}

async function fetchStateDiff(bugId: number): Promise<StateDiff | null> {
  const provider = getProvider()
  const contract = new ethers.Contract(
    CONTRACT_ADDRESSES.arbiterContract,
    ARBITER_CONTRACT_ABI,
    provider,
  )
  try {
    const d = await contract.getStateDiff(bugId)
    return {
      reqHash: d.reqHash,
      stateDiffCid: d.stateDiffCid,
      registered: d.registered,
    }
  } catch {
    return null
  }
}

async function fetchJuryVotes(bugId: number): Promise<JurorVote[]> {
  const provider = getProvider()
  const contract = new ethers.Contract(
    CONTRACT_ADDRESSES.arbiterContract,
    ARBITER_CONTRACT_ABI,
    provider,
  )
  try {
    const jury: bigint[] = await contract.getJury(bugId)
    const votes: JurorVote[] = await Promise.all(
      jury.map(async (jurorId) => {
        const v = await contract.getVote(bugId, jurorId)
        return {
          jurorId: jurorId.toString(),
          committed: v.committed,
          revealed: v.revealed,
          revealedSeverity: Number(v.revealedSeverity),
        }
      }),
    )
    return votes
  } catch {
    return []
  }
}

function PipelineProgress({ state }: { state: number }) {
  return (
    <div className="mb-8">
      <h3 className="text-sm font-medium text-gray-400 mb-3">Pipeline Status</h3>
      <div className="flex items-center gap-0">
        {PIPELINE_STAGES.map((stage, i) => {
          const isComplete = state > i
          const isCurrent = state === i
          return (
            <div key={stage} className="flex items-center flex-1 last:flex-none">
              <div className="flex flex-col items-center">
                <div
                  className={`h-7 w-7 rounded-full border-2 flex items-center justify-center text-xs font-bold transition-colors ${
                    isComplete
                      ? 'border-green-500 bg-green-500 text-white'
                      : isCurrent
                        ? 'border-blue-400 bg-blue-400/20 text-blue-400'
                        : 'border-gray-700 bg-gray-800 text-gray-600'
                  }`}
                >
                  {isComplete ? '✓' : i + 1}
                </div>
                <span
                  className={`text-xs mt-1 whitespace-nowrap ${
                    isComplete ? 'text-green-400' : isCurrent ? 'text-blue-400' : 'text-gray-600'
                  }`}
                >
                  {stage}
                </span>
              </div>
              {i < PIPELINE_STAGES.length - 1 && (
                <div
                  className={`h-0.5 flex-1 mx-1 transition-colors ${
                    state > i ? 'bg-green-500' : 'bg-gray-700'
                  }`}
                />
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

export default function SubmissionDetailPage() {
  const { bugId } = useParams<{ bugId: string }>()
  const id = Number(bugId)

  const enabled = Boolean(CONTRACT_ADDRESSES.bugSubmission) && !isNaN(id)
  const arbiterEnabled = Boolean(CONTRACT_ADDRESSES.arbiterContract) && !isNaN(id)

  const { data: submission, isLoading } = useQuery({
    queryKey: ['submission', id],
    queryFn: () => fetchSubmission(id),
    enabled,
    refetchInterval: 15_000,
  })

  const { data: stateDiff } = useQuery({
    queryKey: ['state-diff', id],
    queryFn: () => fetchStateDiff(id),
    enabled: arbiterEnabled,
    refetchInterval: 15_000,
  })

  const { data: juryVotes } = useQuery({
    queryKey: ['jury-votes', id],
    queryFn: () => fetchJuryVotes(id),
    enabled: arbiterEnabled,
    refetchInterval: 15_000,
  })

  return (
    <div className="p-6 max-w-4xl">
      <div className="mb-4">
        {submission && (
          <Link
            to={`/bounties/${submission.bountyId}`}
            className="text-blue-400 hover:text-blue-300 text-sm"
          >
            &larr; Back to Bounty #{submission.bountyId}
          </Link>
        )}
      </div>

      <h2 className="text-2xl font-bold mb-6">Submission #{id}</h2>

      {!enabled && (
        <div className="rounded-lg border border-yellow-700 bg-yellow-900/20 p-4 text-yellow-300 text-sm mb-4">
          Contract address not configured.
        </div>
      )}

      {isLoading && (
        <div className="flex items-center gap-2 text-gray-400">
          <div className="h-4 w-4 rounded-full border-2 border-gray-600 border-t-blue-400 animate-spin" />
          Loading submission...
        </div>
      )}

      {submission && (
        <>
          <PipelineProgress state={submission.state} />

          {/* Submission metadata */}
          <div className="rounded-lg border border-gray-800 bg-gray-900 p-4 mb-6">
            <h3 className="text-sm font-medium text-gray-400 mb-3">Metadata</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-400">Hunter Agent</span>
                <span className="font-mono">#{submission.hunterAgentId}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Bounty</span>
                <span className="font-mono">#{submission.bountyId}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Stake</span>
                <span className="font-mono">{submission.stakeAmount} USDC</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Severity Claim</span>
                <span
                  className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                    SEVERITY_COLORS[submission.severityClaim] ?? 'bg-gray-700 text-gray-300'
                  }`}
                >
                  {SEVERITY_LABELS[submission.severityClaim] ?? 'Unknown'}
                </span>
              </div>
              {submission.revealedCid && (
                <div className="flex justify-between col-span-2">
                  <span className="text-gray-400">Report CID</span>
                  <a
                    href={`https://ipfs.io/ipfs/${submission.revealedCid.replace('ipfs://', '')}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="font-mono text-blue-400 hover:text-blue-300 truncate max-w-xs"
                  >
                    {submission.revealedCid}
                  </a>
                </div>
              )}
            </div>
          </div>

          {/* State diff */}
          {stateDiff && stateDiff.registered && (
            <div className="rounded-lg border border-gray-800 bg-gray-900 p-4 mb-6">
              <h3 className="text-sm font-medium text-gray-400 mb-3">State Impact</h3>
              <div className="text-sm space-y-2">
                <div className="flex justify-between">
                  <span className="text-gray-400">Request Hash</span>
                  <span className="font-mono text-xs text-gray-300 truncate max-w-xs">
                    {stateDiff.reqHash}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">State Diff CID</span>
                  <a
                    href={`https://ipfs.io/ipfs/${stateDiff.stateDiffCid.replace('ipfs://', '')}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="font-mono text-blue-400 hover:text-blue-300 truncate max-w-xs text-xs"
                  >
                    {stateDiff.stateDiffCid}
                  </a>
                </div>
                <div className="mt-3 rounded border border-green-800 bg-green-900/10 p-2 text-xs text-green-400">
                  Impact registered — arbiter can proceed
                </div>
              </div>
            </div>
          )}

          {/* Jury votes */}
          {juryVotes && juryVotes.length > 0 && (
            <div className="rounded-lg border border-gray-800 bg-gray-900 p-4 mb-6">
              <h3 className="text-sm font-medium text-gray-400 mb-3">Arbiter Votes</h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                {juryVotes.map((vote) => (
                  <div
                    key={vote.jurorId}
                    className="rounded border border-gray-700 bg-gray-800 p-3 text-sm"
                  >
                    <p className="font-mono text-gray-400 text-xs mb-2">Juror #{vote.jurorId}</p>
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span
                          className={`h-2 w-2 rounded-full ${vote.committed ? 'bg-green-400' : 'bg-gray-600'}`}
                        />
                        <span className="text-xs text-gray-300">Committed</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span
                          className={`h-2 w-2 rounded-full ${vote.revealed ? 'bg-green-400' : 'bg-gray-600'}`}
                        />
                        <span className="text-xs text-gray-300">Revealed</span>
                      </div>
                      {vote.revealed && (
                        <div className="mt-2">
                          <span
                            className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                              SEVERITY_COLORS[vote.revealedSeverity] ?? 'bg-gray-700 text-gray-300'
                            }`}
                          >
                            {SEVERITY_LABELS[vote.revealedSeverity] ?? 'Unknown'}
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Verdict */}
          {submission.state >= 4 && (
            <div
              className={`rounded-lg border p-4 ${
                submission.verdict > 0
                  ? 'border-green-800 bg-green-900/20'
                  : 'border-red-800 bg-red-900/20'
              }`}
            >
              <h3 className="text-sm font-medium text-gray-400 mb-2">Final Verdict</h3>
              <div className="flex items-center justify-between">
                <span
                  className={`text-lg font-bold ${
                    submission.verdict > 0 ? 'text-green-400' : 'text-red-400'
                  }`}
                >
                  {submission.verdict > 0
                    ? `Valid — ${SEVERITY_LABELS[submission.verdict] ?? 'Unknown'}`
                    : 'Invalid / Rejected'}
                </span>
                {submission.verdict > 0 && (
                  <span className="font-mono font-bold text-green-400 text-lg">
                    +{submission.payoutAmount} USDC
                  </span>
                )}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
