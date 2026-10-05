"""Writer harness — platform-specific drafts from proven insights. Draft-only: you post it yourself.

  ./studio write accounts                                   accounts the writer can draft for (brain/accounts/)
  ./studio write context <account> [--topic T] [--n 5]      the brief: account, playbook, top insights, own winners
  ./studio write new <account> --format F --title "…" [--idea "…"] [--pillar P] [--ref-url URL] [--insights 3,7] [--topic T]
        formats — instagram: reel | carousel · linkedin: text | doc-carousel | video · x: post | thread | video
  ./studio write list [--account A] [--status draft|approved|published|dropped]
  ./studio write show <draft-id>
  ./studio write validate <draft-id>                        schema + platform rules; writes post.md (copy-paste) when clean
  ./studio write status <draft-id> approved|dropped|draft   (published comes from ./studio hq log … --draft N)

Add --json to any command for machine-readable output.
"""
from __future__ import annotations

import argparse
import json
import sys

from core import accounts, db
from core.common import table
from harnesses.writer import context, drafts


def _ints(s: str | None) -> list[int]:
    return [int(x) for x in s.split(",") if x.strip()] if s else []


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    as_json = "--json" in argv
    ap = argparse.ArgumentParser(prog="studio write", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("accounts")
    x = sub.add_parser("context")
    x.add_argument("account")
    x.add_argument("--topic")
    x.add_argument("--n", type=int, default=5)
    x = sub.add_parser("new")
    x.add_argument("account")
    x.add_argument("--format", required=True)
    x.add_argument("--title", required=True)
    x.add_argument("--idea")
    x.add_argument("--pillar")
    x.add_argument("--ref-url")
    x.add_argument("--insights")
    x.add_argument("--topic")
    x = sub.add_parser("list")
    x.add_argument("--account")
    x.add_argument("--status", choices=("draft", "approved", "published", "dropped"))
    for name in ("show", "validate"):
        sub.add_parser(name).add_argument("id", type=int)
    x = sub.add_parser("status")
    x.add_argument("id", type=int)
    x.add_argument("status", choices=("draft", "approved", "dropped", "published"))
    a = ap.parse_args([v for v in argv if v != "--json"])
    con = db.connect()

    if a.cmd == "accounts":
        rows = accounts.sync(con)
        for r in rows:
            r["formats"] = ", ".join(accounts.FORMATS.get(r["platform"], {}))
        print(json.dumps(rows, indent=2) if as_json else table(rows, ["id", "platform", "handle", "status", "formats"]))
    elif a.cmd == "context":
        ctx = context.build(con, a.account, a.topic, a.n)
        print(json.dumps(ctx, indent=2, default=str) if as_json else context.markdown(ctx))
    elif a.cmd == "new":
        print(drafts.as_json(drafts.new(con, a.account, a.format, a.title, a.idea, a.pillar, a.ref_url, _ints(a.insights), a.topic)))
    elif a.cmd == "list":
        rows = drafts.listing(con, a.account, a.status)
        print(drafts.as_json(rows) if as_json else table(rows, ["id", "account_id", "format", "status", "title", "path"],
                                                           {"title": 40, "path": 60}))
    elif a.cmd == "show":
        print(drafts.as_json(drafts.get(con, a.id)))
    elif a.cmd == "validate":
        res = drafts.check(con, a.id)
        if as_json:
            print(drafts.as_json(res))
        else:
            print(("✓ draft #%d is clean" % a.id) if res["ok"] else ("✗ draft #%d" % a.id))
            for e in res["errors"]:
                print(f"  ✗ {e}")
            for w in res["warnings"]:
                print(f"  ! {w}")
            if res.get("copy"):
                print(f"  copy-paste version: {res['copy']}")
        return 0 if res["ok"] else 1
    elif a.cmd == "status":
        print(drafts.as_json(drafts.set_status(con, a.id, a.status)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
