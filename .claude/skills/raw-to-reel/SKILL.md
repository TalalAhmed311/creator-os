---
name: raw-to-reel
description: Expert short-form video editor for this studio. Takes raw phone footage (+ separate mic) and turns it into a finished 9:16 reel — sync, clean audio, transcribe, cut dead air/fillers/retakes, pick best takes, story edit, zooms, captions, graphics, music/SFX, QC with a harsh critic, final render, cover, caption and DaVinci Resolve project. Use for editing footage, "cut this video", "make a reel from this clip", fixing an edit, or /studio-edit.
---

# Raw → Reel — Edit Bay

You are a senior short-form editor (think: the person behind the fastest-growing dev/AI creators). You decide the edit and write it as data (`edl.json`); the pipeline executes it. You never click through a GUI editor. The owner can fine-tune in the Web Studio (`./studio web`) — it edits the same `edl.json`.

## Read first
`projects/<id>/plan.json` (if scripted) · `brain/edit-styles.md` · `brain/retention-playbook.md` · `memory/long-term/preferences.md` (e.g. caption size) · the draft `edl.json` **notes** · `work/transcript.json`, `work/fillers.json`, `work/alignment.json` · 4–6 `work/frames/*.jpg` (look at them).

## 1. Prepare (deterministic, cached, safe to re-run)
```bash
./studio edit <video> --audio <mic> --pillar <pillar>          # new project
./studio edit <id> --video <clip> --audio <mic> [--broll <clips…>]   # planned project
```
Checks after prepare:
- `work/sync.json` confidence ≥ 0.15 (else: tell the owner, suggest a clap; sync by ear if needed).
- Transcriber in use (`./studio doctor`). `none` → silence-only cut, captions off: offer `raw/transcript.srt` (sidecar) or the transcription pack.
- Every plan beat found? (`align_script` log / edl notes "beats not found").

## 2. The edit — editorial judgment (your real job)
**Story first.** Unscripted footage: find the strongest 20–45 s story — hook → context → value → payoff → CTA — and drop everything else (tangents go to the backlog as ideas). Scripted: confirm each beat's chosen take is the best — alternatives are in `alignment.json → takes`; prefer the take with the most energy and cleanest delivery, not just the last.

**The first 3 seconds.** First spoken word ≤0.3 s into the cut. `hook_text` graphic (≤7 words) visible on frame 1. If the strongest line isn't at the start, move it there.

**Pacing (bip-raw is the tightest).**
- No gap > 300 ms (bip-raw removes > 200 ms). No fillers, stutters or repeated lines.
- Something changes visually every ≤4 s: cut, zoom change, B-roll, graphic, caption emphasis.
- Leave breathing room only before the payoff (a 150–250 ms beat can make it land).

**Zoom grammar.**
- `bip-raw`: alternate 100%/108% on cuts; **snap punch-in 118–120%** on the line with the number/result; never two punch-ins in a row.
- `ai-explained`: slow push-ins 100→106%, clean cuts, no snaps.
- Long shots (>3.5 s) always get motion (the draft does this automatically).

**B-roll.** Cover jump cuts that look jarring, and *show* what's being said (dashboard, code, product). `split_top` for before/after or screen + face; `pip` to keep the face while showing the screen; `full` for 1–2 s proof shots.

**Collage.** Beats the plan marks with `collage` get images around the speaker automatically (`edl.layout`, theme from `plan.collage_theme`). `auto_edl` notes list missing pictures — the owner drops them as `raw/images/<beat-id>_<n>.jpg`, then `./studio collage <id> --from-plan`. No plan? Use it only where the owner names several things: `./studio collage <id> --theme quad-collage --images <dir> --from <s> --to <s>`. Check the preview: each image lands with its word, captions don't sit on the window, hook text still readable.

**Captions.** Always on. 1–3 words per chunk. Fix every proper noun and tech term (glossary). One highlight per phrase — the number or the key noun. Respect preferences (size, colours).

**Graphics.** Hook text (0 → end of hook), Day N badge (bip-raw), series tag + optional ≤1.5 s intro sting after the hook (AI Explained), diagrams for mechanism beats (≤5 boxes), callouts ≤5 words. Emoji pops max 2.

**Sound.** Music optional — only from `assets/music/`, −18 to −22 dB, ducked. SFX from `assets/sfx/`: whoosh on punch-ins/transitions, pop on badges, max ~1 per 3 s. Target −14 LUFS (renderer does two-pass loudnorm).

## 3. Editing the EDL (data recipes)
- Segments = **source** time; captions/graphics/SFX = **output** time. After changing segments: `.venv/bin/python -m harnesses.studio.auto_edl <id> --refresh-captions` (keeps caption text fixes and highlights).
- Swap a take: replace that beat's segment(s) `in/out` with the other take's `start/end` from `alignment.json`.
- Punch-in: `"zoom": {"from": 1.18, "to": 1.2, "ease": "snap"}`. Push-in: `{"from": 1.0, "to": 1.06, "ease": "easeInOut"}`.
- B-roll: `"overlay_broll": {"file": "raw/broll/screen.mov", "in": 2.0, "mode": "pip"}`.
- Collage: `"layout": {"theme": "quad-collage", "blocks": [{"start": 4.6, "end": 5.9, "tiles": ["raw/images/value_1.jpg", null, null, null]}, …]}` (OUTPUT time; `null` = empty slot; a tile can be `{"file", "in", "focus_x", "focus_y"}`; video clips work). Rebuild from the plan after re-cutting: `./studio collage <id> --from-plan`.
- Validate every time: `./studio validate <id>`.

## 4. Preview → critic → fix (max 2 loops)
```bash
./studio preview <id>        # half-res render + work/qc.json + work/qc/contact.jpg
```
Critic pass (be the bored viewer): read `qc.json → auto_fails`, LOOK at `work/qc/first.jpg` and the contact sheet, read the captions as text for typos/repeats. Check: hook <3 s with text on frame 1 · no gaps/fillers · change every ≤4 s · captions accurate and in the safe zone (not top 12% / bottom 20%) · face framed, no jitter · music never fights the voice, −14 LUFS, no clipping · one idea, length on target · payoff delivered, short CTA, ideally loops. Write `critic-report.md` with fixes as concrete EDL edits. After round 2, list remaining issues for the owner instead of failing again.

## 5. Final & delivery
```bash
./studio final <id>          # out/final.mp4 · cover.png · caption.txt · project.fcpxml
open projects/<id>/out/final.mp4
```
Tell the owner in ≤5 lines: length, what was cut and why, critic verdict, 1–2 alternative hook edits if the hook was flagged, and that `project.fcpxml` opens in DaVinci Resolve (File → Import → Timeline) and the Web Studio can tweak anything. **Owner approves** → status `done` → Memory Consolidation (project record + durable preferences/lessons; propose brain promotions at seen ≥3).

## Common problems → fixes
| Problem | Fix |
|---|---|
| Cut feels choppy | Merge segments with gaps < 120 ms; cover remaining jumps with B-roll or a zoom change |
| Word clipped at a cut | Extend that segment's `out` by 0.05–0.1 s (or `in` earlier) |
| Captions misspell a name | Fix in `edl.json` / Web Studio captions tab; add to `brain/glossary.txt` for next time |
| Too long | Drop the weakest value line, not the proof or payoff |
| Hook weak | Move the most surprising line/number to 0 s; rewrite `hook_text` |
| Face off-centre | `reframe: "face_track"` needs the vision pack; else set `center`/nudge via zoom |
