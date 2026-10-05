---
description: Research Desk — discover new creators, refresh numbers, review candidates (the creator database)
argument-hint: discover <niche> [platform] | refresh | review | show <handle> | track|drop <handle> | import <doc.md>
---
Arguments: `$ARGUMENTS`

Load the `content-research` skill first (Operation 2).

- `discover <niche> [platform]` → **creator-scout** agent; report the best candidates.
- `refresh` → **creator-scout** refreshes tracked creators (snapshots + `./studio research post refresh --tracked`).
- `review` → `./studio research creators list --status candidate` → recommend track/drop, then apply only what the owner approves.
- `show <handle>` → `./studio research creators show <handle> [--platform p]` and summarise.
- `track|drop <handle>` → `./studio research creators track|drop <handle> --why "…"` (owner asked, so just do it).
- `import <doc.md>` → `./studio research import-seed <doc.md>` and report counts.

Always end with the database state: `./studio db stats` (creators, snapshots, posts).
