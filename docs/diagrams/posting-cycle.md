# Posting Cycle — Sequence Diagram

What happens when the scheduler fires one of the entries in
`post_times` (default `["09:00", "17:00"]`). Mirrors
`FishFluencer._generate_and_post` in `src/main.py`.

---

## Happy path

```mermaid
sequenceDiagram
  autonumber
  participant Sched as schedule (cron-in-process)
  participant Orch as FishFluencer<br/>orchestrator
  participant DB as SQLite
  participant Sum as BehaviorSummarizer
  participant Claude as Claude API
  participant Pub as Publisher
  participant Plat as Social platform

  Sched->>Orch: tick at post_time (e.g. 09:00)
  Orch->>Sum: generate_summary(hours=12)
  Sum->>DB: SELECT behaviors, temps,<br/>snapshots WHERE ts >= now-12h
  DB-->>Sum: rows
  Sum-->>Orch: text summary (≤ a few KB)

  loop for each platform in config
    Orch->>Claude: messages.create(<br/>fish_profile + summary,<br/>text-only)
    Claude-->>Orch: cheeky post text
    Orch->>Pub: publish(platform, post)
    Pub->>Plat: POST /tweet (or equivalent)
    Plat-->>Pub: 200 OK, post_id
    Pub-->>Orch: post_id
    Orch->>DB: INSERT INTO posts<br/>(platform, content, summary, ts)
  end

  Orch-->>Sched: done
```

Key points:

- The Claude call payload is **text only**. No images, no base64, no
  signed URLs. The summary is generated entirely from SQLite rows.
- The fish persona (`primary_poster`) and its quirks come from
  `config/fish_profiles.yaml` — swapping the speaker is a config
  change, not code.
- Every post lands in the `posts` table along with the summary that
  produced it, so you can audit / regenerate offline.

---

## Failure path

```mermaid
sequenceDiagram
  autonumber
  participant Orch as FishFluencer<br/>orchestrator
  participant Claude as Claude API
  participant Err as ErrorLogPusher
  participant GH as GitHub repo

  Orch->>Claude: messages.create(...)
  Claude--xOrch: HTTP 5xx / timeout
  Note over Orch: caught in try/except<br/>around _generate_and_post
  Orch->>Err: report_error(exc,<br/>context={phase: "post_generation"})
  Err->>Err: sanitize traceback<br/>(strip env, paths, secrets)
  Err->>GH: git push error-report/<ts>-<hash><br/>(adds error_reports/*.json)
  GH-->>Err: branch created
  Note over GH: triggers .github/workflows/auto-fix.yml<br/>(see ota-error-loop.md)
```

A failed cycle does **not** crash the main loop — the orchestrator
keeps capturing frames and the next `post_time` will retry from
scratch with a fresh 12-hour summary window.
