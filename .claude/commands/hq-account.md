---
description: HQ — set up or update one of your accounts (what the page is for, audience, formats, cadence, goals, plan)
argument-hint: <instagram|linkedin|x|tiktok|youtube> [handle]
---
Arguments: `$ARGUMENTS`

Load the `content-ops` skill (Accounts). The account files are `brain/` — the owner approves every change.

1. Open `brain/accounts/<platform>-*.md` if it exists (else start from `brain/accounts/README.md`). Pre-fill from it, the brand
   bible and memory.
2. Interview in ONE message (≤ 6 numbered questions, each answerable in a line): handle · who it's for (and their level) · what
   each format is for on this account · cadence · goal for the next 90 days · what it must never post. If the owner pastes a long
   description of how their pages work, use it as-is and only ask what's missing.
3. Write the file (frontmatter + a body in the owner's words: how the page works, the plan, examples they like). If the handle is new,
   name the file `<platform>-<handle>.md` and rename the placeholder (e.g. `x-curio.md` → `x-<handle>.md`) — update drafts that
   point at the old id: `./studio db sql "SELECT id FROM drafts WHERE account_id = '<old>'"` and tell the owner.
4. Show the diff, save on a yes, then `./studio hq accounts sync`.
