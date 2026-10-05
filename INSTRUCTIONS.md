# How to use the studio

Four jobs, each with its own guide below. Each job is backed by an **expert skill** that Claude loads automatically, so you get a strategist, a scriptwriter, an editor or a curator, not a generic assistant.

| # | Job | Start it with | Expert skill | You end up with |
|---|---|---|---|---|
| 1 | [Plan the week](#1-plan-the-week) | `/studio-week` | `content-planning` | `plans/<year>-W<week>.md`: what to make, shoot, edit, post |
| 2 | [Reel idea & script](#2-reel-idea--script) | `/studio-plan` | `reel-scripting` | hooks, script, teleprompter, shot list |
| 3 | [Raw footage → reel](#3-raw-footage--reel) | `/studio-edit` | `raw-to-reel` | `final.mp4`, cover, caption, DaVinci Resolve file |
| 4 | [Resource carousel](#4-resource-carousel) | `/carousel` | `resource-carousel` | slide PNGs, LinkedIn PDF, caption |

**Before anything else, once:** open Claude Code in this folder and run `/studio-setup`. It fills in your brand bible (who you are, product, audience, voice, colours, handle), and every job uses it.

```bash
cd ~/Documents/build-in-public/personal-studio
claude
```

> Three ways to work, and you can mix them: **Claude Code** (slash commands, where the agents do the work), the **Web Studio** (`./studio web` in a terminal, where you edit visually in the browser), and the **terminal** (`./studio …` commands). All three read and write the same project files.

---

## 1. Plan the week

**What it's for:** deciding *what* to post this week so you batch your shooting and keep a rhythm across the three pillars.

### Steps
1. In Claude Code:
   ```
   /studio-week shipping onboarding v2 this week, can do 4 posts
   ```
2. Answer up to 3 quick questions (what's happening in your build, how many posts are realistic, days to avoid).
3. You get a table: each day's post, pillar, one-line idea, hook angle, format, and your **shoot block** and **edit block**. Edit anything you like; nothing is final until you say so.
4. It's saved to `plans/<year>-W<week>.md`. Unused ideas go to your ideas backlog in memory.
5. Say *"start the first one"* and it hands off to job 2 or job 4.

### What the planner does for you
- Default mix: **3 Build-in-Public reels, 1 AI Explained episode and 1 carousel**, adjusted to your cadence.
- Build in Public is sequenced as a story: a decision early in the week, a struggle mid-week, a result late. It also keeps your Day N count and leaves one slot for whatever actually happens.
- AI Explained goes out on the same weekday every week, taking the next episode from the series bible.
- **One experiment per week:** one thing it changes on purpose (a hook type, the length or the post time) so you learn what works.
- It uses your stats (`/log`) to favour hook types that have worked for you.

### Mid-week
Ask *"how's the week going?"* and it updates each item's status (idea → planned → shot → edited → posted) from your projects and moves anything that slipped.

---

## 2. Reel idea & script

**What it's for:** turning a rough idea into something you can read to camera, in under 10 minutes.

### Steps
1. In Claude Code:
   ```
   /studio-plan build-in-public   I cut onboarding from 5 screens to 2
   ```
   Pillars: `build-in-public`, `ai-explained`, or `resources` (which switches to job 4).
2. **Answer 3–5 short questions** in one reply. Your own words get reused in the script, so talk naturally.
3. **Pick one of 3 hooks.** Each has a spoken line, the text on screen, and what's in the very first frame. They're deliberately different types: one safe, one bold, one wildcard.
4. You get the **shoot package** in `projects/<id>/`:
   - `script.md`: a read-aloud version, a **teleprompter** version (short lines, hook in caps), and shoot notes
   - `plan.json`: the beats (hook → context → value → payoff → CTA), shot list, B-roll list, caption, hashtags
5. Go shoot (see the checklist below), then continue with job 3.

### What the scriptwriter guarantees
- **One idea per reel**, with a real number, event or mistake, and **proof you can show on screen**.
- **The length fits:** word count is at most 2.6 × the target seconds (about 78 words for a 30 s reel).
- **A visual change planned every 2–4 s:** screen, zoom or graphic.
- **Pillar recipes:**
  - AI Explained: analogy first, then an animated diagram, then why it matters, then a tease for the next episode.
  - Build in Public: Day N, one real event, the screen shown.

### Shooting checklist
- Phone vertical, eye level, face lit (window light works), separate mic on.
- **Clap once at the start of each take**; that's how the mic gets synced.
- Fluffed a line? Pause and **say the whole line again**. The editor keeps the last complete take.
- Record the hook 2–3 times with different energy.
- Record the screen or product for B-roll (screen recordings count).

---

## 3. Raw footage → reel

**What it's for:** your phone clip and mic recording become a finished, captioned 9:16 reel.

### Steps (Claude Code)
1. A reel you scripted in job 2:
   ```
   /studio-edit 2026-09-26_bip-onboarding ~/Movies/IMG_1234.MOV ~/Movies/mic.wav
   ```
   Unscripted footage:
   ```
   /studio-edit ~/Movies/IMG_1234.MOV ~/Movies/mic.wav
   ```
2. **Automatic:** sync the mic to the phone → clean the audio → transcribe → remove dead air, "um"/"uh", stutters and retakes → pick the best take of each script line → draft the edit.
3. **Expert pass:** the editor tightens the story, pacing and zooms; captions, graphics and sound are added. For an unscripted clip it finds the strongest 20–45 s story and proposes a hook.
4. **Low-res preview → harsh critic → fixes** (at most 2 rounds). The critic checks: a hook in under 3 s, no gaps or fillers, a visual change every 4 s or less, accurate captions, framing, and loudness.
5. **Final:** `out/final.mp4`, `out/cover.png`, `out/caption.txt` and `out/project.fcpxml`. It opens on your Mac.
6. **Approve** or ask for changes ("hook text smaller", "cut the part about pricing"). Once you approve, the studio saves what it learned.

### Tweak it yourself: Web Studio
```bash
./studio web
```
Open the reel, then:
- **Transcript:** select words → **⌫** cuts them, **R** restores them. Click a word to jump to it.
- **Timeline:** drag a cut's edges to trim; **S** splits at the playhead.
- **Captions tab:** type over a wrong word; ★ highlights it.
- **Graphics tab:** hook text, Day badge, callouts, diagrams.
- **Audio tab:** music, ducking, sound effects.
- **▶ Render preview** / **⬆ Render final** give you the exact result. Everything autosaves; **⌘Z** undoes.

### Or in a pro editor
Open `out/project.fcpxml` in DaVinci Resolve (File → Import → Timeline). It has your cuts, the synced audio, and markers where the graphics go.

### Where to put your files
Every video has its own folder, `projects/<id>/`, made when you start it (`/studio-plan` or `./studio new`). Inside, `README.md` lists what goes where:
- `raw/`: your camera video and your mic recording (one file each)
- `raw/broll/`: B-roll and screen recordings
- `raw/images/`: screenshots, photos, logos

Then run `/studio-edit <id>`. It finds the camera and mic in `raw/` on its own. Need audio from a video? `/convert <file>` (mp3 by default, wav for editing).

### Grab audio or clips from other videos
- `/yt <url>`: download a YouTube video into `videos/` (say "audio" for just the mp3).
- `/ref <url>`: save a video to study in `references/<id>/` and get a breakdown: transcript, hook (first 3 s), visual hooks, pacing, what to borrow. `/ref list` shows the library.
- `/clip <file or url> 1:23 1:45`: keep only that part's audio (mp3 by default; say "wav" for editing, "keep video" for the trimmed video too). For a URL the full video is kept in `references/`.
- **Nothing is deleted unless you say so.** "Delete the original" / `/ref rm <id>` removes a file only after you confirm.
- Only use videos you have the rights to (your own, Creative Commons, or with permission). The studio never downloads music into `assets/music/`.

### Good to know
- Captions need a transcript. Whisper is installed. If you ever turn it off, drop a `transcript.srt` (from CapCut, for example) into the project's `raw/` folder.
- Music and sound effects are only used if you put files in `assets/music/` and `assets/sfx/`. The studio never downloads music.
- Your original files in `raw/` are never modified.

---

## 4. Resource carousel

**What it's for:** a themed, save-worthy Instagram carousel of resources you'd genuinely recommend.

### Steps (Claude Code)
1. ```
   /carousel 7 free resources to learn AI agents, for beginner devs
   ```
   Add a theme if you want one (`terminal`, `blueprint`, `math-wall`, `clean-light`); otherwise the curator picks by topic and tells you why.
2. The curator researches and **vets** every resource: is the link live, is the repo maintained, is it credible, is it at the right level. Resources are ordered as a learning path (concepts → hands-on → build), and it tells you what it dropped and why.
3. Slides are written and rendered: hook slide → one resource per slide (name, one-line value, who it's for, tag, link) → save/follow slide.
4. Every slide is checked for overflow and readability before you see it.
5. You get `out/slides/01.png…` (1080×1350; ask for square 1080×1080 if you like), `out/carousel.pdf` for LinkedIn, and `out/caption.txt`.
6. Ask for changes ("swap #3", "shorter lines", "blueprint theme"), then approve. The studio records what was shared so it never repeats a resource.

### Tweak it yourself: Web Studio
`./studio web` → open the carousel → edit text, reorder or add slides, switch theme or size, and watch every slide update live. Then **🔗 Verify links** and **⬆ Render PNG + PDF**.

### By hand (terminal)
```bash
./studio new resources ai-agents
```
That prints the project ID. Copy the template into it:
```bash
cp tests/fixtures/carousel.json projects/<id>/carousel.json
```
Edit that file, then:
```bash
./studio verify <id>
./studio carousel <id>
open projects/<id>/out/slides
```

---

## After you post (every job)
```
/log <project-id> <post url>
```
Paste views, average watch %, likes, comments, saves and shares. Every 5 posts the strategist tells you what's working (for example, "your failure-story hooks get 2× watch time"), and the weekly planner uses that.

## Memory
- `/remember I hate yellow captions`: saved as a preference and applied from then on.
- `/recall captions`: see what the studio knows about a topic.
- `/studio-resume`: continue anything unfinished.
- When a preference has come up 3 or more times, the studio *asks* to add it permanently to your playbooks. It never changes them without your OK.

## If something's off
```bash
./studio doctor
```
It shows what's installed and what each tool will use. More fixes are in [README.md → Troubleshooting](README.md#10-troubleshooting).
