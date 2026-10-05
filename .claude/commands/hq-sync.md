---
description: HQ — collect metrics for your posts that are due (day 1/3/7/30) and list what needs numbers by hand
argument-hint: [--dry-run]
---
Arguments: `$ARGUMENTS`

Load the `content-ops` skill (Metrics).

1. `./studio hq sync $ARGUMENTS` → synced / pending.
2. Pending posts: read public counters from the post pages (built-in browser `get_page_text`) → `./studio hq metrics add <id> … --source browser`.
   For private numbers ask the owner once, one message, all posts listed (or ask for an analytics CSV export →
   `./studio hq metrics import <file> --source <platform>-export`).
3. If every account has new numbers since the last review and it's been ≥ 7 days, offer `/hq-review`.
4. If the daily job isn't installed (`./studio hq schedule`), mention once that `./studio hq schedule --install` runs this every morning.
