---
description: Edit Bay — raw footage (+ separate mic) → finished 9:16 reel, cover, caption and DaVinci Resolve project
argument-hint: <project-id | video path> [mic audio path]
---
**Load the `raw-to-reel` skill first** (`.claude/skills/raw-to-reel/SKILL.md`) — it holds the editing expertise (story, pacing, zooms, captions, sound, critic) this flow relies on.

You are the **showrunner** (read `.claude/agents/showrunner.md`) running the Edit Bay. Arguments: `$ARGUMENTS`

1. **Prepare** (deterministic, cached):
   `.venv/bin/python -m harnesses.studio.edit prepare <project-or-video> [--audio <mic>] [--pillar <pillar>]`
   (a video path creates a new project; a project id reuses its plan.json). It runs ingest → sync → clean → transcribe → silences → fillers → align → frames → face track → draft `edl.json`, updating working memory as it goes. Run Memory Load for the pillar into the working file (`core.memory load <pillar> --project <id>`).
   If `sync.json` confidence < 0.15, tell the owner and suggest a clap next time.
   Transcription goes through the pluggable Transcriber (`./studio doctor` shows which one is active). If it's `none`,
   the draft edl is cut by silence with captions off — tell the owner, and offer: drop `raw/transcript.srt` (sidecar)
   or install the transcription pack (`scripts/setup.sh --with transcribe`). The editor then works from frames + silences.
2. **Editor** agent refines `edl.json` (story selection / best takes / pacing / zooms / B-roll). Without a plan.json the editor also proposes the hook.
3. **Motion designer** (captions/graphics) and **sound designer** (music/SFX/loudness) — can run in parallel; both only touch their section of `edl.json`. Then `.venv/bin/python -m harnesses.studio.validate projects/<id>`.
4. **Preview**: `.venv/bin/python -m harnesses.studio.edit preview <id>` → `work/preview.mp4` + qc pack.
5. **Critic** reviews → `critic-report.md`. FAIL → route fixes to editor/motion/sound, preview again. **Max 2 revision loops**.
6. **Final**: `.venv/bin/python -m harnesses.studio.edit final <id>` → `out/final.mp4` (1080×1920, H.264/AAC, −14 LUFS), `out/cover.png`, `out/caption.txt`, `out/project.fcpxml`.
7. **Summarise** for the owner: length, what was cut and why (from working-memory decisions), critic verdict, and 1–2 alternative hook edits if the critic flagged the hook. Then `open projects/<id>/out/final.mp4`. Mention `out/project.fcpxml` opens in DaVinci Resolve (File → Import → Timeline).
8. **Owner approval gate.** Feedback → log it (`feedback`), fix, re-render. Approved → set status `done` and run **Memory Consolidation** (showrunner §). If the plan came from `/studio-plan`, this is the same working-memory file — consolidate once, here.
