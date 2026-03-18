import { useQuery } from '@tanstack/react-query'
import { ethers } from 'ethers'
import { getProvider } from '../config'
import { CONTRACT_ADDRESSES, IDENTITY_REGISTRY_ABI, REPUTATION_REGISTRY_ABI } from '../contracts'

interface Agent {
  id: number
  owner: string
  uri: string
  reputation: number
}

const ROLE_BADGES: { label: string; color: string }[] = [
  { label: 'Protocol', color: 'bg-purple-900 text-purple-300' },
  { label: 'Hunter', color: 'bg-blue-900 text-blue-300' },
  { label: 'Executor', color: 'bg-yellow-900 text-yellow-300' },
  { label: 'Arbiter', color: 'bg-green-900 text-green-300' },
]

function inferRole(agentId: number): { label: string; color: string } {
  // Placeholder heuristic — replace with actual on-chain role lookup
  const idx = (agentId - 1) % ROLE_BADGES.length
  return ROLE_BADGES[idx]
}

async function fetchAgents(): Promise<Agent[]> {
  const provider = getProvider()
  const identityContract = new ethers.Contract(
    CONTRACT_ADDRESSES.identityRegistry,
    IDENTITY_REGISTRY_ABI,
    provider,
  )
  const reputationContract = new ethers.Contract(
    CONTRACT_ADDRESSES.reputationRegistry,
    REPUTATION_REGISTRY_ABI,
    provider,
  )

  const count = await identityContract.agentCount()
  const total = Number(count)
  const agents: Agent[] = []

  for (let i = 1; i <= total; i++) {
    const [owner, uri, rep] = await Promise.all([
      identityContract.ownerOf(i),
      identityContract.tokenURI(i),
      reputationContract.getReputation(i),
    ])
    agents.push({
      id: i,
      owner: owner as string,
      uri: uri as string,
      reputation: Number(rep),
    })
  }

  return agents
}

function ReputationBar({ value }: { value: number }) {
  // Reputation can be negative; clamp to [-500, 500] for display
  const clamped = Math.max(-500, Math.min(500, value))
  const pct = ((clamped + 500) / 1000) * 100
  const color =
    value >= 200 ? 'bg-green-500' : value >= 0 ? 'bg-blue-500' : value >= -100 ? 'bg-yellow-500' : 'bg-red-500'

  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 rounded-full bg-gray-700 overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className={`text-xs font-mono w-12 text-right ${value >= 0 ? 'text-green-400' : 'text-red-400'}`}>
        {value >= 0 ? '+' : ''}{value}
      </span>
    </div>
  )
}

export default function AgentsPage() {
  const enabled =
    Boolean(CONTRACT_ADDRESSES.identityRegistry) &&
    Boolean(CONTRACT_ADDRESSES.reputationRegistry)

  const { data: agents, isLoading, error } = useQuery({
    queryKey: ['agents'],
    queryFn: fetchAgents,
    enabled,
    refetchInterval: 30_000,
  })

  return (
    <div className="p-6">
      <h2 className="text-xl font-bold mb-6">Registered Agents</h2>

      {!enabled && (
        <div className="rounded-lg border border-yellow-700 bg-yellow-900/20 p-4 text-yellow-300 text-sm mb-4">
          Contract addresses not configured. Update <code>src/contracts.ts</code>.
        </div>
      )}

      {isLoading && (
        <div className="flex items-center gap-2 text-gray-400">
          <div className="h-4 w-4 rounded-full border-2 border-gray-600 border-t-blue-400 animate-spin" />
          Loading agents...
        </div>
      )}

      {error && (
        <div className="rounded-lg border border-red-800 bg-red-900/20 p-4 text-red-400 text-sm">
          Failed to load agents: {String(error)}
        </div>
      )}

      {agents && agents.length === 0 && (
        <p className="text-gray-500 text-sm">No agents registered yet.</p>
      )}

      {agents && agents.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {agents.map((agent) => {
            const role = inferRole(agent.id)
            return (
              <div
                key={agent.id}
                className="rounded-lg border border-gray-800 bg-gray-900 p-4 flex flex-col gap-3"
              >
                <div className="flex items-start justify-between">
                  <div>
                    <p className="font-bold">Agent #{agent.id}</p>
                    <p className="text-xs font-mono text-gray-400 truncate max-w-[180px] mt-0.5">
                      {agent.owner}
                    </p>
                  </div>
                  <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${role.color}`}>
                    {role.label}
                  </span>
                </div>

                <ReputationBar value={agent.reputation} />

                {agent.uri && (
                  <a
                    href={`https://ipfs.io/ipfs/${agent.uri.replace('ipfs://', '')}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs text-blue-400 hover:text-blue-300 truncate"
                  >
                    {agent.uri}
                  </a>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
