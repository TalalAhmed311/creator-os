---
description: Plan the week — which reels and carousels to make, when to shoot, edit and post (writes plans/<YYYY>-W<ww>.md)
argument-hint: [anything happening this week]
---
**Load the `content-planning` skill** (`.claude/skills/content-planning/SKILL.md`) and follow it. Notes from the owner: `$ARGUMENTS`

You are the **showrunner** (`.claude/agents/showrunner.md`) with the strategist's eye for performance:
1. Load memory for all three pillars, the series bible, last week's plan, `./studio projects` and `pipeline.content_log analyze`.
2. Ask at most 3 questions in one message (what's happening in the build, how many posts are realistic, dates to avoid).
3. Present the week table; the owner edits it (approval gate). Save `plans/<YYYY>-W<ww>.md`, add unused ideas to the backlog.
4. Offer to start the first item with `/studio-plan` or `/carousel`.
