import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { ethers } from 'ethers'
import { getProvider } from '../config'
import { CONTRACT_ADDRESSES, BOUNTY_REGISTRY_ABI } from '../contracts'

interface Bounty {
  id: number
  protocolAgentId: string
  name: string
  totalFunding: string
  active: boolean
}

async function fetchBounties(): Promise<Bounty[]> {
  const provider = getProvider()
  const contract = new ethers.Contract(
    CONTRACT_ADDRESSES.bountyRegistry,
    BOUNTY_REGISTRY_ABI,
    provider,
  )

  const count = await contract.getBountyCount()
  const total = Number(count)
  const bounties: Bounty[] = []

  for (let i = 1; i <= total; i++) {
    const b = await contract.getBounty(i)
    bounties.push({
      id: i,
      protocolAgentId: b.protocolAgentId.toString(),
      name: b.name,
      totalFunding: ethers.formatUnits(b.totalFunding, 6),
      active: b.active,
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
    <div className="max-w-6xl mx-auto px-6 py-8">
      <h1
        className="font-extrabold uppercase text-white mb-8"
        style={{ fontSize: 'clamp(1.5rem, 3vw, 2.5rem)', letterSpacing: '-0.05em' }}
      >
        BOUNTIES
      </h1>

      {!enabled && (
        <div className="border border-[#f59e0b] p-4 text-[#f59e0b] text-xs mb-6" style={{ borderRadius: 0 }}>
          CONTRACT ADDRESS NOT CONFIGURED. UPDATE <code>src/contracts.ts</code> WITH DEPLOYED ADDRESSES.
        </div>
      )}

      {isLoading && (
        <div className="flex items-center gap-2 text-[#6b7280] text-xs">
          <span className="inline-block w-2 h-2 bg-[#10b981] animate-pulse" style={{ borderRadius: 0 }} />
          LOADING BOUNTIES...
        </div>
      )}

      {error && (
        <div className="border border-[#ef4444] p-4 text-[#ef4444] text-xs mb-6" style={{ borderRadius: 0 }}>
          FAILED TO LOAD BOUNTIES: {String(error)}
        </div>
      )}

      {!isLoading && !error && bounties && bounties.length === 0 && (
        <p className="text-[#6b7280] text-xs text-center py-16 uppercase tracking-tight">
          NO ACTIVE BOUNTIES
        </p>
      )}

      {bounties && bounties.length > 0 && (
        <div className="overflow-x-auto border border-[#333]" style={{ borderRadius: 0 }}>
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-[#333]">
                <th className="text-left px-4 py-3 text-[#6b7280] uppercase tracking-tight font-extrabold">ID</th>
                <th className="text-left px-4 py-3 text-[#6b7280] uppercase tracking-tight font-extrabold">NAME</th>
                <th className="text-left px-4 py-3 text-[#6b7280] uppercase tracking-tight font-extrabold">PROTOCOL AGENT</th>
                <th className="text-right px-4 py-3 text-[#6b7280] uppercase tracking-tight font-extrabold">TOTAL FUNDING</th>
                <th className="text-left px-4 py-3 text-[#6b7280] uppercase tracking-tight font-extrabold">STATUS</th>
              </tr>
            </thead>
            <tbody>
              {bounties.map((b) => (
                <tr
                  key={b.id}
                  className="border-b border-[#333] hover:border-l-2 hover:border-l-[#06b6d4] transition-all duration-150 group"
                >
                  <td className="px-4 py-3 text-[#6b7280]">#{b.id}</td>
                  <td className="px-4 py-3">
                    <Link
                      to={`/bounties/${b.id}`}
                      className="text-[#06b6d4] hover:text-white transition-colors duration-150 font-extrabold"
                    >
                      {b.name}
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-[#6b7280]">AGENT #{b.protocolAgentId}</td>
                  <td className="px-4 py-3 text-right font-extrabold text-white">{b.totalFunding} USDC</td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <span
                        className="inline-block w-2 h-2"
                        style={{
                          borderRadius: 0,
                          backgroundColor: b.active ? '#10b981' : '#6b7280',
                        }}
                      />
                      <span className={b.active ? 'text-[#10b981]' : 'text-[#6b7280]'}>
                        {b.active ? 'ACTIVE' : 'CLOSED'}
                      </span>
                    </div>
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
