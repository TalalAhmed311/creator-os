---
description: Design Desk — resource list → themed, verified carousel slides (PNG + LinkedIn PDF)
argument-hint: [topic or list] [theme]
---
**Load the `resource-carousel` skill first** (`.claude/skills/resource-carousel/SKILL.md`) — it holds the curation, copy and design expertise this flow relies on.

You are the **showrunner** (read `.claude/agents/showrunner.md`) running the Design Desk. Arguments: `$ARGUMENTS`

1. `.venv/bin/python -m pipeline.new_project resources <slug> --task carousel` → project id (creates working memory + Memory Load). Check `memory/long-term/pillars/resources.md` for resources already shared.
2. Ask (one message, ≤3 questions, skip what the arguments answer): which resources (or what to research)? who are they for? which theme (math-wall, blueprint, terminal, clean-light, or "propose 3")?
3. **Resource curator** → `carousel.json`, verified with `pipeline.verify_links`. Report anything dropped.
4. **Carousel designer** → theme/background → `.venv/bin/python -m carousel.render <id>` → `out/slides/*.png`, `out/carousel.pdf`, `out/caption.txt`. It must look at every slide and fix overflow.
5. Show the owner the slide paths (open the folder: `open projects/<id>/out/slides`). Approval gate — iterate on feedback, logging it (`feedback`).
6. On approval: status `done`, **Memory Consolidation** — include a `pillar` fact for resources listing what was shared + the theme used; if a new theme was created, note it.
