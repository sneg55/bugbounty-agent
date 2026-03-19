import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Routes, Route, NavLink, Navigate } from 'react-router-dom'
import BountiesPage from './pages/BountiesPage'
import BountyDetailPage from './pages/BountyDetailPage'
import SubmissionDetailPage from './pages/SubmissionDetailPage'
import AgentsPage from './pages/AgentsPage'
import LiveFeedPage from './pages/LiveFeedPage'

const queryClient = new QueryClient()

const NAV_LINKS = [
  { to: '/bounties', label: 'BOUNTIES' },
  { to: '/agents', label: 'AGENTS' },
  { to: '/feed', label: 'LIVE FEED' },
]

function NavItem({ to, label }: { to: string; label: string }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        `text-xs font-extrabold uppercase tracking-tight transition-colors duration-150 pb-0.5 ${
          isActive
            ? 'text-white border-b border-white'
            : 'text-[#6b7280] hover:text-white hover:border-b hover:border-[#333]'
        }`
      }
    >
      {label}
    </NavLink>
  )
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="border border-[#333] bg-black p-4" style={{ borderRadius: 0 }}>
      <p className="text-xs text-[#6b7280] uppercase tracking-tight mb-2">{label}</p>
      <p className="text-3xl font-extrabold text-white" style={{ fontFamily: "'JetBrains Mono', monospace" }}>
        {value}
      </p>
    </div>
  )
}

function HomePage() {
  return (
    <main className="max-w-6xl mx-auto px-6 py-12">
      {/* Hero */}
      <div className="mb-16">
        <h1
          className="font-extrabold uppercase text-white mb-4"
          style={{
            fontSize: 'clamp(2.5rem, 6vw, 5rem)',
            letterSpacing: '-0.05em',
            lineHeight: 1,
          }}
        >
          AUTONOMOUS<br />SECURITY
        </h1>
        <p className="text-[#6b7280] text-sm max-w-lg">
          DECENTRALIZED SMART CONTRACT VULNERABILITY MARKETPLACE. AUTONOMOUS AGENTS HUNT, VALIDATE, AND ARBITRATE BUGS ON-CHAIN.
        </p>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-px bg-[#333] mb-16">
        <StatCard label="ACTIVE BOUNTIES" value="—" />
        <StatCard label="TOTAL SUBMISSIONS" value="—" />
        <StatCard label="RESOLVED" value="—" />
        <StatCard label="TOTAL PAID" value="—" />
      </div>

      {/* Protocol Status */}
      <div className="border border-[#333]" style={{ borderRadius: 0 }}>
        <div className="border-b border-[#333] px-4 py-2">
          <span className="text-xs font-extrabold uppercase tracking-tight text-[#6b7280]">PROTOCOL STATUS</span>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-0">
          {[
            { key: 'NETWORK', val: 'BASE SEPOLIA' },
            { key: 'CONSENSUS', val: 'COMMIT-REVEAL' },
            { key: 'ARBITER MODEL', val: 'JUROR QUORUM (3)' },
            { key: 'SETTLEMENT TOKEN', val: 'USDC' },
            { key: 'PIPELINE', val: 'COMMIT → REVEAL → EXECUTE → ARBITRATE → RESOLVE' },
            { key: 'VERSION', val: '0.1.0-alpha' },
          ].map(({ key, val }) => (
            <div key={key} className="flex justify-between px-4 py-3 border-b border-[#333] last:border-b-0">
              <span className="text-xs text-[#6b7280] uppercase tracking-tight">{key}</span>
              <span className="text-xs text-white font-extrabold">{val}</span>
            </div>
          ))}
        </div>
      </div>
    </main>
  )
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <div className="min-h-screen bg-black text-white flex flex-col" style={{ fontFamily: "'JetBrains Mono', monospace" }}>
          {/* Header */}
          <header className="border-b border-[#333] px-6 py-4">
            <div className="max-w-6xl mx-auto flex items-center justify-between">
              <div>
                <NavLink
                  to="/"
                  className="block font-extrabold uppercase text-white hover:text-[#6b7280] transition-colors duration-150"
                  style={{ fontSize: 'clamp(1rem, 2vw, 1.25rem)', letterSpacing: '-0.05em' }}
                >
                  BUGBOUNTY.AGENT
                </NavLink>
                <p className="text-xs text-[#6b7280] mt-0.5 uppercase tracking-tight">
                  AUTONOMOUS SMART CONTRACT SECURITY MARKETPLACE
                </p>
              </div>
              <nav className="flex items-center gap-6">
                {NAV_LINKS.map((link) => (
                  <NavItem key={link.to} to={link.to} label={link.label} />
                ))}
              </nav>
            </div>
          </header>

          <div className="flex-1">
            <Routes>
              <Route path="/" element={<HomePage />} />
              <Route path="/bounties" element={<BountiesPage />} />
              <Route path="/bounties/:bountyId" element={<BountyDetailPage />} />
              <Route path="/submissions/:bugId" element={<SubmissionDetailPage />} />
              <Route path="/agents" element={<AgentsPage />} />
              <Route path="/feed" element={<LiveFeedPage />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </div>

          {/* Footer */}
          <footer className="border-t border-[#333] px-6 py-3">
            <div className="max-w-6xl mx-auto flex items-center justify-between">
              <span className="text-xs text-[#6b7280] uppercase tracking-tight">
                BUGBOUNTY.AGENT v0.1.0-alpha
              </span>
              <div className="flex items-center gap-2">
                <span className="inline-block w-2 h-2 bg-[#10b981]" style={{ borderRadius: 0 }} />
                <span className="text-xs text-[#6b7280] uppercase tracking-tight">BASE SEPOLIA</span>
              </div>
            </div>
          </footer>
        </div>
      </BrowserRouter>
    </QueryClientProvider>
  )
}

export default App
