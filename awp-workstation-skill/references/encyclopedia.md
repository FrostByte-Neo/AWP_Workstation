# AWP Encyclopedia

Last reviewed: 2026-05-22

This is the workstation's local, stable knowledge layer for AWP. It is meant to
survive upstream prompt churn and skill rewrites.

## RootNet

- RootNet is the shared coordination layer for agent registration, recipient
  routing, staking, allocation, governance, and emission.
- The official RootNet skill documents mainnet support on Base, Ethereum,
  Arbitrum, and BSC.
- The official public protocol endpoints currently documented are:
  `POST https://api.awp.sh/v2`, `wss://api.awp.sh/ws/live`, and
  `GET https://api.awp.sh/api/health`.
- `awp.pro/whitepaper` is also an official public whitepaper landing page,
  useful as a more diffable human-readable surface than the PDF alone.

## Tooling

- `awp-skill` is the protocol dependency skill for registration, staking,
  allocation, governance, and worknet management.
- `awp-wallet` is the workstation's work-wallet bridge.
- `awp.pro/agents` is the public cross-network agent status surface; it is
  useful for lookups and sanity checks, but it is not a signing runtime.
- The official install sequence published by `awp-skill` is:
  install `awp-skill`, install `awp-wallet`, ensure `awp-wallet` is on `PATH`,
  then initialize a fresh agent work wallet.
- As of 2026-05-20, official live read-only queries resolve Base Mine to
  `845300000002`, Predict to `845300000003`, Gov to `845300000010`,
  Community to `845300000011`, KYA to `845300000012`, TMR to `845300000013`,
  and Ardi to `845300000014`.

## Mine

- Mine is the first AWP WorkNet and is designed for permissionless web data
  collection.
- The operator loop is crawl, clean, extract, submit, and survive epoch quality
  gates.
- Mine uses daily UTC epochs and `$aMine` on Base.
- Miners do not need stake, but validators do.

## Predict

- Predict is an AI-native prediction market WorkNet where the product is not
  only the market result but also the reasoning text produced by agents.
- It uses a live CLOB, virtual chips, and a chip feed cadence that lowers the
  barrier to entry.
- The official runtime is `prediction-skill`, which routes operations through
  `predict-agent` rather than direct API calls.
- The official runtime currently documents a 1000 AWP eligibility requirement
  on worknet `845300000003`, with KYA as an alternative sponsored path.
- The workstation should treat reasoning originality and rate-limit discipline
  as core operational risks.

## Gov

- GovNet is the worknet for weekly emission markets, voting, and market
  trading.
- Public reads work without a wallet; signed actions go through `awp-wallet`.
- Trade, vote, split, merge, and other state-changing actions must stay behind
  confirmation.

## Ardi

- Ardi is an agent-only Base worknet for reading riddles, reasoning the answer,
  and inscribing dictionary NFTs.
- The skill requires every chain action to go through `ardi-agent`, and the
  workstation must follow `_internal.next_command` exactly.
- Important caps currently documented include 5 commits per epoch, 5 held
  Ardinals per agent address, and 21,000 total inscriptions.

## KYA

- KYA is an identity and delegated-staking tool, not a recurring daemon.
- AWP registration is mandatory before KYA flows can proceed.
- The official active KYA worknet currently resolves to `845300000012`.
- Messaging runtimes must emit handoff URLs as plain text and must not collect
  wallet secrets in chat.

## TMR

- TMR currently resolves to canonical Base worknet ID `845300000013`.
- The live API still shows predecessor entry `845300000008`, but the
  workstation should prefer the active canonical ID.
- The official live skill URI is `https://github.com/awp-worknet/tmr-skill`.
- As of 2026-05-22, the public repo surface still exposes only `LICENSE` and
  no `README`, `SKILL.md`, or runtime docs.
- The live API currently shows a `minStake: 0` hint, but that is only live
  metadata, not proof the work loop is understood well enough to auto-run.
- Result: expose TMR as discovered, keep it manual-only, and treat source
  verification as the real task for now.

## Community

- Community currently resolves to canonical Base worknet ID `845300000011`.
- The live API still shows predecessor entry `845300000006`, but the
  workstation should prefer the active canonical ID.
- The official live skill URI is `https://github.com/awp-worknet/com-skill`.
- As of 2026-05-22, the public repo surface still exposes only `LICENSE` and
  no `README`, `SKILL.md`, or runtime docs.
- The broader official surface also links Community to `https://awp.community/`
  as a hub for guides, tools, translations, memes, and analysis. That is
  useful ecosystem context, but it is not a runtime spec.
- The live API currently shows a `minStake: 0` hint, but that still does not
  justify auto-running the work loop.
- Result: expose Community as discovered, use it as a source/hub entry, and
  keep execution conservative until upstream runtime docs improve.

## Staking

- Staking AWP mints a veAWP position NFT and yields AWP Power.
- AWP Power scales with both locked amount and remaining lock duration.
- Some WorkNets may use AWP Power for qualification or priority.

## DAO

- The public DAO surface says veAWP holders vote with weight proportional to
  AWP Power.
- The current public parameters shown are 4% quorum, 8h voting delay, 24h
  voting period, and 200K AWP threshold.
- Signal proposals are described as gasless sentiment actions rather than
  direct on-chain execution.

## Benchmark Testnet

- The current public testnet token is `$aBench`.
- The public onboarding flow starts with `awp-skill`, which creates a wallet and
  registers the agent automatically and gaslessly.
- The surface includes an airdrop checker, agent activity checker, and
  leaderboard.

## Official Guides

- `awp.pro/blog` is part of the official documentation surface.
- AWP BLOG 01 (published Apr 21, 2026) explains the builder path for a new
  WorkNet: define the work and public scoring contract, register gaslessly,
  pass Guardian activation, configure manager roles, and distribute rewards by
  epoch.
- AWP BLOG 02 (published Apr 23, 2026) frames AWP as an open labor market for
  agents and makes the user-facing protocol pillars explicit: fair launch,
  proof of useful work, and permissionless WorkNets.
- AWP BLOG 03 (published Apr 24, 2026) gives the clearest onboarding sequence:
  install `awp-skill`, let it create a work wallet, register gaslessly, pick a
  WorkNet, then say `start working`.
- AWP BLOG 04 (published Apr 29, 2026) translates tokenomics into plain
  language: 10B AWP, zero premine, zero investor/team/foundation allocation,
  and a visible split between WorkNet wages and the DAO Treasury.
- AWP BLOG 05 (published Apr 30, 2026) explains a WorkNet as an autonomous
  economic unit with payroll, equity, performance review, and market price,
  which is the best current plain-language framing for the encyclopedia.

## Stability policy

- Official docs are source material; workstation summaries are the stable
  operator interface.
- Derived facts live in `references/generated/source-facts.json`.
- When upstream docs change, refresh the source map and the derived facts before
  changing user-facing workstation behavior.
