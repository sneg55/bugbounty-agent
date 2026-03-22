import { describe, it, expect } from 'vitest'
import { derivePipelineState } from './SubmissionDetailPage'

describe('derivePipelineState', () => {
  it('returns COMMITTED (0) for status=0', () => {
    expect(derivePipelineState(0, null)).toBe(0)
  })

  it('returns REVEALED (1) for status=1, no arbitration', () => {
    expect(derivePipelineState(1, null)).toBe(1)
  })

  it('returns REVEALED (1) for status=1, arbiter awaiting state impact', () => {
    expect(derivePipelineState(1, 0)).toBe(1)
  })

  it('returns ARBITRATING (3) for status=1, voting phase', () => {
    expect(derivePipelineState(1, 1)).toBe(3)
  })

  it('returns ARBITRATING (3) for status=1, revealing phase', () => {
    expect(derivePipelineState(1, 2)).toBe(3)
  })

  it('returns RESOLVED (4) for status=2', () => {
    expect(derivePipelineState(2, null)).toBe(4)
  })

  it('returns RESOLVED (4) for arbiter phase=3 (resolved)', () => {
    expect(derivePipelineState(1, 3)).toBe(4)
  })
})
