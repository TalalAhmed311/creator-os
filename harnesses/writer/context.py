"""Writer's brief for one account: who it's for, the platform playbook, the top proven insights, the posts behind them,
the account's own winners and flops, and recent drafts (so ideas don't repeat).

  ./studio write context <account> [--topic T] [--n 5] [--json]
"""
from __future__ import annotations

import sqlite3

from core import accounts, db
from core.common import BRAIN
from core.insights import ranked


def build(con: sqlite3.Connection, account_id: str, topic: str | None = None, n: int = 5) -> dict:
    acc = accounts.get(con, account_id)
    own = db.with_outlier_scores(con, db.post_table(con, "p.account_id = ?", (account_id,)))
    scored = [p for p in own if p["outlier"] is not None]
    scored.sort(key=lambda p: -p["outlier"])
    playbook = BRAIN / "platforms" / f"{acc['platform']}.md"
    return {
        "account": {k: acc[k] for k in ("id", "platform", "handle", "status", "purpose", "audience", "pillars", "formats",
                                        "cadence", "goals", "voice", "profile_path")},
        "account_notes": acc["body"],
        "formats": accounts.FORMATS.get(acc["platform"], {}),
        "playbook": str(playbook.relative_to(BRAIN.parent)) if playbook.exists() else None,
        "insights": [{k: i[k] for k in ("id", "kind", "platform", "topic", "pattern", "how_to_apply", "confidence", "seen",
                                        "avg_outlier", "evidence")} for i in ranked(con, platform=acc["platform"], topic=topic, n=n)],
        "own_winners": [_brief(p) for p in scored[:3]],
        "own_flops": [_brief(p) for p in scored[-3:][::-1]] if len(scored) >= 6 else [],
        "own_posts": len(own),
        "recent_drafts": db.dicts(con.execute("""SELECT id, format, title, status, created_at FROM drafts WHERE account_id = ?
                                                 ORDER BY id DESC LIMIT 10""", (account_id,))),
        "read_also": ["brain/brand-bible.md", "brain/hooks-library.md", "memory/long-term/lessons.md"],
    }


def _brief(p: dict) -> dict:
    return {"post_id": p["id"], "url": p["url"], "format": p["format"], "views": p["views"], "outlier": p["outlier"],
            "hook": p["hook_text"], "posted_at": (p["posted_at"] or "")[:10]}


def markdown(ctx: dict) -> str:
    a = ctx["account"]
    out = [f"# Writer context — {a['id']}", "",
           f"**{a['platform']}** @{a['handle'] or '(handle TODO)'} · {a['status']} · formats: {', '.join(ctx['formats'])}",
           f"- Purpose: {a['purpose'] or 'TODO'}", f"- Audience: {a['audience'] or 'TODO'}",
           f"- Pillars: {', '.join(a['pillars']) or 'TODO'} · Cadence: {a['cadence'] or 'TODO'}",
           f"- Goals: {a['goals'] or 'TODO'}", f"- Voice: {a['voice'] or 'see brain/brand-bible.md'}",
           f"- Profile: {a['profile_path']} · Playbook: {ctx['playbook'] or '—'}", ""]
    if ctx["account_notes"]:
        out += ["## Account notes", ctx["account_notes"], ""]
    out += ["## Top insights (use 1–2, cite their ids in insights_used)", ""]
    if not ctx["insights"]:
        out.append("_None for this platform yet — run /research-analyse first, or write from the playbook and say so._")
    for i in ctx["insights"]:
        out.append(f"- **#{i['id']}** [{i['kind']}, {i['confidence']}, seen {i['seen']}×, avg {i['avg_outlier'] or '—'}× normal] {i['pattern']}")
        if i["how_to_apply"]:
            out.append(f"  - how: {i['how_to_apply']}")
        for e in i["evidence"][:3]:
            out.append(f"  - e.g. @{e['author']} {e['url']} ({e['outlier'] or '—'}×)" + (f" — “{e['hook'][:80]}”" if e["hook"] else ""))
    out += ["", f"## This account's own posts ({ctx['own_posts']} logged)"]
    for label, rows in (("Winners", ctx["own_winners"]), ("Flops", ctx["own_flops"])):
        for p in rows:
            out.append(f"- {label[:-1]}: {p['outlier']}× own median · {p['format']} · {p['posted_at']} · {p['hook'] or ''} {p['url']}")
    if ctx["recent_drafts"]:
        out += ["", "## Recent drafts (don't repeat)"] + [f"- #{d['id']} {d['format']} · {d['status']} · {d['title']}"
                                                          for d in ctx["recent_drafts"]]
    out += ["", "Also read: " + ", ".join(ctx["read_also"])]
    return "\n".join(out)
