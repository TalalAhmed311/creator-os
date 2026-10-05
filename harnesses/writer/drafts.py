"""Drafts: one project folder per piece, one row in `drafts`. Draft-only — creator-os never posts.

Formats by platform (core/accounts.FORMATS): reels/videos → plan.json (the Edit Bay's contract), carousels and
LinkedIn document carousels → carousel.json (the Design Desk renders slides + PDF), text posts / threads → post.json
(+ post.md, the copy-paste version, written on a clean validate).
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from core import accounts, db, memory
from core.common import PILLARS, Project, STUDIO, load_json, save_json, validate
from harnesses.writer import context

X_LIMIT = 280
LINKEDIN_LIMIT = 3000
TASK = {"plan.json": "plan", "carousel.json": "carousel", "post.json": "other"}


def new(con: sqlite3.Connection, account_id: str, fmt: str, title: str, idea: str | None = None, pillar: str | None = None,
        reference_url: str | None = None, insight_ids: list[int] | None = None, topic: str | None = None) -> dict:
    acc = accounts.get(con, account_id)
    files = accounts.FORMATS.get(acc["platform"], {})
    if fmt not in files:
        raise SystemExit(f"{acc['platform']} drafts can be: {', '.join(files)}")
    pillar = pillar or next((p for p in acc["pillars"] if p in PILLARS), "build-in-public")
    proj = Project.create(pillar, f"{acc['platform']}-{title}")
    contract = files[fmt]
    ctx = context.build(con, account_id, topic=topic or title)
    save_json(proj.root / "context.json", ctx)
    if contract == "post.json" and not (proj.root / "post.json").exists():
        save_json(proj.root / "post.json", {"platform": acc["platform"], "account": account_id,
                                            "format": "thread" if fmt == "thread" else "text" if fmt == "text" else "post",
                                            "topic": topic or title, "hooks": [], "chosen_hook": None, "body": "",
                                            "insights_used": insight_ids or [], "reference_url": reference_url})
    with con:
        did = con.execute("""INSERT INTO drafts (account_id, platform, format, title, idea, project_id, path, reference_url,
                             created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                          (account_id, acc["platform"], fmt, title, idea, proj.id, f"projects/{proj.id}/{contract}",
                           reference_url, db.now(), db.now())).lastrowid
        con.executemany("INSERT OR IGNORE INTO draft_insights VALUES (?, ?)", [(did, i) for i in insight_ids or []])
    memory.create_working(proj.id, pillar, TASK[contract], goal=f"{acc['platform']} {fmt} for {account_id}: {title}")
    memory.append(proj.id, "requirements", f"- draft #{did} · account {account_id} · format {fmt}"
                  + (f" · reference {reference_url}" if reference_url else "") + (f" · idea: {idea}" if idea else ""),
                  agent="writer")
    memory.memory_load(pillar, proj.id)
    return {"draft_id": did, "project_id": proj.id, "path": f"projects/{proj.id}/{contract}",
            "context": f"projects/{proj.id}/context.json"}


def get(con: sqlite3.Connection, draft_id: int) -> dict:
    row = con.execute("SELECT * FROM drafts WHERE id = ?", (draft_id,)).fetchone()
    if not row:
        raise SystemExit(f"no draft #{draft_id}")
    d = dict(row)
    d["insights"] = [r[0] for r in con.execute("SELECT insight_id FROM draft_insights WHERE draft_id = ?", (draft_id,))]
    return d


def listing(con: sqlite3.Connection, account_id: str | None = None, status: str | None = None) -> list[dict]:
    where, params = ["1"], []
    if account_id:
        where.append("account_id = ?")
        params.append(account_id)
    if status:
        where.append("status = ?")
        params.append(status)
    return db.dicts(con.execute(f"SELECT * FROM drafts WHERE {' AND '.join(where)} ORDER BY id DESC", params))


def set_status(con: sqlite3.Connection, draft_id: int, status: str) -> dict:
    if status == "published":
        raise SystemExit("drafts become 'published' when you log the live post: ./studio hq log <account> <url> --draft N")
    get(con, draft_id)
    with con:
        con.execute("UPDATE drafts SET status = ?, updated_at = ? WHERE id = ?", (status, db.now(), draft_id))
    return get(con, draft_id)


def check_post(post: dict) -> tuple[list[str], list[str]]:
    """Platform rules beyond the schema → (errors, warnings)."""
    errors, warnings = [], []
    plat, fmt = post["platform"], post["format"]
    parts = post.get("thread") or ([post["body"]] if post.get("body") else [])
    if not parts:
        errors.append("no copy yet: fill `body` (or `thread` for an X thread)")
    if plat == "x":
        for i, t in enumerate(parts):
            if len(t) > X_LIMIT:
                errors.append(f"X post {i + 1} is {len(t)} characters (limit {X_LIMIT})")
        if fmt == "thread" and len(post.get("thread") or []) < 2:
            errors.append("a thread needs ≥ 2 posts in `thread`")
        if len(post.get("hashtags") or []) > 2:
            warnings.append("X: more than 2 hashtags reads as spam")
    if plat == "linkedin":
        body = post.get("body") or ""
        if len(body) > LINKEDIN_LIMIT:
            errors.append(f"LinkedIn post is {len(body)} characters (limit {LINKEDIN_LIMIT})")
        if len(post.get("hashtags") or []) > 5:
            warnings.append("LinkedIn: keep hashtags to 3–5")
        if "http" in body:
            warnings.append("LinkedIn: link in the body — put it in `first_comment` instead")
        first = body.split("\n", 1)[0]
        if len(first) > 210:
            warnings.append("LinkedIn: first line is past the ~210-character 'see more' cut")
    if post.get("chosen_hook") is not None and parts:
        hook = post["hooks"][post["chosen_hook"]]["text"].strip().lower()[:40]
        if hook and hook not in parts[0].lower():
            warnings.append("the chosen hook isn't in the opening line")
    if len({h["type"] for h in post.get("hooks", [])}) < len(post.get("hooks", [])):
        warnings.append("hooks should be three different types")
    if not post.get("insights_used"):
        warnings.append("insights_used is empty — say which proven pattern this draft uses (or why none)")
    return errors, warnings


def render_post(post: dict) -> str:
    """post.md: exactly what the owner pastes, in order."""
    out = [f"<!-- {post['platform']} · {post['account']} · {post['format']} — draft, post it yourself -->", ""]
    if post.get("thread"):
        for i, t in enumerate(post["thread"], 1):
            out += [f"**{i}/{len(post['thread'])}** ({len(t)} chars)", "", t, "", "---", ""]
    else:
        out += [post.get("body", ""), ""]
    if post.get("hashtags"):
        out += [" ".join(h if h.startswith("#") else f"#{h}" for h in post["hashtags"]), ""]
    if post.get("first_comment"):
        out += ["**First comment:**", "", post["first_comment"], ""]
    for m in post.get("media") or []:
        out.append(f"- media ({m['kind']}{', post ' + str(m['attach_to'] + 1) if 'attach_to' in m else ''}): {m['description']}"
                   + (f" → {m['path']}" if m.get("path") else ""))
    return "\n".join(out).rstrip() + "\n"


def check(con: sqlite3.Connection, draft_id: int) -> dict:
    d = get(con, draft_id)
    path = Project(d["project_id"]).root / Path(d["path"]).name
    if not path.exists():
        return {"draft_id": draft_id, "ok": False, "errors": [f"{d['path']} not written yet"], "warnings": []}
    import jsonschema

    data = load_json(path)
    errors, warnings = [], []
    schema = {"post.json": "post", "plan.json": "plan", "carousel.json": "carousel"}[path.name]
    try:
        validate(data, schema)
    except jsonschema.ValidationError as e:
        errors.append(f"{path.name}: {'/'.join(map(str, e.absolute_path)) or '(root)'}: {e.message}")
    if not errors and schema == "post":
        e2, warnings = check_post(data)
        errors += e2
        if not errors:
            (path.parent / "post.md").write_text(render_post(data))
    if not errors and schema == "plan" and data.get("chosen_hook") is not None and data["chosen_hook"] >= len(data["hooks"]):
        errors.append("plan.json: chosen_hook out of range")
    return {"draft_id": draft_id, "ok": not errors, "errors": errors, "warnings": warnings,
            "copy": _rel(path.parent / "post.md") if path.name == "post.json" and not errors else None}


def _rel(p: Path) -> str:
    return str(p.relative_to(STUDIO)) if p.resolve().is_relative_to(STUDIO) else str(p)


def as_json(d: dict) -> str:
    return json.dumps(d, indent=2, default=str)


