"""The owner's content database: log published posts, add metrics, and the daily sync.

Metrics are captured at checkpoints after posting — 1, 3, 7 and 30 days — so posts are compared at the same age.
A post is *due* when it has passed a checkpoint and has no snapshot taken since that checkpoint.
"""
from __future__ import annotations

import csv
import datetime as _dt
import sqlite3
from pathlib import Path

from core import accounts, db
from core.common import STUDIO, Project, load_json
from harnesses.hq import providers

CHECKPOINTS = (1, 3, 7, 30)
ALIASES = {  # analytics-export column → metric (lower-case)
    "views": "views", "plays": "views", "video views": "views", "impressions": "impressions", "reach": "reach",
    "accounts reached": "reach", "likes": "likes", "reactions": "likes", "comments": "comments", "shares": "shares",
    "sends": "shares", "reposts": "reposts", "retweets": "reposts", "saves": "saves", "saved": "saves",
    "bookmarks": "saves", "avg watch %": "avg_watch_pct", "average watch percentage": "avg_watch_pct",
    "avg_watch_pct": "avg_watch_pct", "profile visits": "profile_visits", "profile_visits": "profile_visits",
    "follows": "follows", "new followers": "follows",
}


def _parse_dt(s: str | None) -> _dt.datetime | None:
    if not s:
        return None
    try:
        return _dt.datetime.fromisoformat(s.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


def _num(v) -> float | int | None:
    if v is None or str(v).strip() in ("", "-", "N/A"):
        return None
    s = str(v).replace(",", "").replace("%", "").strip()
    try:
        f = float(s)
    except ValueError:
        return None
    return int(f) if f.is_integer() else f


# ---------------------------------------------------------------- log

def log(con: sqlite3.Connection, account_id: str, url: str, draft_id: int | None = None, project_id: str | None = None,
        posted_at: str | None = None, fmt: str | None = None, pillar: str | None = None, topic: str | None = None,
        metrics: dict | None = None, source: str = "manual", quality: str = "verified") -> dict:
    acc = accounts.get(con, account_id)
    draft = None
    if draft_id is not None:
        row = con.execute("SELECT * FROM drafts WHERE id = ?", (draft_id,)).fetchone()
        if not row:
            raise SystemExit(f"no draft #{draft_id}")
        if row["account_id"] != account_id:
            raise SystemExit(f"draft #{draft_id} belongs to {row['account_id']}, not {account_id}")
        draft = dict(row)
    project_id = project_id or (draft or {}).get("project_id")
    plan_path = Project(project_id).root / "plan.json" if project_id else None
    plan = load_json(plan_path) if plan_path and plan_path.exists() else {}
    with con:
        pid = db.upsert_post(con, url, acc["platform"], account_id=account_id, project_id=project_id,
                             posted_at=posted_at or db.now(), format=fmt or (draft or {}).get("format"),
                             pillar=pillar or plan.get("pillar") or (acc["pillars"][0] if acc["pillars"] else None),
                             title=(draft or {}).get("title"), topic=topic)
        if draft:
            con.execute("UPDATE drafts SET status = 'published', post_id = ?, updated_at = ? WHERE id = ?", (pid, db.now(), draft_id))
        mid = db.add_metrics(con, pid, source, quality, **(metrics or {}))
    return {"post_id": pid, "account": account_id, "draft": draft_id, "project": project_id, "metrics_snapshot": mid}


# ---------------------------------------------------------------- metrics

def add_metrics(con: sqlite3.Connection, ref: str, source: str, quality: str, captured_at: str | None = None, **values) -> dict:
    post = db.find_post(con, ref)
    if not post:
        raise SystemExit(f"no post {ref} — log it first: ./studio hq log <account> <url>")
    with con:
        mid = db.add_metrics(con, post["id"], source, quality, captured_at, **values)
    if mid is None:
        raise SystemExit("no metric values given")
    return {"post_id": post["id"], "snapshot_id": mid}


def import_csv(con: sqlite3.Connection, path: Path, source: str, quality: str = "verified", account_id: str | None = None) -> dict:
    """Rows with a url/link/permalink column + metric columns (header names from ALIASES). Unknown posts are logged
    to `account_id` when given, else skipped."""
    added, skipped, created = 0, [], 0
    with open(path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            low = {(k or "").strip().lower(): v for k, v in row.items()}
            url = next((low[k] for k in ("url", "link", "permalink", "post url", "post link") if low.get(k)), None)
            if not url:
                skipped.append("row without url")
                continue
            post = db.find_post(con, url)
            if not post and account_id:
                log(con, account_id, url, posted_at=low.get("posted_at") or low.get("date") or low.get("created"))
                post, created = db.find_post(con, url), created + 1
            if not post:
                skipped.append(url)
                continue
            vals = {}
            for k, v in low.items():
                if k in ALIASES and _num(v) is not None:
                    vals[ALIASES[k]] = _num(v)
            with con:
                if db.add_metrics(con, post["id"], source, quality, low.get("captured_at") or None, **vals):
                    added += 1
    return {"snapshots_added": added, "posts_created": created, "skipped": skipped}


# ---------------------------------------------------------------- sync

def due(con: sqlite3.Connection, now: _dt.datetime | None = None) -> list[dict]:
    """Owner posts that passed a checkpoint without a snapshot since then (latest checkpoint per post)."""
    now = now or _dt.datetime.now()
    out = []
    for p in db.dicts(con.execute("SELECT * FROM posts WHERE account_id IS NOT NULL")):
        posted = _parse_dt(p["posted_at"]) or _parse_dt(p["added_at"])
        if not posted:
            continue
        passed = [c for c in CHECKPOINTS if now >= posted + _dt.timedelta(days=c)]
        if not passed:
            continue
        cp = passed[-1]
        since = (posted + _dt.timedelta(days=cp)).isoformat(timespec="seconds")
        if not con.execute("SELECT 1 FROM metric_snapshots WHERE post_id = ? AND captured_at >= ?", (p["id"], since)).fetchone():
            out.append({"post_id": p["id"], "account": p["account_id"], "platform": p["platform"], "url": p["url"],
                        "checkpoint_days": cp, "posted_at": p["posted_at"]})
    return out


def sync(con: sqlite3.Connection, dry_run: bool = False, now: _dt.datetime | None = None, fetcher=providers.fetch) -> dict:
    todo = due(con, now)
    done, pending = [], []
    for d in todo:
        if dry_run:
            pending.append({**d, "provider": providers.configured(d["platform"]), "reason": "dry run"})
            continue
        try:
            metrics, source, quality = fetcher(d["platform"], d["url"])
            with con:
                db.add_metrics(con, d["post_id"], source, quality, **metrics)
            done.append({**d, "source": source, **metrics})
            if d["platform"] == "instagram" and "views" not in metrics:  # yt-dlp can't see IG plays
                pending.append({**d, "provider": source, "reason": "views not readable by this provider"})
        except providers.ProviderError as e:
            pending.append({**d, "provider": providers.configured(d["platform"]), "reason": str(e)})
    if not dry_run:
        write_pending(pending)
    return {"due": len(todo), "synced": done, "pending": pending, "pending_file": _rel(pending_path())}


def pending_path() -> Path:
    return db.data_dir() / "hq" / "pending-metrics.md"


def _rel(p: Path) -> str:
    return str(p.relative_to(STUDIO)) if p.resolve().is_relative_to(STUDIO) else str(p)


def write_pending(pending: list[dict]) -> Path:
    path = pending_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"# Metrics to add by hand — {db.now()[:16].replace('T', ' ')}", ""]
    if not pending:
        lines.append("Nothing pending. ✓")
    else:
        lines += ["Open each post's insights in the app (or an analytics export) and add the numbers:", ""]
        for p in pending:
            lines += [f"- **{p['account']}** · day {p['checkpoint_days']} · {p['url']}  _({p['reason']})_",
                      f"  `./studio hq metrics add {p['post_id']} --views N --likes N --comments N --shares N --saves N"
                      f"{' --avg-watch N' if p['platform'] == 'instagram' else ''}`"]
        lines += ["", "Bulk: export analytics as CSV → `./studio hq metrics import <file.csv> --source <platform>-export`."]
    path.write_text("\n".join(lines) + "\n")
    return path


def import_content_log(con: sqlite3.Connection, path: Path, account_by_platform: dict[str, str]) -> dict:
    """One-off migration of the old brain/content-log.csv rows into posts + metric snapshots."""
    n, skipped = 0, []
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            acc = account_by_platform.get(r.get("platform", ""))
            if not acc or not r.get("url"):
                skipped.append(r.get("url") or r.get("project_id"))
                continue
            log(con, acc, r["url"], project_id=r.get("project_id") or None, posted_at=r.get("date") or None,
                pillar=r.get("pillar") or None, source="content-log", quality="verified",
                metrics={"views": _num(r.get("views")), "avg_watch_pct": _num(r.get("avg_watch_pct")), "likes": _num(r.get("likes")),
                         "comments": _num(r.get("comments")), "saves": _num(r.get("saves")), "shares": _num(r.get("shares"))})
            n += 1
    return {"imported": n, "skipped": skipped}
