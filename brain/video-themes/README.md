# Video theme packs (collage layouts)

One folder per theme. `theme.json` describes a **collage layout**: image tiles around (or behind) you while you talk.
Used by `edl.json → layout` (`python -m harnesses.studio.collage <project> --theme <name>`), rendered by `harnesses/studio/remotion/src/Collage.tsx`.

| Theme | Look |
|---|---|
| `quad-collage` | 2×2 full-bleed images, you in a small window in the middle (the "your major tells me…" look) |
| `trio-stack` | one wide image on top, two below, you in a rounded card across the seam |
| `scatter-cards` | you stay full-frame, images drop in as tilted photo cards |

All positions are fractions of the 1080×1920 frame (`x, y` = top-left corner, `w, h` = size).

- `slots[]` — where the images go (`rotate` in degrees, optional). A block can fill fewer tiles than there are slots.
- `presenter` — your camera window. `{0,0,1,1}` = full frame. `above_tiles: false` puts the images on top of you.
- `tiles.enter` — pop | slide | drop | cut. `stagger` (s) between tiles when a collage opens. `ken_burns` = end zoom (1 = still).
- `tiles.scrim` (0–1) — dark gradient behind the title, for busy images like screenshots.
- `tiles.saturate / contrast / brightness / dim` — grade, so mixed images look like one set and captions stay readable.
- `title` — how the hook text looks while a collage is on screen. `captions_top` — caption band (fraction of height) during a collage.
- `morph` — seconds for your video to shrink from full frame into the window (and back).

Images: the owner's own photos/screenshots/screen recordings (`raw/images/`, `raw/broll/`) or `assets/broll/`.
Generated images are fine as **pictures only — never generated text in them**. Short muted video clips work as tiles too.

To make a new theme: copy a folder, rename it, edit `theme.json`.
