# Worknet Profiles

Last reviewed: 2026-05-20

This file is the workstation's stable summary layer for AWP jobs. It does not
replace upstream specs. It translates them into operator-facing defaults.

## Current live Base IDs

- Reviewed against official live AWP queries on 2026-05-20.
- Active canonical IDs currently resolve to:
  Mine `845300000002`, Predict `845300000003`, Gov `845300000010`,
  Community `845300000011`, KYA `845300000012`, TMR `845300000013`,
  Ardi `845300000014`.
- Gov, Community, KYA, TMR, and Ardi also currently show older pending
  predecessor entries in the official API; the workstation should prefer the
  active IDs above.

## Mine

- Status: active on the public AWP worknet page
- User-facing job: collect, clean, and structure public web data
- Default role: operator
- Automation fit: high
- Primary loop: discover URLs, dedupe, crawl, clean, extract schema fields,
  submit, heartbeat
- What success looks like: accepted submissions, low duplication, clean worker
  health, stable heartbeat
- Main risks: auth churn, dataset mismatch, platform throttling, long-running
  crawler cost
- Local evidence: `/root/.nanobot/workspace/mine`

## Predict

- Status: active on the public AWP worknet page
- User-facing job: submit original price predictions with reasoning
- Default role: strategist or observer
- Automation fit: medium through the official `predict-agent` runtime
- Primary loop: read market context, gather price signals, write unique
  reasoning, submit orders, track settlement quality
- What success looks like: low reasoning repetition, healthy rate limit usage,
  good alpha capture
- Main risks: duplicate reasoning, overtrading, thin market context, and the
  1000 AWP eligibility gate before live submissions
- Local evidence: no local skill found in this workstation

## KYA

- Status: supporting identity and delegated-staking service
- User-facing job: verify the human or social identity behind an agent, then
  bind reward and staking rights safely
- Default role: identity tool
- Automation fit: guided, one-shot
- Primary flow: choose agent address, run attestation or KYC, set recipient or
  delegate only with explicit confirmation
- Main risks: signing the wrong payload, confusing agent and owner addresses
- Local evidence: `/root/.nanobot/workspace/kya-skill`

## Ardi

- Status: public official operator page available
- User-facing job: solve riddles, commit answers, reveal, and inscribe when
  selected
- Default role: event-driven operator
- Automation fit: medium after install
- Primary flow: preflight, fund Base gas, satisfy the stake path, follow the
  runtime's next-command journal, stop at the mint cap
- Main risks: Base gas depletion, missing stake eligibility, committing outside
  the round window
- Known public fact: the official operator page references worknet
  `845300000014`
- Local evidence: no local skill found in this workstation

## Gov

- Status: public official operator page available
- User-facing job: express weekly worknet value views through stake, allocation,
  vote, and trade
- Default role: governor
- Automation fit: supervised
- Primary flow: lock AWP, allocate power to GovNet, vote in the weekly window,
  trade if desired, review settlement
- Main risks: governance and trading both move value, so every write action
  must be confirmed
- Local evidence: no local skill found in this workstation

## TMR

- Status: active via official live AWP query, but public operator docs are thin
- User-facing job: not yet stable enough to summarize beyond official
  discovery and skill URI
- Default role: observer until the official skill is inspected locally
- Automation fit: manual-only for now
- Workstation behavior: expose the canonical ID and official skill URI, but do
  not auto-run the work loop yet

## Community

- Status: active via official live AWP query, but public operator docs are thin
- User-facing job: not yet stable enough to summarize beyond official
  discovery and skill URI
- Default role: observer until the official skill is inspected locally
- Automation fit: manual-only for now
- Workstation behavior: expose the canonical ID and official skill URI, but do
  not auto-run the work loop yet
