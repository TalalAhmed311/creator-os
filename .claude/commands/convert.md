---
description: Convert a video (or audio) file to mp3 / wav / m4a
argument-hint: <file…> [mp3|wav|m4a]
---
Arguments: `$ARGUMENTS`

1. Resolve the file(s). If only a name is given, look in the active project's `raw/` (and `raw/broll/`) first, then `projects/*/raw/`, then `videos/`. If several match or none, ask for the path.
2. Format = the one named in the arguments, else **mp3**. If the file is going into the Edit Bay (mic recording, voice-over), suggest **wav** instead (lossless).
3. Run `./studio convert <file…> --to <fmt>` (add `--out <dir>` if the owner named a folder). Outputs go next to the input; files under `projects/*/raw/` go to that project's `work/` — never write into `raw/`.
4. Reply with the output path(s), duration and size (`ffprobe`), in ≤2 lines.
