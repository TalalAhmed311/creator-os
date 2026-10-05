# Carousel theme packs

One folder per theme. `theme.json` holds colours, fonts and the background recipe.

- `background.generator` — a built-in CSS/SVG background (math-wall, blueprint, terminal, clean-light), used when no image is given.
- `background.image` — optional file in this folder (e.g. `bg.jpg`). Owner photo or an image-gen result. **Backgrounds only — never text in the image.**
- `background.darken` (0–1) / `blur_px` — readability over photos.
- `background_prompt` — the prompt to use with an image-gen connector (Higgsfield) for a fresh background.
- `card_style` — chalk | outline | terminal | soft.

To make a new theme: copy a folder, rename it, edit `theme.json`, drop a `bg.jpg` in if you have one.
