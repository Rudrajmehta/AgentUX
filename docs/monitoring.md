# Monitoring Guide

AgentUX can run evaluations on a recurring schedule and alert you when usability regresses. This is useful for catching regressions after deploys, documentation changes, or CLI updates.

## Monitor Config Format

Monitors are defined as YAML files. Place them in a directory and point AgentUX at it.

```yaml
name: pricing-page
surface: browser
target: https://example.com/pricing
task: "Find the Pro plan price and the free trial CTA"
schedule: "0 */6 * * *"       # Every 6 hours
backend: openai
model: gpt-4.1
enabled: true
thresholds:
  aes_drop_pct: 10.0          # Alert if AES drops more than 10%
  success_rate_min: 0.8        # Alert if success rate drops below 80%
  max_steps: 20                # Alert if run exceeds 20 steps
tags:
  - production
  - pricing
```

### Required Fields

| Field     | Type   | Description                           |
|-----------|--------|---------------------------------------|
| `name`    | string | Unique monitor identifier              |
| `surface` | string | `browser`, `markdown`, `cli`, or `mcp` |
| `target`  | string | URL, file path, or command             |
| `task`    | string | Task description for the agent         |

### Optional Fields

| Field        | Default          | Description                             |
|--------------|------------------|-----------------------------------------|
| `schedule`   | `0 */6 * * *`   | Cron expression (UTC)                    |
| `backend`    | `openai`         | LLM backend to use                       |
| `model`      | `gpt-4.1`       | Model name                               |
| `enabled`    | `true`           | Whether the monitor is active            |
| `thresholds` | See below        | Alert thresholds                         |
| `tags`       | `[]`             | Tags for filtering                       |

### Default Thresholds

```yaml
thresholds:
  aes_drop_pct: 10.0
  success_rate_min: 0.8
  max_steps: 20
```

## Schedule Syntax

Monitors use standard 5-field cron expressions (minute, hour, day-of-month, month, day-of-week):

| Expression       | Meaning                  |
|------------------|--------------------------|
| `0 */6 * * *`   | Every 6 hours             |
| `0 9 * * 1-5`   | Weekdays at 9 AM          |
| `30 0 * * *`    | Daily at 12:30 AM         |
| `0 */12 * * *`  | Every 12 hours            |
| `0 8 * * 1`     | Mondays at 8 AM           |

## Managing Monitors

### Add a monitor from a YAML file

```bash
agentux monitor add monitors/pricing-monitor.yaml
```

### List active monitors

```bash
agentux monitor list
```

### Run a monitor manually

```bash
agentux monitor run pricing-page
```

### Disable a monitor

```bash
agentux monitor disable pricing-page
```

## CI Integration

Run monitors as part of your CI pipeline to catch UX regressions before merging:

```yaml
# In your GitHub Actions workflow
- name: Run AgentUX monitors
  run: |
    pip install agentux
    agentux monitor run pricing-page
```

The command prints alerts to stdout if thresholds are breached. You can check the exit output in your CI pipeline.

## Alerting

### Slack

Set the `AGENTUX_SLACK_WEBHOOK` environment variable or add it to your config:

```yaml
# ~/.config/agentux/config.yaml
alerts:
  slack_webhook: https://hooks.slack.com/services/T.../B.../xxx
```

### Discord

```yaml
alerts:
  discord_webhook: https://discord.com/api/webhooks/.../...
```

### Alert Severity Levels

| Severity   | Trigger                                          |
|------------|--------------------------------------------------|
| `info`     | Run exceeded max step count                       |
| `warning`  | AES dropped beyond threshold; success rate dipped |
| `critical` | Task failed outright; success rate below 50%      |

### Viewing Alerts

```bash
agentux alerts             # list unacknowledged alerts
agentux alerts ack <alert-id>
```

Or browse alerts interactively in the TUI:

```bash
agentux tui
```
