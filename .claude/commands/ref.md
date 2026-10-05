---
description: Reference library — download videos to study, transcribe them, break down hooks / visual hooks / pacing
argument-hint: <url…> | analyze <id> | list | rm <id>
---
Arguments: `$ARGUMENTS`

**Nothing in `references/` is deleted unless the owner says so in this conversation.** Never pass `--yes` to `rm` on your own initiative; for `rm`, show what would be deleted first (`./studio ref rm <id>`), then delete only after a clear yes.

1. URLs → `./studio ref add <url…> --analyze` (run in the background for long videos; the 16-min transcription takes a few minutes on CPU).
2. After `analyze`, write the **Breakdown** section of `references/<id>/analysis.md` yourself — LOOK at `hook.jpg` and `contact.jpg`, read `transcript.txt` and `metrics.json`:
   - **Hook (0–3 s):** spoken line, on-screen text, first frame — which hook type (`brain/hooks-library.md`) and why it works or doesn't.
   - **Visual hooks:** what changes on screen and how often (cuts, zooms, text pops, B-roll, graphics), pattern interrupts in the first 10 s.
   - **Audio:** pace (wpm), music/SFX, silence used for emphasis, loudness.
   - **Structure:** beat list with timestamps (hook → context → value → payoff → CTA).
   - **Steal this for us:** 3–5 concrete, adaptable ideas for the owner's content (techniques, not their words or footage).
   Summarise in your own words; quote at most one short line. Their footage, words and branding are not ours to reuse — reference only.
3. Report to the owner in ≤8 lines and offer to save useful patterns: `pipeline.memory remember … --kind lesson` (brain promotions need a yes).
