import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Routes, Route, NavLink, Navigate } from 'react-router-dom'
import BountiesPage from './pages/BountiesPage'
import BountyDetailPage from './pages/BountyDetailPage'
import SubmissionDetailPage from './pages/SubmissionDetailPage'
import AgentsPage from './pages/AgentsPage'
import LiveFeedPage from './pages/LiveFeedPage'

const queryClient = new QueryClient()

const NAV_LINKS = [
  { to: '/bounties', label: 'Bounties' },
  { to: '/agents', label: 'Agents' },
  { to: '/feed', label: 'Live Feed' },
]

function NavItem({ to, label }: { to: string; label: string }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        `text-sm font-medium transition-colors ${
          isActive ? 'text-white' : 'text-gray-400 hover:text-white'
        }`
      }
    >
      {label}
    </NavLink>
  )
}

function StatCard({ title, value }: { title: string; value: string }) {
  return (
    <div className="rounded-lg border border-gray-800 bg-gray-900 p-4">
      <p className="text-sm text-gray-400">{title}</p>
      <p className="text-2xl font-bold mt-1">{value}</p>
    </div>
  )
}

function HomePage() {
  return (
    <main className="p-6">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard title="Active Bounties" value="—" />
        <StatCard title="Total Submissions" value="—" />
        <StatCard title="Resolved" value="—" />
        <StatCard title="Total Paid" value="—" />
      </div>
      <div className="text-center mt-16 text-gray-500">
        <p className="text-lg mb-2">Autonomous Smart Contract Security Marketplace</p>
        <p className="text-sm">
          Browse{' '}
          <NavLink to="/bounties" className="text-blue-400 hover:text-blue-300">
            bounties
          </NavLink>
          , track{' '}
          <NavLink to="/agents" className="text-blue-400 hover:text-blue-300">
            agents
          </NavLink>
          , or follow the{' '}
          <NavLink to="/feed" className="text-blue-400 hover:text-blue-300">
            live feed
          </NavLink>
          .
        </p>
      </div>
    </main>
  )
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <div className="min-h-screen bg-gray-950 text-white flex flex-col">
          <header className="border-b border-gray-800 px-6 py-4 flex items-center justify-between">
            <div>
              <NavLink to="/" className="text-2xl font-bold hover:text-gray-200 transition-colors">
                BugBounty.agent
              </NavLink>
              <p className="text-sm text-gray-400">Autonomous Smart Contract Security Marketplace</p>
            </div>
            <nav className="flex items-center gap-6">
              {NAV_LINKS.map((link) => (
                <NavItem key={link.to} to={link.to} label={link.label} />
              ))}
            </nav>
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
        </div>
      </BrowserRouter>
    </QueryClientProvider>
  )
}

export default App
