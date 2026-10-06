---
project_id: research-2026-10-06-instagram-reach
pillar: build-in-public
task: other
status: done
started: 2026-10-06T18:56
updated: 2026-10-06T19:26
---
## Goal
Research: what gets reach on Instagram for AI / tech / build-in-public reels and carousels (20 tracked creators)

## Requirements

## Context loaded from long-term memory

## Decisions (with reason)
- [19:00] (research-analyst) ## AI explainers & tools — resumed after API overload; DB had 0 posts for my 13 creators, 0 downloads used so far. Plan: browser reels tabs for play counts, prioritise tenfoldmarc/samalytics/nima.eslamloo/adamstewartmarketing.
- [19:00] (research-analyst) ## Builders & developers — scope: 7 tracked IG builders (daniallqureshi, sicknider.raw, mewtru, buildwithcody, vibecodeapp, pikacodes, realrileybrown); topic build-in-public; cap 10 downloads (resumed after API overload: 0 of my posts were in DB, 0 downloads used).
- [19:08] (research-analyst) [Builders] Collected via built-in browser reels grid (logged-out play counts, verified; K/M counters rounded). sicknider.raw = age-restricted logged-out (no posts); buildwithcody = 'Profile isn't available' (renamed/removed). Old pinned reels from 2024-25 skipped (pikacodes, vibecodeapp); 2026 pinned kept.
- [19:11] (research-analyst) AI explainers & tools: 67 reels from 7 creators added (views read from public reels grid, browser, verified; pinned posts skipped). Bug: post metrics --date YYYY-MM-DD sorts before yt-dlp's timestamped snapshot so latest_metrics hid views; re-added with --date 2026-10-06T21:00:00. Using 10 analyses on 115,128,224,158,142,136,169,213 + flops 171,228.
- [19:22] (research-analyst) [Builders] 49 reels stored (daniallqureshi 12, mewtru 12, realrileybrown 10, pikacodes 9, vibecodeapp 6). 10/10 downloads used: 135,155,168,172,195,181,189,212 (winners) + 150,182 (flops). Insights 11-15 (--topic build-in-public). Report data/reports/research/2026-10-06-ig-build-in-public.md with Summary. Excluded pikacodes 13.2M Meta collab (203) from evidence.
- [19:25] (research-analyst) AI explainers & tools DONE: 103 reels / 11 creators (rowancheung, thevarunmayya not reachable - IG logged-out rate limit). 10 downloads: 115,128,224,158,142,232,249,171,228,264 (136 only fetched metadata after stop). Insights 16-21 (ai-explained/resources). Report data/reports/research/2026-10-06-ig-ai-explained.md.

## My feedback

## Progress
- [19:22] (research-analyst) [Builders] BUG: 'post add' with download writes a yt-dlp metric snapshot without views that becomes latest and blanks browser views → re-applied views with 'post metrics'. BUG: analyze crashed for 212 (cv2 imdecode in contact sheet). Untested hypothesis: comment-keyword CTA isn't the reach driver (same Danial caption: 8.3x vs 0.35x).

## Open items / ideas spotted
