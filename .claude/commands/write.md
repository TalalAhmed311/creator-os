---
description: Writer's Desk — idea → draft for one account (IG reel/carousel, LinkedIn post/doc, X post/thread), built on proven insights
argument-hint: <account | platform> [format] <idea>
---
Arguments: `$ARGUMENTS`

Load the `platform-writing` skill first. You are the **showrunner** (`.claude/agents/showrunner.md`).

1. **Account + format.** Resolve the account from the arguments (`./studio write accounts`; "linkedin" → the linkedin account,
   "x"/"twitter" → the x account, "instagram"/"ig" → instagram). Format from the arguments, else the platform default
   (instagram reel, linkedin text, x post). Ask only if it's genuinely ambiguous.
2. **Context.** `./studio write context <account> --topic "<idea>"` — pick the 1–2 insights to build on.
3. **Draft.** `./studio write new <account> --format <f> --title "…" --idea "…" --insights <ids>` → draft id + project.
4. **Write.**
   - reel / video → run the `/studio-plan` flow from step 3 (interview → strategist → hook-specialist → scriptwriter) **in this
     project**; pass the chosen insights to the hook-specialist.
   - carousel / doc-carousel → the `/carousel` flow from step 3 in this project.
   - text / post / thread → delegate to **platform-writer** with the draft id.
5. **Owner picks the hook** (show 3, numbered). Set `chosen_hook`, finish the copy, `./studio write validate <id>` until ✓.
6. Show the result (`post.md`, or the shoot package / slides). On "good": `./studio write status <id> approved`.
   Remind: post it yourself, then `/hq-log <account> <url>` (links the draft and starts the metrics).
