# 2026-09-30_bip-day-1-laid-off-building

One folder per video. Drop your files here:

| Put this | In |
|---|---|
| Camera video (phone footage, one file) | `raw/` |
| Mic recording (separate mic, one file) | `raw/` |
| B-roll / screen recordings | `raw/broll/` |
| Screenshots, photos, logos | `raw/images/` |

Then run `./studio edit 2026-09-30_bip-day-1-laid-off-building` (or `/studio-edit 2026-09-30_bip-day-1-laid-off-building`). It finds the camera and mic in `raw/` on its own.
Files in `raw/` are never modified.

Everything else is made for you:
- `plan.json`, `script.md`: the plan and the script to read
- `edl.json`: the edit (also editable in `./studio web`)
- `work/`: intermediate files (transcript, cleaned audio, frames); safe to delete, it is rebuilt
- `out/`: finished files (`final.mp4`, `cover.png`, `caption.txt`, `project.fcpxml`)
