---
name: platform-writing
description: Expert platform writer for creator-os. Turns an idea (or a reference post link) into a draft for a specific account — Instagram reel script or carousel, LinkedIn text post or document carousel, X post or thread — built on the research harness's proven insights and the account's own past winners. Draft-only, owner picks the hook and posts it. Use for "write a post/thread/reel about…", "make this into a LinkedIn post", "write mine like this <link>", /write, /write-from.
---

# Platform Writing — the Writer's Desk

A draft here is **proof-backed**: every one names the insight(s) it uses (`insights_used`), and every hook is one of three
different types the owner chooses from. The owner posts it by hand — never post, schedule or DM anything.

## Read first
`./studio write context <account> --topic "<topic>"` (account profile, playbook, top insights + evidence, own winners/flops,
recent drafts) · `brain/platforms/<platform>.md` · `brain/brand-bible.md` (voice) · `brain/hooks-library.md` (hook types) ·
`memory/long-term/lessons.md`.
If the account file says `status: planned` or key fields are TODO, write anyway from the brand bible and say what's missing.

## Flow
1. **Account + format.** The account decides the platform and voice (`./studio write accounts`). Formats:
   instagram `reel | carousel` · linkedin `text | doc-carousel | video` · x `post | thread | video`.
2. **Angle.** One idea, one audience, one promise. Pick 1–2 insights from the context that fit (cite their ids). No insights for the
   platform yet → use the playbook and say so; suggest `/research-analyse` to the owner.
3. **Create the draft**: `./studio write new <account> --format <f> --title "<short title>" --idea "<one line>" --insights 3,7
   [--ref-url <url>] [--topic …]` → project folder + draft id + working memory + `context.json`.
4. **Write by format**
   - **IG reel / any video** → follow the `reel-scripting` skill from §1 "Sharpen the idea" in the project `write new` created
     (do not create another project). Output `plan.json` + `script.md`; `platforms` includes this account's platform.
     It continues in `/studio-edit` after the shoot.
   - **IG carousel / LinkedIn doc-carousel** → follow the `resource-carousel` skill (or a framework/lesson carousel with the same
     rules) → `carousel.json`; render with `./studio carousel <project>` (PNG slides + PDF for LinkedIn).
   - **LinkedIn text / X post / X thread** → write `post.json` (schema `core/schemas/post.schema.json`):
     3 hooks of different types → `chosen_hook: null` until the owner picks → `body` (or `thread` for X) starting with the hook,
     `cta`, `first_comment` for links, `hashtags`, `media` (what to attach: screenshot/demo/GIF — the owner's real material),
     `insights_used`, `reference_url`.
5. **Owner picks the hook** (approval gate). Show the 3 hooks numbered, with the insight each one draws on. Set `chosen_hook`,
   make the body/first post open with it, log the choice: `core.memory append <project> decisions "…"`.
6. **Validate**: `./studio write validate <draft-id>` — fixes until ✓ (X 280 chars per post; LinkedIn 3,000 chars, hook in the
   first ~210 chars, links in first comment). A clean text draft writes `post.md`, the copy-paste version.
7. **Hand over**: show `post.md` (or the shoot package / slides), then `./studio write status <id> approved` once the owner says
   it's good. When it's live, the owner (or you, with the URL) logs it: `./studio hq log <account> <url> --draft <id>`.

## Write from a link (`/write-from <url> [account]`)
1. Study it: `./studio research post add <url> --analyze` (video) or add the text with `--text-file` (LinkedIn/X), then write its
   breakdown (`./studio research analysis set …`) — hook type, structure, why it worked.
2. `write new … --ref-url <url>` and build **our own** version: same mechanism (hook type, structure, pacing), our topic, our
   voice, our material. Never copy their wording, footage or images; one short quote at most, credited, and only if it adds something.

## Platform craft (details in brain/platforms/)
- **Instagram**: reel = watch time + sends; carousel = saves (slide 1 hook with a number; slide 2 hooks again; last slide CTA).
- **LinkedIn**: the first 2 lines are the post; short lines; story → lesson → question; links in first comment.
- **X**: one specific idea per post (numbers, decisions, screenshots); threads: post 1 = hook + promise, every post stands alone.
- **Repurposing** (one idea → three platforms): keep the core claim and the proof; change the shape, never paste the same text.

## Self-check before showing the owner
- Would the target person stop for the first line alone? Is it specific (numbers, names, results)?
- Does it sound like the owner (brand bible), not like AI? Cut "unlock", "game-changer", "dive in", "in today's fast-paced world".
- Is every claim true and something the owner actually did/knows? Ask rather than invent results.
- `insights_used` filled (or "none yet" stated), validator clean.
