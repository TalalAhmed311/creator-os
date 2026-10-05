---
description: Download an Instagram reel/post (or its audio) into inspiration/
argument-hint: <url> [audio]
---
Arguments: `$ARGUMENTS`

1. Run `./studio ig <url>` (add `--audio-only` if they said audio/mp3). Default folder: `inspiration/`.
2. If it fails with a login/rate-limit error, retry once with `--browser chrome` (uses the owner's logged-in cookies) and say so.
3. It's for inspiration — remind the owner in one line not to repost someone else's content. To study hooks/pacing, offer `/ref <url>`.
4. Reply with the path, duration and size (`ffprobe`) in ≤2 lines.
