# creator-os — Harness Plan

Status: **Phases 0–5 built; Phase 6 scaffolded** — waiting on the owner's account details (`/hq-account`) · 2026-10-06

`personal-studio` grows into **creator-os**: one repo, several harnesses that share code and one database.
Same principle as today: Claude decides and writes **structured data**; deterministic tools execute it.
Everything stays **draft-only** — creator-os never posts on its own; the owner publishes by hand.

## Decisions so far

| Question | Decision |
|---|---|
| Repo name | `creator-os` (rename at the end of Phase 1, after the restructure is green) |
| Posting | Draft only. No auto-posting. |
| Research data access | Claude's plugins and connectors (see §4), not hand-written scrapers |
| Creator seed | Owner's Instagram research → `docs/research/2026-10-05-instagram-ai-tech-creators.md` (75 creators, 20 in the research set) |
| Own accounts | Detailed account profiles come **last**. Known so far: Instagram `@buildwith.talal` (AI, research, products being built, tools, learning-material carousels); X (build-in-public for the product **Curio**); LinkedIn (TBD) |

## 1. Repo layout (target)

```
creator-os/
├── CLAUDE.md                 # top-level router: which harness handles what
├── .claude/                  # ONE .claude at root (commands only load from root)
│   ├── commands/             #   namespaced: /studio-*, /research-*, /write-*, /hq-*
│   ├── agents/               #   grouped by prefix
│   └── skills/
├── core/                     # shared by every harness
│   ├── fetch/                #   download.py, instagram.py (+ platform fetchers later)
│   ├── media/                #   convert.py, clip.py
│   ├── providers/            #   transcriber + face detector interfaces
│   ├── schemas/              #   plan / edl / carousel contracts
│   ├── db/                   #   SQLite schema, migrations, query helpers (Phase 2)
│   └── common.py, memory.py, refs.py, cli.py, deps.py
├── data/
│   ├── creator-os.db         # single source of truth
│   └── media/<platform>/<id>/   # downloaded references (today's references/ moves here)
├── brain/                    # human-readable, owner-controlled (unchanged rules)
│   └── accounts/<platform>-<handle>.md   # NEW: what each account is for
├── harnesses/
│   ├── studio/               # existing: edit bay, carousel, remotion, webstudio
│   ├── research/             # agent 1
│   ├── writer/               # agent 2
│   └── hq/                   # agent 3 — harness of harnesses
└── studio                    # CLI grows: ./studio research|write|hq|edit|…
```

Why SQLite: daily metric snapshots × posts × platforms + creators + insights is relational time-series data; CSV breaks.
Agents still render markdown reports from the DB, so humans keep reading `brain/` and reports, not tables.

## 2. Shared data model

| Table | Holds |
|---|---|
| `accounts` | the owner's accounts: platform, handle, purpose, audience, pillars, cadence, goals |
| `creators` | people studied: name, primary/secondary niche, cluster, country, account type, original (yes/unclear), status `candidate / tracked / dropped`, signal label, why tracked, in_research_set |
| `creator_handles` | one row per creator per platform (IG / LinkedIn / X) |
| `creator_snapshots` | followers, posts, typical views, posting frequency **with `source`, `captured_at`, `verified\|estimated`** — numbers are never stored without provenance |
| `posts` | any post (owner's or a creator's): platform, url, author, format (reel / carousel / text / thread / doc), posted_at, transcript path, topic, pillar |
| `metric_snapshots` | post_id, captured_at, views, likes, comments, shares, saves, watch %, impressions — time series, never overwritten |
| `analyses` | structured breakdown per post: hook type, hook text, visual hook, structure, pacing, CTA, why it worked |
| `insights` | patterns with evidence post_ids, platform, confidence, seen count → the "top 5" |
| `drafts` | writer output: target account, insights used, status (`draft / approved / published`), linked post once live |

Key metrics:
- **Outlier score** = post views ÷ creator's median views. What to copy is "8× their normal", not raw views.
- **Reach ratio** = typical views ÷ followers (already used in the seed research).

The seed research's provenance codes (A = Apify, H = Hafi, S = Socialpruf, …) map straight into `creator_snapshots.source`.

## 3. The three new harnesses

### Research (agent 1)
- `/research-analyse <topic | creator | url>` — pick posts from the creator DB (by platform / niche / cluster),
  fetch, transcribe (video) or read (text), rank by outlier score, break down, write the **top 5 patterns** to `insights` + a readable report.
- `/research-creators discover <niche> [platform]` — find new creators, score them (same weighted score as the seed:
  reach, relevance, consistency, originality, size), add as `candidate`. Owner promotes to `tracked`.
- `/research-creators refresh` — new snapshots for tracked creators; closes data gaps (missing reel views, peaks, frequency).
- Reuses `pipeline/refs.py` (download → transcript → cuts → hook frames → analysis.md) as the video-analysis engine.

### Writer (agent 2)
- Input: idea + **target account** (account ⇒ platform, voice, format).
- Pulls relevant top-5 insights, the evidence posts behind them, and the owner's own past winners on that account.
- Accepts a link: "write mine like this" → download → transcribe → analyse → use as reference.
- Output per platform:
  - IG reel → `plan.json` + `script.md` (feeds the existing Edit Bay unchanged)
  - IG carousel → `carousel.json` (feeds the Design Desk)
  - LinkedIn → text post / document carousel
  - X → single post / thread
- Absorbs the existing `reel-scripting` skill + scriptwriter / hook-specialist agents; `/studio-plan` becomes the writer's reel path.
- Hook rule stays: 3 options, owner picks.

### HQ — harness of harnesses (agent 3)
- Account registry `brain/accounts/*.md` (filled in last, when the owner gives the details).
- Content DB of the owner's posts, categorised by account/platform (named when generating).
- `/hq-log <account> <url>` registers a published post and links it to its draft (replaces `/log` + `content-log.csv`).
- `hq sync` (daily, scheduled): metrics for every post at 1d / 3d / 7d / 30d.
- Weekly learning pass → lessons per account → proposals to `brain/` (approval gate) and research priorities.
- Repurposing: one idea → IG reel + LinkedIn post + X thread drafts.

**Loop:** Research → insights → Writer → Studio produces → owner posts → HQ logs + syncs → learnings → Research & Writer.

## 4. Research & metrics access (via Claude plugins/connectors)

Access is a **pluggable interface**, like the transcriber: chosen per platform in `studio.json`.

| Need | Providers to use (in order) |
|---|---|
| Web research, rankings, creator discovery | Exa MCP (`web_search_exa`, `web_fetch_exa`), WebSearch / WebFetch, `deep-research` skill |
| Reading platform posts (IG / X / LinkedIn) | `agent-reach` skill (multi-platform backends) → built-in browser → Claude in Chrome |
| Downloading video for transcription | yt-dlp (`core/fetch`) — already works for IG reels |
| Owner's own metrics | IG Graph API (if Business/Creator + Meta app) → platform analytics export dropped in `inbox/` → browser read → manual entry |

Rules: read-only on platforms; never log in or post on the owner's behalf; respect rate limits;
every number stored with its source and date.

## 5. Build order

| Phase | What | Done when |
|---|---|---|
| 0 ✅ | **Initial git commit** (repo has none — baseline before moving files) | clean `git log` |
| 1 ✅ | **Restructure** into `core/` + `harnesses/studio/`; keep `./studio` and every existing command working; rename repo to `creator-os` (folder rename pending — see note below) | `pytest` green, `./studio doctor` OK, `/studio-edit` dry run OK |
| 2 ✅ | **Data layer**: SQLite schema + migrations, import the 75-creator seed, migrate `content-log.csv` | `./studio db stats` shows 75 creators with sourced snapshots |
| 3 ✅ | **Research agent**: analyse + creator discover/refresh, top-5 insights | runs on the 20-creator research set, produces insights + report |
| 4 ✅ | **Writer agent**: IG reel / carousel, LinkedIn, X outputs, link-as-reference | one idea → drafts for all three platforms |
| 5 ✅ | **HQ**: content DB, `/hq-log`, daily `hq sync` (scheduled), weekly learning pass | metrics appear daily without manual steps where an API/export exists |
| 6 ◐ | **Account profiles**: owner's detailed page plans → `brain/accounts/` | writer + HQ use per-account goals |

## What was built (2026-10-06)

| Phase | Result |
|---|---|
| 2 | `core/db` (SQLite, migrations, provenance on every number), `./studio db stats|sql|export|restore`; 75 creators, 217 sourced snapshots from the seed; `content-log.csv` importer (`./studio hq import-log`) |
| 3 | `harnesses/research` + `./studio research …`: creators (score, track/drop, link platforms, snapshots), posts (yt-dlp download + analysis, text posts via connectors, refresh), outlier ranking, insights (merge + rank), reports; skill `content-research`, agents `research-analyst`, `creator-scout`, `/research-analyse`, `/research-creators`. Verified on a live IG reel. |
| 4 | `harnesses/writer` + `./studio write …`: context brief per account, drafts as projects (`plan.json` / `carousel.json` / new `post.json` contract), platform rules (X 280, LinkedIn see-more/links), `post.md` copy-paste; `brain/platforms/*`; skill `platform-writing`, agent `platform-writer`, `/write`, `/write-from` |
| 5 | `harnesses/hq` + `./studio hq …`: account sync, log (closes drafts), metrics add/CSV import, 1/3/7/30-day `due`/`sync` with providers (`instagram-graph`, `ytdlp`, `manual`), pending list, review vs own median (format, hook, pillar, length, weekday, insight used), launchd daily job (`hq schedule --install`); skill `content-ops`, agent `hq-analyst`, `/hq-log` (`/log`), `/hq-sync`, `/hq-review`, `/hq-account`, `/hq-repurpose`. Old `content_log.py` removed. |
| 6 | `brain/accounts/` with `instagram-buildwith.talal`, `x-curio`, `linkedin-talal` (TODO fields) — filled by `/hq-account` once the owner describes the pages |

## Open items
- **Owner:** describe each page (`/hq-account instagram|x|linkedin`) — X handle, LinkedIn status, audiences, goals, cadence.
- **Owner:** install the daily sync when ready: `./studio hq schedule --install`.
- **Owner (optional):** Instagram Graph API — Business/Creator account + Meta app → `IG_ACCESS_TOKEN`, `IG_USER_ID` in
  `~/.config/creator-os/env`. Without it, IG views come from the app or an export (yt-dlp can't read IG play counts).
- First real research run: `/research-analyse` on the 20-creator set (each run ≤ 20 downloads).
- Folder rename `personal-studio` → `creator-os`: do it outside a Claude session, then run `scripts/setup.sh`
  (venv console scripts like yt-dlp carry absolute paths) and update `.claude/launch.json`.
- X metrics: `ytdlp` reads video posts only; text posts → manual/export unless an API budget is added later.
- Creator seeds for LinkedIn and X (the current seed is Instagram only).
