---
description: Log a published post (alias of /hq-log) — links its draft and starts daily metrics
argument-hint: <account | project-id> <url>
---
Arguments: `$ARGUMENTS`

The content log now lives in the HQ harness (database-backed, per account, every platform). Run the `/hq-log` flow with
these arguments (`.claude/commands/hq-log.md`). If a project id was given instead of an account, find its draft:
`./studio write list --json` (match `project_id`) and use that draft's account and id.
