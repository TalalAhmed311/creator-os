---
description: One-time studio setup — interview the owner and write the brand bible, brand.json, glossary, series bible skeleton
---
You are the **showrunner** (read `.claude/agents/showrunner.md`) running `/studio-setup`, with the **strategist** playbook (`.claude/agents/strategist.md`).

1. `.venv/bin/python -m pipeline.memory create setup-$(date +%F) build-in-public setup --goal "Set up the brand bible"` (use the real date).
2. Read `brain/brand-bible.md` — keep anything already filled in; only ask about TODOs.
3. Interview the owner in **two short rounds** (≈5 questions each, numbered, one-line answers):
   - Round 1: name/handle(s) · product name + one line · audience + skill level · what they want from you · posting cadence
   - Round 2: tone in 3 words · phrases you use / words you never use · brand colours (or "pick for me") · creators whose style you like (reference only) · anything to never show on camera
4. Write `brain/brand-bible.md` (replace TODOs, keep structure), update `brain/brand.json` colours/handle, add the product name + tools to `brain/glossary.txt`.
5. Record stable preferences: `.venv/bin/python -m pipeline.memory remember "<fact>" --kind preference --tags <tags>` for each.
6. Seed `memory/long-term/pillars/build-in-public.md` via `pipeline.memory remember "Product: <name> — <one line>. Current day: Day <N>" --kind pillar --pillar build-in-public`.
7. Confirm the series bible (`brain/series-bible.md`) episode list with the owner (keep or edit).
8. Consolidate (`pipeline.memory consolidate`) and show the owner a 5-line summary of their brand bible.
