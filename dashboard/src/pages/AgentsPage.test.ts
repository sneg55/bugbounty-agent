import { describe, it, expect } from 'vitest'

const ROLE_DEFS = [
  { label: 'PROTOCOL', color: '#a855f7' },
  { label: 'HUNTER', color: '#06b6d4' },
  { label: 'EXECUTOR', color: '#f59e0b' },
  { label: 'ARBITER', color: '#10b981' },
]

function inferRole(agentId: number): { label: string; color: string } {
  const idx = (agentId - 1) % ROLE_DEFS.length
  return ROLE_DEFS[idx]
}

describe('inferRole', () => {
  it('assigns PROTOCOL to agent 1', () => {
    expect(inferRole(1)).toEqual({ label: 'PROTOCOL', color: '#a855f7' })
  })

  it('assigns HUNTER to agent 2', () => {
    expect(inferRole(2)).toEqual({ label: 'HUNTER', color: '#06b6d4' })
  })

  it('assigns EXECUTOR to agent 3', () => {
    expect(inferRole(3)).toEqual({ label: 'EXECUTOR', color: '#f59e0b' })
  })

  it('assigns ARBITER to agent 4', () => {
    expect(inferRole(4)).toEqual({ label: 'ARBITER', color: '#10b981' })
  })

  it('wraps around — agent 5 is PROTOCOL', () => {
    expect(inferRole(5)).toEqual({ label: 'PROTOCOL', color: '#a855f7' })
  })

  it('wraps around — agent 6 is HUNTER', () => {
    expect(inferRole(6)).toEqual({ label: 'HUNTER', color: '#06b6d4' })
  })
})
