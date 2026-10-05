"""Learning loop: what works for *this* account, measured against its own normal.

Each post's score = its reach metric ÷ the account's median (reach metric = views, else impressions, else reach — latest
snapshot). Posts are grouped by format, hook type, pillar, length, weekday and the research insights the draft used;
a finding is a group whose median score beats another group's by ≥ 1.2× with ≥ min_group posts on each side.
Findings feed lessons (memory) and, at seen ≥ 3, proposals to brain/ — never edited without the owner's yes.
"""
from __future__ import annotations

import datetime as _dt
import json
import sqlite3
from collections import defaultdict
from statistics import median

from core import db
from core.common import STUDIO, Project, load_json, today

WEEKDAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


def _reach(p: dict) -> float | None:
    return next((p[k] for k in ("views", "impressions", "reach") if p.get(k) is not None), None)


def _project_features(project_id: str | None) -> dict:
    out: dict = {}
    if not project_id:
        return out
    root = Project(project_id).root
    for name in ("plan.json", "post.json"):
        f = root / name
        if f.exists():
            d = load_json(f)
            if d.get("hooks") and d.get("chosen_hook") is not None and d["chosen_hook"] < len(d["hooks"]):
                out["hook_type"] = d["hooks"][d["chosen_hook"]].get("type")
    if (root / "edl.json").exists():
        segs = load_json(root / "edl.json").get("segments", [])
        out["length_s"] = sum(s["out"] - s["in"] for s in segs)
    elif (root / "carousel.json").exists():
        out["slides"] = len(load_json(root / "carousel.json").get("slides", []))
    return out


def _length_bucket(f: dict) -> str | None:
    if f.get("slides"):
        return f"{f['slides']} slides" if f["slides"] < 6 else "6-10 slides" if f["slides"] <= 10 else "11+ slides"
    s = f.get("length_s")
    if s is None:
        return None
    return "<20s" if s < 20 else "20-35s" if s < 35 else "35-50s" if s < 50 else "50s+"


def posts_with_scores(con: sqlite3.Connection, account_id: str, since: str | None = None) -> list[dict]:
    rows = db.post_table(con, "p.account_id = ?" + (" AND p.posted_at >= ?" if since else ""),
                         (account_id, since) if since else (account_id,))
    vals = [v for v in map(_reach, rows) if v]
    med = median(vals) if vals else None
    for p in rows:
        v = _reach(p)
        p["reach_value"], p["score"] = v, (round(v / med, 2) if v and med else None)
        eng = sum(p.get(k) or 0 for k in ("likes", "comments", "shares", "saves", "reposts"))
        p["engagement_rate"] = round(eng / v * 100, 2) if v else None
        f = _project_features(p["project_id"])
        p["hook_type"] = p.get("hook_type") or f.get("hook_type")
        p["length"] = _length_bucket(f) if f else (_length_bucket({"length_s": p["duration_s"]}) if p.get("duration_s") else None)
        try:
            p["weekday"] = WEEKDAYS[_dt.datetime.fromisoformat(p["posted_at"][:19]).weekday()] if p["posted_at"] else None
        except ValueError:
            p["weekday"] = None
        p["insights"] = [r[0] for r in con.execute(
            "SELECT di.insight_id FROM drafts d JOIN draft_insights di ON di.draft_id = d.id WHERE d.post_id = ?", (p["id"],))]
    return rows


def findings(rows: list[dict], min_group: int = 2) -> tuple[dict, list[str]]:
    dims = {"format": lambda p: [p["format"]], "hook_type": lambda p: [p["hook_type"]], "pillar": lambda p: [p["pillar"]],
            "length": lambda p: [p["length"]], "weekday": lambda p: [p["weekday"]],
            "insight": lambda p: [f"#{i}" for i in p["insights"]] or ["none"]}
    by: dict = {}
    out: list[str] = []
    for dim, keys in dims.items():
        g = defaultdict(list)
        for p in rows:
            if p["score"] is None:
                continue
            for k in keys(p):
                if k:
                    g[k].append(p["score"])
        by[dim] = {k: {"n": len(v), "median_score": round(median(v), 2)} for k, v in g.items()}
        valid = {k: v for k, v in by[dim].items() if v["n"] >= min_group}
        if len(valid) >= 2:
            best = max(valid, key=lambda k: valid[k]["median_score"])
            worst = min(valid, key=lambda k: valid[k]["median_score"])
            lo = valid[worst]["median_score"]
            if lo > 0 and valid[best]["median_score"] / lo >= 1.2:
                out.append(f"{dim}: '{best}' posts reach {valid[best]['median_score']}× your median vs "
                           f"{lo}× for '{worst}' (n={valid[best]['n']}/{valid[worst]['n']})")
    return by, out


def review(con: sqlite3.Connection, account_id: str | None = None, days: int | None = None, min_group: int = 2,
           write: bool = True) -> dict:
    since = (_dt.date.today() - _dt.timedelta(days=days)).isoformat() if days else None
    ids = [account_id] if account_id else [r[0] for r in con.execute("SELECT id FROM accounts ORDER BY id")]
    result = {"date": today(), "since": since, "accounts": {}}
    for aid in ids:
        rows = posts_with_scores(con, aid, since)
        scored = sorted((p for p in rows if p["score"] is not None), key=lambda p: -p["score"])
        by, found = findings(rows, min_group)
        vals = [p["reach_value"] for p in rows if p["reach_value"]]
        result["accounts"][aid] = {
            "posts": len(rows), "with_metrics": len(scored), "median_reach": median(vals) if vals else None,
            "top": [_short(p) for p in scored[:3]], "bottom": [_short(p) for p in scored[-3:][::-1]] if len(scored) > 3 else [],
            "by": by, "findings": found,
            "missing_metrics": [p["url"] for p in rows if p["reach_value"] is None],
        }
    if write:
        path = _write(result, account_id)
        result["report"] = str(path.relative_to(STUDIO)) if path.resolve().is_relative_to(STUDIO) else str(path)
    return result


def _short(p: dict) -> dict:
    return {"post_id": p["id"], "url": p["url"], "score": p["score"], "reach": p["reach_value"], "format": p["format"],
            "hook_type": p["hook_type"], "engagement_rate": p["engagement_rate"], "posted_at": (p["posted_at"] or "")[:10]}


def _write(result: dict, account_id: str | None):
    reports = db.data_dir() / "reports" / "hq"
    reports.mkdir(parents=True, exist_ok=True)
    out = reports / f"{result['date']}-review{'-' + account_id if account_id else ''}.md"
    summary = "## Summary\n_(HQ analyst: 3–5 lines — what to do more of / less of next week, with the numbers)_\n"
    if out.exists():
        old = out.read_text()
        i, j = old.find("## Summary"), old.find("\n## ", old.find("## Summary") + 3)
        if i >= 0:
            summary = old[i:j if j > i else None].rstrip() + "\n"
    lines = [f"# HQ review — {result['date']}" + (f" (since {result['since']})" if result["since"] else ""), "", summary]
    for aid, a in result["accounts"].items():
        lines += [f"## {aid}", "", f"{a['posts']} posts · {a['with_metrics']} with metrics · median reach {a['median_reach'] or '—'}", ""]
        if a["findings"]:
            lines += ["**Findings**"] + [f"- {f}" for f in a["findings"]] + [""]
        elif a["with_metrics"] < 4:
            lines += ["_Not enough posts with metrics yet for findings (need ≥ 2 per group)._", ""]
        for label in ("top", "bottom"):
            if a[label]:
                lines += [f"**{label.title()}**"] + [f"- {p['score']}× · {p['format']} · {p['hook_type'] or '—'} · {p['posted_at']} · {p['url']}"
                                                    for p in a[label]] + [""]
        if a["missing_metrics"]:
            lines += [f"Missing metrics: {len(a['missing_metrics'])} posts (see data/hq/pending-metrics.md)", ""]
    out.write_text("\n".join(lines))
    (out.with_suffix(".json")).write_text(json.dumps(result, indent=2, default=str))
    return out
