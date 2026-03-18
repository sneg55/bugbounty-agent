import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import { ethers } from 'ethers'
import { getProvider } from '../config'
import { CONTRACT_ADDRESSES, BUG_SUBMISSION_ABI, ARBITER_CONTRACT_ABI } from '../contracts'

interface SubmissionData {
  bountyId: number
  hunterAgentId: string
  stake: string
  encryptedCID: string
  claimedSeverity: number
  status: number
  finalSeverity: number
  isValid: boolean
}

interface ArbitrationData {
  stateImpactCID: string
  validationRequestHash: string
  jurors: string[]
  revealedSeverities: number[]
  revealed: boolean[]
  revealCount: number
  phase: number
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
    stake: ethers.formatUnits(s.stake, 6),
    encryptedCID: s.encryptedCID,
    claimedSeverity: Number(s.claimedSeverity),
    status: Number(s.status),
    finalSeverity: Number(s.finalSeverity),
    isValid: s.isValid,
  }
}

async function fetchArbitration(bugId: number): Promise<ArbitrationData | null> {
  const provider = getProvider()
  const contract = new ethers.Contract(
    CONTRACT_ADDRESSES.arbiterContract,
    ARBITER_CONTRACT_ABI,
    provider,
  )
  try {
    const a = await contract.getArbitration(bugId)
    return {
      stateImpactCID: a.stateImpactCID,
      validationRequestHash: ethers.hexlify(a.validationRequestHash),
      jurors: (a.jurors as bigint[]).map((j) => j.toString()),
      revealedSeverities: (a.revealedSeverities as bigint[]).map((v) => Number(v)),
      revealed: Array.from(a.revealed as boolean[]),
      revealCount: Number(a.revealCount),
      phase: Number(a.phase),
    }
  } catch {
    return null
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

  const { data: arbitration } = useQuery({
    queryKey: ['arbitration', id],
    queryFn: () => fetchArbitration(id),
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
          <PipelineProgress state={submission.status} />

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
                <span className="font-mono">{submission.stake} USDC</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Severity Claim</span>
                <span
                  className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                    SEVERITY_COLORS[submission.claimedSeverity] ?? 'bg-gray-700 text-gray-300'
                  }`}
                >
                  {SEVERITY_LABELS[submission.claimedSeverity] ?? 'Unknown'}
                </span>
              </div>
              {submission.encryptedCID && (
                <div className="flex justify-between col-span-2">
                  <span className="text-gray-400">Report CID</span>
                  <a
                    href={`https://ipfs.io/ipfs/${submission.encryptedCID.replace('ipfs://', '')}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="font-mono text-blue-400 hover:text-blue-300 truncate max-w-xs"
                  >
                    {submission.encryptedCID}
                  </a>
                </div>
              )}
            </div>
          </div>

          {/* Arbitration: state impact and jury votes */}
          {arbitration && arbitration.stateImpactCID && (
            <div className="rounded-lg border border-gray-800 bg-gray-900 p-4 mb-6">
              <h3 className="text-sm font-medium text-gray-400 mb-3">State Impact</h3>
              <div className="text-sm space-y-2">
                <div className="flex justify-between">
                  <span className="text-gray-400">Validation Request Hash</span>
                  <span className="font-mono text-xs text-gray-300 truncate max-w-xs">
                    {arbitration.validationRequestHash}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">State Impact CID</span>
                  <a
                    href={`https://ipfs.io/ipfs/${arbitration.stateImpactCID.replace('ipfs://', '')}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="font-mono text-blue-400 hover:text-blue-300 truncate max-w-xs text-xs"
                  >
                    {arbitration.stateImpactCID}
                  </a>
                </div>
                <div className="mt-3 rounded border border-green-800 bg-green-900/10 p-2 text-xs text-green-400">
                  Impact registered — arbiter can proceed
                </div>
              </div>
            </div>
          )}

          {/* Jury votes */}
          {arbitration && arbitration.jurors.some((j) => j !== '0') && (
            <div className="rounded-lg border border-gray-800 bg-gray-900 p-4 mb-6">
              <h3 className="text-sm font-medium text-gray-400 mb-3">
                Arbiter Votes ({arbitration.revealCount} / {arbitration.jurors.length} revealed)
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                {arbitration.jurors.map((jurorId, idx) => (
                  <div
                    key={jurorId + idx}
                    className="rounded border border-gray-700 bg-gray-800 p-3 text-sm"
                  >
                    <p className="font-mono text-gray-400 text-xs mb-2">Juror #{jurorId}</p>
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span
                          className={`h-2 w-2 rounded-full ${arbitration.revealed[idx] ? 'bg-green-400' : 'bg-gray-600'}`}
                        />
                        <span className="text-xs text-gray-300">Revealed</span>
                      </div>
                      {arbitration.revealed[idx] && (
                        <div className="mt-2">
                          <span
                            className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                              SEVERITY_COLORS[arbitration.revealedSeverities[idx]] ?? 'bg-gray-700 text-gray-300'
                            }`}
                          >
                            {SEVERITY_LABELS[arbitration.revealedSeverities[idx]] ?? 'Unknown'}
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
          {submission.status >= 2 && (
            <div
              className={`rounded-lg border p-4 ${
                submission.isValid
                  ? 'border-green-800 bg-green-900/20'
                  : 'border-red-800 bg-red-900/20'
              }`}
            >
              <h3 className="text-sm font-medium text-gray-400 mb-2">Final Verdict</h3>
              <div className="flex items-center justify-between">
                <span
                  className={`text-lg font-bold ${
                    submission.isValid ? 'text-green-400' : 'text-red-400'
                  }`}
                >
                  {submission.isValid
                    ? `Valid — ${SEVERITY_LABELS[submission.finalSeverity] ?? 'Unknown'}`
                    : 'Invalid / Rejected'}
                </span>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
