---
name: awp-workstation
description: >
  Total-control skill for an AWP personal workstation. Use this when the user
  says "awp start", "start AWP", "help me use AWP", "workstation",
  "research WorkNet", "start working", "how much did I earn today", "pause",
  "resume", "only run Mine", "开始 AWP", "帮我用 AWP 赚钱", "开始工作",
  "研究 WorkNet", "今天赚了多少", "为什么失败", or asks for a plain-language
  operator for the full AWP network. This skill hides RootNet, WorkNet,
  skillURI, epoch, CLOB, and staking details behind a single conversational
  workflow: preflight, capability scan, playbook build, execution, and review.
---

# AWP Workstation

This skill is the top-level operator for a personal AWP agent workstation.
Its job is to translate user intent into safe AWP actions without forcing the
user to understand protocol internals.

## Operating contract

- Speak in plain language first. The user should hear what the workstation will
  do, not protocol jargon.
- Never ask for a private key, seed phrase, or wallet password.
- Use `awp-wallet` as the local work wallet bridge when wallet access is needed.
- Treat all asset-moving, staking, voting, allocation, and irreversible actions
  as confirmation-gated.
- Generate install actions only for official skill URIs under
  `github.com/awp-worknet/*`, and show the action before execution.
- If a runnable skill comes from a third-party or unverified source, explain the
  risk and wait for user confirmation before installing or executing it.
- Browser UI is optional. Core flows must work from terminal and JSON outputs.

## Trigger phrases

Primary trigger phrases include:

- `awp start`
- `start AWP`
- `开始 AWP`
- `帮我用 AWP 赚钱`
- `workstation`
- `研究 WorkNet`
- `start working`
- `开始工作`
- `今天赚了多少`
- `为什么失败`

## Default workflow

1. Run `python3 scripts/start-workstation.py`.
2. If the wallet or registration path is incomplete, follow the returned safe
   next action.
3. When the user asks a free-form status question such as `今天赚了多少`,
   `为什么失败`, `暂停`, `继续`, `只跑 Mine`, or `不要动资金`, run
   `python3 scripts/workstation-status.py --query "<user question>"`.
4. When you need proactive reminder judgement, quiet-hours handling, cooldown
   behaviour, or adapter-facing notification payloads, run
   `python3 scripts/workstation-monitor.py`.
5. Run `python3 scripts/workstation-preflight.py --json` when you need the raw
   preflight contract.
6. Run `python3 scripts/scan-worknets.py`.
7. Pick a worknet, then run `python3 scripts/build-playbook.py --worknet <id>`.
8. Start the loop with `python3 scripts/run-workstation.py --mode autopilot`.
9. At the end of an epoch or task window, run `python3 scripts/review-epoch.py`.

To refresh official upstream source snapshots into workstation-owned cache, run
`python3 scripts/refresh-sources.py`.

To look up one stable topic bundle from the local encyclopedia, run
`python3 scripts/query-knowledge.py --topic <key>`.

To resolve one protocol term such as `RootNet`, `epoch`, or `CLOB`, run
`python3 scripts/query-glossary.py --term <term>`.

To inspect one source key and everything derived from it, run
`python3 scripts/query-source.py --source-key <key>`.

To inspect or execute the best available registration path, run
`python3 scripts/register-agent.py` or `python3 scripts/register-agent.py --execute`.

To answer one user-facing workstation question in plain-language JSON, run
`python3 scripts/workstation-status.py --query "<question>"`.

To produce a proactive monitor payload for reminders or external notification
bridges, run `python3 scripts/workstation-monitor.py`. Use `--read-only` for a
cheap cached check, `--force` when the caller wants a notification even if the
status digest has not changed, and `--full` when the caller also needs the full
status payload.

To inspect or persist workstation defaults such as preferred WorkNet or
non-financial autopilot mode, run `python3 scripts/workstation-preferences.py`.

To cache the latest official live WorkNet scan, run
`python3 scripts/sync-live-worknets.py`.

To inspect one installed or managed skill runtime, run
`python3 scripts/inspect-skill.py --skill-key <key>`.

## Mine runtime bootstrap

Mine requires Python 3.10+; Python 3.11 is the preferred runtime. On systems
where `python3` is older, bootstrap the managed Mine checkout with:

```bash
env PYTHON_BIN=/usr/bin/python3.11 bash ./scripts/bootstrap.sh
```

When `python3.11` is available on `PATH`, workstation-generated Mine bootstrap
commands should set `PYTHON_BIN` automatically. After bootstrap, Mine probes
should run through the checkout venv, for example:

```bash
./.venv/bin/python scripts/run_tool.py agent-status
./.venv/bin/python scripts/run_tool.py agent-control status
```

## References

Read these on demand instead of bloating this file:

- `references/source-map.md`
  Use this first when you need to know which upstream docs and local repos are
  trustworthy.
- `references/protocol-overview.md`
  Use this when you need a plain-language model of RootNet, WorkNet, staking,
  emission, or the AWP API surface.
- `references/worknet-profiles.md`
  Use this when the user asks which WorkNet to run, what is safe to automate,
  or why a worknet is not yet runnable.
- `references/encyclopedia.md`
  Use this when you need the workstation's stable human-readable AWP knowledge
  layer instead of raw upstream docs.
- `references/generated/knowledge-catalog.json`
  Use this when another agent or script needs the workstation's current
  machine-readable source catalog, skill registry, safety rules, and worknet
  summaries.
- `references/generated/source-facts.json`
  Use this when you need the workstation's locally-derived facts extracted from
  official AIPs and skill docs.
- `references/generated/source-evidence.json`
  Use this when you need to inspect the provenance, locator, and stability of a
  derived claim.
- `references/generated/topic-dossiers.json`
  Use this when you need operator-ready dossiers for protocol components and
  worknets.
- `references/generated/glossary.json`
  Use this when you need the workstation's canonical AWP term dictionary.
- `references/generated/coverage-audit.json`
  Use this when you need the workstation's current view of which encyclopedia
  capabilities are covered, partial, or still missing.
- `cache/official-live-worknets.json`
  Use this when you need the most recent live official WorkNet scan cached by
  `sync-live-worknets.py`.
- `references/evidence-model.md`
  Use this when you need to understand how source inventory, facts, evidence,
  and dossiers fit together.
- `references/generated/source-snapshot.json`
  Use this when you need the latest fetched copy status of official upstream
  AWP documents.

## Local state

The workstation state root defaults to `~/.awp-workstation/`.

For testing or sandboxed runs, override it with `AWP_WORKSTATION_HOME`.

Expected subdirectories:

- `cache/` for worknet scans and source inventory
- `skills/` for installation records
- `playbooks/` for generated work plans
- `runs/` for loop records and confirmation queues
- `reviews/` for epoch reviews
- `user/` for risk preference and operator defaults

Important state files:

- `cache/preflight.json`
- `cache/capability-scan.json`
- `cache/source-inventory.json`
- `cache/knowledge-catalog.json`
- `cache/workstation-monitor.json`
- `skills/install-status.json`
- `skills/*-dependency-sync.json`
- `runs/latest-run.json`
- `runs/pending-confirmations.json`

## Upstream drift policy

- Upstream AWP sites and repos are sources, not the workstation interface.
- Keep the workstation's JSON contracts stable even when upstream skills change.
- When upstream changes, update the source map and the internal catalog first.
- Prefer derived summaries in `references/` over copying upstream prose into the
  conversational flow.
