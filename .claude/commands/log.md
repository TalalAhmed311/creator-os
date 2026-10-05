---
description: Log a posted piece's stats into brain/content-log.csv (the learning loop)
argument-hint: <project-id> <url>
---
Arguments: `$ARGUMENTS`

1. Ask the owner (one message) for whatever isn't given: platform, views, average watch % (reels), likes, comments, saves, shares, any notes.
2. `.venv/bin/python -m harnesses.studio.content_log add <project-id> --url <url> --platform <p> --views N --avg-watch N --likes N --comments N --saves N --shares N --notes "..."`
3. Link the stats to the project record: `.venv/bin/python -m core.memory remember "<project-id> on <platform>: <views> views, <avg watch>% avg watch, <saves> saves" --kind lesson --tags performance,<pillar>,<hook_type>`
4. If the command says 5 posts have been logged (or a multiple of 5), act as the **strategist**: run `harnesses.studio.content_log analyze`, write findings with numbers to lessons (`core.memory remember ... --kind lesson`), and give the owner up to 3 weekly suggestions (e.g. "your failure-story hooks get 2× watch time"). Propose promotions for anything seen ≥3× (never edit brain/ without a yes).
5. For AI Explained episodes, ask the series-producer to mark the episode `posted` in `brain/series-bible.md`.
