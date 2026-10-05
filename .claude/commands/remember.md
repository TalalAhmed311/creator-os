---
description: Save something to the studio's long-term memory right now
argument-hint: <note>
---
Note: `$ARGUMENTS`

Classify it: a stable taste → `preference`; something that worked/failed → `lesson`; a content idea → `idea` (tag the pillar); story progress → `pillar` (with `--pillar`). Pick 1–3 short tags.
Run `.venv/bin/python -m pipeline.memory remember "<cleaned-up note>" --kind <kind> --tags <tags> [--pillar <pillar>]`.
Reply in one line: where it was saved, and whether it merged with an existing memory (seen N×). If the result says `"promote": true`, propose adding it to the relevant `brain/` file and wait for a yes.
