"""creator-os database: one SQLite file shared by every harness (data/creator-os.db, override with CREATOR_OS_DB).

Every number goes in with a source, a capture time and a quality ('verified' = the platform's own counter,
'estimated' = third-party tracker or derived). Snapshots are appended, never overwritten.
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import re
import sqlite3
from pathlib import Path
from statistics import median
from typing import Any, Iterable

from core.common import STUDIO

DATA = STUDIO / "data"
SCHEMA = Path(__file__).with_name("schema.sql")
PLATFORMS = ("instagram", "linkedin", "x", "tiktok", "youtube")
QUALITIES = ("verified", "estimated")
METRICS = ("views", "likes", "comments", "shares", "saves", "reposts", "impressions", "reach", "avg_watch_pct",
           "profile_visits", "follows")


def _latest_metrics_view() -> str:
    """v2: each metric is its newest non-empty value, so a snapshot that lacks a counter (yt-dlp has no IG views) never
    hides one read elsewhere. captured_at/source/quality describe the snapshot the views came from (else the newest)."""
    newest = "SELECT {sel} FROM metric_snapshots s WHERE s.post_id = p.post_id{cond} ORDER BY s.captured_at DESC, s.id DESC LIMIT 1"
    cols = ",\n  ".join(f"({newest.format(sel='s.' + m, cond=f' AND s.{m} IS NOT NULL')}) AS {m}" for m in METRICS)
    meta = ",\n  ".join(
        f"COALESCE(({newest.format(sel='s.' + c, cond=' AND s.views IS NOT NULL')}), ({newest.format(sel='s.' + c, cond='')})) AS {c}"
        for c in ("id", "captured_at", "source", "quality"))
    return f"""DROP VIEW IF EXISTS latest_metrics;
CREATE VIEW latest_metrics AS
SELECT p.post_id,
  {meta},
  {cols}
FROM (SELECT DISTINCT post_id FROM metric_snapshots) p;"""


MIGRATIONS: list[str] = [SCHEMA.read_text(), _latest_metrics_view()]  # append new migration SQL here; never edit a shipped one


def db_path() -> Path:
    return Path(os.environ.get("CREATOR_OS_DB") or DATA / "creator-os.db")


def data_dir() -> Path:
    """Folder next to the database for reports, pending lists and exports (follows CREATOR_OS_DB)."""
    return db_path().parent


def now() -> str:
    return _dt.datetime.now().replace(microsecond=0).isoformat()


def connect(path: Path | None = None) -> sqlite3.Connection:
    path = Path(path or db_path())
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    migrate(con)
    return con


def schema_version(con: sqlite3.Connection) -> int:
    if not con.execute("SELECT 1 FROM sqlite_master WHERE name = 'meta'").fetchone():
        return 0
    row = con.execute("SELECT value FROM meta WHERE key = 'schema_version'").fetchone()
    return int(row[0]) if row else 0


def migrate(con: sqlite3.Connection) -> int:
    v = schema_version(con)
    for i, sql in enumerate(MIGRATIONS[v:], start=v + 1):
        with con:
            con.executescript(sql)
            con.execute("INSERT OR REPLACE INTO meta (key, value) VALUES ('schema_version', ?)", (str(i),))
    return len(MIGRATIONS)


def dicts(rows: Iterable[sqlite3.Row]) -> list[dict]:
    return [dict(r) for r in rows]


def norm_handle(handle: str) -> str:
    return handle.strip().lstrip("@").replace("\\_", "_").lower()


def platform_of(url: str) -> str | None:
    u = url.lower()
    for key, plat in (("instagram.com", "instagram"), ("linkedin.com", "linkedin"), ("x.com", "x"), ("twitter.com", "x"),
                      ("tiktok.com", "tiktok"), ("youtube.com", "youtube"), ("youtu.be", "youtube")):
        if key in u:
            return plat
    return None


def profile_url(platform: str, handle: str) -> str | None:
    return {"instagram": f"https://www.instagram.com/{handle}/", "x": f"https://x.com/{handle}",
            "linkedin": f"https://www.linkedin.com/in/{handle}/", "tiktok": f"https://www.tiktok.com/@{handle}",
            "youtube": f"https://www.youtube.com/@{handle}"}.get(platform)


def _check(platform: str | None = None, quality: str | None = None) -> None:
    if platform is not None and platform not in PLATFORMS:
        raise ValueError(f"unknown platform '{platform}' (one of {', '.join(PLATFORMS)})")
    if quality is not None and quality not in QUALITIES:
        raise ValueError(f"quality must be one of {QUALITIES}")


# ---------------------------------------------------------------- creators

def find_handle(con: sqlite3.Connection, platform: str, handle: str) -> sqlite3.Row | None:
    return con.execute("""SELECT h.*, c.name, c.status, c.cluster, c.primary_niche FROM creator_handles h
                          JOIN creators c ON c.id = h.creator_id WHERE h.platform = ? AND h.handle = ?""",
                       (platform, norm_handle(handle))).fetchone()


def ensure_handle(con: sqlite3.Connection, platform: str, handle: str, name: str | None = None, **creator: Any) -> int:
    """handle id for platform/handle; creates the creator (status candidate unless given) when new."""
    _check(platform)
    h = norm_handle(handle)
    row = find_handle(con, platform, h)
    if row:
        if creator:
            update_creator(con, row["creator_id"], **creator)
        return row["id"]
    fields = {"name": name or h, "status": "candidate", "added_at": now(), "updated_at": now(), **creator}
    cur = con.execute(f"INSERT INTO creators ({', '.join(fields)}) VALUES ({', '.join('?' * len(fields))})", list(fields.values()))
    return con.execute("INSERT INTO creator_handles (creator_id, platform, handle, url) VALUES (?, ?, ?, ?)",
                       (cur.lastrowid, platform, h, profile_url(platform, h))).lastrowid


def update_creator(con: sqlite3.Connection, creator_id: int, **fields: Any) -> None:
    fields = {k: v for k, v in fields.items() if v is not None}
    if not fields:
        return
    fields["updated_at"] = now()
    con.execute(f"UPDATE creators SET {', '.join(f'{k} = ?' for k in fields)} WHERE id = ?", [*fields.values(), creator_id])


def add_creator_snapshot(con: sqlite3.Connection, handle_id: int, source: str, quality: str,
                         captured_at: str | None = None, **values: Any) -> int:
    _check(quality=quality)
    values = {k: v for k, v in values.items() if v is not None}
    cols = ["handle_id", "captured_at", "source", "quality", *values]
    return con.execute(f"INSERT INTO creator_snapshots ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})",
                       [handle_id, captured_at or now(), source, quality, *values.values()]).lastrowid


def latest_creator_value(con: sqlite3.Connection, handle_id: int, column: str) -> Any:
    if column not in ("followers", "posts", "typical_views", "peak_views", "reach_ratio", "posts_per_week"):
        raise ValueError(column)
    row = con.execute(f"""SELECT {column} FROM creator_snapshots WHERE handle_id = ? AND {column} IS NOT NULL
                          ORDER BY captured_at DESC, id DESC LIMIT 1""", (handle_id,)).fetchone()
    return row[0] if row else None


# ---------------------------------------------------------------- posts & metrics

def upsert_post(con: sqlite3.Connection, url: str, platform: str | None = None, handle_id: int | None = None,
                account_id: str | None = None, **fields: Any) -> int:
    """Insert a post (or fill in fields of an existing one with the same url). Returns the post id."""
    platform = platform or platform_of(url)
    _check(platform)
    fields = {k: v for k, v in fields.items() if v is not None}
    row = con.execute("SELECT id FROM posts WHERE url = ?", (url,)).fetchone()
    if row:
        if fields:
            con.execute(f"UPDATE posts SET {', '.join(f'{k} = ?' for k in fields)} WHERE id = ?", [*fields.values(), row[0]])
        return row[0]
    cols = {"url": url, "platform": platform, "handle_id": handle_id, "account_id": account_id, "added_at": now(), **fields}
    return con.execute(f"INSERT INTO posts ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})", list(cols.values())).lastrowid


def find_post(con: sqlite3.Connection, ref: str | int) -> sqlite3.Row | None:
    if isinstance(ref, int) or str(ref).isdigit():
        return con.execute("SELECT * FROM posts WHERE id = ?", (int(ref),)).fetchone()
    return con.execute("SELECT * FROM posts WHERE url = ?", (str(ref),)).fetchone()


def add_metrics(con: sqlite3.Connection, post_id: int, source: str, quality: str, captured_at: str | None = None,
                **values: Any) -> int | None:
    """Append a metric snapshot. Returns None (and writes nothing) when no metric value is given."""
    _check(quality=quality)
    values = {k: v for k, v in values.items() if k in METRICS and v is not None}
    if not values:
        return None
    if captured_at and len(captured_at) == 10 and captured_at == now()[:10]:
        captured_at = None  # "today" as a bare date would sort before this morning's timestamped snapshots
    cols = ["post_id", "captured_at", "source", "quality", *values]
    return con.execute(f"INSERT INTO metric_snapshots ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})",
                       [post_id, captured_at or now(), source, quality, *values.values()]).lastrowid


def post_table(con: sqlite3.Connection, where: str = "1", params: tuple = ()) -> list[dict]:
    """Posts with author and latest metrics."""
    return dicts(con.execute(f"""
        SELECT p.*, COALESCE(h.handle, a.handle) AS author_handle, c.name AS creator_name, c.id AS creator_id,
               m.views, m.likes, m.comments, m.shares, m.saves, m.reposts, m.impressions, m.reach, m.avg_watch_pct,
               m.captured_at AS metrics_at, m.source AS metrics_source, m.quality AS metrics_quality,
               an.hook_type, an.hook_text
        FROM posts p
        LEFT JOIN creator_handles h ON h.id = p.handle_id
        LEFT JOIN creators c ON c.id = h.creator_id
        LEFT JOIN accounts a ON a.id = p.account_id
        LEFT JOIN latest_metrics m ON m.post_id = p.id
        LEFT JOIN analyses an ON an.post_id = p.id
        WHERE {where}""", params))


OUTLIER_METRICS = ("views", "likes")  # likes = reactions; the fallback where views aren't public (LinkedIn)


def with_outlier_scores(con: sqlite3.Connection, posts: list[dict], min_posts: int = 3, metric: str = "auto") -> list[dict]:
    """Add `outlier` = views ÷ the author's median views (needs ≥ min_posts posts with views by that author on that
    platform); otherwise views ÷ the creator's latest typical views snapshot; otherwise (metric "auto" or "likes")
    likes ÷ the author's median likes. `outlier_metric` and `outlier_basis` say which."""
    if metric not in ("auto", *OUTLIER_METRICS):
        raise ValueError(f"metric must be auto, {' or '.join(OUTLIER_METRICS)}")
    order = OUTLIER_METRICS if metric == "auto" else (metric,)
    groups: dict[tuple, dict[str, list[float]]] = {}
    # medians use every post the author has in the database, not only the ones passed in
    for plat, hid, aid in {(p["platform"], p["handle_id"], p["account_id"]) for p in posts}:
        col, val = ("handle_id", hid) if hid is not None else ("account_id", aid)
        groups[(plat, hid, aid)] = {m: [r[0] for r in con.execute(
            f"""SELECT m.{m} FROM posts p JOIN latest_metrics m ON m.post_id = p.id
                WHERE p.platform = ? AND p.{col} = ? AND m.{m} IS NOT NULL""", (plat, val))] for m in order}
    for p in posts:
        p["outlier"], p["outlier_basis"], p["outlier_metric"], p["author_median"] = None, None, None, None
        g = groups.get((p["platform"], p["handle_id"], p["account_id"]), {})
        for m in order:
            if p.get(m) is None:
                continue
            vals = g.get(m, [])
            if len(vals) >= min_posts and median(vals) > 0:
                p["author_median"] = median(vals)
                p["outlier"], p["outlier_basis"] = round(p[m] / median(vals), 2), f"median {m} of {len(vals)} posts"
            elif m == "views" and p.get("handle_id") and (typical := latest_creator_value(con, p["handle_id"], "typical_views")):
                p["outlier"], p["outlier_basis"] = round(p["views"] / typical, 2), "typical views snapshot"
            if p["outlier"] is not None:
                p["outlier_metric"] = m
                break
    return posts


# ---------------------------------------------------------------- accounts

def upsert_account(con: sqlite3.Connection, account_id: str, platform: str, **fields: Any) -> None:
    _check(platform)
    fields = {k: (json.dumps(v) if isinstance(v, (list, dict)) else v) for k, v in fields.items()}
    fields["updated_at"] = now()
    cols = {"id": account_id, "platform": platform, **fields}
    con.execute(f"""INSERT INTO accounts ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})
                    ON CONFLICT (id) DO UPDATE SET {', '.join(f'{k} = excluded.{k}' for k in cols if k != 'id')}""",
                list(cols.values()))


def get_account(con: sqlite3.Connection, account_id: str) -> dict | None:
    row = con.execute("SELECT * FROM accounts WHERE id = ?", (account_id,)).fetchone()
    if not row:
        return None
    d = dict(row)
    for k in ("pillars", "formats"):
        d[k] = json.loads(d[k]) if d[k] else []
    return d


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:48] or "untitled"
