# Bounty Validation Rules

On-chain enforcement in `BountyRegistry.createBounty()`:

```solidity
require(tiers.low > 0, "Low tier must be > 0");
require(tiers.medium >= tiers.low, "Tiers must be ordered: medium >= low");
require(tiers.high >= tiers.medium, "Tiers must be ordered: high >= medium");
require(tiers.critical >= tiers.high, "Tiers must be ordered: critical >= high");
require(funding >= tiers.critical, "Funding must cover at least one critical payout");
```

## Acceptance Payout

`acceptSubmission(bugId, severity)` pays at the provided severity, NOT the claimed severity. The protocol agent passes `min(claimed, estimated)` to prevent overpay.

## Auto-Accept on Timeout

If the protocol doesn't respond within 72 hours, anyone can call `autoAcceptOnTimeout(bugId)` which pays at the hunter's claimed severity. The keeper service handles this automatically.
