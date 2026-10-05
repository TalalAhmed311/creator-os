# Harnesses

Each harness is one job of creator-os: its own Python tools, plus agents/commands/skills in the root `.claude/`
(namespaced by prefix). Harnesses share `core/` and the data folders at the repo root. Plan: `docs/HARNESS_PLAN.md`.

| Harness | Status | Does | Commands |
|---|---|---|---|
| `studio/` | live | raw footage → finished reel (Edit Bay), carousels (Design Desk), Web Studio | `/studio-*`, `/carousel`, `/ref`, `/clip`, `/convert`, `/yt`, `/ig`, `/log` |
| `research/` | planned (Phase 3) | creator database, content analysis, top-5 insights | `/research-*` |
| `writer/` | planned (Phase 4) | platform-specific drafts (IG reel/carousel, LinkedIn, X) from insights | `/write-*` |
| `hq/` | planned (Phase 5) | own-content DB, daily metrics sync, learning loop across platforms | `/hq-*` |

Rules for a new harness:
- Python lives in `harnesses/<name>/` and runs as `.venv/bin/python -m harnesses.<name>.<tool>`; add a route in `core/cli.py`.
- Import from `core`, never from another harness. Anything two harnesses need moves to `core/`.
- Agents, commands and skills go in the root `.claude/` (Claude Code only loads commands from there), prefixed with the harness name.
