"""The owner's accounts: brain/accounts/<id>.md (human-owned) → accounts table (what the writer and HQ query).

File format — frontmatter, then free text the agents read in full:

    ---
    platform: instagram            # instagram | linkedin | x | tiktok | youtube
    handle: buildwith.talal        # without @; TODO until known
    status: active                 # active | planned | paused
    purpose: …
    audience: …
    pillars: [ai-explained, build-in-public, resources]
    formats: [reel, carousel]
    cadence: …
    goals: …
    voice: …
    ---
    # Anything else: what the page is for, what it must never do, examples …

The id is the file stem (e.g. instagram-buildwith.talal). The markdown is the truth; `sync` copies it into the DB.
"""
from __future__ import annotations

import re
import sqlite3
from pathlib import Path

from core import db
from core.common import BRAIN, STUDIO

ACCOUNTS = BRAIN / "accounts"
FORMATS = {  # what the writer can draft per platform → the file it writes
    "instagram": {"reel": "plan.json", "carousel": "carousel.json"},
    "linkedin": {"text": "post.json", "doc-carousel": "carousel.json", "video": "plan.json"},
    "x": {"post": "post.json", "thread": "post.json", "video": "plan.json"},
    "tiktok": {"reel": "plan.json"},
    "youtube": {"short": "plan.json"},
}
LIST_KEYS = ("pillars", "formats")


def parse(path: Path) -> dict:
    text = Path(path).read_text()
    m = re.match(r"^---\n(.*?)\n---\n?(.*)$", text, re.S)
    if not m:
        raise SystemExit(f"{path}: missing --- frontmatter --- block")
    front: dict = {}
    for ln in m.group(1).splitlines():
        ln = ln.split(" #", 1)[0].rstrip()
        if not ln.strip() or ":" not in ln:
            continue
        k, v = (x.strip() for x in ln.split(":", 1))
        if k in LIST_KEYS:
            front[k] = [x.strip() for x in v.strip("[]").split(",") if x.strip()]
        else:
            front[k] = v or None
    if front.get("platform") not in db.PLATFORMS:
        raise SystemExit(f"{path}: platform must be one of {', '.join(db.PLATFORMS)}")
    if front.get("handle") in ("TODO", ""):
        front["handle"] = None
    front["id"] = Path(path).stem
    front["body"] = m.group(2).strip()
    return front


def files(root: Path | None = None) -> list[Path]:
    root = root or ACCOUNTS
    return sorted(p for p in root.glob("*.md") if p.name != "README.md") if root.exists() else []


def sync(con: sqlite3.Connection, root: Path | None = None) -> list[dict]:
    out = []
    with con:
        for p in files(root):
            a = parse(p)
            db.upsert_account(con, a["id"], a["platform"], handle=a.get("handle"), status=a.get("status") or "active",
                              purpose=a.get("purpose"), audience=a.get("audience"), pillars=a.get("pillars", []),
                              formats=a.get("formats", []), cadence=a.get("cadence"), goals=a.get("goals"),
                              voice=a.get("voice"), profile_path=str(p.resolve().relative_to(STUDIO)) if p.resolve().is_relative_to(STUDIO) else str(p))
            out.append({"id": a["id"], "platform": a["platform"], "handle": a.get("handle"), "status": a.get("status")})
    return out


def get(con: sqlite3.Connection, account_id: str, root: Path | None = None) -> dict:
    """Account by id (syncs brain/accounts first so edits to the markdown are always picked up)."""
    sync(con, root)
    acc = db.get_account(con, account_id)
    if not acc:
        known = ", ".join(p.stem for p in files(root)) or "none — add brain/accounts/<platform>-<handle>.md"
        raise SystemExit(f"no account '{account_id}' (known: {known})")
    path = (root or ACCOUNTS) / f"{account_id}.md"
    acc["body"] = parse(path)["body"] if path.exists() else ""
    return acc
