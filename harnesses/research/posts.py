"""Posts the research harness studies: collect (with public counters), analyse, rank by outlier score.

Video posts (IG reels, TikTok, YouTube, X video) are downloaded into the reference library (references/<id>/) and
analysed there (transcript, cuts, hook frames, pacing). Text posts (LinkedIn, X) come in as text the agent fetched
through a connector (agent-reach, Exa, the browser) — pass --text/--text-file plus the counters it saw.
"""
from __future__ import annotations

import datetime as _dt
import json
import sqlite3
from pathlib import Path

from core import db, refs
from core.common import STUDIO, load_json

VIDEO_PLATFORMS = ("instagram", "tiktok", "youtube")


def _date(upload_date: str | None, timestamp: float | None = None) -> str | None:
    if timestamp:
        return _dt.datetime.fromtimestamp(timestamp).replace(microsecond=0).isoformat()
    if upload_date and len(upload_date) == 8:
        return f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:]}"
    return upload_date


def _rel(p: Path) -> str:
    p = Path(p).resolve()
    return str(p.relative_to(STUDIO)) if p.is_relative_to(STUDIO) else str(p)


def _handle_from_meta(meta: dict) -> str | None:
    for k in ("channel", "uploader_id", "uploader"):
        v = meta.get(k)
        if v and not str(v).isdigit() and " " not in str(v):
            return str(v)
    return None


def add(con: sqlite3.Connection, url: str, handle: str | None = None, platform: str | None = None, download: bool | None = None,
        text: str | None = None, posted_at: str | None = None, fmt: str | None = None, topic: str | None = None,
        source: str | None = None, quality: str | None = None, metrics: dict | None = None) -> dict:
    """Register a creator's post. Returns {post_id, ref, metrics_source}."""
    platform = platform or db.platform_of(url)
    if not platform:
        raise SystemExit(f"can't tell the platform of {url}; pass --platform")
    meta, ref = {}, None
    is_video = download if download is not None else (platform in VIDEO_PLATFORMS and not text)
    if is_video:
        ref = refs.add(url)
        meta = load_json(ref / "info.json")
    elif text is None:
        try:
            meta = refs.probe(url)
        except RuntimeError:
            meta = {}
    handle = handle or _handle_from_meta(meta)
    if not handle:
        raise SystemExit("couldn't read the author's handle from the post; pass --handle")
    with con:
        hid = db.ensure_handle(con, platform, handle, name=meta.get("uploader") if meta.get("uploader") != handle else None)
        src = ref / "source.mp4" if ref else None
        pid = db.upsert_post(con, url, platform, handle_id=hid, external_id=meta.get("id"),
                             format=fmt or ("reel" if platform == "instagram" and is_video else "video" if is_video else "text"),
                             posted_at=posted_at or _date(meta.get("upload_date"), meta.get("timestamp")),
                             title=meta.get("title"), text=text if text is not None else (meta.get("description") or None),
                             topic=topic, duration_s=meta.get("duration"),
                             media_path=_rel(src) if src and src.exists() else None)
        counters = {"views": meta.get("view_count"), "likes": meta.get("like_count"), "comments": meta.get("comment_count"),
                    "reposts": meta.get("repost_count")}
        msrc, mq = ("yt-dlp", "verified") if any(v is not None for v in counters.values()) else (None, None)
        if metrics and any(v is not None for v in metrics.values()):
            counters, msrc, mq = metrics, source or "manual", quality or "estimated"
        if msrc:
            db.add_metrics(con, pid, msrc, mq, **counters)
    return {"post_id": pid, "ref": _rel(ref) if ref else None, "metrics_source": msrc}


def refresh(con: sqlite3.Connection, post_ids: list[int]) -> list[dict]:
    """New public-counter snapshot for posts (yt-dlp metadata, no download)."""
    out = []
    for pid in post_ids:
        p = db.find_post(con, pid)
        try:
            meta = refs.probe(p["url"])
        except RuntimeError as e:
            out.append({"post_id": pid, "ok": False, "error": str(e).splitlines()[0]})
            continue
        with con:
            mid = db.add_metrics(con, pid, "yt-dlp", "verified", views=meta.get("view_count"), likes=meta.get("like_count"),
                                 comments=meta.get("comment_count"), reposts=meta.get("repost_count"))
        out.append({"post_id": pid, "ok": mid is not None, "views": meta.get("view_count")})
    return out


def analyze(con: sqlite3.Connection, post_ref: str | int, force: bool = False) -> dict:
    """Run the reference analyser on a downloaded post and store its numbers; the agent writes the breakdown."""
    p = db.find_post(con, post_ref)
    if not p:
        raise SystemExit(f"no post {post_ref}")
    if not p["media_path"]:
        raise SystemExit(f"post {p['id']} has no video (text posts are analysed by reading them: research analysis set …)")
    ref = (STUDIO / p["media_path"]).parent
    md = refs.analyze(ref, force)
    m = load_json(ref / "metrics.json")
    old = con.execute("SELECT hook_text FROM analyses WHERE post_id = ?", (p["id"],)).fetchone()
    with con:
        con.execute("UPDATE posts SET transcript_path = ? WHERE id = ?", (_rel(ref / "transcript.txt"), p["id"]))
        # the spoken first 3 s is a starting hook_text; never overwrite one the agent already wrote
        _upsert_analysis(con, p["id"], auto_metrics=json.dumps(m), analysis_path=_rel(md),
                         hook_text=None if old and old["hook_text"] else (m.get("hook_first_3s") or None))
    return {"post_id": p["id"], "analysis": _rel(md), "metrics": m}


ANALYSIS_FIELDS = ("hook_type", "hook_text", "visual_hook", "structure", "pacing", "cta", "why_it_worked")


def _upsert_analysis(con: sqlite3.Connection, post_id: int, **fields) -> None:
    fields = {k: v for k, v in fields.items() if v is not None}
    fields["updated_at"] = db.now()
    con.execute(f"""INSERT INTO analyses (post_id, {', '.join(fields)}) VALUES (?, {', '.join('?' * len(fields))})
                    ON CONFLICT (post_id) DO UPDATE SET {', '.join(f'{k} = excluded.{k}' for k in fields)}""",
                [post_id, *fields.values()])


def set_analysis(con: sqlite3.Connection, post_ref: str | int, **fields) -> dict:
    p = db.find_post(con, post_ref)
    if not p:
        raise SystemExit(f"no post {post_ref}")
    with con:
        _upsert_analysis(con, p["id"], **{k: v for k, v in fields.items() if k in ANALYSIS_FIELDS})
    return db.dicts(con.execute("SELECT * FROM analyses WHERE post_id = ?", (p["id"],)))[0]


def listing(con: sqlite3.Connection, platform: str | None = None, handle: str | None = None, cluster: str | None = None,
            min_outlier: float | None = None, analysed: bool | None = None, limit: int | None = None) -> list[dict]:
    where, params = ["p.handle_id IS NOT NULL"], []
    if platform:
        where.append("p.platform = ?")
        params.append(platform)
    if handle:
        where.append("h.handle = ?")
        params.append(db.norm_handle(handle))
    if cluster:
        where.append("c.cluster = ?")
        params.append(cluster)
    if analysed is not None:
        where.append(f"an.id IS {'NOT ' if analysed else ''}NULL")
    rows = db.with_outlier_scores(con, db.post_table(con, " AND ".join(where), tuple(params)))
    if min_outlier is not None:
        rows = [r for r in rows if r["outlier"] is not None and r["outlier"] >= min_outlier]
    rows.sort(key=lambda r: (r["outlier"] is None, -(r["outlier"] or 0), -(r["views"] or 0)))
    return rows[:limit] if limit else rows
