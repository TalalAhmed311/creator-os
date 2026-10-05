"""Memory engine (§14): working memory per task + distilled long-term memory.

CLI:
  python -m core.memory create <project_id> <pillar> <task> [--goal ...] [--requirements ...]
  python -m core.memory append <project_id> <section> <text> [--agent NAME]
  python -m core.memory progress <project_id> <step> [--todo]
  python -m core.memory status <project_id> <status>
  python -m core.memory load <pillar> [--project <project_id>]      # Memory Load (§14.4)
  python -m core.memory consolidate <project_id> --facts facts.json # Memory Consolidation (§14.5)
  python -m core.memory remember <text> [--kind preference] [--tags a,b] [--pillar P]
  python -m core.memory search <query> [--tags a,b]
  python -m core.memory open                                         # unfinished tasks for /resume

facts.json for consolidate:
  {"record": "<markdown project record, <=30 lines>",
   "summary": "<one line for index.md>",
   "facts": [{"kind": "preference|lesson|idea|pillar", "text": "...", "tags": ["captions"],
              "pillar": "build-in-public", "replaces": "<old text, optional>"}]}
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

from core.common import MEMORY, PILLARS, PROJECTS, now_iso, today

WORKING = MEMORY / "working"
LONG = MEMORY / "long-term"
INDEX = LONG / "index.md"

SECTIONS = [
    "Goal",
    "Requirements",
    "Context loaded from long-term memory",
    "Decisions (with reason)",
    "My feedback",
    "Progress",
    "Open items / ideas spotted",
]
SECTION_ALIASES = {
    "goal": "Goal", "requirements": "Requirements", "context": "Context loaded from long-term memory",
    "decisions": "Decisions (with reason)", "decision": "Decisions (with reason)",
    "feedback": "My feedback", "progress": "Progress", "ideas": "Open items / ideas spotted",
    "open": "Open items / ideas spotted",
}
STATUSES = ("in_progress", "waiting_on_me", "done", "abandoned")
TASKS = ("plan", "edit", "carousel", "setup", "log", "other")
KIND_FILE = {"preference": "preferences.md", "lesson": "lessons.md", "idea": "ideas-backlog.md"}
PROMOTE_AT = 3
_META_RE = re.compile(r"\s+— _seen: (\d+) · last: ([\d-]+)(?: · tags: ([^·]*?))?(?: · from: ([^·]*?))?(?: · (promoted))?_$")


# ---------- working memory ----------

def working_path(project_id: str) -> Path:
    return WORKING / f"{project_id}.md"


def _split(text: str) -> tuple[dict, dict[str, list[str]]]:
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    if not m:
        raise ValueError("working memory file has no front matter")
    front = {}
    for ln in m.group(1).splitlines():
        if ":" in ln:
            k, v = ln.split(":", 1)
            front[k.strip()] = v.split("#")[0].strip()
    sections: dict[str, list[str]] = {}
    cur = None
    for ln in m.group(2).splitlines():
        if ln.startswith("## "):
            cur = ln[3:].strip()
            sections[cur] = []
        elif cur is not None:
            sections[cur].append(ln)
    return front, sections


def _join(front: dict, sections: dict[str, list[str]]) -> str:
    fm = "\n".join(f"{k}: {v}" for k, v in front.items())
    body = []
    for name in list(SECTIONS) + [s for s in sections if s not in SECTIONS]:
        lines = [ln for ln in sections.get(name, []) if ln.strip()]
        body.append(f"## {name}\n" + ("\n".join(lines) + "\n" if lines else ""))
    return f"---\n{fm}\n---\n" + "\n".join(body)


def create_working(project_id: str, pillar: str, task: str, goal: str = "", requirements: str = "") -> Path:
    WORKING.mkdir(parents=True, exist_ok=True)
    path = working_path(project_id)
    if path.exists():
        return path  # resuming — never clobber a live task
    front = {"project_id": project_id, "pillar": pillar, "task": task, "status": "in_progress",
             "started": now_iso(), "updated": now_iso()}
    sections = {s: [] for s in SECTIONS}
    if goal:
        sections["Goal"] = [goal]
    if requirements:
        sections["Requirements"] = [f"- {r.strip()}" for r in requirements.split(";") if r.strip()]
    path.write_text(_join(front, sections))
    return path


def _edit(project_id: str, fn) -> Path:
    path = working_path(project_id)
    if not path.exists():
        raise FileNotFoundError(f"no working memory for {project_id}")
    front, sections = _split(path.read_text())
    fn(front, sections)
    front["updated"] = now_iso()
    path.write_text(_join(front, sections))
    return path


def append(project_id: str, section: str, text: str, agent: str | None = None) -> Path:
    name = SECTION_ALIASES.get(section.lower(), section)
    stamp = now_iso()[11:]
    who = f" ({agent})" if agent else ""
    line = text if section.lower() in ("goal",) else f"- [{stamp}]{who} {text}"

    def fn(front, sections):
        sections.setdefault(name, []).append(line)
    return _edit(project_id, fn)


def progress(project_id: str, step: str, done: bool = True) -> Path:
    def fn(front, sections):
        lines = sections.setdefault("Progress", [])
        mark = "x" if done else " "
        for i, ln in enumerate(lines):
            if re.match(rf"^- \[[ x]\] {re.escape(step)}$", ln):
                lines[i] = f"- [{mark}] {step}"
                return
        lines.append(f"- [{mark}] {step}")
    return _edit(project_id, fn)


def set_status(project_id: str, status: str) -> Path:
    if status not in STATUSES:
        raise ValueError(f"status must be one of {STATUSES}")
    return _edit(project_id, lambda front, sections: front.__setitem__("status", status))


def read_working(project_id: str) -> tuple[dict, dict[str, list[str]]]:
    return _split(working_path(project_id).read_text())


def list_open() -> list[dict]:
    out = []
    for p in sorted(WORKING.glob("*.md")):
        try:
            front, sections = _split(p.read_text())
        except ValueError:
            continue
        if front.get("status") in ("in_progress", "waiting_on_me"):
            todo = [ln[6:] for ln in sections.get("Progress", []) if ln.startswith("- [ ] ")]
            done = [ln[6:] for ln in sections.get("Progress", []) if ln.startswith("- [x] ")]
            out.append({**front, "file": str(p), "next_steps": todo, "done_steps": done})
    return out


# ---------- long-term memory ----------

def _ensure_long_term() -> None:
    (LONG / "pillars").mkdir(parents=True, exist_ok=True)
    (LONG / "projects").mkdir(parents=True, exist_ok=True)
    defaults = {
        "index.md": "# Long-term memory index\n\nOne line per memory: `date | type | tags | file | summary`\n\n",
        "preferences.md": "# Preferences\n\nStable likes/dislikes about style, tone, captions, music, words.\n\n",
        "lessons.md": "# Lessons\n\nWhat worked / what failed, with evidence.\n\n",
        "ideas-backlog.md": "# Ideas backlog\n\nContent ideas spotted during tasks, tagged by pillar.\n\n",
    }
    for name, head in defaults.items():
        if not (LONG / name).exists():
            (LONG / name).write_text(head)
    for p in PILLARS:
        f = LONG / "pillars" / f"{p}.md"
        if not f.exists():
            f.write_text(f"# {p}\n\nRunning story and pillar-specific learnings.\n\n")


def _fact_file(kind: str, pillar: str | None) -> Path:
    if kind == "pillar":
        if pillar not in PILLARS:
            raise ValueError("pillar facts need a valid --pillar")
        return LONG / "pillars" / f"{pillar}.md"
    return LONG / KIND_FILE[kind]


def _parse_entry(line: str) -> dict | None:
    if not line.startswith("- "):
        return None
    m = _META_RE.search(line)
    if not m:
        return {"text": line[2:].strip(), "seen": 1, "last": "", "tags": [], "from": [], "promoted": False}
    return {"text": line[2:m.start()].strip(), "seen": int(m.group(1)), "last": m.group(2),
            "tags": [t.strip() for t in (m.group(3) or "").split(",") if t.strip()],
            "from": [t.strip() for t in (m.group(4) or "").split(",") if t.strip()],
            "promoted": bool(m.group(5))}


def _format_entry(e: dict) -> str:
    meta = f"_seen: {e['seen']} · last: {e['last']}"
    if e["tags"]:
        meta += f" · tags: {', '.join(e['tags'])}"
    if e["from"]:
        meta += f" · from: {', '.join(e['from'][-3:])}"
    if e.get("promoted"):
        meta += " · promoted"
    return f"- {e['text']} — {meta}_"


def _similar(a: str, b: str) -> float:
    from rapidfuzz import fuzz
    return fuzz.token_set_ratio(a.lower(), b.lower())


def add_fact(kind: str, text: str, tags: list[str] | None = None, pillar: str | None = None,
             source: str | None = None, replaces: str | None = None) -> dict:
    """Add or merge a durable fact. Returns {"action": added|bumped|replaced, "entry": ..., "file": ...}."""
    _ensure_long_term()
    path = _fact_file(kind, pillar)
    lines = path.read_text().splitlines()
    tags = sorted({t.strip().lower() for t in (tags or []) if t.strip()} | ({pillar} if pillar else set()))
    date = today()
    target_idx, action = None, "added"
    for i, ln in enumerate(lines):
        e = _parse_entry(ln)
        if not e:
            continue
        if replaces and _similar(e["text"], replaces) >= 85:
            target_idx, action = i, "replaced"
            break
        if _similar(e["text"], text) >= 88:
            target_idx, action = i, "bumped"
            break
    if target_idx is None:
        entry = {"text": text, "seen": 1, "last": date, "tags": tags, "from": [source] if source else [], "promoted": False}
        lines.append(_format_entry(entry))
    else:
        old = _parse_entry(lines[target_idx])
        entry = {**old, "seen": old["seen"] + 1, "last": date,
                 "tags": sorted(set(old["tags"]) | set(tags)),
                 "from": old["from"] + ([source] if source and source not in old["from"] else [])}
        if action == "replaced":
            entry["text"] = f"{text} (updated {date}; was: {old['text']})"
        lines[target_idx] = _format_entry(entry)
    path.write_text("\n".join(lines).rstrip() + "\n")
    _index_line(kind, tags, path, entry["text"])
    return {"action": action, "entry": entry, "file": str(path.relative_to(MEMORY.parent)),
            "promote": entry["seen"] >= PROMOTE_AT and not entry.get("promoted")}


def _index_line(kind: str, tags: list[str], path: Path, summary: str) -> None:
    _ensure_long_term()
    rel = path.relative_to(LONG)
    summary = summary.replace("|", "/").replace("\n", " ")[:140]
    line = f"{today()} | {kind} | {','.join(tags)} | {rel} | {summary}"
    lines = INDEX.read_text().splitlines()
    # dedupe: same file + near-identical summary → replace the line in place
    for i, ln in enumerate(lines):
        parts = [p.strip() for p in ln.split("|")]
        if len(parts) == 5 and parts[3] == str(rel) and _similar(parts[4], summary) >= 88:
            lines[i] = line
            break
    else:
        lines.append(line)
    INDEX.write_text("\n".join(lines).rstrip() + "\n")


def mark_promoted(kind: str, text: str, pillar: str | None = None) -> bool:
    path = _fact_file(kind, pillar)
    lines = path.read_text().splitlines()
    for i, ln in enumerate(lines):
        e = _parse_entry(ln)
        if e and _similar(e["text"], text) >= 88:
            e["promoted"] = True
            lines[i] = _format_entry(e)
            path.write_text("\n".join(lines).rstrip() + "\n")
            return True
    return False


def pending_promotions() -> list[dict]:
    _ensure_long_term()
    out = []
    files = [LONG / f for f in KIND_FILE.values()] + list((LONG / "pillars").glob("*.md"))
    for f in files:
        for ln in f.read_text().splitlines():
            e = _parse_entry(ln)
            if e and e["seen"] >= PROMOTE_AT and not e["promoted"]:
                out.append({"file": str(f.relative_to(LONG)), **e})
    return out


def consolidate(project_id: str, record: str | None = None, facts: list[dict] | None = None,
                summary: str | None = None) -> dict:
    """§14.5: project record, durable facts (deduped), index, archive working memory."""
    _ensure_long_term()
    wpath = working_path(project_id)
    front, sections = _split(wpath.read_text()) if wpath.exists() else ({}, {})
    pillar = front.get("pillar")
    if record is None:
        record = _auto_record(project_id, front, sections)
    rec_lines = record.strip().splitlines()
    if len(rec_lines) > 30:
        rec_lines = rec_lines[:29] + ["- … (trimmed to 30 lines)"]
    rec_path = LONG / "projects" / f"{project_id}.md"
    rec_path.write_text("\n".join(rec_lines) + "\n")
    tags = [t for t in (pillar, front.get("task")) if t]
    _index_line("project", tags, rec_path, summary or (sections.get("Goal") or [project_id])[0])

    results = []
    for f in facts or []:
        results.append(add_fact(f["kind"], f["text"], f.get("tags"), f.get("pillar") or (pillar if f["kind"] == "pillar" else None),
                                source=project_id, replaces=f.get("replaces")))

    archived = None
    if wpath.exists():
        if front.get("status") not in ("done", "abandoned"):
            set_status(project_id, "done")
        proj_dir = PROJECTS / project_id
        dest = proj_dir / "working-memory.md" if proj_dir.exists() else LONG / "projects" / f"{project_id}.working.md"
        shutil.move(str(wpath), dest)
        archived = str(dest)
    return {"record": str(rec_path), "facts": results, "archived_working": archived,
            "promotions": pending_promotions()}


def _auto_record(project_id: str, front: dict, sections: dict[str, list[str]]) -> str:
    out = [f"# {project_id}", "",
           f"- pillar: {front.get('pillar', '?')} · task: {front.get('task', '?')} · "
           f"started: {front.get('started', '?')} · finished: {now_iso()}"]
    for name in ("Goal", "Decisions (with reason)", "My feedback", "Open items / ideas spotted"):
        lines = [ln for ln in sections.get(name, []) if ln.strip()]
        if lines:
            out += ["", f"## {name}", *lines[:6]]
    return "\n".join(out)


# ---------- load & search ----------

def _index_rows() -> list[dict]:
    _ensure_long_term()
    rows = []
    for ln in INDEX.read_text().splitlines():
        parts = [p.strip() for p in ln.split("|")]
        if len(parts) == 5 and re.match(r"\d{4}-\d{2}-\d{2}", parts[0]):
            rows.append({"date": parts[0], "type": parts[1], "tags": [t for t in parts[2].split(",") if t],
                         "file": parts[3], "summary": parts[4]})
    return rows


def memory_load(pillar: str, project_id: str | None = None, max_lessons: int = 8) -> list[str]:
    """§14.4: small, relevant context — never everything."""
    _ensure_long_term()
    bullets: list[str] = []
    for ln in (LONG / "preferences.md").read_text().splitlines():
        e = _parse_entry(ln)
        if e:
            bullets.append(f"Preference: {e['text']}")
    pf = LONG / "pillars" / f"{pillar}.md"
    if pf.exists():
        entries = [e for e in map(_parse_entry, pf.read_text().splitlines()) if e]
        bullets += [f"Pillar story: {e['text']}" for e in entries[-6:]]
    lessons = [e for e in map(_parse_entry, (LONG / "lessons.md").read_text().splitlines()) if e]
    lessons.sort(key=lambda e: (pillar in e["tags"], e["seen"], e["last"]), reverse=True)
    bullets += [f"Lesson (seen {e['seen']}×): {e['text']}" for e in lessons[:max_lessons]]
    projects = [r for r in _index_rows() if r["type"] == "project" and pillar in r["tags"]]
    projects.sort(key=lambda r: r["date"], reverse=True)
    for r in projects[:5]:
        bullets.append(f"Recent project ({r['date']}): {r['summary']} → memory/long-term/{r['file']}")
    ideas = [e for e in map(_parse_entry, (LONG / "ideas-backlog.md").read_text().splitlines()) if e and pillar in e["tags"]]
    bullets += [f"Backlog idea: {e['text']}" for e in ideas[:5]]
    if project_id and working_path(project_id).exists():
        def fn(front, sections):
            sections["Context loaded from long-term memory"] = [f"- {b}" for b in bullets] or ["- (nothing relevant yet)"]
        _edit(project_id, fn)
    return bullets


def search(query: str, tags: list[str] | None = None, limit: int = 20) -> list[dict]:
    """Grep index.md first, then matching files; return scored snippets."""
    _ensure_long_term()
    terms = [t for t in re.findall(r"[a-z0-9]+", query.lower()) if len(t) > 1]
    tags = [t.lower() for t in (tags or [])]
    hits: list[dict] = []

    def score(text: str) -> int:
        low = text.lower()
        return sum(low.count(t) for t in terms)

    for r in _index_rows():
        if tags and not set(tags) & set(r["tags"]):
            continue
        s = score(" ".join([r["summary"], " ".join(r["tags"]), r["file"], r["type"]]))
        if s:
            hits.append({"source": "index.md", "file": r["file"], "score": s + 1, "snippet": f"{r['date']} [{r['type']}] {r['summary']}"})
    for f in sorted(LONG.rglob("*.md")):
        if f == INDEX:
            continue
        for ln in f.read_text().splitlines():
            if not ln.strip() or ln.startswith("#"):
                continue
            s = score(ln)
            if s and (not tags or any(t in ln.lower() for t in tags)):
                hits.append({"source": str(f.relative_to(LONG)), "file": str(f.relative_to(LONG)), "score": s, "snippet": ln.strip()[:240]})
    hits.sort(key=lambda h: h["score"], reverse=True)
    seen, out = set(), []
    for h in hits:
        key = (h["file"], h["snippet"])
        if key not in seen:
            seen.add(key)
            out.append(h)
    return out[:limit]


# ---------- CLI ----------

def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="core.memory")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("create"); c.add_argument("project_id"); c.add_argument("pillar"); c.add_argument("task")
    c.add_argument("--goal", default=""); c.add_argument("--requirements", default="")
    a = sub.add_parser("append"); a.add_argument("project_id"); a.add_argument("section"); a.add_argument("text"); a.add_argument("--agent")
    p = sub.add_parser("progress"); p.add_argument("project_id"); p.add_argument("step"); p.add_argument("--todo", action="store_true")
    s = sub.add_parser("status"); s.add_argument("project_id"); s.add_argument("status", choices=STATUSES)
    ld = sub.add_parser("load"); ld.add_argument("pillar", choices=PILLARS); ld.add_argument("--project")
    co = sub.add_parser("consolidate"); co.add_argument("project_id"); co.add_argument("--facts", help="facts.json path")
    r = sub.add_parser("remember"); r.add_argument("text"); r.add_argument("--kind", default="preference", choices=["preference", "lesson", "idea", "pillar"])
    r.add_argument("--tags", default=""); r.add_argument("--pillar")
    se = sub.add_parser("search"); se.add_argument("query"); se.add_argument("--tags", default="")
    sub.add_parser("open")
    sub.add_parser("promotions")
    mp = sub.add_parser("mark-promoted"); mp.add_argument("kind"); mp.add_argument("text"); mp.add_argument("--pillar")
    args = ap.parse_args(argv)

    if args.cmd == "create":
        print(create_working(args.project_id, args.pillar, args.task, args.goal, args.requirements))
    elif args.cmd == "append":
        append(args.project_id, args.section, args.text, args.agent)
    elif args.cmd == "progress":
        progress(args.project_id, args.step, done=not args.todo)
    elif args.cmd == "status":
        set_status(args.project_id, args.status)
    elif args.cmd == "load":
        for b in memory_load(args.pillar, args.project):
            print(f"- {b}")
    elif args.cmd == "consolidate":
        payload = json.loads(Path(args.facts).read_text()) if args.facts else {}
        print(json.dumps(consolidate(args.project_id, payload.get("record"), payload.get("facts"), payload.get("summary")), indent=2))
    elif args.cmd == "remember":
        tags = [t for t in args.tags.split(",") if t]
        print(json.dumps(add_fact(args.kind, args.text, tags, args.pillar, source="manual"), indent=2))
    elif args.cmd == "search":
        res = search(args.query, [t for t in args.tags.split(",") if t])
        if not res:
            print("(no memories match)")
        for h in res:
            print(f"[{h['file']}] {h['snippet']}")
    elif args.cmd == "open":
        items = list_open()
        if not items:
            print("(no unfinished tasks)")
        for it in items:
            print(f"{it['project_id']} · {it['task']} · {it['status']} · updated {it['updated']} · next: {', '.join(it['next_steps'][:3]) or '—'}")
    elif args.cmd == "promotions":
        print(json.dumps(pending_promotions(), indent=2))
    elif args.cmd == "mark-promoted":
        print(mark_promoted(args.kind, args.text, args.pillar))


if __name__ == "__main__":
    sys.exit(main())
