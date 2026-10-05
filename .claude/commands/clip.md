---
description: Cut an exact part of a video (file or URL) and keep its audio; deletes nothing unless asked
argument-hint: <file|url> <from> <to> [mp3|wav|m4a] [keep video] [delete original]
---
Arguments: `$ARGUMENTS`

1. Resolve the source: a URL, or a file name (look in the active project's `raw/`, then `videos/`). Parse the from/to times the owner gave (e.g. "1:23 to 1:45", "from 83s for 20s" → to = from + 20).
2. Audio format: what they named, else mp3 (suggest wav if it goes into an edit). `--keep-video` if they want the trimmed video too.
3. **Never delete unless the owner said so in this message.** "Dump/delete the original" → `--delete-original` (local files only). URL sources are downloaded into `references/<id>/` and **kept**; clips go to `references/<id>/clips/`. Removing a reference is a separate, explicit step (`/ref rm <id>`). Files in `projects/*/raw/` are never deleted by the tool.
4. Run `./studio clip <source> --from <a> --to <b> --audio <fmt> [--keep-video] [--delete-original]`.
5. Reply with the output path(s) and length; say whether the original was deleted.
