---
description: List unfinished studio tasks (working memory) and continue one
---
1. Run `.venv/bin/python -m core.memory open`.
2. None → say so. One → confirm and continue it. Several → ask which (numbered list with task, status, last update, next step).
3. Read `memory/working/<project_id>.md` fully (goal, decisions, feedback, progress). Re-enter the right flow at the first unchecked Progress step:
   plan task → continue `/studio-plan` from that step; edit task → `/studio-edit` (pipeline steps are cached, so re-running `harnesses.studio.edit prepare <id>` is cheap and safe); carousel → `/carousel`.
4. Tell the owner in one line where you're picking up.
