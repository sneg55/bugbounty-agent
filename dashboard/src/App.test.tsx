import { describe, it, expect } from 'vitest'
import { screen } from '@testing-library/react'
import App from './App'
import { render } from '@testing-library/react'

describe('App', () => {
  it('renders the header with app name', () => {
    render(<App />)
    expect(screen.getByText('BUGBOUNTY.AGENT')).toBeInTheDocument()
  })

  it('renders navigation links', () => {
    render(<App />)
    expect(screen.getByText('BOUNTIES')).toBeInTheDocument()
    expect(screen.getByText('AGENTS')).toBeInTheDocument()
    expect(screen.getByText('LIVE FEED')).toBeInTheDocument()
  })

  it('renders footer with version', () => {
    render(<App />)
    expect(screen.getByText('BUGBOUNTY.AGENT v0.1.0-alpha')).toBeInTheDocument()
  })

  it('renders footer with network indicator', () => {
    render(<App />)
    // "BASE SEPOLIA" appears in both protocol status table and footer
    const matches = screen.getAllByText('BASE SEPOLIA')
    expect(matches.length).toBeGreaterThanOrEqual(1)
  })

  it('renders home page hero text', () => {
    render(<App />)
    // The h1 contains AUTONOMOUS<br/>SECURITY
    const heading = screen.getByRole('heading', { level: 1 })
    expect(heading).toHaveTextContent(/AUTONOMOUS/)
    expect(heading).toHaveTextContent(/SECURITY/)
  })

  it('renders stat cards on home page', () => {
    render(<App />)
    expect(screen.getByText('ACTIVE BOUNTIES')).toBeInTheDocument()
    expect(screen.getByText('TOTAL SUBMISSIONS')).toBeInTheDocument()
    expect(screen.getByText('TOTAL PAID')).toBeInTheDocument()
  })

  it('renders protocol status table', () => {
    render(<App />)
    expect(screen.getByText('PROTOCOL STATUS')).toBeInTheDocument()
    expect(screen.getByText('NETWORK')).toBeInTheDocument()
    expect(screen.getByText('COMMIT-REVEAL')).toBeInTheDocument()
    expect(screen.getByText('JUROR QUORUM (3)')).toBeInTheDocument()
  })
})
