import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import { renderWithProviders } from '../test/helpers'
import BountiesPage from './BountiesPage'

vi.mock('../config', () => ({
  getProvider: vi.fn(),
}))

const mockGetBountyCount = vi.fn()
const mockGetBounty = vi.fn()

vi.mock('ethers', async () => {
  const actual = await vi.importActual('ethers')
  const realEthers = (actual as { ethers: Record<string, unknown> }).ethers
  return {
    ...actual,
    ethers: {
      ...realEthers,
      Contract: class MockContract {
        getBountyCount = mockGetBountyCount
        getBounty = mockGetBounty
      },
    },
  }
})

beforeEach(() => {
  vi.clearAllMocks()
})

describe('BountiesPage', () => {
  it('renders the heading', () => {
    mockGetBountyCount.mockResolvedValue(0n)
    renderWithProviders(<BountiesPage />)
    expect(screen.getByText('BOUNTIES')).toBeInTheDocument()
  })

  it('shows loading state', () => {
    mockGetBountyCount.mockReturnValue(new Promise(() => {}))
    renderWithProviders(<BountiesPage />)
    expect(screen.getByText('LOADING BOUNTIES...')).toBeInTheDocument()
  })

  it('shows empty state when no bounties', async () => {
    mockGetBountyCount.mockResolvedValue(0n)
    renderWithProviders(<BountiesPage />)
    await waitFor(() => {
      expect(screen.getByText('NO ACTIVE BOUNTIES')).toBeInTheDocument()
    })
  })

  it('renders bounties in a table', async () => {
    mockGetBountyCount.mockResolvedValue(2n)
    mockGetBounty.mockImplementation((id: number) => {
      const bounties: Record<number, unknown> = {
        1: {
          protocolAgentId: 1n,
          name: 'TestProtocol',
          totalFunding: 50000000000n,
          active: true,
        },
        2: {
          protocolAgentId: 1n,
          name: 'AnotherProtocol',
          totalFunding: 10000000000n,
          active: false,
        },
      }
      return Promise.resolve(bounties[id])
    })

    renderWithProviders(<BountiesPage />)

    await waitFor(() => {
      expect(screen.getByText('TestProtocol')).toBeInTheDocument()
    })

    expect(screen.getByText('AnotherProtocol')).toBeInTheDocument()
    expect(screen.getByText('50000.0 USDC')).toBeInTheDocument()
    expect(screen.getByText('ACTIVE')).toBeInTheDocument()
    expect(screen.getByText('CLOSED')).toBeInTheDocument()
  })

  it('shows error state on fetch failure', async () => {
    mockGetBountyCount.mockRejectedValue(new Error('RPC error'))
    renderWithProviders(<BountiesPage />)

    await waitFor(() => {
      expect(screen.getByText(/FAILED TO LOAD BOUNTIES/)).toBeInTheDocument()
    })
  })
})
