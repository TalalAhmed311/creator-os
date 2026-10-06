---
project_id: research-2026-10-06-linkedin-x-reach
pillar: build-in-public
task: other
status: done
started: 2026-10-06T18:34
updated: 2026-10-06T18:44
---
## Goal
Research: what gets reach on LinkedIn (AI research/technical explainers) and X (product build in public)

## Requirements

## Context loaded from long-term memory

## Decisions (with reason)
- [18:41] (research-analyst) X: excluded posts <24h old (views still rising) and self-reposts/replies so the creator median reflects mature original posts. marclou's top outliers are fitness/personal (off-topic) - kept in the median but only the format mechanics used, flagged in insight #4.
- [18:41] (research-analyst) X: anti-pattern 'link/ask in body' stored as a cta insight backed by the winners (no URL in body) with flops cited in how_to_apply, since insights need >=1.5x evidence.
- [18:42] (research-analyst) ## LinkedIn — outlier metric: ./studio research outliers needs views; LinkedIn has no public views, so LinkedIn posts are ranked on REACTIONS ÷ that creator's median reactions (46 posts, 5 tracked creators, 7-12 each). Reactions stored as likes, never as views. Source: logged-out public post page JSON-LD (LinkedIn's own counters), quality verified.
- [18:42] (research-analyst) ## LinkedIn — excluded: 2 reshares (mgrootendorst GPT-OSS, luisgserrano Illustrated Transformer) and 1 post with no reaction counter (sebastianraschka PyTorch talk). Reposts not shown logged-out, left empty. Format 'image' = single image/diagram on the logged-out page; doc carousels only detectable in one page layout, so some 'image' posts may be documents.

## My feedback

## Progress
- [18:44] (research-analyst) ## LinkedIn — 46 posts (ids 69-114) from 5 tracked creators, 17 breakdowns, 5 insights (ids 6-10), report data/reports/research/2026-10-06-linkedin-ai-research.md. Top: reference maps 2.17x, numbered-layer structure 3.05x, personal-experiment hook 1.75x (all on reactions ÷ creator median). Plain paper breakdowns sit around 1x; release posts flop at 0.29-0.59x.

## Open items / ideas spotted

## X
- [18:41] (research-analyst) Source: api.fxtwitter.com /2/profile/<h>/statuses (timeline) + /<h>/status/<id> (counters) -> verified (x-public-api). syndication.twitter.com returned 429 (rate limit). 67 original posts (excl. replies, reposts, posts <24h old) from 6 tracked creators -> post ids 2-68. Candidates mubashariqbal (latest posts from 2024) and rameerez (sparse, off-topic) skipped. Studied 14 winners + 6 flops (analysis set). Insights x/build-in-public ids 1-5; report data/reports/research/2026-10-06-x-build-in-public.md

## open items
- [18:44] (research-analyst) ## LinkedIn — gaps: no views on LinkedIn; reposts hidden logged-out; doc-carousel vs single image not reliably detectable (only 1 confirmed doc carousel, so no format verdict); post 69 has a duplicate identical metric snapshot (harmless). Small-account check not done: the 'related posts' sidebar on public post pages lists small accounts posting the same paper, which could be a source for scouting under-10K LinkedIn creators.
