"""Research report: the top insights with their evidence, the outlier posts and the creators covered → markdown.

data/reports/research/<date>-<slug>.md. The "## Summary" section (top) is the analyst's and survives re-generation.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

from core import db
from core.common import today
from harnesses.research import insights, posts



def _n(v) -> str:
    if v is None:
        return "—"
    return f"{v / 1e6:.1f}M" if v >= 1e6 else f"{v / 1e3:.1f}K" if v >= 1e3 else f"{v:g}"


def build(con: sqlite3.Connection, slug: str, platform: str | None = None, topic: str | None = None, n: int = 5,
          out_dir: Path | None = None) -> Path:
    out = (out_dir or db.data_dir() / "reports" / "research") / f"{today()}-{db.slug(slug)}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    top = insights.ranked(con, platform=platform, topic=topic, n=n)
    outliers = posts.listing(con, platform=platform, limit=15)
    authors = sorted({p["author_handle"] for p in outliers if p["author_handle"]})
    scope = " · ".join(x for x in (platform, topic) if x) or "all platforms"

    summary = "## Summary\n_(analyst: 3–5 lines — what to make next and why, citing the insights below)_\n"
    if out.exists():  # keep the analyst's summary across re-generation
        old = out.read_text()
        i, j = old.find("## Summary"), old.find("## Top insights")
        if i >= 0 and j > i:
            summary = old[i:j].rstrip() + "\n"
    lines = [f"# Research — {slug}", "", f"{today()} · {scope} · {len(top)} insights · {len(outliers)} outlier posts", "",
             summary]
    lines += ["## Top insights", ""]
    if not top:
        lines.append("_No insights yet — analyse outlier posts and add patterns with `./studio research insight add`._")
    for i, r in enumerate(top, 1):
        lines += [f"### {i}. {r['pattern']}",
                  f"{r['kind']} · {r['platform'] or 'any platform'} · confidence {r['confidence']} · seen {r['seen']}× · "
                  f"{len(r['evidence'])} posts · avg outlier {r['avg_outlier'] or '—'}×", ""]
        if r["how_to_apply"]:
            lines += [f"**How to apply:** {r['how_to_apply']}", ""]
        for e in r["evidence"]:
            lines.append(f"- [@{e['author']}]({e['url']}) — {_n(e['views'])} views, {e['outlier'] or '—'}× their normal"
                         + (f" — “{e['hook'][:90]}”" if e["hook"] else ""))
        lines.append("")
    lines += ["## Outlier posts", "", "| # | Creator | Views | × normal | Basis | Hook | Post |", "|--:|---|--:|--:|---|---|---|"]
    for i, p in enumerate(outliers, 1):
        hook = (p["hook_text"] or "").replace("|", "/")[:60]
        lines.append(f"| {i} | @{p['author_handle']} | {_n(p['views'])} | {p['outlier'] or '—'} | {p['outlier_basis'] or '—'} | {hook} | [link]({p['url']}) |")
    lines += ["", f"Creators in this report: {', '.join('@' + a for a in authors) or '—'}", "",
              "Numbers: public counters at capture time (yt-dlp = platform's own counter) or third-party estimates; "
              "see `creator_snapshots.source` / `metric_snapshots.source`.", ""]
    out.write_text("\n".join(lines))
    return out
