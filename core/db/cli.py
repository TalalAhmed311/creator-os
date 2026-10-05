"""Database tools.   ./studio db <command>

  ./studio db init                 create / migrate data/creator-os.db
  ./studio db stats                rows per table, schema version, file
  ./studio db sql "SELECT …"       read-only query (agents use this to explore); --json for rows as JSON
  ./studio db export [--out DIR]   every table → DIR/<table>.jsonl (default data/export/) — the git-friendly backup
  ./studio db restore [--from DIR] rebuild an EMPTY database from an export (refuses if data exists)

The database file is git-ignored; `db export` writes the version you commit.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

from core import db
from core.common import table

TABLES = ("accounts", "creators", "creator_handles", "creator_snapshots", "posts", "metric_snapshots", "analyses",
          "insights", "insight_evidence", "drafts", "draft_insights")


def stats(con: sqlite3.Connection) -> dict:
    return {"file": str(db.db_path()), "schema_version": db.schema_version(con),
            "rows": {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in TABLES}}


def query(sql: str) -> list[dict]:
    con = sqlite3.connect(f"file:{db.db_path()}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA query_only = ON")
    return db.dicts(con.execute(sql))


def export(con: sqlite3.Connection, out: Path) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    counts = {}
    for t in TABLES:
        rows = db.dicts(con.execute(f"SELECT * FROM {t} ORDER BY rowid"))
        (out / f"{t}.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
        counts[t] = len(rows)
    return counts


def restore(con: sqlite3.Connection, src: Path) -> dict:
    if any(stats(con)["rows"].values()):
        raise SystemExit("database is not empty — restore only into a fresh file (move data/creator-os.db aside first)")
    counts = {}
    with con:
        for t in TABLES:  # TABLES is in foreign-key order
            f = src / f"{t}.jsonl"
            rows = [json.loads(ln) for ln in f.read_text().splitlines() if ln.strip()] if f.exists() else []
            for r in rows:
                con.execute(f"INSERT INTO {t} ({', '.join(r)}) VALUES ({', '.join('?' * len(r))})", list(r.values()))
            counts[t] = len(rows)
    return counts


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="studio db", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init")
    sub.add_parser("stats")
    q = sub.add_parser("sql")
    q.add_argument("sql")
    q.add_argument("--json", action="store_true")
    e = sub.add_parser("export")
    e.add_argument("--out", default=str(db.DATA / "export"))
    r = sub.add_parser("restore")
    r.add_argument("--from", dest="src", default=str(db.DATA / "export"))
    a = ap.parse_args(argv)
    con = db.connect()
    if a.cmd in ("init", "stats"):
        print(json.dumps(stats(con), indent=2))
    elif a.cmd == "sql":
        rows = query(a.sql)
        print(json.dumps(rows, indent=2, default=str) if a.json else table(rows, list(rows[0]) if rows else []))
    elif a.cmd == "export":
        print(json.dumps(export(con, Path(a.out)), indent=2))
    elif a.cmd == "restore":
        print(json.dumps(restore(con, Path(a.src)), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
