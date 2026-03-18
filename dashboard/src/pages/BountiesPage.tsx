import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { ethers } from 'ethers'
import { getProvider } from '../config'
import { CONTRACT_ADDRESSES, BOUNTY_REGISTRY_ABI } from '../contracts'

interface Bounty {
  id: number
  agentId: string
  name: string
  maxPayout: string
  status: number
}

const STATUS_LABELS: Record<number, string> = {
  0: 'Active',
  1: 'Paused',
  2: 'Closed',
}

const STATUS_COLORS: Record<number, string> = {
  0: 'text-green-400',
  1: 'text-yellow-400',
  2: 'text-gray-400',
}

async function fetchBounties(): Promise<Bounty[]> {
  const provider = getProvider()
  const contract = new ethers.Contract(
    CONTRACT_ADDRESSES.bountyRegistry,
    BOUNTY_REGISTRY_ABI,
    provider,
  )

  const count = await contract.bountyCount()
  const total = Number(count)
  const bounties: Bounty[] = []

  for (let i = 1; i <= total; i++) {
    const b = await contract.getBounty(i)
    bounties.push({
      id: i,
      agentId: b.agentId.toString(),
      name: b.name,
      maxPayout: ethers.formatUnits(b.totalPool, 6),
      status: Number(b.status),
    })
  }

  return bounties
}

export default function BountiesPage() {
  const enabled = Boolean(CONTRACT_ADDRESSES.bountyRegistry)

  const { data: bounties, isLoading, error } = useQuery({
    queryKey: ['bounties'],
    queryFn: fetchBounties,
    enabled,
    refetchInterval: 15_000,
  })

  return (
    <div className="p-6">
      <h2 className="text-xl font-bold mb-6">Active Bounties</h2>

      {!enabled && (
        <div className="rounded-lg border border-yellow-700 bg-yellow-900/20 p-4 text-yellow-300 text-sm mb-4">
          Contract address not configured. Update <code>src/contracts.ts</code> with deployed addresses.
        </div>
      )}

      {isLoading && (
        <div className="flex items-center gap-2 text-gray-400">
          <div className="h-4 w-4 rounded-full border-2 border-gray-600 border-t-blue-400 animate-spin" />
          Loading bounties...
        </div>
      )}

      {error && (
        <div className="rounded-lg border border-red-800 bg-red-900/20 p-4 text-red-400 text-sm">
          Failed to load bounties: {String(error)}
        </div>
      )}

      {!isLoading && !error && bounties && bounties.length === 0 && (
        <p className="text-gray-500">No bounties found.</p>
      )}

      {bounties && bounties.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-800 text-gray-400 text-left">
                <th className="pb-3 pr-4">ID</th>
                <th className="pb-3 pr-4">Name</th>
                <th className="pb-3 pr-4">Agent</th>
                <th className="pb-3 pr-4">Pool</th>
                <th className="pb-3">Status</th>
              </tr>
            </thead>
            <tbody>
              {bounties.map((b) => (
                <tr key={b.id} className="border-b border-gray-800/50 hover:bg-gray-900/50">
                  <td className="py-3 pr-4 font-mono text-gray-400">#{b.id}</td>
                  <td className="py-3 pr-4">
                    <Link
                      to={`/bounties/${b.id}`}
                      className="text-blue-400 hover:text-blue-300 font-medium"
                    >
                      {b.name}
                    </Link>
                  </td>
                  <td className="py-3 pr-4 font-mono text-gray-400">Agent #{b.agentId}</td>
                  <td className="py-3 pr-4 font-mono">{b.maxPayout} USDC</td>
                  <td className="py-3">
                    <span className={STATUS_COLORS[b.status] ?? 'text-gray-400'}>
                      {STATUS_LABELS[b.status] ?? 'Unknown'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
