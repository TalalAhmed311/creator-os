---
description: Research Desk — find what's working (outlier posts), break down why, rank the top 5 insights
argument-hint: <topic | @creator | post-url> [platform]
---
Arguments: `$ARGUMENTS`

Load the `content-research` skill first.

1. **Memory Load**: `.venv/bin/python -m core.memory create research-$(date +%F)-<slug> build-in-public other --goal "Research: <topic>"`
   (use a short slug of the topic) and read `./studio research insight top --n 10` so you build on what's known.
2. Scope in one line to the owner (platform, topic, creators) — don't wait for an answer unless the topic is unclear.
3. Delegate to the **research-analyst** agent with the scope. A single post URL → just add + analyse that post and say how it
   compares to the creator's normal.
4. Show the owner the top 5 insights (pattern · evidence · avg outlier ×) and the report path. Offer: "Write a draft from #N?" (→ `/write`).
5. **Memory Consolidation**: `core.memory consolidate <task_id> --facts …` with the durable lessons (numbers included).
