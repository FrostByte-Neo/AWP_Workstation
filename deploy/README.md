# AWP Workstation Monitor Deployment Templates

This directory contains simple templates for scheduling
`scripts/workstation-monitor.py`.

Replace these placeholders before use:

- `__REPO_ROOT__`: absolute path to this repository
- `__PYTHON__`: Python interpreter path
- `__STATE_ROOT__`: workstation state root

Included templates:

- `cron/awp-workstation-monitor.cron`
- `systemd/awp-workstation-monitor.service`
- `systemd/awp-workstation-monitor.timer`

You can render these templates with:

```bash
python3 scripts/install-monitor-schedule.py --mode systemd --target-dir /tmp/awp-monitor
python3 scripts/install-monitor-schedule.py --mode cron --target-dir /tmp/awp-monitor-cron
```

The default templates emit a `codex-heartbeat` delivery and mark the digest as
delivered. Switch the adapter or add webhook/email arguments if your deployment
needs a different notification path.
