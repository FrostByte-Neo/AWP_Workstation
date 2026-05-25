# AWP Workstation

Agent-native AWP workstation skill and supporting documentation.

## Verification

Run the repository verification entrypoint from the repo root:

```bash
make verify-workstation
```

This is the same verification command used by CI. For the full project overview,
CLI reference, and maintainer runbook, see
[`awp-workstation-skill/SKILL.md`](awp-workstation-skill/SKILL.md).

## Primary Entrypoints

The workstation is centered around a small set of operator commands:

```bash
python3 awp-workstation-skill/scripts/start-workstation.py
python3 awp-workstation-skill/scripts/workstation-status.py --brief
python3 awp-workstation-skill/scripts/workstation-status.py --actions-only
python3 awp-workstation-skill/scripts/workstation-status.py --timeline
python3 awp-workstation-skill/scripts/run-workstation.py --mode autopilot
python3 awp-workstation-skill/scripts/review-epoch.py
python3 awp-workstation-skill/scripts/workstation-monitor.py --full
```

`workstation-status.py` supports `--brief`, `--actions-only`, `--timeline`,
`--monitor`, and `--full`. `workstation-monitor.py` evaluates reminder type,
dedupe, cooldown, quiet hours, and adapter-facing notification payloads.

## State Files

The workstation now maintains a unified cached state snapshot alongside the
existing run and review files:

- `runs/latest-run.json`
- `runs/active-processes.json`
- `runs/pending-confirmations.json`
- `runs/timeline.jsonl`
- `reviews/latest-review.json`
- `cache/workstation-status.json`
- `cache/workstation-monitor.json`
- `cache/workstation-state.json`

## Deployment Templates

Basic `cron` and `systemd` monitor templates live under
[`awp-workstation-skill/deploy/`](awp-workstation-skill/deploy/README.md).
Render them with:

```bash
python3 awp-workstation-skill/scripts/install-monitor-schedule.py --mode systemd --target-dir /tmp/awp-monitor
```
