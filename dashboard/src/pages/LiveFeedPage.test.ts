import { describe, it, expect } from 'vitest'
import { ethers } from 'ethers'

// Re-implement formatEvent here since it's not exported.
// This tests the logic in isolation; keeps the production file untouched.
const SEVERITY_LABELS = ['INVALID', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL']

function formatEvent(eventName: string, args: ethers.Result): string {
  switch (eventName) {
    case 'BountyCreated':
      return `Bounty #${args[0]} created: "${args[2]}" — max ${ethers.formatUnits(args[3], 6)} USDC`
    case 'BugCommitted':
      return `Bug #${args[0]} committed to Bounty #${args[1]} by Agent #${args[2]}`
    case 'BugRevealed':
      return `Bug #${args[0]} revealed — CID: ${String(args[1]).slice(0, 30)}...`
    case 'StateImpactRegistered':
      return `State impact registered for Bug #${args[0]}`
    case 'JurySelected':
      return `Jury selected for Bug #${args[0]} — ${(args[1] as bigint[]).length} jurors`
    case 'VoteCommitted':
      return `Juror #${args[1]} committed vote for Bug #${args[0]}`
    case 'VoteRevealed':
      return `Juror #${args[1]} revealed vote for Bug #${args[0]}: severity ${args[2]}`
    case 'SubmissionResolved': {
      const severity = Number(args[1])
      const isValid = args[2]
      return `Bug #${args[0]} resolved — ${SEVERITY_LABELS[severity] || 'UNKNOWN'} severity, ${isValid ? 'valid' : 'invalid'}`
    }
    case 'PatchGuidance':
      return `Patch guidance issued for Bug #${args[0]}`
    default:
      return eventName
  }
}

describe('formatEvent', () => {
  it('formats BountyCreated', () => {
    const args = [1n, 2n, 'TestProtocol', 50000000000n, 1700000000n] as unknown as ethers.Result
    expect(formatEvent('BountyCreated', args)).toBe(
      'Bounty #1 created: "TestProtocol" — max 50000.0 USDC',
    )
  })

  it('formats BugCommitted', () => {
    const args = [5n, 1n, 3n, 4] as unknown as ethers.Result
    expect(formatEvent('BugCommitted', args)).toBe(
      'Bug #5 committed to Bounty #1 by Agent #3',
    )
  })

  it('formats BugRevealed with truncated CID', () => {
    const longCid = 'ipfs://QmLongCidThatShouldBeTruncatedBeyondThirtyCharacters'
    const args = [1n, longCid] as unknown as ethers.Result
    const result = formatEvent('BugRevealed', args)
    expect(result).toContain('Bug #1 revealed — CID:')
    expect(result).toContain('...')
  })

  it('formats StateImpactRegistered', () => {
    const args = [7n] as unknown as ethers.Result
    expect(formatEvent('StateImpactRegistered', args)).toBe(
      'State impact registered for Bug #7',
    )
  })

  it('formats JurySelected', () => {
    const args = [1n, [4n, 5n, 6n]] as unknown as ethers.Result
    expect(formatEvent('JurySelected', args)).toBe(
      'Jury selected for Bug #1 — 3 jurors',
    )
  })

  it('formats VoteCommitted', () => {
    const args = [1n, 4n] as unknown as ethers.Result
    expect(formatEvent('VoteCommitted', args)).toBe(
      'Juror #4 committed vote for Bug #1',
    )
  })

  it('formats VoteRevealed', () => {
    const args = [1n, 4n, 3] as unknown as ethers.Result
    expect(formatEvent('VoteRevealed', args)).toBe(
      'Juror #4 revealed vote for Bug #1: severity 3',
    )
  })

  it('formats SubmissionResolved valid CRITICAL', () => {
    const args = [1n, 4, true] as unknown as ethers.Result
    expect(formatEvent('SubmissionResolved', args)).toBe(
      'Bug #1 resolved — CRITICAL severity, valid',
    )
  })

  it('formats SubmissionResolved invalid', () => {
    const args = [2n, 0, false] as unknown as ethers.Result
    expect(formatEvent('SubmissionResolved', args)).toBe(
      'Bug #2 resolved — INVALID severity, invalid',
    )
  })

  it('formats PatchGuidance', () => {
    const args = [3n] as unknown as ethers.Result
    expect(formatEvent('PatchGuidance', args)).toBe(
      'Patch guidance issued for Bug #3',
    )
  })

  it('returns event name for unknown events', () => {
    const args = [] as unknown as ethers.Result
    expect(formatEvent('SomeUnknownEvent', args)).toBe('SomeUnknownEvent')
  })
})
