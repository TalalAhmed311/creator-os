# Edit Styles (presets)

Presets are applied by `pipeline/auto_edl.py` and rendered by `remotion/`. The editor agent may override per segment.

| Preset | Cuts | Zooms | Captions | Graphics | Music |
|---|---|---|---|---|---|
| `bip-raw` | Tight jump cuts (gaps > 200 ms removed) | Punch-in 118–120% (snap) on lines with numbers/key terms; otherwise alternate 100%/108% | Montserrat 900, UPPERCASE, word-by-word pop, numbers + glossary terms in accent | "Day N" badge (top-left, 0–2.5 s), screen-recording zoom, before/after split (`split_top` b-roll) | Low energetic bed, −18 dB, ducked under voice |
| `ai-explained` | Clean cuts (gaps > 280 ms removed) | Gentle push-in 100→106% per shot | Inter 800, sentence case, dark pill, keyword in accent | Diagrams (boxes/arrows/data flow), callout labels, series tag (top-right), optional intro sting | Subtle ambient, ducked |
| `talking-head-basic` | Jump cuts (gaps > 300 ms removed) | Alternate 100%/115% every cut | Inter 800, white + black stroke | None | Optional |

## EDL knobs the agents can use
- `segments[].zoom` `{from, to, ease}` — ease: linear | easeIn | easeOut | easeInOut | snap
- `segments[].reframe` — face_track | center | none
- `segments[].overlay_broll` `{file, in, mode}` — mode: full | split_top | pip
- `captions.size` (1.0 = preset default), `captions.max_words` (1–6)
- `layout` `{theme, blocks[{start, end, tiles[]}]}` — collage around the speaker (see above; built from the plan)
- `graphics[]` types: hook_text, badge, callout, diagram, series_tag, intro_sting, lower_third, emoji_pop
- `audio.music` `{file, gain_db, duck}`, `audio.sfx[]` `{file, at, gain_db}`

## Collage around the speaker (technique, not a template)
Images surround you (or drop in beside you) while you keep talking — the viewer *sees* every item you name.
Learned from a "your major tells me about your personality" reel; we use the idea where the script earns it, never as a default look.
- **Use it for:** lists and montages ("5 tools I use", "what each model is good at"), "X tells me about Y" / vibe-matching, before→after sets, naming several real things fast.
- **Skip it for:** the hook's eye contact moment (unless the hook *is* the list), mechanism explanations (use a diagram), emotional/honest beats (stay full-frame).
- **One image per named idea**, landing as the word is said; images are real things (owner's screenshots, photos, product shots) or generated pictures with **no text in them**.
- Max ~1 collage beat per reel, 3–8 s. Never on the same beat as a diagram.
- Themes: `brain/video-themes/` — `quad-collage` (2×2, you in a small centre window), `trio-stack` (wide + two, you in a card), `scatter-cards` (you full-frame, tilted photo cards). Pick by mood; new themes are welcome.
- Data: plan beat `collage.images` → `auto_edl` → `edl.layout` (OUTPUT time). Rebuild after adding images: `./studio collage <id> --from-plan`.

## Learned tweaks
(Promoted from memory with the owner's approval — see memory/long-term/preferences.md)
