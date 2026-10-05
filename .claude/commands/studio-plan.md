---
description: Writers' Room — idea → shoot-ready script (hooks, script, shot list, caption) in under 10 minutes
argument-hint: [build-in-public|ai-explained|resources] [idea]
---
**Load the `reel-scripting` skill first** (`.claude/skills/reel-scripting/SKILL.md`) — it holds the idea, hook and scripting expertise this flow relies on.

You are the **showrunner** (read `.claude/agents/showrunner.md`) running the Writers' Room. Arguments: `$ARGUMENTS`

Speed target: the whole session in **under 10 minutes**. Ask the owner as few messages as possible.

1. **Pillar.** From the arguments, or ask (one question). `resources` → hand off to `/carousel` flow instead.
2. **Project + memory.** `.venv/bin/python -m pipeline.new_project <pillar> <short-slug> --task plan` → prints the project id; it creates the working memory and runs Memory Load. Read the "Context loaded" section of `memory/working/<id>.md`. If the owner has no idea, offer 2–3 backlog ideas from it.
3. **Interview** (strategist's questions from `brain/pillars/<pillar>.md`, ≤5, ONE message, pre-filled from memory — e.g. "Day 13?"). Record answers verbatim in the working memory (`requirements`).
4. Delegate to **strategist** → `brief.md`.
5. Delegate to **hook-specialist** → 3 hooks in `plan.json`. Show them to the owner, numbered. **Owner picks** (approval gate). Set `chosen_hook`, log the choice + reason to working memory (`decisions`).
6. Delegate to **scriptwriter** → full `plan.json` + `script.md`. For ai-explained, then delegate to **series-producer**.
7. Validate: `.venv/bin/python -m pipeline.validate projects/<id>`. Fix until ✓.
8. **Deliver the shoot package**: show the teleprompter version, shot list, B-roll list and the path to `script.md`. Remind: clap at the start of each take (mic sync); re-say a fluffed line from its start; after shooting run `/studio-edit <id> <video> <mic audio>`.
9. Set working status to `waiting_on_me` (`pipeline.memory status <id> waiting_on_me`) — the task continues in `/studio-edit`, so do NOT consolidate yet unless the owner abandons it. Stop.
