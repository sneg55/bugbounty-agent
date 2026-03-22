import { describe, it, expect } from 'vitest'
import { roleFromURI } from './AgentsPage'

describe('roleFromURI', () => {
  it('detects PROTOCOL from URI', () => {
    expect(roleFromURI('ipfs://protocol-metadata')).toEqual({ label: 'PROTOCOL', color: '#a855f7' })
  })

  it('detects HUNTER from URI', () => {
    expect(roleFromURI('ipfs://hunter-metadata')).toEqual({ label: 'HUNTER', color: '#06b6d4' })
  })

  it('detects EXECUTOR from URI', () => {
    expect(roleFromURI('ipfs://executor-metadata')).toEqual({ label: 'EXECUTOR', color: '#f59e0b' })
  })

  it('detects ARBITER from URI (arbiter1)', () => {
    expect(roleFromURI('ipfs://arb1')).toEqual({ label: 'ARBITER', color: '#10b981' })
  })

  it('is case-insensitive', () => {
    expect(roleFromURI('ipfs://PROTOCOL-Agent')).toEqual({ label: 'PROTOCOL', color: '#a855f7' })
  })

  it('returns UNKNOWN for unrecognized URI', () => {
    expect(roleFromURI('ipfs://something-else')).toEqual({ label: 'UNKNOWN', color: '#6b7280' })
  })
})
