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

const SEVERITY_LABELS: Record<number, string> = { 0: 'NONE', 1: 'LOW', 2: 'MEDIUM', 3: 'HIGH', 4: 'CRITICAL' }
const SEVERITY_COLORS: Record<number, string> = {
  0: '#6b7280',
  1: '#06b6d4',
  2: '#f59e0b',
  3: '#f97316',
  4: '#ef4444',
}

const PIPELINE_STAGES = ['COMMITTED', 'REVEALED', 'DISPUTED', 'ARBITRATING', 'RESOLVED']

/**
 * Derive pipeline position from contract state.
 * BugSubmission.Status: 0=Committed, 1=Revealed, 2=Resolved
 * ArbiterContract.Phase: 0=AwaitingStateImpact, 1=Voting, 2=Revealing, 3=Resolved
 */
export function derivePipelineState(submissionStatus: number, arbiterPhase: number | null): number {
  if (submissionStatus === 0) return 0 // COMMITTED
  if (submissionStatus === 2) return 4 // RESOLVED
  // status === 1 (Revealed) — check arbiter phase for more detail
  if (arbiterPhase === null || arbiterPhase === 0) return 1 // REVEALED (awaiting dispute or state impact)
  if (arbiterPhase === 1 || arbiterPhase === 2) return 3   // ARBITRATING (voting/revealing)
  if (arbiterPhase === 3) return 4                          // RESOLVED via arbitration
  return 2                                                  // DISPUTED (state impact registered)
}

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
    <div className="mb-10">
      <p className="text-xs text-[#6b7280] uppercase tracking-tight mb-4">PIPELINE STATUS</p>
      <div className="flex items-start gap-0">
        {PIPELINE_STAGES.map((stage, i) => {
          const isComplete = state > i
          const isCurrent = state === i
          const color = isComplete ? '#10b981' : isCurrent ? '#06b6d4' : '#333'
          const textColor = isComplete ? '#10b981' : isCurrent ? '#06b6d4' : '#6b7280'
          return (
            <div key={stage} className="flex items-start flex-1 last:flex-none">
              <div className="flex flex-col items-center">
                <div
                  style={{
                    width: 20,
                    height: 20,
                    borderRadius: 0,
                    border: `2px solid ${color}`,
                    backgroundColor: isComplete ? '#10b981' : 'transparent',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                >
                  <span style={{ fontSize: 9, color: isComplete ? '#000' : color, fontWeight: 800 }}>
                    {isComplete ? 'X' : String(i + 1)}
                  </span>
                </div>
                <span
                  className="text-xs mt-1 whitespace-nowrap uppercase tracking-tight"
                  style={{ color: textColor, fontSize: 9 }}
                >
                  {stage}
                </span>
              </div>
              {i < PIPELINE_STAGES.length - 1 && (
                <div
                  className="text-xs flex-1 text-center"
                  style={{ color: state > i ? '#10b981' : '#333', marginTop: 4, letterSpacing: '0.1em' }}
                >
                  ---
                </div>
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
    <div className="max-w-6xl mx-auto px-6 py-8">
      <div className="mb-6">
        {submission && (
          <Link
            to={`/bounties/${submission.bountyId}`}
            className="text-xs text-[#06b6d4] hover:text-white transition-colors duration-150 uppercase tracking-tight"
          >
            &larr; BACK TO BOUNTY #{submission.bountyId}
          </Link>
        )}
      </div>

      <h1
        className="font-extrabold uppercase text-white mb-8"
        style={{ fontSize: 'clamp(1.5rem, 3vw, 2.5rem)', letterSpacing: '-0.05em' }}
      >
        SUBMISSION #{id}
      </h1>

      {!enabled && (
        <div className="border border-[#f59e0b] p-4 text-[#f59e0b] text-xs mb-6" style={{ borderRadius: 0 }}>
          CONTRACT ADDRESS NOT CONFIGURED.
        </div>
      )}

      {isLoading && (
        <div className="flex items-center gap-2 text-[#6b7280] text-xs">
          <span className="inline-block w-2 h-2 bg-[#10b981] animate-pulse" style={{ borderRadius: 0 }} />
          LOADING SUBMISSION...
        </div>
      )}

      {submission && (
        <>
          <PipelineProgress state={derivePipelineState(submission.status, arbitration?.phase ?? null)} />

          {/* Metadata table */}
          <div className="border border-[#333] mb-8" style={{ borderRadius: 0 }}>
            <div className="border-b border-[#333] px-4 py-2">
              <span className="text-xs font-extrabold uppercase tracking-tight text-[#6b7280]">METADATA</span>
            </div>
            {[
              { key: 'HUNTER AGENT', val: `#${submission.hunterAgentId}` },
              { key: 'BOUNTY', val: `#${submission.bountyId}` },
              { key: 'STAKE', val: `${submission.stake} USDC` },
              {
                key: 'SEVERITY CLAIM',
                val: SEVERITY_LABELS[submission.claimedSeverity] ?? 'UNKNOWN',
                color: SEVERITY_COLORS[submission.claimedSeverity],
              },
              ...(submission.encryptedCID
                ? [{ key: 'REPORT CID', val: submission.encryptedCID, isLink: true, href: `https://ipfs.io/ipfs/${submission.encryptedCID.replace('ipfs://', '')}` }]
                : []),
            ].map(({ key, val, color, isLink, href }) => (
              <div key={key} className="flex justify-between items-center px-4 py-3 border-b border-[#333] last:border-b-0">
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
                  <span className="text-xs font-extrabold" style={{ color: color ?? '#fff' }}>{val}</span>
                )}
              </div>
            ))}
          </div>

          {/* State Impact */}
          {arbitration && arbitration.stateImpactCID && (
            <div className="border border-[#333] mb-8" style={{ borderRadius: 0 }}>
              <div className="border-b border-[#333] px-4 py-2">
                <span className="text-xs font-extrabold uppercase tracking-tight text-[#6b7280]">STATE IMPACT</span>
              </div>
              <div className="px-4 py-3 space-y-3">
                <div className="flex justify-between">
                  <span className="text-xs text-[#6b7280] uppercase tracking-tight">VALIDATION HASH</span>
                  <span className="text-xs text-white truncate max-w-xs">{arbitration.validationRequestHash}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-xs text-[#6b7280] uppercase tracking-tight">STATE IMPACT CID</span>
                  <a
                    href={`https://ipfs.io/ipfs/${arbitration.stateImpactCID.replace('ipfs://', '')}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs text-[#06b6d4] hover:text-white transition-colors duration-150 truncate max-w-xs"
                  >
                    {arbitration.stateImpactCID}
                  </a>
                </div>
                <div className="flex items-center gap-2 pt-1">
                  <span className="inline-block w-2 h-2 bg-[#10b981]" style={{ borderRadius: 0 }} />
                  <span className="text-xs text-[#10b981] uppercase tracking-tight">IMPACT REGISTERED — ARBITER CAN PROCEED</span>
                </div>
              </div>
            </div>
          )}

          {/* Jury votes */}
          {arbitration && arbitration.jurors.some((j) => j !== '0') && (
            <div className="border border-[#333] mb-8" style={{ borderRadius: 0 }}>
              <div className="border-b border-[#333] px-4 py-2 flex justify-between">
                <span className="text-xs font-extrabold uppercase tracking-tight text-[#6b7280]">ARBITER VOTES</span>
                <span className="text-xs text-[#6b7280]">
                  {arbitration.revealCount} / {arbitration.jurors.length} REVEALED
                </span>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-px bg-[#333]">
                {arbitration.jurors.map((jurorId, idx) => (
                  <div
                    key={jurorId + idx}
                    className="bg-black px-4 py-4"
                    style={{ borderRadius: 0 }}
                  >
                    <p className="text-xs text-[#6b7280] uppercase tracking-tight mb-3">JUROR #{jurorId}</p>
                    <div className="flex items-center gap-2 mb-2">
                      <span
                        className="inline-block w-2 h-2"
                        style={{
                          borderRadius: 0,
                          backgroundColor: arbitration.revealed[idx] ? '#10b981' : '#333',
                        }}
                      />
                      <span className="text-xs text-[#6b7280] uppercase tracking-tight">
                        {arbitration.revealed[idx] ? 'REVEALED' : 'PENDING'}
                      </span>
                    </div>
                    {arbitration.revealed[idx] && (
                      <div className="flex items-center gap-2 mt-2">
                        <span
                          className="inline-block w-2 h-2"
                          style={{
                            borderRadius: 0,
                            backgroundColor: SEVERITY_COLORS[arbitration.revealedSeverities[idx]] ?? '#6b7280',
                          }}
                        />
                        <span
                          className="text-xs font-extrabold uppercase tracking-tight"
                          style={{ color: SEVERITY_COLORS[arbitration.revealedSeverities[idx]] ?? '#6b7280' }}
                        >
                          {SEVERITY_LABELS[arbitration.revealedSeverities[idx]] ?? 'UNKNOWN'}
                        </span>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Verdict */}
          {submission.status >= 2 && (
            <div
              className="border border-[#333] p-6"
              style={{
                borderRadius: 0,
                borderLeftWidth: 4,
                borderLeftColor: submission.isValid ? '#10b981' : '#ef4444',
              }}
            >
              <p className="text-xs text-[#6b7280] uppercase tracking-tight mb-3">FINAL VERDICT</p>
              <p
                className="text-xl font-extrabold uppercase"
                style={{
                  letterSpacing: '-0.05em',
                  color: submission.isValid ? '#10b981' : '#ef4444',
                }}
              >
                {submission.isValid
                  ? `VALID — ${SEVERITY_LABELS[submission.finalSeverity] ?? 'UNKNOWN'}`
                  : 'INVALID / REJECTED'}
              </p>
            </div>
          )}
        </>
      )}
    </div>
  )
}
