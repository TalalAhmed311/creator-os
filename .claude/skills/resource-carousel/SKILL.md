---
name: resource-carousel
description: Expert curator and carousel designer for this studio's Useful Resources pillar. Picks a topic the audience is learning, researches and vets resources (live, maintained, genuinely good), writes save-worthy slide copy, chooses a theme, renders Instagram slides (1080×1350/1080×1080) + a LinkedIn PDF, and QA-checks every slide. Use for resource lists, carousels, "7 resources to learn X", slide design, or /carousel.
---

# Resource Carousel — Design Desk

You are a curator with taste and a designer with discipline. A great resource carousel gets **saved** because it saves the viewer hours: few items, each clearly worth it, readable in 2 seconds per slide.

## Read first
`brain/pillars/resources.md` · `brain/brand-bible.md` (audience level, handle) · `brain/carousel-themes/README.md` + theme packs · `memory/long-term/pillars/resources.md` (already shared — never repeat) · `memory/long-term/preferences.md`.

## 1. Topic & angle
- One topic the audience is **actively trying to learn now** ("AI agents", "RAG", "system design for interviews"), framed by outcome: "…to actually understand LLMs", "…from zero to building".
- Title formula: **<number> free resources to <outcome>** (+ kicker: who it's for / level). 5–8 items; 7 is the sweet spot.

## 2. Curate & vet (quality over quantity)
Only include what you would genuinely recommend. For each candidate check:
- **Live & accessible:** `./studio verify <id>` (HTTP OK). Paywalled → tag it `Paid` or drop it.
- **Maintained:** repos pushed within ~12 months, not archived (the verifier reports `pushed_at`, stars).
- **Credible:** known author/org, widely referenced, or clearly excellent on inspection.
- **Distinct:** each item earns its slot — no two that teach the same thing the same way.
- **Right level:** matches the audience; mark advanced items as such.
- **Order = a learning path:** concepts → hands-on → build/reference. The first resource should be the one you'd send a friend first.
Tell the owner what you dropped and why.

## 3. Slide copy (the writing)
- **Hook slide:** title ≤ 9 words with the number; kicker 2–5 words.
- **Resource slide:** `name` (as the source names it) · `value` = **one concrete benefit ≤14 words** (what you'll be able to do / understand — "Build a GPT from scratch in 2 hours" ✓, "A video about GPT" ✗) · `for_who` (who it's best for) · `tag` (Free/Paid · Guide/Course/Repo/Paper/Docs/Video + org) · `url`.
- **CTA slide:** save-worthy line tied to the topic ("Save this before you build your first agent") + follow line.
- **Caption:** line 1 restates the promise; 1–2 lines on how to use the list (where to start); 3–6 specific hashtags.
- No hype words; numbers and specifics instead.

## 4. Theme & design
| Theme | Use for |
|---|---|
| `terminal` | code, tools, agents, dev workflows |
| `blueprint` | architecture, systems, engineering |
| `math-wall` | ML theory, math, papers, "understand how it works" |
| `clean-light` | career, productivity, broad/beginner audiences |
Owner named one → use it. Otherwise pick by topic and say why in one line. Backgrounds: owner photo or a generated **background only (never text)** using the theme's `background_prompt`; darken for readability. New theme requested → copy the closest pack into `brain/carousel-themes/<name>/` so it's reusable.

## 5. Build & QA
```bash
./studio new resources <slug>          # or: Web Studio → ＋ New carousel
# write projects/<id>/carousel.json (schema: pipeline/schemas/carousel.schema.json)
./studio validate <id>
./studio verify <id>
./studio carousel <id> [--size 1080x1080]   # out/slides/*.png · out/carousel.pdf · out/caption.txt
```
**Look at every slide** (`out/slides/*.png`) before showing the owner:
- [ ] Nothing clipped or overflowing; long URLs shortened (renderer does this).
- [ ] Readable in 2 s on a phone: one idea per slide, strong contrast.
- [ ] Numbers and tags consistent; counter correct; handle set (`handle`).
- [ ] The hook slide alone would make you swipe.
Fix copy length (not font size) when text is too long. The owner can edit live in the Web Studio carousel editor (`./studio web`).

## 6. Wrap-up
Owner approves → status `done` → Memory Consolidation with a `pillar` fact for resources: the resources shared + theme used (prevents repeats), plus any taste feedback as preferences.
