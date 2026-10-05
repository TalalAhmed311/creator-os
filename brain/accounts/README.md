# Accounts

One file per account you post from: `<platform>-<handle>.md` (X with no handle yet: `x-curio.md`). The file name is the
account id used everywhere (`./studio write new <id> …`, `./studio hq log <id> <url>`).

The frontmatter is read by the tools; the text below it is read in full by the writer and HQ agents — put everything
about how the page works there: what it's for, who it's for, what it must never post, examples you love, your plan.
Fill or update one with `/hq-account <platform>` (a short interview), or edit by hand — `./studio hq accounts sync` picks it up.

```
---
platform: instagram          # instagram | linkedin | x | tiktok | youtube
handle: buildwith.talal      # without @; TODO until known
status: active               # active | planned | paused
purpose: one line
audience: who, skill level, what they want
pillars: [ai-explained, build-in-public, resources]
formats: [reel, carousel]    # instagram: reel, carousel · linkedin: text, doc-carousel, video · x: post, thread, video
cadence: e.g. 3 reels + 2 carousels / week
goals: e.g. 10K followers by …; saves per carousel > 100
voice: how this account sounds (defaults to brain/brand-bible.md)
---
```
