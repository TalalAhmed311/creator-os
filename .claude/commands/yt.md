---
description: Download a YouTube (or other) video, or just its audio
argument-hint: <url> [audio]
---
Arguments: `$ARGUMENTS`

1. If the owner wants to study it (transcript, hooks, pacing), use `/ref` instead. If they want only part of it, use `/clip`. Nothing is ever deleted unless the owner asks.
2. Run `./studio yt <url>` (add `--audio-only` if they said audio/mp3; `--out <folder>` if they named one, e.g. `projects/<id>/raw/broll/`). Default folder: `videos/`.
3. Never save into `assets/music/`. If it is clearly someone else's music or content, remind the owner in one line to only use what they have rights to.
4. Reply with the path, duration and size (`ffprobe`) in ≤2 lines.
