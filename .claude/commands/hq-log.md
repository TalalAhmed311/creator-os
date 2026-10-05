---
description: HQ — log a post you published (links the draft, starts the 1/3/7/30-day metrics)
argument-hint: <account> <url> [draft-id] [numbers…]
---
Arguments: `$ARGUMENTS`

Load the `content-ops` skill.

1. Account: from the arguments, else infer from the URL's platform (`./studio hq accounts`); ask only if two accounts share the platform.
2. Draft: given, else the newest `approved` draft for that account (`./studio write list --account <a> --status approved`) — confirm in
   one line ("Linking to draft #12 'Curio 100 users' — right?") only if there are several candidates.
3. `./studio hq log <account> <url> --draft <id> [--views N --likes N …]` (numbers only if the owner gave them).
4. Tell the owner: logged, which draft/project, when the next metric checkpoints are (day 1, 3, 7, 30). For AI Explained episodes, ask
   the series-producer to mark the episode `posted` in `brain/series-bible.md`.
