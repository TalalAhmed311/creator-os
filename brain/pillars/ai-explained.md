# Pillar: AI Explained (series)

**Format:** numbered reel series · **Preset:** `ai-explained` · **Vibe:** polished, clear "aha" per episode.

## Episode recipe
1. **Hook** (question / curiosity gap) — ≤3 s, episode tag "AI Explained #N" in the corner.
2. **Intro sting** ≤ 1.5 s (optional after the hook, never before it).
3. **Analogy first** — a familiar thing that behaves the same way.
4. **Mechanism** — the actual steps, shown as an **animated diagram** (required). Use `graphic` beats: `diagram: tokens -> embeddings -> attention -> next token`.
5. **Why it matters** — one line connecting to something the viewer uses.
6. **Tease the next episode** ("Next: why it hallucinates.").

## Rules
- One concept per episode. If you need "and also…", that's the next episode.
- No jargon without an analogy right before it.
- Every diagram ≤ 5 boxes. Labels ≤ 3 words each.
- Keep continuity in `brain/series-bible.md` (the series-producer owns it).

## Diagram spec syntax (for `graphic` beats and edl diagrams)
- Chain: `request -> model -> response`
- Branches: separate chains with `;` → `prompt -> model; model -> tools; tools -> model`
- Edge labels: `query -[embed]-> vector DB`

## Interview questions (strategist, ≤4)
1. Which concept?
2. The one "aha" the viewer should leave with?
3. Episode number? (suggest the next one from the series bible)
4. A good analogy you already use for it?
