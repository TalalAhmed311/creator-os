# Hooks Library

The first 1–3 seconds decide whether anyone keeps watching. **Every hook = spoken line + on-screen text (≤7 words) + a first-frame visual.** All three must say the same thing in different ways.

## Hard rules
- No "Hey guys", no intro, no name, no logo first. Start mid-thought.
- On-screen hook text ≤ 7 words, visible on frame 1 (not faded in).
- The spoken hook is ≤ 2.5 s when read at normal speed (≈ 8–10 words).
- Make one promise and pay it off before the end.
- Numbers beat adjectives ("3 hours" > "super fast").
- Specific beats general ("my Stripe webhook" > "a bug").

## Types (use the `type` key in plan.json)

| type | Template | Example | Best for |
|---|---|---|---|
| `result_first` | "This [result] took me [time/cost]." | "This took 3 hours instead of 3 weeks." | BIP wins, tool demos |
| `curiosity_gap` | "Nobody explains [specific part] of [thing]." | "Nobody explains this part of how ChatGPT works." | AI Explained |
| `contrarian` | "Stop [common practice] for [case]." | "Stop using RAG for this." | Opinions, AI Explained |
| `callout` | "If you're [specific person], watch this." | "If you're building your first SaaS, watch this." | Resources, advice |
| `mistake` | "I just [broke/lost/wasted] [X]. Here's why." | "I just broke production. Here's why." | BIP failures (often the best performers) |
| `progress_marker` | "Day [N] of building [X] in public." | "Day 12 of building X in public." | BIP continuity — pair with a second hook type in the same line |
| `question` | "How does [thing] actually [do Y]?" | "How does an AI actually 'see' an image?" | AI Explained |
| `visual_break` | Start mid-action: screen already moving, walking toward camera, hand slamming laptop shut | — | Any; combine with a spoken hook |

## First-frame visuals that work
- The result on screen (dashboard number, working feature, error message).
- Face close, mid-sentence, moving toward the camera.
- A before/after split.
- For AI Explained: the diagram's first box already drawn.

## Pairings for this studio
- **Build in Public:** `progress_marker` + (`mistake` | `result_first`) → "Day 12. I just deleted my whole database."
- **AI Explained:** `question` or `curiosity_gap`, with the episode tag in the corner.
- **Resources:** `callout` or `result_first` on slide 1 ("7 free resources to actually understand LLMs").

## The three-option rule
The hook-specialist always returns 3 hooks of **different types**. At least one must be the "safe" pick for the pillar and one should be a bolder angle. Check `./studio hq review` (own results) and `./studio research insight top --kind hook` / `memory/long-term/lessons.md` for which types have performed for me.
