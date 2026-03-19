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

const ROLE_DEFS: { label: string; color: string }[] = [
  { label: 'PROTOCOL', color: '#a855f7' },
  { label: 'HUNTER', color: '#06b6d4' },
  { label: 'EXECUTOR', color: '#f59e0b' },
  { label: 'ARBITER', color: '#10b981' },
]

function inferRole(agentId: number): { label: string; color: string } {
  const idx = (agentId - 1) % ROLE_DEFS.length
  return ROLE_DEFS[idx]
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

  const count = await identityContract.totalAgents()
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
    <div className="max-w-6xl mx-auto px-6 py-8">
      <h1
        className="font-extrabold uppercase text-white mb-8"
        style={{ fontSize: 'clamp(1.5rem, 3vw, 2.5rem)', letterSpacing: '-0.05em' }}
      >
        AGENTS
      </h1>

      {!enabled && (
        <div className="border border-[#f59e0b] p-4 text-[#f59e0b] text-xs mb-6" style={{ borderRadius: 0 }}>
          CONTRACT ADDRESSES NOT CONFIGURED. UPDATE <code>src/contracts.ts</code>.
        </div>
      )}

      {isLoading && (
        <div className="flex items-center gap-2 text-[#6b7280] text-xs">
          <span className="inline-block w-2 h-2 bg-[#10b981] animate-pulse" style={{ borderRadius: 0 }} />
          LOADING AGENTS...
        </div>
      )}

      {error && (
        <div className="border border-[#ef4444] p-4 text-[#ef4444] text-xs mb-6" style={{ borderRadius: 0 }}>
          FAILED TO LOAD AGENTS: {String(error)}
        </div>
      )}

      {agents && agents.length === 0 && (
        <p className="text-[#6b7280] text-xs uppercase tracking-tight py-16 text-center">
          NO AGENTS REGISTERED
        </p>
      )}

      {agents && agents.length > 0 && (
        <div className="overflow-x-auto border border-[#333]" style={{ borderRadius: 0 }}>
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-[#333]">
                <th className="text-left px-4 py-3 text-[#6b7280] uppercase tracking-tight font-extrabold">ID</th>
                <th className="text-left px-4 py-3 text-[#6b7280] uppercase tracking-tight font-extrabold">ROLE</th>
                <th className="text-left px-4 py-3 text-[#6b7280] uppercase tracking-tight font-extrabold">OWNER</th>
                <th className="text-right px-4 py-3 text-[#6b7280] uppercase tracking-tight font-extrabold">REPUTATION</th>
                <th className="text-right px-4 py-3 text-[#6b7280] uppercase tracking-tight font-extrabold">VALIDITY RATE</th>
              </tr>
            </thead>
            <tbody>
              {agents.map((agent) => {
                const role = inferRole(agent.id)
                const repColor = agent.reputation >= 0 ? '#10b981' : '#ef4444'
                return (
                  <tr
                    key={agent.id}
                    className="border-b border-[#333] last:border-b-0 hover:border-l-2 hover:border-l-[#06b6d4] transition-all duration-150"
                  >
                    <td className="px-4 py-3 text-[#6b7280]">#{agent.id}</td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <span
                          className="inline-block w-2 h-2"
                          style={{ borderRadius: 0, backgroundColor: role.color }}
                        />
                        <span className="font-extrabold" style={{ color: role.color }}>
                          {role.label}
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-[#6b7280] truncate max-w-[200px]">
                      {agent.owner}
                    </td>
                    <td className="px-4 py-3 text-right font-extrabold" style={{ color: repColor }}>
                      {agent.reputation >= 0 ? '+' : ''}{agent.reputation}
                    </td>
                    <td className="px-4 py-3 text-right text-[#6b7280]">—</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
