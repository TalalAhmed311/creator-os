"""Creator database: who the research harness studies, on which platform, and how they score.

Score (out of 5, same weights as the seed research): 35% organic reach (typical views ÷ followers),
35% relevance to the owner's content (1–5, set by the scout; 3 when unknown), 10% posting consistency,
15% originality, 5% audience size. Missing data counts as neutral (reach 2.5, consistency 3), so a
creator is never ranked high on numbers that don't exist.
"""
from __future__ import annotations

import sqlite3

from core import db


def _reach_score(ratio: float | None) -> float:
    if ratio is None:
        return 2.5
    return 5 if ratio >= 3 else 4.5 if ratio >= 2 else 4 if ratio >= 1 else 3 if ratio >= 0.5 else 2 if ratio >= 0.2 else 1


def _consistency_score(per_week: float | None) -> float:
    if per_week is None:
        return 3
    return 5 if per_week >= 4 else 4 if per_week >= 2 else 3 if per_week >= 1 else 2


def _size_score(followers: float | None) -> float:
    if followers is None:
        return 3
    return 5 if followers >= 500e3 else 4 if followers >= 100e3 else 3 if followers >= 25e3 else 2


def score(c: dict) -> float:
    orig = {"yes": 5, "unclear": 3, "no": 1}.get((c.get("original") or "").lower(), 3)
    return round(0.35 * _reach_score(c.get("reach_ratio")) + 0.35 * (c.get("relevance") or 3)
                 + 0.10 * _consistency_score(c.get("posts_per_week")) + 0.15 * orig + 0.05 * _size_score(c.get("followers")), 2)


def listing(con: sqlite3.Connection, platform: str | None = None, status: str | None = None, cluster: str | None = None,
            signal: str | None = None, research_set: bool = False, query: str | None = None) -> list[dict]:
    where, params = ["1"], []
    for col, val in (("h.platform", platform), ("c.status", status), ("c.cluster", cluster), ("c.signal", signal)):
        if val:
            where.append(f"{col} = ?")
            params.append(val)
    if research_set:
        where.append("c.in_research_set = 1")
    if query:
        where.append("(c.name LIKE ? OR h.handle LIKE ? OR c.primary_niche LIKE ? OR c.notes LIKE ?)")
        params += [f"%{query}%"] * 4
    rows = db.dicts(con.execute(f"""
        SELECT c.*, h.id AS handle_id, h.platform, h.handle, h.url,
               (SELECT COUNT(*) FROM posts p WHERE p.handle_id = h.id) AS posts_in_db
        FROM creators c JOIN creator_handles h ON h.creator_id = c.id
        WHERE {' AND '.join(where)}""", params))
    for r in rows:
        for col in ("followers", "typical_views", "reach_ratio", "posts_per_week", "peak_views"):
            r[col] = db.latest_creator_value(con, r["handle_id"], col)
        if r["reach_ratio"] is None and r["typical_views"] and r["followers"]:
            r["reach_ratio"] = round(r["typical_views"] / r["followers"], 2)
        r["score"] = score(r)
    return sorted(rows, key=lambda r: -r["score"])


def show(con: sqlite3.Connection, platform: str, handle: str) -> dict:
    h = db.find_handle(con, platform, handle)
    if not h:
        raise SystemExit(f"no {platform} creator @{db.norm_handle(handle)} (./studio research creators list)")
    c = next(r for r in listing(con, platform=platform) if r["handle_id"] == h["id"])
    c["other_handles"] = db.dicts(con.execute("SELECT platform, handle, url FROM creator_handles WHERE creator_id = ? AND id != ?",
                                              (c["id"], h["id"])))
    c["snapshots"] = db.dicts(con.execute("SELECT * FROM creator_snapshots WHERE handle_id = ? ORDER BY captured_at DESC, id DESC",
                                          (h["id"],)))
    c["posts"] = db.with_outlier_scores(con, db.post_table(con, "p.handle_id = ?", (h["id"],)))
    return c


def set_status(con: sqlite3.Connection, platform: str, handle: str, status: str, why: str | None = None) -> None:
    h = db.find_handle(con, platform, handle)
    if not h:
        raise SystemExit(f"no {platform} creator @{db.norm_handle(handle)}")
    with con:
        db.update_creator(con, h["creator_id"], status=status, why=why)


def link_handle(con: sqlite3.Connection, platform: str, handle: str, other_platform: str, other_handle: str) -> int:
    """Same person on another platform → one creator, two handles."""
    h = db.find_handle(con, platform, handle)
    if not h:
        raise SystemExit(f"no {platform} creator @{db.norm_handle(handle)}")
    if db.find_handle(con, other_platform, other_handle):
        raise SystemExit(f"{other_platform} @{other_handle} already belongs to a creator")
    oh = db.norm_handle(other_handle)
    with con:
        return con.execute("INSERT INTO creator_handles (creator_id, platform, handle, url) VALUES (?, ?, ?, ?)",
                           (h["creator_id"], other_platform, oh, db.profile_url(other_platform, oh))).lastrowid
