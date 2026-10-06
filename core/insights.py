"""Insight ranking, shared by the research harness (which writes insights) and the writer/HQ (which read them).

Rank score: confidence (low 1 · medium 2 · high 3) × 2 + seen + evidence posts + average outlier of the evidence
(capped at 10) ÷ 2. Patterns proven by several posts that beat their creators' normal reach rise.
"""
from __future__ import annotations

import sqlite3
from statistics import mean

from rapidfuzz import fuzz

from core import db

CONF = {"low": 1, "medium": 2, "high": 3}


def evidence(con: sqlite3.Connection, insight_id: int) -> list[dict]:
    rows = db.post_table(con, "p.id IN (SELECT post_id FROM insight_evidence WHERE insight_id = ?)", (insight_id,))
    return db.with_outlier_scores(con, rows)


def ranked(con: sqlite3.Connection, platform: str | None = None, topic: str | None = None, kind: str | None = None,
           n: int | None = None, include_retired: bool = False) -> list[dict]:
    where, params = ["1" if include_retired else "status = 'active'"], []
    if platform:
        where.append("(platform = ? OR platform IS NULL)")
        params.append(platform)
    if kind:
        where.append("kind = ?")
        params.append(kind)
    rows = db.dicts(con.execute(f"SELECT * FROM insights WHERE {' AND '.join(where)}", params))
    if topic:
        rows = [r for r in rows if not r["topic"] or fuzz.partial_ratio(topic.lower(), r["topic"].lower()) >= 70
                or fuzz.partial_ratio(topic.lower(), r["pattern"].lower()) >= 70]
    for r in rows:
        ev = evidence(con, r["id"])
        outs = [min(p["outlier"], 10) for p in ev if p["outlier"] is not None]
        r["evidence"] = [{"post_id": p["id"], "url": p["url"], "author": p["author_handle"], "views": p["views"],
                          "likes": p["likes"], "outlier": p["outlier"], "outlier_metric": p["outlier_metric"], "hook": p["hook_text"]} for p in ev]
        r["avg_outlier"] = round(mean(outs), 2) if outs else None
        r["rank_score"] = round(CONF[r["confidence"]] * 2 + r["seen"] + len(ev) + (mean(outs) / 2 if outs else 0), 2)
    rows.sort(key=lambda r: -r["rank_score"])
    return rows[:n] if n else rows
