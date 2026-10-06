"""Insights: patterns behind outlier posts, with the posts that prove them. The writer's "top 5" come from here.

Adding a pattern that matches an existing one (same kind and platform, ≥ 85% similar wording) doesn't create a
duplicate: it bumps `seen`, merges the evidence and keeps the higher confidence.

Ranking lives in core/insights.py (the writer and HQ read it too).
"""
from __future__ import annotations

import sqlite3

from rapidfuzz import fuzz

from core import db
from core.insights import CONF, evidence, ranked  # noqa: F401  (re-exported for the research CLI)

KINDS = ("hook", "structure", "format", "visual", "topic", "cadence", "cta", "other")


def add(con: sqlite3.Connection, pattern: str, kind: str, platform: str | None = None, topic: str | None = None,
        how: str | None = None, evidence: list[int] | None = None, confidence: str = "low") -> dict:
    if kind not in KINDS:
        raise SystemExit(f"kind must be one of {', '.join(KINDS)}")
    evidence = evidence or []
    for pid in evidence:
        if not db.find_post(con, pid):
            raise SystemExit(f"evidence post {pid} is not in the database (research post add <url>)")
    same = con.execute("SELECT * FROM insights WHERE kind = ? AND status = 'active' AND platform IS ?", (kind, platform)).fetchall()
    match = max(same, key=lambda r: fuzz.token_set_ratio(r["pattern"], pattern), default=None)
    with con:
        if match and fuzz.token_set_ratio(match["pattern"], pattern) >= 85:
            iid = match["id"]
            conf = max(match["confidence"], confidence, key=CONF.get)
            con.execute("""UPDATE insights SET seen = seen + 1, confidence = ?, how_to_apply = COALESCE(?, how_to_apply),
                           topic = COALESCE(topic, ?), updated_at = ? WHERE id = ?""", (conf, how, topic, db.now(), iid))
            merged = True
        else:
            iid = con.execute("""INSERT INTO insights (platform, topic, kind, pattern, how_to_apply, confidence, created_at, updated_at)
                                 VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                              (platform, topic, kind, pattern, how, confidence, db.now(), db.now())).lastrowid
            merged = False
        con.executemany("INSERT OR IGNORE INTO insight_evidence (insight_id, post_id) VALUES (?, ?)", [(iid, p) for p in evidence])
    return {"insight_id": iid, "merged": merged}


def add_evidence(con: sqlite3.Connection, insight_id: int, evidence: list[int]) -> dict:
    """Attach more proving posts to an existing insight (e.g. one another analyst found later)."""
    if not con.execute("SELECT 1 FROM insights WHERE id = ?", (insight_id,)).fetchone():
        raise SystemExit(f"no insight {insight_id} (research insight list)")
    for pid in evidence:
        if not db.find_post(con, pid):
            raise SystemExit(f"evidence post {pid} is not in the database (research post add <url>)")
    with con:
        before = con.execute("SELECT COUNT(*) FROM insight_evidence WHERE insight_id = ?", (insight_id,)).fetchone()[0]
        con.executemany("INSERT OR IGNORE INTO insight_evidence (insight_id, post_id) VALUES (?, ?)",
                        [(insight_id, p) for p in evidence])
        after = con.execute("SELECT COUNT(*) FROM insight_evidence WHERE insight_id = ?", (insight_id,)).fetchone()[0]
        con.execute("UPDATE insights SET updated_at = ? WHERE id = ?", (db.now(), insight_id))
    return {"insight_id": insight_id, "added": after - before, "evidence_posts": after}


def retire(con: sqlite3.Connection, insight_id: int) -> None:
    with con:
        con.execute("UPDATE insights SET status = 'retired', updated_at = ? WHERE id = ?", (db.now(), insight_id))
