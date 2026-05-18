# OTA Updates & Error-Report Auto-Fix Loop

How code gets onto the device, and how errors flow back without
needing inbound SSH, a VPN, or port forwarding.

The device only ever makes **outbound** HTTPS / SSH connections.

---

## OTA pull

`fishfluencer-sync.timer` fires `fishfluencer-sync.service` every
15 minutes. That service runs the `github_sync` module, which fetches
`origin/main`, fast-forwards if there are new commits, and restarts
the main service.

```mermaid
sequenceDiagram
  autonumber
  participant Timer as systemd timer<br/>(every 15 min)
  participant Sync as github_sync
  participant GH as GitHub repo
  participant Svc as fishfluencer.service

  Timer->>Sync: start
  Sync->>GH: git fetch origin main
  alt new commits
    GH-->>Sync: commits ahead
    Sync->>Sync: git merge --ff-only
    Sync->>Svc: systemctl restart fishfluencer
    Svc-->>Sync: started
  else up to date
    GH-->>Sync: no changes
    Sync-->>Timer: noop
  end
```

Constraints:

- **Fast-forward only.** If the local branch has diverged the sync
  refuses to merge — prevents an on-device hand-edit from being
  silently overwritten.
- A failed restart triggers the error path below.

---

## Error report + auto-fix

Any uncaught exception in the orchestrator funnels through
`ErrorLogPusher`, which writes a sanitized JSON file to
`error_reports/`, commits it on a `error-report/*` branch, and pushes.
That push triggers a GitHub Action that drafts a fix PR.

```mermaid
sequenceDiagram
  autonumber
  participant Orch as Orchestrator
  participant Err as ErrorLogPusher
  participant GH as GitHub repo
  participant Act as auto-fix.yml<br/>(GitHub Action)
  participant Agent as Coding agent
  participant Human as Reviewer

  Orch->>Err: report_error(exc, context)
  Err->>Err: redact secrets / paths
  Err->>GH: git checkout -b error-report/<ts>-<hash>
  Err->>GH: git add error_reports/<id>.json
  Err->>GH: git commit & push origin error-report/<ts>-<hash>

  GH->>Act: push event matches paths:<br/>error_reports/*.json
  Act->>Agent: dispatch with traceback context
  Agent->>Agent: read repo, propose patch
  Agent->>GH: open PR against main

  GH-->>Human: PR notification
  Human->>GH: review, merge (or close)

  Note over GH,Orch: next 15-min sync pulls the merged fix<br/>and restarts the service
```

Key properties:

- **Humans approve every merge.** The coding agent only opens PRs; it
  cannot self-merge.
- **No secrets leave the device.** Sanitization strips env vars,
  absolute paths, and API key fragments before the JSON is committed.
- **Closed loop.** Once a fix is merged into `main`, the next OTA
  pull (≤ 15 min later) deploys it and restarts the service. The
  device does not need any inbound access at any point.

---

## Network surface summary

| Direction | Endpoint | Purpose |
|---|---|---|
| Out | `api.anthropic.com` | Post generation (text only) |
| Out | `github.com` (SSH) | OTA pull, error report push |
| Out | `api.github.com` | Used by GitHub Actions only |
| Out | Social platform API host | Post publishing |
| **In** | **none** | No listening ports required |

If your network policy blocks one of the outbound hosts the device
will degrade gracefully: failed posts/syncs are logged and retried at
the next scheduled tick.
