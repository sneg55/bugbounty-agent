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

const EVENT_COLORS: Record<string, string> = {
  BountyCreated: 'border-purple-700 bg-purple-900/20',
  BugCommitted: 'border-blue-700 bg-blue-900/20',
  BugRevealed: 'border-cyan-700 bg-cyan-900/20',
  StateImpactRegistered: 'border-yellow-700 bg-yellow-900/20',
  JurySelected: 'border-indigo-700 bg-indigo-900/20',
  VoteCommitted: 'border-green-700 bg-green-900/20',
  VoteRevealed: 'border-teal-700 bg-teal-900/20',
  SubmissionResolved: 'border-emerald-700 bg-emerald-900/20',
  PatchGuidance: 'border-orange-700 bg-orange-900/20',
}

const EVENT_TYPE_COLORS: Record<string, string> = {
  BountyCreated: 'text-purple-400',
  BugCommitted: 'text-blue-400',
  BugRevealed: 'text-cyan-400',
  StateImpactRegistered: 'text-yellow-400',
  JurySelected: 'text-indigo-400',
  VoteCommitted: 'text-green-400',
  VoteRevealed: 'text-teal-400',
  SubmissionResolved: 'text-emerald-400',
  PatchGuidance: 'text-orange-400',
}

function formatEvent(eventName: string, args: ethers.Result): string {
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
    case 'SubmissionResolved':
      return `Bug #${args[0]} resolved — verdict ${args[1]}, payout ${ethers.formatUnits(args[2], 6)} USDC`
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
        const latest = await provider.getBlockNumber()
        const fromBlock = Math.max(0, latest - 500) // last ~500 blocks
        const fetched = await fetchRecentEvents(fromBlock)
        if (!cancelled) {
          setEvents(fetched)
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
    <div className="p-6 flex flex-col h-full">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-bold">Live Event Feed</h2>
        <div className="flex items-center gap-2 text-sm text-gray-400">
          {isPolling && (
            <div className="h-3 w-3 rounded-full border-2 border-gray-600 border-t-blue-400 animate-spin" />
          )}
          <span>{isPolling ? 'Polling...' : 'Idle'}</span>
          {events.length > 0 && (
            <span className="text-gray-600">({events.length} events)</span>
          )}
        </div>
      </div>

      {!enabled && (
        <div className="rounded-lg border border-yellow-700 bg-yellow-900/20 p-4 text-yellow-300 text-sm mb-4">
          No contract addresses configured. Update <code>src/contracts.ts</code>.
        </div>
      )}

      {error && (
        <div className="rounded-lg border border-red-800 bg-red-900/20 p-4 text-red-400 text-sm mb-4">
          Error fetching events: {error}
        </div>
      )}

      <div className="flex-1 overflow-y-auto space-y-2 pr-1">
        {events.length === 0 && !isPolling && enabled && (
          <p className="text-gray-500 text-sm">No events found in the last 500 blocks.</p>
        )}

        {events.map((event) => (
          <div
            key={event.id}
            className={`rounded-lg border p-3 text-sm ${EVENT_COLORS[event.type] ?? 'border-gray-800 bg-gray-900'}`}
          >
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1 min-w-0">
                <span
                  className={`text-xs font-medium uppercase tracking-wide ${
                    EVENT_TYPE_COLORS[event.type] ?? 'text-gray-400'
                  }`}
                >
                  {event.type}
                </span>
                <p className="text-gray-200 mt-0.5 truncate">{event.description}</p>
              </div>
              <div className="text-right text-xs text-gray-500 shrink-0">
                <p>Block #{event.blockNumber}</p>
                <a
                  href={`https://sepolia.basescan.org/tx/${event.txHash}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-500 hover:text-blue-400 font-mono"
                >
                  {event.txHash.slice(0, 10)}...
                </a>
              </div>
            </div>
          </div>
        ))}

        <div ref={bottomRef} />
      </div>

      {/* Legend */}
      <div className="mt-4 pt-4 border-t border-gray-800">
        <p className="text-xs text-gray-500 mb-2">Event types:</p>
        <div className="flex flex-wrap gap-2">
          {Object.entries(EVENT_TYPE_COLORS).map(([type, color]) => (
            <span key={type} className={`text-xs ${color}`}>
              {type}
            </span>
          ))}
        </div>
      </div>
    </div>
  )
}
