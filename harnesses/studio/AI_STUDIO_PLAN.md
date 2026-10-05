# Personal AI Content Studio — Build Plan

> **Layout note (creator-os restructure, 2026-10-05):** `pipeline/` was split into `core/` (shared: common, memory, providers, schemas, fetch, media, refs, cli) and `harnesses/studio/` (Edit Bay tools, `carousel/`, `webstudio/`, `remotion/`). Paths below are updated; the spec is otherwise unchanged — except the content log: `/log` + `content-log.csv` are replaced by the HQ harness (`/hq-log`, database-backed, per account). System plan: `docs/HARNESS_PLAN.md`.

> **For Claude Code:** This is the full spec for a local, Claude-powered content studio on macOS. Read it end to end, then build it phase by phase (see §11). Ask the owner the open questions in §12 before Phase 1. Keep every step runnable and tested before moving on.

---

## 1. What we're building

A content studio that lives in one folder on my Mac. It has two halves:

1. **Writers' Room (pre-production).** A team of agents plans content *with me*: they interview me quickly, then produce shoot-ready scripts with hooks, shot lists, and captions.
2. **Edit Bay (post-production).** I drop in raw video/audio. The agents transcribe it, pick the best takes, cut, add captions, motion, zooms, sound and music, and hand back a finished vertical reel. They also export a project file I can tweak in DaVinci Resolve.

Plus a **Design Desk** that turns resource lists into themed harnesses/studio/carousel/collage posts.

### My personal brand: 3 content pillars

| Pillar | Format | Vibe |
|---|---|---|
| **Build in Public** — building my product openly | Reels (talking head + screen recordings) | Raw, energetic, "Day N" progress, honest wins and failures |
| **AI Explained** — a series on how AI things work | Reels as a numbered series | Polished, animated diagrams, clear "aha" per episode |
| **Useful Resources** — tools, repos, papers, courses | Carousel / collage posts | Clean, themed backgrounds (e.g. math-equation wall, chalkboard, blueprint, terminal) |

### Core principle
**Claude is the editor's brain, not the mouse.** Agents decide the edit and write it as structured data (an edit plan). Deterministic tools (ffmpeg, Remotion, Python) execute that plan. Never automate clicking through a GUI editor.

---

## 2. Environment (macOS, Apple Silicon assumed)

Install via Homebrew / pip / npm. Create `scripts/setup.sh` that installs and verifies everything.

| Need | Tool | Notes |
|---|---|---|
| Orchestration | **Claude Code** | Subagents in `.claude/agents/`, commands/skills in `.claude/` |
| Media processing | **ffmpeg** (`brew install ffmpeg`) | Cutting, concat, audio filters, encoding |
| Transcription | **mlx-whisper** (Apple Silicon, fast), fallback **whisper.cpp** | Must output **word-level timestamps**. Model: `large-v3-turbo` default |
| Silence / VAD | **silero-vad** or ffmpeg `silencedetect` | Detect dead air |
| Audio cleanup | ffmpeg `afftdn` / `arnndn` + `loudnorm` (target −14 LUFS) | Optional upgrade: DeepFilterNet |
| Audio sync (separate mic) | Python cross-correlation (`numpy`/`scipy`) on camera audio vs mic audio | Returns offset in ms |
| Face tracking / reframe | **mediapipe** face detection | 16:9 → 9:16 crop that follows the face, smoothed |
| Scene / shot detection | **PySceneDetect** | For B-roll and screen recordings |
| Captions + motion graphics | **Remotion** (Node/React) | Animated captions, callouts, diagrams, series intro, "Day N" badge |
| Carousel rendering | HTML/CSS templates → PNG via **Playwright** | Crisp text over backgrounds |
| Background images | Owner-supplied photos, or an image-gen connector (Higgsfield MCP is available) | Image models are bad at text: generate backgrounds only, never text |
| NLE export | **OpenTimelineIO** → FCPXML | Opens in DaVinci Resolve / Final Cut |
| Python | 3.11+, venv in `.venv/` | `requirements.txt` pinned |

Hardware note: Apple Silicon Macs run mlx-whisper and Remotion rendering fine. Use `h264_videotoolbox` for fast hardware encoding when available.

---

## 3. Folder structure

```
ai-studio/
├── CLAUDE.md                     # Studio rules for Claude Code (short; points to brain/)
├── AI_STUDIO_PLAN.md             # This file
├── .claude/
│   ├── agents/                   # Subagent definitions (see §5)
│   └── commands/                 # /studio-setup, /plan, /edit, /carousel, /log
├── brain/                        # The content-creator brain (see §4)
│   ├── brand-bible.md
│   ├── hooks-library.md
│   ├── retention-playbook.md
│   ├── pillars/
│   │   ├── build-in-public.md
│   │   ├── ai-explained.md
│   │   └── resources.md
│   ├── series-bible.md
│   ├── edit-styles.md
│   ├── carousel-themes/          # one folder per theme pack
│   └── content-log.csv
├── memory/                       # Memory engine (see §14)
│   ├── working/                  # Short-term: one live .md per running task
│   └── long-term/                # Permanent: what the studio has learned
│       ├── index.md
│       ├── preferences.md
│       ├── lessons.md
│       ├── ideas-backlog.md
│       ├── pillars/
│       └── projects/
├── projects/                     # One folder per piece of content
│   └── 2026-09-26_bip-day-12/
│       ├── brief.md              # Interview answers
│       ├── plan.json             # Script + hooks + shot list (contract, §6)
│       ├── script.md             # Human-readable + teleprompter version
│       ├── raw/                  # My footage/audio (never modified)
│       ├── work/                 # Intermediates: synced audio, transcript, frames
│       ├── edl.json              # Edit decision list (contract, §6)
│       ├── critic-report.md
│       └── out/                  # final.mp4, cover.png, caption.txt, project.fcpxml
├── core/                         # shared tools: common, memory, providers, schemas, fetch, media, refs
├── harnesses/studio/             # Python CLI tools (see §7)
│   ├── remotion/                 # Remotion project (captions, motion, intros)
│   └── carousel/                 # HTML templates + render script
├── assets/                       # music/, sfx/, fonts/, logos/, broll/
└── scripts/setup.sh
```

**Rule:** files in `raw/` are never modified. All work happens in `work/` and `out/`.

---

## 4. The content-creator brain (`brain/`)

These files are the studio's expertise. Every agent reads the relevant ones before acting. Write them with real, specific guidance (starter content below), and keep them editable by me.

### `brand-bible.md` (filled in by `/studio-setup` interview)
- Who I am, what I'm building, who my audience is (skill level, what they want)
- Tone of voice, phrases I use, words I never use
- Language(s) I speak in videos
- Platforms and handles, posting cadence
- Visual identity: colors, fonts, caption style

### `hooks-library.md`
The first 1–3 seconds decide whether someone keeps watching. Every hook needs **spoken line + on-screen text + a visual in the first frame**. Hook types with templates:
- **Result first:** "This took me 3 hours instead of 3 weeks."
- **Curiosity gap:** "Nobody explains this part of how ChatGPT works."
- **Contrarian:** "Stop using RAG for this."
- **Callout:** "If you're building your first SaaS, watch this."
- **Mistake / failure:** "I just broke production. Here's why."
- **Progress marker:** "Day 12 of building X in public."
- **Question:** "How does an AI actually 'see' an image?"
- **Visual pattern break:** start mid-action, show the screen, move toward the camera.
Rules: no "Hey guys", no intro, no logo first. Hook text ≤ 7 words on screen.

### `retention-playbook.md`
- Structure: **Hook (0–3s) → Context in one line → Value, delivered fast → Payoff → Loop or CTA**
- Length: 20–45s default. The AI series may go to 60–90s if every second earns its place.
- **One idea per reel.** Extra ideas become extra reels.
- **Pattern interrupt every 2–4s:** cut, punch-in zoom, caption pop, B-roll, on-screen graphic, or SFX.
- Remove every breath gap > ~250ms, filler words (um, uh, like, you know), false starts, repeated lines.
- Captions always on (most people watch muted). 1–3 words at a time, center-lower third, keyword highlighted.
- Loopable ending: the last line flows back into the first when possible.
- End with one clear CTA at most (follow for the series / comment a word / save this).

### `pillars/*.md`: one playbook per pillar
- **build-in-public.md:** story angles (win, failure, decision, metric, behind-the-scenes), "Day N" continuity, always show the screen/product, honesty over polish, a CTA to follow the journey.
- **ai-explained.md:** one concept per episode; analogy first, then mechanism, then "why it matters"; animated diagram required; recurring intro sting (≤1.5s); episode tag "AI Explained #N"; tease next episode.
- **resources.md:** carousel structure (see §9), who it's for, why each resource is worth it, a save-worthy final slide.

### `series-bible.md`
Series name, format, recurring intro, episode list (planned / shot / posted), running callbacks, visual style rules.

### `edit-styles.md`: editing presets per pillar
| Preset | Cuts | Zooms | Captions | Graphics | Music |
|---|---|---|---|---|---|
| `bip-raw` | Tight jump cuts | Punch-in 110–120% on key lines | Bold, word-by-word pop, highlight numbers | "Day N" badge, screen-recording auto-zoom, before/after split | Low energetic bed, ducked −18dB under voice |
| `ai-explained` | Clean cuts | Gentle slow push-ins | Clean, keyword highlight in brand color | Remotion diagrams (boxes, arrows, data flow), callout labels, series tag | Subtle ambient, ducked |
| `talking-head-basic` | Jump cuts | Alternate 100%/115% every cut | Standard | None | Optional |

### `content-log.csv`
`date, project_id, pillar, hook_type, hook_text, length_s, platform, url, views, avg_watch_pct, likes, comments, saves, shares, notes`. Filled by `/log`. The Strategist reads it to learn which hooks and angles work for me.

---

## 5. The agent team (`.claude/agents/*.md`)

Each agent is a Claude Code subagent with a clear role, the brain files it must read, its inputs and its output. Agents communicate through files in the project folder, not chat.

| Agent | Role | Reads | Writes |
|---|---|---|---|
| **showrunner** | My single point of contact. Routes work, runs the flow, keeps me informed, never skips my approval gates. | Everything | Project folder scaffolding |
| **strategist** | Runs the quick interview (3–5 questions max), finds the angle, checks the content log for what's worked. | brand-bible, pillar playbook, content-log | `brief.md` |
| **scriptwriter** | Writes the script in my voice. | brief, brand-bible, retention-playbook, pillar playbook | `plan.json`, `script.md` |
| **hook-specialist** | Produces 3 distinct hook options (different hook types), each with spoken line, on-screen text and first-frame visual. | hooks-library, content-log | hooks section of `plan.json` |
| **series-producer** | Owns AI Explained continuity: episode numbers, intro, callbacks, next-episode tease. | series-bible | Updates `series-bible.md`, series fields in `plan.json` |
| **editor** | Aligns transcript to script, picks best takes, builds the cut, pacing, zooms and B-roll placements. | plan.json, transcript, frames, edit-styles, retention-playbook | `edl.json` |
| **motion-designer** | Captions style, keyword highlights, callouts, diagrams, badges, intro sting. | edl.json, edit-styles, brand-bible | Remotion props in `edl.json` |
| **sound-designer** | Music pick, ducking, SFX on cuts/pops/transitions, loudness. | edl.json, assets/ | Audio section of `edl.json` |
| **critic** | Harsh viewer. Reviews sampled frames + transcript of the render against the checklist (§10). Sends back fixes (max 2 revision loops). | Rendered output, checklist | `critic-report.md` |
| **resource-curator** | Verifies resources (links live, still maintained, actually useful), writes one-line value per item. | brief, resources playbook | Carousel content JSON |
| **carousel-designer** | Picks/creates theme, lays out slides, gets backgrounds. | carousel-themes, brand-bible | Slide PNGs |

---

## 6. Data contracts (the most important part for reliability)

Validate both with JSON Schema (`core/schemas/`). Every tool reads/writes these, nothing freeform.

### `plan.json`
```json
{
  "project_id": "2026-09-26_bip-day-12",
  "pillar": "build-in-public",
  "edit_preset": "bip-raw",
  "target_length_s": 35,
  "platforms": ["instagram", "tiktok"],
  "series": { "name": null, "episode": null },
  "hooks": [
    { "type": "result_first", "spoken": "...", "on_screen": "...", "first_frame_visual": "..." }
  ],
  "chosen_hook": 0,
  "beats": [
    { "id": "hook", "spoken": "...", "on_screen": "...", "broll": null },
    { "id": "context", "spoken": "...", "on_screen": null, "broll": "screen recording of dashboard" },
    { "id": "value", "spoken": "...", "graphic": "diagram: request -> model -> response" },
    { "id": "payoff", "spoken": "..." },
    { "id": "cta", "spoken": "Follow — day 13 tomorrow." }
  ],
  "shot_list": ["Talking head, eye level, window light", "Screen: new onboarding flow", "Hands on keyboard"],
  "caption_draft": "...",
  "hashtags": ["..."]
}
```

### `edl.json` (edit decision list)
```json
{
  "project_id": "...",
  "output": { "width": 1080, "height": 1920, "fps": 30 },
  "sources": { "cam": "raw/cam.mp4", "mic": "raw/mic.wav", "mic_offset_ms": 412 },
  "segments": [
    {
      "src": "cam", "in": 12.34, "out": 15.80,
      "beat": "hook",
      "reframe": "face_track",
      "zoom": { "from": 1.0, "to": 1.15, "ease": "easeOut" },
      "overlay_broll": null
    }
  ],
  "captions": {
    "style": "bip-raw",
    "words": [ { "text": "three", "start": 0.12, "end": 0.40, "highlight": true } ]
  },
  "graphics": [
    { "type": "badge", "text": "Day 12", "start": 0.0, "end": 2.5 },
    { "type": "diagram", "spec": "request -> model -> response", "start": 14.0, "end": 19.0 }
  ],
  "audio": {
    "music": { "file": "assets/music/energetic-01.mp3", "gain_db": -18, "duck": true },
    "sfx": [ { "file": "assets/sfx/whoosh.wav", "at": 3.2 } ],
    "loudness_lufs": -14
  }
}
```
Timestamps in `segments` are **source time**. Caption/graphic times are **output time**. The render step maps between them.

---

## 7. Pipeline tools (`harnesses/studio/` + `core/`)

Small, single-purpose Python CLIs. Each one is idempotent, caches its output in `work/`, and logs what it did.

| Script | Does |
|---|---|
| `ingest.py <project>` | Probe media (ffprobe), copy/link into `raw/`, detect separate audio |
| `sync_audio.py` | Cross-correlate mic vs camera audio → `mic_offset_ms` |
| `clean_audio.py` | Denoise + loudness normalize → `work/voice.wav` |
| `transcribe.py` | mlx-whisper, word timestamps → `work/transcript.json` (+ `.srt`) |
| `detect_silence.py` | VAD → `work/silences.json` |
| `detect_fillers.py` | Mark um/uh/like/false starts from transcript |
| `align_script.py` | Fuzzy-align transcript to `plan.json` beats; find retakes per beat; default pick = last complete take, flag alternatives |
| `extract_frames.py` | Sample frames (e.g. 1 fps + scene changes) → `work/frames/` for agents to look at |
| `face_track.py` | mediapipe → smoothed crop path for 9:16 → `work/crop_path.json` |
| `rough_cut.py` | Apply `edl.json` segments with ffmpeg → `work/rough.mp4` |
| `render.py` | Pass rough cut + edl to Remotion for captions/graphics, mix audio → `out/final.mp4` |
| `export_nle.py` | edl.json → OpenTimelineIO → `out/project.fcpxml` |
| `make_cover.py` | Pick strongest frame + hook text → `out/cover.png` |
| `qc_frames.py` | Sample frames from final render for the critic |

---

## 8. Commands (user-facing flows)

### `/studio-setup` (run once)
Strategist interviews me (~10 questions) and writes `brand-bible.md`. Creates the series bible skeleton and one default carousel theme.

### `/plan [pillar]`: Writers' Room
1. Showrunner asks which pillar (if not given) and creates the project folder.
2. Strategist asks **3–5 quick questions**:
   - *Build in public:* What did you build or break? What was hard? Any number or result? What's next?
   - *AI Explained:* Which concept? The one "aha" the viewer should leave with? Episode number?
   - *Resources:* What resources? Who are they for? Which theme? (→ hands off to `/carousel`)
3. Hook specialist → 3 hook options. **I pick one** (approval gate).
4. Scriptwriter → `script.md` (read-aloud version + teleprompter version, short lines), shot list, B-roll list, caption draft.
5. Series producer updates the series bible if it's an AI Explained episode.
6. Deliver the shoot package and stop. Speed target: the whole planning session in under 10 minutes.

### `/edit <project or video path> [audio path]`: Edit Bay
1. Ingest → sync audio (if separate) → clean audio → transcribe → silences/fillers → frames.
2. If `plan.json` exists: align to script and pick the best takes. If not: the editor finds the strongest 20–45s story in the footage and proposes a hook from what was said.
3. Editor writes `edl.json` using the pillar's edit preset.
4. Motion designer adds captions/graphics. Sound designer adds music/SFX.
5. Render a quick **low-res preview** → critic reviews → fix loop (max 2).
6. Final render: `out/final.mp4` (1080×1920, H.264, AAC, −14 LUFS), `cover.png`, `caption.txt`, `project.fcpxml`.
7. Showrunner summarizes what was cut and why, and gives me 1–2 alternative hook edits if the critic flagged the hook.
8. `open out/final.mp4` so it plays on my Mac. Optionally open the fcpxml in DaVinci Resolve.

### `/carousel`: Design Desk
See §9.

### `/log <project> <url>`
I paste stats later. Appends to `content-log.csv`. The Strategist uses it to learn.

### Memory commands (see §14)
- `/remember <note>`: save something to long-term memory right now ("I hate yellow captions").
- `/recall <topic>`: search long-term memory and show what the studio knows.
- `/resume`: list unfinished tasks in `memory/working/` and continue one.

**Every flow (`/plan`, `/edit`, `/carousel`) starts with Memory Load and ends with Memory Consolidation (§14).**

---

## 9. Carousel / collage pipeline

1. Resource curator verifies each resource (link live, what it is, why it's worth it) and writes slide copy.
2. Structure: **Slide 1 = hook** ("7 free resources to actually understand LLMs") → **one resource per slide** (name, one-line value, who it's for, small screenshot/logo if available) → **last slide = save/follow CTA**.
3. Theme: I name one (e.g. "math wall"), give a photo, or ask the designer to propose 3.
4. Backgrounds: my photo, or generated via an image-gen connector (**background only, no text**). Darken/blur for readability.
5. Text and layout: HTML/CSS templates rendered to PNG with Playwright. This keeps text crisp and consistent.
6. Output sizes: 1080×1350 (Instagram 4:5) by default; 1080×1080 and a LinkedIn PDF export on request.
7. Save each new theme as a **theme pack** in `brain/carousel-themes/<name>/` (background style prompt, fonts, colors, template variant) so it's reusable.

Starter theme packs: `math-wall` (equations on a dark board, chalk-white text), `blueprint` (blue grid, white technical font), `terminal` (black, mono font, green accents), `clean-light` (brand colors, minimal).

---

## 10. Critic checklist (quality gate)

Fail = send back with specific fixes.
- [ ] Hook lands in < 3s. On-screen hook text is visible in the first frame.
- [ ] No gap > 300ms, no filler words, no repeated takes left in.
- [ ] Something changes visually at least every 4s.
- [ ] Captions are accurate (proper nouns/tech terms correct), readable, within safe zones (not under platform UI: avoid top ~12% and bottom ~20%).
- [ ] Face is framed well in 9:16 and the crop doesn't jitter.
- [ ] Music never fights the voice. Loudness ≈ −14 LUFS. No clipping.
- [ ] One idea only. Length within the target.
- [ ] Payoff delivered. CTA is short. The ending ideally loops.
- [ ] Matches the pillar's edit preset and brand.

Glossary for caption accuracy: keep `brain/glossary.txt` (my product name, tech terms like "RAG", "LLM", "Claude"). Feed it to Whisper as an initial prompt and use it to correct transcripts.

---

## 11. Build phases (build in order; each ends with a working demo)

**Phase 0: Foundation**
- `setup.sh`, venv, folder structure, `CLAUDE.md`, JSON schemas, brain files with starter content.
- ✅ Done when: `setup.sh` passes on my Mac and the schemas validate sample files.

**Phase 0.5: Memory engine**
- `memory/` folders, working-memory template, `core/memory.py` (create / update / consolidate / search), `/remember`, `/recall`, `/resume`.
- ✅ Done when: a dummy task creates a working file, updates it step by step, and on finish is consolidated into long-term memory with `index.md` updated. `/recall` finds it.

**Phase 1: Edit Bay MVP (talking head → reel)**
- ingest, clean_audio, transcribe, detect_silence, detect_fillers, rough_cut, face_track, basic Remotion captions, render.
- Agents: showrunner, editor, critic (simple).
- ✅ Done when: `/edit clip.mp4` on a 3-minute talking-head video returns a clean 9:16 captioned reel with no dead air in under ~10 minutes.

**Phase 2: Writers' Room**
- `/studio-setup`, `/plan` with strategist, hook-specialist, scriptwriter. `plan.json` output.
- ✅ Done when: I can go from idea → shoot package in under 10 minutes.

**Phase 3: Script-aware editing + separate audio**
- sync_audio, align_script (best-take selection), beat-aware editing, hook check.
- ✅ Done when: I shoot a script with retakes plus a separate mic and the edit picks the right takes automatically.

**Phase 4: Style & polish**
- Edit presets, punch-in zooms, "Day N" badge, SFX, music ducking, cover image, fcpxml export, full critic loop.
- ✅ Done when: build-in-public reels look distinctly "on brand" and open in DaVinci Resolve.

**Phase 5: Design Desk**
- Carousel pipeline, 4 starter theme packs, resource verification.
- ✅ Done when: "7 resources on X, math-wall theme" → finished slides.

**Phase 6: AI Explained series**
- Series producer, series bible, Remotion diagram components (boxes, arrows, flow, labels), intro sting, episode tag.
- ✅ Done when: an episode reel includes animated diagrams generated from the script's `graphic` beats.

**Phase 7: Learning loop**
- `/log`, the strategist reads performance, and weekly suggestions ("your failure-story hooks get 2× watch time").

---

## 12. Open questions for the owner (ask before Phase 1)

1. Apple Silicon chip and RAM? (Affects the Whisper model size.)
2. Language spoken in videos: English, Urdu, or mixed? (Whisper handles code-switching less reliably. We may need the glossary + manual caption review.)
3. Target platforms: Instagram, TikTok, YouTube Shorts, LinkedIn?
4. What product am I building in public? Name + one line (goes into the brand bible and glossary).
5. Camera + mic setup: phone? separate mic?
6. Any creators whose style I like (for reference only; don't copy)?
7. Music source: royalty-free library I'll drop in `assets/music/`, or leave music optional for now?

---

## 13. Rules for Claude Code while building

- Build one phase at a time. Demo it, then continue.
- Prefer boring, reliable tools. No GUI automation of editors.
- Every pipeline step caches output and can be re-run on its own.
- Never modify `raw/`. Never delete my footage.
- Keep agents' outputs in files matching the schemas. Validate before rendering.
- Make a fast low-res preview before any full render.
- Keep `brain/` human-readable. It's my studio's expertise and I'll edit it over time.
- Every task gets a working-memory file on start and is consolidated to long-term memory on finish (§14). No task ends without consolidation.

---

## 14. Memory engine

The studio remembers. **`brain/` = expertise** (rules and playbooks I control). **`memory/` = experience** (what actually happened, what I liked, what worked). Both are plain markdown so I can read and edit them.

### 14.1 Two layers

| Layer | Where | Lifetime | Purpose |
|---|---|---|---|
| **Working memory** (short-term) | `memory/working/<project_id>.md` | Created at task start, lives while the task runs | Scratchpad for the current content requirement: goal, decisions, my feedback, progress. Lets a crashed or paused task resume. |
| **Long-term memory** | `memory/long-term/` | Permanent | Distilled knowledge carried into every future task |

### 14.2 Working memory file (created at runtime)

When `/plan`, `/edit` or `/carousel` starts, the showrunner creates `memory/working/<project_id>.md` from this template:

```markdown
---
project_id: 2026-09-26_bip-day-12
pillar: build-in-public
task: edit            # plan | edit | carousel
status: in_progress   # in_progress | waiting_on_me | done | abandoned
started: 2026-09-26T03:40
updated: 2026-09-26T03:52
---
## Goal
What this piece of content must achieve, in one or two lines.

## Requirements
Length, platform, pillar preset, anything I specifically asked for.

## Context loaded from long-term memory
Bullets of relevant preferences / lessons pulled in at start.

## Decisions (with reason)
- Chose hook #2 (result-first) — I said it sounds most like me.
- Cut the 40s tangent about pricing — separate reel idea.

## My feedback
- "Captions too big" → reduced to 80% size.

## Progress
- [x] ingest  - [x] transcribe  - [ ] rough cut  - [ ] critic  - [ ] final

## Open items / ideas spotted
- Pricing tangent → could be its own reel.
```

**Rules:**
- Every agent **appends** to it after each meaningful step (decision, my feedback, step finished). Agents never overwrite other agents' entries.
- Update `updated` and `Progress` after every pipeline step, so `/resume` knows exactly where to continue.
- Keep it short. Log decisions and feedback, not tool output.

### 14.3 Long-term memory layout

```
memory/long-term/
├── index.md              # One line per memory: date | type | tags | file | one-line summary
├── preferences.md        # My stable likes/dislikes (style, tone, captions, music, words)
├── lessons.md            # What worked / what failed, with evidence (links to project + stats)
├── ideas-backlog.md      # Content ideas spotted during tasks, tagged by pillar
├── pillars/
│   ├── build-in-public.md   # Running story: where the product is, last Day N, recurring themes
│   ├── ai-explained.md      # Pillar-specific learnings (series continuity lives in brain/series-bible.md)
│   └── resources.md         # Resources already shared (avoid repeats), themes used
└── projects/
    └── 2026-09-26_bip-day-12.md   # Condensed record of each finished task
```

### 14.4 Memory Load (start of every task)

Before asking me anything, the showrunner:
1. Reads `index.md`, `preferences.md`, the relevant `pillars/<pillar>.md`, and the top relevant lines of `lessons.md`.
2. Pulls the **last 3–5 project records** of the same pillar (by date/tags in `index.md`).
3. Checks `ideas-backlog.md` for ideas matching this pillar and offers them if I have no idea yet.
4. Writes the relevant bullets into the working file's "Context loaded" section.

This keeps context small: load the index first, then only the files that match. Never load everything.

### 14.5 Memory Consolidation (end of every task)

When a task hits `done` (or I abandon it), the showrunner runs consolidation:
1. **Project record:** write `memory/long-term/projects/<project_id>.md`: goal, final hook, length, key decisions, my feedback, output paths. ≤ 30 lines.
2. **Extract durable facts.** Anything that will matter again goes to the right file:
   - Feedback that reflects a stable taste → `preferences.md` (e.g. "prefers smaller captions, white + one accent color").
   - Something that worked or failed → `lessons.md`.
   - New ideas spotted → `ideas-backlog.md`.
   - Story progress (Day N, product milestones, resources shared, episode shot) → `pillars/<pillar>.md`.
3. **Deduplicate.** If a fact already exists, update it (and bump a `seen: N` counter) rather than adding a duplicate. If new info contradicts an old entry, replace it and note the date.
4. **Update `index.md`** with one line per new or changed memory.
5. **Archive working memory.** Move the working file to `projects/<project_id>/working-memory.md` (keeps full history with the project) and clear it from `memory/working/`.
6. Tell me in 2–3 lines what the studio learned from this task.

### 14.6 Promotion: memory → brain

When a lesson or preference has been seen **3+ times**, the showrunner **proposes** adding it to the relevant `brain/` playbook (e.g. add to `edit-styles.md`: "bip-raw captions at 80% size"). It asks me first and never edits `brain/` without approval.

### 14.7 Learning from performance

`/log` stats get linked to the project record. After every 5 logged posts, the strategist compares hooks/angles/lengths, writes findings to `lessons.md` with the numbers, and flags anything worth promoting.

### 14.8 Implementation

`core/memory.py` exposes:
- `create_working(project_id, pillar, task)` → creates the file from the template
- `append(project_id, section, text)` → safe append with timestamp
- `set_status(project_id, status)`
- `consolidate(project_id)` → steps in §14.5 (the showrunner writes the content; the script handles file moves, index update and dedupe checks)
- `search(query, tags=None)` → greps `index.md` first, then matching files; returns snippets for `/recall`
- `list_open()` → unfinished tasks for `/resume`

Simple markdown + grep is enough at this scale. Only consider embeddings or a vector DB if long-term memory grows past a few hundred files.
