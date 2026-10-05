---
project_id: 2026-09-30_bip-day-1-laid-off-building
pillar: build-in-public
task: plan
status: waiting_on_me
started: 2026-09-30T23:31
updated: 2026-10-02T23:01
---
## Goal

## Requirements
- [23:43] Owner: plan video around original script (3 pillars) in the headline→face→b-roll→Day 1 structure; black placeholders where face goes, generate all other visuals.

## Context loaded from long-term memory
- (nothing relevant yet)

## Decisions (with reason)
- [23:43] Built Remotion animatic (remotion/src/Animatic.tsx → out/animatic.mp4, 54.6s) using hook A 'Yeah. I got laid off too.' as default; chosen_hook still null pending owner pick. 3 news sites blocked headless screenshots → typographic headline cards citing sources.
- [23:59] v2 animatic 61.6s: 5.6s news montage from owner screenshots, stamp removed, Remote+Revoked scenes added, em dashes removed, synthesized music (work/make_music.py, no downloads) with silence on 'laid off too' and before 'I'm going to build'. Timing shared via work/animatic_timing.json.
- [00:15] Added LUMS beat (owner doing MS AI at LUMS, Lahore): Lahore 🎓 pin + owner's LUMS photo + LUMS name tag in that scene only; 🎓 pin persists through layoff beat. Pillars trimmed; total 64.2s.
- [04:28] Owner shot videos/intro.mov (ingested → raw/cam.mov, 1620x1080 landscape, 80s, camera mic only). Transcribed (mlx-whisper turbo). Cut only the 5 FACE lines (source 0.20-1.12+1.52-3.72, 4.02-6.12, 32.14-37.05, 40.52-41.72, 69.00-75.22; boundaries from audio envelope, whisper ran ~0.3s early) into the animatic slots, 9:16 crop on face-track median cx, audio from cleaned voice.wav, music ducked -12 dB under voice. Animatic now 67.7s.
- [06:15] Owner deleted-on-request raw/cam.mov (original still videos/intro.mov); derived work files cleared. New full-script voice take raw/video-to-audio.mp4 (69s, clean: -10.5 LUFS, silent floor). Cut 16 lines (cuts in work/animatic_timing.json voice.parts, starts from envelope since whisper ~0.4s early), scenes retimed to the voice (70.3s), captions follow voiced frames, music ducked under all voice. Face slots back to black placeholders pending owner's new face video.
- [07:13] New hook (8.35s): real news video (CNBC 100k opener w/ their audio, Meta 10%, 'A new AI era begins', layoff chart spike), 1.3s screenshot burst, rolling 'TECH JOBS LOST IN 2026' counter 100,000→129,994, ends on Firstpost anchor line 'the layoff story ... is a human story' → black → face1. Clips in work/news/. Music under news at 50%. Video 73.1s.
- [22:51] Owner added vertical face takes raw/'face 1 2.mp4', face3.mp4, 'face 4.mp4', 'face 5.mp4' (464x832 60fps, green cast, mic in hand). work/faces/build_faces.py: MFCC+DTW lip-sync of each take to the voice line (speed clamp ~0.55-1.7, avg 0.79-1.15x), enhance (deblock, hqdn3d, lanczos 1080x1920, colorbalance de-green, eq, cas), clip audio never used. SyncedFace replaces black placeholders. Video 73.1s.
- [23:01] face1 now uses hand-placed word anchors (yeah / I got laid / off / too) instead of DTW; face5 window cut to 0.45-4.55 with MAX_T 4.70 (stand-up starts 4.75 by motion energy). Lesson: DTW fails when takes have different pauses or extra words; use envelope anchors.

## My feedback
- [23:59] Owner v2 notes: add background music; longer layoff-news opening using owner's own screenshots; remove the red LAID OFF stamp; no em dashes in on-screen text; add 'working remotely from Pakistan' to the story.
- [00:08] Owner: clock/standup Pakistan scene not good; wants a map with Karachi highlighted + cute emoji (asked for Pikachu; used 🧑‍💻 instead, Pikachu is Nintendo IP). Built vector map from Natural Earth instead of Google Maps screenshot (ToS).
- [00:51] Owner: only ONE location on the map, Lahore (lives/studies there). Removed Karachi entirely; single Lahore pin carries 🧑‍💻 → 🎓 → 😶.
- [07:13] Owner found the screenshot-only hook boring. Picked news clips: Firstpost 1:00,1:51,5:10 and CNBC-TV18 0:00,0:15 (3s each).
- [23:01] Owner: face1 lip sync off; face5 showed him standing up after the line.

## Progress
- [x] ingest
- [x] sync audio
- [x] clean audio
- [x] transcribe
- [x] silences
- [x] fillers
- [x] align script
- [x] frames
- [x] face track
- [x] draft edl
- [ ] preview
- [ ] critic
- [ ] final

## Open items / ideas spotted

## lessons
- [04:28] Camera-mic take: -23 LUFS raw, constant low rumble (fan/AC), gaps only 5-10 dB below speech; energy dips 42-58s. Whisper misheard LUMS→LAMS, RAG→PAC. Next shoot: separate mic, fan off, 9:16 vertical.
- [07:13] Static screenshots + slow push-ins read as boring; moving footage + real voices + accelerating cuts + a live counter fixes it.
- [22:51] Owner's phone takes have a green cast under that light and low bitrate; ask for 1080p+/4K export and white balance set, or a warmer light, next shoot.
- [23:01] When recording separate face takes: hold still ~1 s after the last word before moving, and match the voice take's pauses.
