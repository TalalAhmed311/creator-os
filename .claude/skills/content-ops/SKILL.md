---
name: content-ops
description: HQ — the harness of harnesses for creator-os. Keeps the owner's own content database per account and platform (Instagram, LinkedIn, X), logs published posts against their drafts, collects metrics daily (1/3/7/30-day checkpoints), reviews what works for each account vs its own median, turns findings into lessons and brain proposals, steers research and writing, and repurposes winners across platforms. Use for "log this post", "update my stats", "how did my posts do", "what's working on my LinkedIn", "set up my accounts", "repurpose this", /hq-log, /hq-sync, /hq-review, /hq-account, /hq-repurpose.
---

# Content Ops — HQ

HQ connects the harnesses: **Research** finds what works for others → **Writer** drafts → **Studio** produces → the owner
posts → **HQ** logs it, measures it, learns → back to Research (what to study next) and Writer (what to make next).

## Read first
`brain/accounts/*.md` (what each account is for — the owner's words) · `./studio hq accounts` · `./studio hq review --json` ·
`data/hq/pending-metrics.md` · `memory/long-term/lessons.md` · `docs/HARNESS_PLAN.md` §3 (HQ).

## Accounts (`/hq-account <platform>`)
One file per account in `brain/accounts/` (`README.md` there has the format). The frontmatter feeds the tools; the body is
read in full by the writer — it should say how the page works, who it's for, what each format is for, what it must never post,
the plan. Interview the owner (≤ 6 questions, one message, pre-fill from what's known), write the file, show the diff, and save
only on a yes (it's `brain/`). Then `./studio hq accounts sync`.

## Logging (`/hq-log <account> <url>`)
`./studio hq log <account> <url> [--draft N] [--posted-at …] [--format …]` — with `--draft` the draft becomes `published` and the
post inherits its project, format, pillar and hook. Add any numbers the owner already has (`--views … --saves …`).
Find the draft with `./studio write list --account <account> --status approved`.

## Metrics (`/hq-sync`, daily)
- `./studio hq sync` fetches metrics for posts past a 1/3/7/30-day checkpoint, using the provider set per platform in `studio.json`
  (`instagram-graph` | `ytdlp` | `manual` | `auto` — `harnesses/hq/providers.py`). What it can't read goes to
  `data/hq/pending-metrics.md` with the exact commands to run.
- For pending posts: read the **public** counters from the post page (built-in browser `get_page_text`, or `agent-reach`) and add
  them `--source browser --quality verified`; private numbers (reach, saves, watch %, profile visits) come from the owner — ask once,
  one message listing all pending posts — or from an analytics export: `./studio hq metrics import <file.csv> --source <platform>-export`.
  Never log into the owner's accounts; never guess a number.
- Daily automation: `./studio hq schedule` shows the launchd job; the **owner** installs it with `./studio hq schedule --install`
  (Graph API secrets go in `~/.config/creator-os/env`, never in the repo).

## Review & learn (`/hq-review [account] [days]`)
1. `./studio hq review [--account A] [--days N]` → findings per account (format, hook type, pillar, length, weekday, research insight
   used), each vs that account's own median, plus top/bottom posts → `data/reports/hq/<date>-review.md`.
2. Write the report's `## Summary`: what to do more of / less of next week, with numbers. Low n → say so; don't over-read 2 posts.
3. Save durable findings as lessons: `.venv/bin/python -m core.memory remember "<finding with numbers>" --kind lesson --tags <account>,<platform>,<dimension>`.
   A lesson seen ≥ 3× → **propose** the change to the right brain file (`brain/platforms/<p>.md`, `brain/hooks-library.md`,
   `brain/accounts/<id>.md`) and wait for a yes.
4. Close the loop:
   - Research insights that worked for the owner (`insight` dimension) → confidence up (`./studio research insight add` the same
     pattern with the owner's post as evidence); ones that flopped twice → tell the owner, suggest retiring.
   - What to research next (a format/topic that beat the median but has no insights yet) → suggest `/research-analyse <topic>`.
   - What to write next → suggest 2–3 `/write` ideas per account built on the winners.

## Repurpose (`/hq-repurpose <post-url|draft-id> [to platforms]`)
Take a post that beat its account's median (score ≥ 1.5) and draft it for the other accounts: same core claim and proof,
reshaped per platform (IG reel → LinkedIn text story + X thread; IG carousel → LinkedIn doc-carousel + X thread). One `write new`
per target with `--ref-url <original>` and `--idea "repurpose of …"`; run the writer flow for each. Never paste the same text.

## Report to the owner
≤ 10 lines: what was logged/synced, what's pending (and what you need from them), the top finding per account, the next 2–3 moves.
