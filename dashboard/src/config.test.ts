import { describe, it, expect } from 'vitest'
import { RPC_URL, CHAIN_ID } from './config'
import { CONTRACT_ADDRESSES } from './contracts'

describe('config', () => {
  it('has Base Sepolia RPC URL', () => {
    expect(RPC_URL).toBe('https://sepolia.base.org')
  })

  it('has Base Sepolia chain ID', () => {
    expect(CHAIN_ID).toBe(84532)
  })
})

describe('contract addresses', () => {
  it('has all required contract addresses', () => {
    expect(CONTRACT_ADDRESSES.bountyRegistry).toBeTruthy()
    expect(CONTRACT_ADDRESSES.bugSubmission).toBeTruthy()
    expect(CONTRACT_ADDRESSES.arbiterContract).toBeTruthy()
    expect(CONTRACT_ADDRESSES.identityRegistry).toBeTruthy()
    expect(CONTRACT_ADDRESSES.reputationRegistry).toBeTruthy()
  })

  it('all addresses are valid hex format', () => {
    for (const [, addr] of Object.entries(CONTRACT_ADDRESSES)) {
      expect(addr).toMatch(/^0x[0-9a-fA-F]{40}$/)
    }
  })
})
