# AWP Source Map

Last reviewed: 2026-05-20

This workstation keeps its own stable interface and treats upstream AWP docs,
sites, and skill repos as inputs. The goal is to keep workstation behavior
stable even when upstream wording, repo layout, or recommended prompts change.

## Source tiers

Tier 1 is official public network context.

- `https://awp.pro/`
  High-level protocol entry point and quickstart.
- `https://awp.pro/worknet`
  Public worknet directory. Current public page shows Mine and Predict as
  active worknets.
- `https://awp.pro/aip`
  AIP registry for worknet-level specs.
- `https://github.com/awp-core/awp-skill`
  RootNet skill covering wallet onboarding, registration, staking, allocation,
  governance, worknet management, and the official JSON-RPC endpoint.
- `https://api.awp.sh/v2`
  Official live JSON-RPC surface used by the workstation to resolve current
  worknet IDs, skills URIs, and statuses.
- `https://gov.works/`
  Official GovNet public entry and official `github.com/awp-worknet/gov-skill`
  reference.
- `https://api.gov.works/v1/markets`
  Official GovNet live market feed showing current worknet-share symbols and
  phase timing.
- `https://www.ardinals.com/agents`
  Official Ardi operator page and official
  `github.com/awp-worknet/ardi-skill` reference.
- `https://kya.link/verify/human`
  Official KYA verification page and official
  `https://github.com/awp-worknet/kya-skill` reference.
- `https://raw.githubusercontent.com/awp-worknet/mine-skill/main/SKILL.md`
  Raw official Mine skill spec.
- `https://raw.githubusercontent.com/awp-worknet/prediction-skill/main/SKILL.md`
  Raw official Predict skill spec.
- `https://github.com/awp-worknet/tmr-skill`
  Official live skill URI currently returned for TMR.
- `https://github.com/awp-worknet/com-skill`
  Official live skill URI currently returned for Community.

Tier 2 is local machine evidence.

- `/root/.nanobot/workspace/awp-wallet`
  Local clone of the AWP wallet CLI with `SKILL.md`, `README.md`, docs, tests,
  and scripts.
- `/root/.nanobot/workspace/mine`
  Local clone of the Mine skill and runtime with operational docs, schemas, and
  agent-facing JSON wrappers.
- `/root/.nanobot/workspace/kya-skill`
  Local clone of the KYA skill with stdlib Python scripts and tests.
- `/root/.nanobot/workspace/awp-data`
  Local data workspace, currently weakly documented.

Tier 3 is workstation-owned derived knowledge.

- `references/protocol-overview.md`
- `references/worknet-profiles.md`
- `references/encyclopedia.md`
- `references/evidence-model.md`
- `references/generated/knowledge-catalog.json`
- `references/generated/capability-catalog.json`
- `references/generated/source-inventory.json`
- `references/generated/skill-registry.json`
- `references/generated/source-facts.json`
- `references/generated/source-evidence.json`
- `references/generated/topic-dossiers.json`
- `references/generated/glossary.json`
- `references/generated/coverage-audit.json`
- `references/generated/source-snapshot.json`
- `references/generated/official-live-worknets.json`
- `cache/official-live-worknets.json`
- machine-readable catalog inside `scripts/awp_workstation_lib.py`

## Trust and install policy

- Auto-install is restricted to `github.com/awp-worknet/*`.
- `awp-core/awp-skill` is treated as protocol-official and safe to depend on,
  even though it is not under `awp-worknet/*`.
- Local third-party or non-allowlisted worknet skills can still be used, but
  only after an explicit risk explanation and user confirmation.

## Gaps to track

- No local Predict runtime is installed in this workstation.
- No local Gov skill was found in this workstation.
- No local Ardi skill was found in this workstation.
- No local TMR or Community skill clone is installed yet, and their public
  operator docs are still sparse.
- `awp-data` needs curation before it is useful as a workstation knowledge
  source.

## Maintenance rules

- Update this file before changing workstation defaults when upstream AWP
  changes.
- Keep upstream URLs and local paths together so future scans can compare them.
- Prefer adding one new source record over scattering the same knowledge across
  multiple files.
- After changing the library catalog, rerun `python3 scripts/export-knowledge.py`
  so the generated references stay aligned.
- After refreshing upstream source text or PDFs, rerun
  `python3 scripts/refresh-sources.py` and inspect the generated snapshot file.
