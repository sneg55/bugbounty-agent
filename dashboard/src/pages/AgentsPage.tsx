import { useQuery } from '@tanstack/react-query'
import { ethers } from 'ethers'
import { getProvider } from '../config'
import { CONTRACT_ADDRESSES, IDENTITY_REGISTRY_ABI, REPUTATION_REGISTRY_ABI } from '../contracts'

interface Agent {
  id: number
  owner: string
  uri: string
  reputation: number
  validityRate: number
  role: { label: string; color: string }
}

const ROLE_COLORS: Record<string, string> = {
  PROTOCOL: '#a855f7',
  HUNTER: '#06b6d4',
  EXECUTOR: '#f59e0b',
  ARBITER: '#10b981',
}

export function roleFromURI(uri: string): { label: string; color: string } {
  const lower = uri.toLowerCase()
  if (lower.includes('protocol')) return { label: 'PROTOCOL', color: ROLE_COLORS.PROTOCOL }
  if (lower.includes('hunter')) return { label: 'HUNTER', color: ROLE_COLORS.HUNTER }
  if (lower.includes('executor')) return { label: 'EXECUTOR', color: ROLE_COLORS.EXECUTOR }
  if (lower.includes('arb')) return { label: 'ARBITER', color: ROLE_COLORS.ARBITER }
  return { label: 'UNKNOWN', color: '#6b7280' }
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
    const [owner, uri, rep, validity, roleBytes] = await Promise.all([
      identityContract.ownerOf(i),
      identityContract.tokenURI(i),
      reputationContract.getReputation(i),
      reputationContract.getValidityRate(i),
      identityContract.getMetadata(i, 'role').catch(() => '0x'),
    ])
    const uriStr = uri as string
    // Prefer on-chain "role" metadata; fall back to URI heuristic
    const roleStr = roleBytes && roleBytes !== '0x' ? ethers.toUtf8String(roleBytes) : ''
    const role = roleStr ? roleFromURI(roleStr) : roleFromURI(uriStr)
    agents.push({
      id: i,
      owner: owner as string,
      uri: uriStr,
      reputation: Number(rep),
      validityRate: Number(validity),
      role,
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
                          style={{ borderRadius: 0, backgroundColor: agent.role.color }}
                        />
                        <span className="font-extrabold" style={{ color: agent.role.color }}>
                          {agent.role.label}
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-[#6b7280] truncate max-w-[200px]">
                      {agent.owner}
                    </td>
                    <td className="px-4 py-3 text-right font-extrabold" style={{ color: repColor }}>
                      {agent.reputation >= 0 ? '+' : ''}{agent.reputation}
                    </td>
                    <td className="px-4 py-3 text-right text-white font-extrabold">
                      {agent.validityRate}%
                    </td>
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
