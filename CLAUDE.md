# creator-os

A harness of harnesses for the owner's content. Plan for the whole system: `docs/HARNESS_PLAN.md`.
Studio spec: `harnesses/studio/AI_STUDIO_PLAN.md`. This file is the short version of the rules.

## Layout
| Path | What |
|---|---|
| `core/` | shared by every harness: `common` (paths, Project, ffmpeg, JSON), `memory`, `providers/` (transcriber, face), `fetch/` (yt-dlp, Instagram), `media/` (convert, clip), `refs` (reference library), `schemas/` (plan/edl/carousel contracts), `cli` (`./studio`), `deps` (doctor) |
| `harnesses/studio/` | Edit Bay, Design Desk (`carousel/`), Web Studio (`webstudio/`), Remotion templates (`remotion/`) |
| `harnesses/research/`, `writer/`, `hq/` | planned — see `docs/HARNESS_PLAN.md` |
| `brain/`, `memory/`, `projects/`, `assets/`, `references/`, `plans/` | shared data at the repo root (unchanged) |

A harness may import `core`; `core` never imports a harness (except `core/cli.py`, which routes to them, and `core/deps.py`, which checks them).

## Principle
Claude is the editor's brain, not the mouse. Agents decide and write **structured data** (`plan.json`, `edl.json`, `carousel.json`); deterministic tools (`core/`, `harnesses/studio/`, its `remotion/` and `carousel/`) execute it. Never automate a GUI editor.

## Flows (slash commands in `.claude/commands/`)
| Command | Does |
|---|---|
| `/studio-setup` | one-time brand interview → `brain/brand-bible.md` |
| `/studio-week` | weekly content plan → `plans/<YYYY>-W<ww>.md` |
| `/studio-plan [pillar]` | Writers' Room → shoot package (hooks, script, shot list) |
| `/studio-edit <project or video> [mic]` | Edit Bay → `out/final.mp4`, cover, caption, fcpxml |
| `/carousel` | Design Desk → themed slides |
| `/log <project> <url>` | stats → `brain/content-log.csv` |
| `/convert <file> [mp3\|wav\|m4a]` | extract audio from a video (`./studio convert`) |
| `/yt <url> [audio]` | download a video or its audio into `videos/` (`./studio yt`) |
| `/clip <file\|url> <from> <to>` | cut an exact part, keep the audio (`./studio clip`) |
| `/ref <url>` · `/ref rm <id>` | reference library: download, transcribe, break down hooks/pacing (`./studio ref`) |
| `/remember`, `/recall`, `/studio-resume` | memory |
(`/plan` and `/resume` are Claude Code built-ins, hence the `studio-` prefix.)

## Expert skills (`.claude/skills/`) — load the matching one before doing the task
| Task | Skill |
|---|---|
| Weekly/monthly content plan, calendar, "what should I post" | `content-planning` |
| Reel idea, hooks, script, teleprompter | `reel-scripting` |
| Editing footage into a reel, fixing an edit | `raw-to-reel` |
| Resource lists, carousels, slide design | `resource-carousel` |
User-facing guide for all four: `INSTRUCTIONS.md`.

The main session acts as the **showrunner** (`.claude/agents/showrunner.md`) and delegates to the subagents in `.claude/agents/`. Only the main session talks to the owner.

## Hard rules
- **Never modify or delete anything in `projects/*/raw/`.** All work in `work/` and `out/`.
- Every flow starts with Memory Load and ends with Memory Consolidation (`core/memory.py`). Every task has `memory/working/<project_id>.md`; agents append, never overwrite.
- Contracts must validate before rendering: `.venv/bin/python -m harnesses.studio.validate projects/<id>`.
- Always render a low-res preview (`harnesses.studio.edit preview`) before the final render.
- Approval gates: owner picks the hook, approves the final, approves any change to `brain/`.
- `brain/` = expertise the owner controls (human-readable). `memory/` = experience. Propose promotions from memory → brain at seen ≥3; never edit `brain/` without a yes.
- Background images for carousels: backgrounds only, never generated text.
- Music is optional; never download music — use `assets/music/` only.
- **Delete nothing the owner didn't ask to delete** (downloads, references, originals). Show what would go, then wait for a yes.

## Interfaces & dependencies
- `./studio web` — the owner's browser editor (harnesses/studio/webstudio/); it edits the same edl.json / carousel.json, so re-read those files before changing them.
- `./studio help` — one entry point for every tool. `./studio doctor` — what's installed, which backends are active.
- Transcription and face tracking are **pluggable interfaces** (`core/providers/`), chosen in `studio.json` (`"auto"` = first available):
  transcriber `mlx-whisper | whisper-cpp | sidecar (raw/transcript.srt|vtt|json) | none`; face `mediapipe | opencv | center`.
  With `none`, the Edit Bay still works: cuts dead air by silence, captions off.
- Dependencies: `requirements/core.txt` (always) + optional packs `requirements/transcribe-mlx.txt`, `requirements/vision.txt` (OpenCV), `requirements/face-mediapipe.txt`
  (`scripts/setup.sh --with transcribe`). Never install torch — mlx-whisper goes in with `--no-deps`.

## Running tools
Python: `.venv/bin/python -m harnesses.studio.<tool> <project> …` (shared tools: `core.<tool>`, e.g. `core.memory`) (each tool has `--help`, caches in `work/`, is safe to re-run).
Timestamps: `edl.segments` = SOURCE time; captions/graphics/sfx = OUTPUT time. After editing segments: `.venv/bin/python -m harnesses.studio.auto_edl <id> --refresh-captions`.
Collage around the speaker: a plan beat with `collage.images` → `edl.layout` (themes in `brain/video-themes/`, rules in `brain/edit-styles.md`); rebuild with `./studio collage <id> --from-plan`.
Tests: `.venv/bin/python -m pytest -q`. Setup check: `scripts/setup.sh`.

## Owner facts
English videos · TikTok (reels) + Instagram (reels + carousels) · phone camera + separate mic · music optional · Apple M5, 24 GB, macOS 26.0.
- On macOS 26.0 MLX's M5 GPU kernels don't load, so Whisper runs on CPU automatically (still ~seconds per clip). A macOS update should restore GPU.
- whisper-large-v3-turbo (MLX) is already in the Hugging Face cache — no download needed.
- Slow/flaky network: `scripts/setup.sh` retries; big wheels can be fetched with `curl -C -` into `.wheels/`.
