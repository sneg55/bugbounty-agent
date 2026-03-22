import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import { renderWithProviders } from '../test/helpers'
import SubmissionDetailPage from './SubmissionDetailPage'

vi.mock('../config', () => ({
  getProvider: vi.fn(),
}))

const mockGetSubmission = vi.fn()
const mockGetArbitration = vi.fn()

vi.mock('ethers', async () => {
  const actual = await vi.importActual('ethers')
  const realEthers = (actual as { ethers: Record<string, unknown> }).ethers
  return {
    ...actual,
    ethers: {
      ...realEthers,
      Contract: class MockContract {
        getSubmission = mockGetSubmission
        getArbitration = mockGetArbitration
      },
    },
  }
})

beforeEach(() => {
  vi.clearAllMocks()
})

const mockSubmission = {
  bountyId: 1n,
  hunterAgentId: 2n,
  claimedSeverity: 4,
  commitHash: '0x' + '00'.repeat(32),
  encryptedCID: 'ipfs://QmTestCID',
  stake: 250000000n,
  status: 2, // Resolved
  finalSeverity: 4,
  isValid: true,
  commitBlock: 100n,
  hunterWallet: '0x' + '11'.repeat(20),
}

const mockArbitrationData = {
  bugId: 1n,
  stateImpactCID: 'ipfs://QmStateCID',
  validationRequestHash: new Uint8Array(32),
  jurors: [4n, 5n, 6n],
  commitHashes: [new Uint8Array(32), new Uint8Array(32), new Uint8Array(32)],
  revealedSeverities: [4n, 4n, 3n],
  revealed: [true, true, true],
  revealCount: 3n,
  commitDeadlineBlock: 150n,
  revealDeadlineBlock: 200n,
  phase: 3,
}

function renderPage() {
  return renderWithProviders(<SubmissionDetailPage />, {
    route: '/submissions/1',
    path: '/submissions/:bugId',
  })
}

describe('SubmissionDetailPage', () => {
  it('renders submission heading', () => {
    mockGetSubmission.mockReturnValue(new Promise(() => {}))
    mockGetArbitration.mockReturnValue(new Promise(() => {}))
    renderPage()
    expect(screen.getByText('SUBMISSION #1')).toBeInTheDocument()
  })

  it('shows loading state', () => {
    mockGetSubmission.mockReturnValue(new Promise(() => {}))
    mockGetArbitration.mockReturnValue(new Promise(() => {}))
    renderPage()
    expect(screen.getByText('LOADING SUBMISSION...')).toBeInTheDocument()
  })

  it('renders submission metadata when loaded', async () => {
    mockGetSubmission.mockResolvedValue(mockSubmission)
    mockGetArbitration.mockResolvedValue(mockArbitrationData)
    renderPage()

    await waitFor(() => {
      expect(screen.getByText('250.0 USDC')).toBeInTheDocument()
    })
  })

  it('renders pipeline stages', async () => {
    mockGetSubmission.mockResolvedValue(mockSubmission)
    mockGetArbitration.mockResolvedValue(mockArbitrationData)
    renderPage()

    await waitFor(() => {
      expect(screen.getByText('PIPELINE STATUS')).toBeInTheDocument()
    })

    expect(screen.getByText('COMMITTED')).toBeInTheDocument()
    expect(screen.getByText('DISPUTED')).toBeInTheDocument()
    expect(screen.getByText('ARBITRATING')).toBeInTheDocument()
  })

  it('renders valid verdict for resolved submission', async () => {
    mockGetSubmission.mockResolvedValue(mockSubmission)
    mockGetArbitration.mockResolvedValue(mockArbitrationData)
    renderPage()

    await waitFor(() => {
      expect(screen.getByText('FINAL VERDICT')).toBeInTheDocument()
    })

    expect(screen.getByText(/VALID — CRITICAL/)).toBeInTheDocument()
  })

  it('renders invalid verdict', async () => {
    const invalidSubmission = { ...mockSubmission, isValid: false, finalSeverity: 0, status: 2 }
    mockGetSubmission.mockResolvedValue(invalidSubmission)
    mockGetArbitration.mockResolvedValue(null)
    renderPage()

    await waitFor(() => {
      expect(screen.getByText('INVALID / REJECTED')).toBeInTheDocument()
    })
  })

  it('renders jury votes when arbitration data present', async () => {
    mockGetSubmission.mockResolvedValue(mockSubmission)
    mockGetArbitration.mockResolvedValue(mockArbitrationData)
    renderPage()

    await waitFor(() => {
      expect(screen.getByText('ARBITER VOTES')).toBeInTheDocument()
    })

    expect(screen.getByText('3 / 3 REVEALED')).toBeInTheDocument()
  })
})
