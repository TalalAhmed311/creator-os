---
description: HQ — turn a post that worked into drafts for your other accounts (IG ↔ LinkedIn ↔ X), reshaped per platform
argument-hint: <post-url | draft-id> [to: linkedin,x,instagram]
---
Arguments: `$ARGUMENTS`

Load `content-ops` (Repurpose) and `platform-writing`.

1. Find the post: `./studio hq posts --json` (score vs the account's median). Below 1.5× → say so and ask whether to repurpose anyway.
2. Targets: from the arguments, else every other active account.
3. For each target: `./studio write new <account> --format <best format for that platform> --title "…" --idea "repurpose of <url>"
   --ref-url <url> --insights <ids the original used>` and run the `/write` flow (hooks → owner picks → validate).
4. Show all drafts together; the owner approves each.
