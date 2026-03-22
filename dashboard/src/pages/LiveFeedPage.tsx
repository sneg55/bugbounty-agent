import { useEffect, useRef, useState } from 'react'
import { ethers } from 'ethers'
import { getProvider } from '../config'
import {
  CONTRACT_ADDRESSES,
  BOUNTY_REGISTRY_ABI,
  BUG_SUBMISSION_ABI,
  ARBITER_CONTRACT_ABI,
} from '../contracts'

interface FeedEvent {
  id: string
  type: string
  description: string
  blockNumber: number
  txHash: string
  timestamp: Date
}

const EVENT_TYPE_COLORS: Record<string, string> = {
  BountyCreated: '#a855f7',
  BugCommitted: '#06b6d4',
  BugRevealed: '#06b6d4',
  StateImpactRegistered: '#f59e0b',
  JurySelected: '#a855f7',
  VoteCommitted: '#10b981',
  VoteRevealed: '#10b981',
  SubmissionResolved: '#10b981',
  PatchGuidance: '#f59e0b',
}

export function formatEvent(eventName: string, args: ethers.Result): string {
  switch (eventName) {
    case 'BountyCreated':
      return `Bounty #${args[0]} created: "${args[2]}" — max ${ethers.formatUnits(args[3], 6)} USDC`
    case 'BugCommitted':
      return `Bug #${args[0]} committed to Bounty #${args[1]} by Agent #${args[2]}`
    case 'BugRevealed':
      return `Bug #${args[0]} revealed — CID: ${String(args[1]).slice(0, 30)}...`
    case 'StateImpactRegistered':
      return `State impact registered for Bug #${args[0]}`
    case 'JurySelected':
      return `Jury selected for Bug #${args[0]} — ${(args[1] as bigint[]).length} jurors`
    case 'VoteCommitted':
      return `Juror #${args[1]} committed vote for Bug #${args[0]}`
    case 'VoteRevealed':
      return `Juror #${args[1]} revealed vote for Bug #${args[0]}: severity ${args[2]}`
    case 'SubmissionResolved': {
      const severityLabels = ['INVALID', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'];
      const severity = Number(args[1]);
      const isValid = args[2];
      return `Bug #${args[0]} resolved — ${severityLabels[severity] || 'UNKNOWN'} severity, ${isValid ? 'valid' : 'invalid'}`;
    }
    case 'PatchGuidance':
      return `Patch guidance issued for Bug #${args[0]}`
    default:
      return eventName
  }
}

async function fetchRecentEvents(fromBlock: number): Promise<FeedEvent[]> {
  const provider = getProvider()
  const events: FeedEvent[] = []

  const contracts = [
    { address: CONTRACT_ADDRESSES.bountyRegistry, abi: BOUNTY_REGISTRY_ABI },
    { address: CONTRACT_ADDRESSES.bugSubmission, abi: BUG_SUBMISSION_ABI },
    { address: CONTRACT_ADDRESSES.arbiterContract, abi: ARBITER_CONTRACT_ABI },
  ].filter((c) => Boolean(c.address))

  await Promise.all(
    contracts.map(async ({ address, abi }) => {
      const contract = new ethers.Contract(address, abi, provider)
      const logs = await contract.queryFilter('*' as unknown as ethers.DeferredTopicFilter, fromBlock)

      for (const log of logs) {
        if (!('eventName' in log) || !('args' in log)) continue
        const eventLog = log as ethers.EventLog
        events.push({
          id: `${eventLog.transactionHash}-${eventLog.index}`,
          type: eventLog.eventName,
          description: formatEvent(eventLog.eventName, eventLog.args),
          blockNumber: eventLog.blockNumber,
          txHash: eventLog.transactionHash,
          timestamp: new Date(),
        })
      }
    }),
  )

  return events.sort((a, b) => b.blockNumber - a.blockNumber)
}

export default function LiveFeedPage() {
  const [events, setEvents] = useState<FeedEvent[]>([])
  const [isPolling, setIsPolling] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)
  const lastBlockRef = useRef(0)

  const enabled =
    Boolean(CONTRACT_ADDRESSES.bountyRegistry) ||
    Boolean(CONTRACT_ADDRESSES.bugSubmission) ||
    Boolean(CONTRACT_ADDRESSES.arbiterContract)

  useEffect(() => {
    if (!enabled) return

    let cancelled = false

    async function poll() {
      setIsPolling(true)
      try {
        const provider = getProvider()
        const currentBlock = await provider.getBlockNumber()
        const fromBlock = lastBlockRef.current
          ? lastBlockRef.current + 1
          : Math.max(0, currentBlock - 50)
        const fetched = await fetchRecentEvents(fromBlock)
        lastBlockRef.current = currentBlock
        if (!cancelled) {
          setEvents((prev) => {
            const existingIds = new Set(prev.map((e) => e.id))
            const newEvents = fetched.filter((e) => !existingIds.has(e.id))
            if (newEvents.length === 0) return prev
            return [...prev, ...newEvents].sort((a, b) => b.blockNumber - a.blockNumber)
          })
          setError(null)
        }
      } catch (err) {
        if (!cancelled) setError(String(err))
      } finally {
        if (!cancelled) setIsPolling(false)
      }
    }

    poll()
    const interval = setInterval(poll, 10_000)
    return () => {
      cancelled = true
      clearInterval(interval)
    }
  }, [enabled])

  // Auto-scroll to bottom when new events arrive
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [events])

  return (
    <div className="max-w-6xl mx-auto px-6 py-8 flex flex-col" style={{ minHeight: 'calc(100vh - 120px)' }}>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h1
          className="font-extrabold uppercase text-white"
          style={{ fontSize: 'clamp(1.5rem, 3vw, 2.5rem)', letterSpacing: '-0.05em' }}
        >
          LIVE FEED
        </h1>
        <div className="flex items-center gap-2">
          {isPolling ? (
            <span className="inline-block w-2 h-2 bg-[#10b981] animate-blink" style={{ borderRadius: 0 }} />
          ) : (
            <span className="inline-block w-2 h-2 bg-[#333]" style={{ borderRadius: 0 }} />
          )}
          <span className="text-xs text-[#6b7280] uppercase tracking-tight">
            {isPolling ? 'POLLING' : 'IDLE'}
          </span>
          {events.length > 0 && (
            <span className="text-xs text-[#333] uppercase tracking-tight">({events.length})</span>
          )}
        </div>
      </div>

      {!enabled && (
        <div className="border border-[#f59e0b] p-4 text-[#f59e0b] text-xs mb-6" style={{ borderRadius: 0 }}>
          NO CONTRACT ADDRESSES CONFIGURED. UPDATE <code>src/contracts.ts</code>.
        </div>
      )}

      {error && (
        <div className="border border-[#ef4444] p-4 text-[#ef4444] text-xs mb-6" style={{ borderRadius: 0 }}>
          ERROR FETCHING EVENTS: {error}
        </div>
      )}

      {/* Terminal feed */}
      <div className="flex-1 overflow-y-auto border border-[#333]" style={{ borderRadius: 0 }}>
        <div className="border-b border-[#333] px-4 py-2 flex items-center gap-2">
          <span className="inline-block w-2 h-2 bg-[#10b981]" style={{ borderRadius: 0 }} />
          <span className="text-xs text-[#6b7280] uppercase tracking-tight">EVENT STREAM</span>
        </div>

        {events.length === 0 && !isPolling && enabled && (
          <p className="text-xs text-[#6b7280] uppercase tracking-tight text-center py-12">
            NO EVENTS IN LAST 50 BLOCKS
          </p>
        )}

        {isPolling && events.length === 0 && (
          <p className="text-xs text-[#6b7280] uppercase tracking-tight text-center py-12">
            SCANNING CHAIN...
          </p>
        )}

        {events.map((event) => {
          const typeColor = EVENT_TYPE_COLORS[event.type] ?? '#6b7280'
          return (
            <div
              key={event.id}
              className="flex items-start gap-3 px-4 py-2 border-b border-[#1a1a1a] hover:bg-[#0a0a0a] transition-colors duration-150"
            >
              <span className="text-xs text-[#6b7280] shrink-0 w-20 text-right">
                #{event.blockNumber}
              </span>
              <span
                className="text-xs font-extrabold uppercase tracking-tight shrink-0 w-36"
                style={{ color: typeColor }}
              >
                {event.type}
              </span>
              <span className="text-xs text-white flex-1 truncate">{event.description}</span>
              <a
                href={`https://sepolia.basescan.org/tx/${event.txHash}`}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-[#06b6d4] hover:text-white transition-colors duration-150 shrink-0"
              >
                {event.txHash.slice(0, 8)}...
              </a>
            </div>
          )
        })}

        <div ref={bottomRef} />
      </div>

      {/* Legend */}
      <div className="mt-4 pt-4 border-t border-[#333] flex flex-wrap gap-4">
        {Object.entries(EVENT_TYPE_COLORS).map(([type, color]) => (
          <div key={type} className="flex items-center gap-1.5">
            <span className="inline-block w-1.5 h-1.5" style={{ borderRadius: 0, backgroundColor: color }} />
            <span className="text-xs text-[#6b7280] uppercase tracking-tight">{type}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
