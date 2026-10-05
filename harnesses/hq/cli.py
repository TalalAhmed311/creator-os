"""HQ — the harness of harnesses: your accounts, your published posts, daily metrics, and what's working.

  ./studio hq accounts [sync]                          brain/accounts/*.md → database; list them
  ./studio hq log <account> <url> [--draft N] [--project ID] [--posted-at ISO] [--format F] [--pillar P] [--topic T]
                  [--views N --likes N --comments N --shares N --saves N --reposts N --impressions N --reach N --avg-watch N]
                                                       register a post you published (links + closes the draft)
  ./studio hq posts [--account A] [--limit N]          your posts with latest metrics and score vs your median
  ./studio hq metrics add <post-id|url> [--views N …] [--source manual] [--quality verified|estimated] [--date ISO]
  ./studio hq metrics import <file.csv> --source <name> [--account A]   analytics export → snapshots
  ./studio hq due                                      posts past a 1/3/7/30-day checkpoint without a snapshot
  ./studio hq sync [--dry-run]                         fetch metrics for due posts; the rest → data/hq/pending-metrics.md
  ./studio hq review [--account A] [--days N] [--min-group 2]   findings vs your own median → data/reports/hq/
  ./studio hq import-log [brain/content-log.csv] [--map instagram=instagram-buildwith.talal …]   migrate the old /log CSV
  ./studio hq schedule [--install [--hour 9] | --uninstall]     daily sync with launchd (only installs with --install)

Add --json to any command for machine-readable output.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from core import accounts, db
from core.common import BRAIN, table
from harnesses.hq import content, review, schedule

METRIC_FLAGS = {"views": "views", "likes": "likes", "comments": "comments", "shares": "shares", "saves": "saves",
                "reposts": "reposts", "impressions": "impressions", "reach": "reach", "avg-watch": "avg_watch_pct",
                "profile-visits": "profile_visits", "follows": "follows"}


def _metric_args(p: argparse.ArgumentParser) -> None:
    for flag in METRIC_FLAGS:
        p.add_argument(f"--{flag}", type=float)


def _metrics(a) -> dict:
    out = {}
    for flag, col in METRIC_FLAGS.items():
        v = getattr(a, flag.replace("-", "_"))
        if v is not None:
            out[col] = int(v) if float(v).is_integer() and col != "avg_watch_pct" else v
    return out


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    as_json = "--json" in argv
    ap = argparse.ArgumentParser(prog="studio hq", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    x = sub.add_parser("accounts")
    x.add_argument("action", nargs="?", default="list", choices=("list", "sync"))
    x = sub.add_parser("log")
    x.add_argument("account")
    x.add_argument("url")
    x.add_argument("--draft", type=int)
    x.add_argument("--project")
    x.add_argument("--posted-at")
    x.add_argument("--format")
    x.add_argument("--pillar")
    x.add_argument("--topic")
    x.add_argument("--source", default="manual")
    _metric_args(x)
    x = sub.add_parser("posts")
    x.add_argument("--account")
    x.add_argument("--limit", type=int)
    m = sub.add_parser("metrics").add_subparsers(dest="sub", required=True)
    x = m.add_parser("add")
    x.add_argument("post")
    x.add_argument("--source", default="manual")
    x.add_argument("--quality", default="verified", choices=db.QUALITIES)
    x.add_argument("--date")
    _metric_args(x)
    x = m.add_parser("import")
    x.add_argument("file")
    x.add_argument("--source", required=True)
    x.add_argument("--quality", default="verified", choices=db.QUALITIES)
    x.add_argument("--account")
    sub.add_parser("due")
    x = sub.add_parser("sync")
    x.add_argument("--dry-run", action="store_true")
    x = sub.add_parser("review")
    x.add_argument("--account")
    x.add_argument("--days", type=int)
    x.add_argument("--min-group", type=int, default=2)
    x = sub.add_parser("import-log")
    x.add_argument("file", nargs="?", default=str(BRAIN / "content-log.csv"))
    x.add_argument("--map", nargs="*", default=[], help="platform=account-id pairs")
    x = sub.add_parser("schedule")
    x.add_argument("--install", action="store_true")
    x.add_argument("--uninstall", action="store_true")
    x.add_argument("--hour", type=int, default=9)
    a = ap.parse_args([v for v in argv if v != "--json"])
    con = db.connect()
    dump = lambda d: print(json.dumps(d, indent=2, default=str))  # noqa: E731

    if a.cmd == "accounts":
        rows = accounts.sync(con)
        dump(rows) if as_json else print(table(rows, ["id", "platform", "handle", "status"]))
    elif a.cmd == "log":
        dump(content.log(con, a.account, a.url, a.draft, a.project, a.posted_at, a.format, a.pillar, a.topic, _metrics(a), a.source))
    elif a.cmd == "posts":
        accounts.sync(con)
        ids = [a.account] if a.account else [r[0] for r in con.execute("SELECT id FROM accounts ORDER BY id")]
        rows = [p for aid in ids for p in review.posts_with_scores(con, aid)]
        rows.sort(key=lambda p: p["posted_at"] or "", reverse=True)
        rows = rows[: a.limit] if a.limit else rows
        dump(rows) if as_json else print(table(rows, ["id", "account_id", "format", "posted_at", "reach_value", "score",
                                                      "engagement_rate", "hook_type", "url"], {"posted_at": 10, "url": 50}))
    elif a.cmd == "metrics":
        if a.sub == "add":
            dump(content.add_metrics(con, a.post, a.source, a.quality, a.date, **_metrics(a)))
        else:
            dump(content.import_csv(con, Path(a.file), a.source, a.quality, a.account))
    elif a.cmd == "due":
        rows = content.due(con)
        dump(rows) if as_json else print(table(rows, ["post_id", "account", "checkpoint_days", "posted_at", "url"]))
    elif a.cmd == "sync":
        res = content.sync(con, a.dry_run)
        if as_json:
            dump(res)
        else:
            print(f"{res['due']} due · {len(res['synced'])} synced · {len(res['pending'])} need numbers by hand → {res['pending_file']}")
            for p in res["pending"]:
                print(f"  - {p['account']} day {p['checkpoint_days']}: {p['url']} ({p['reason']})")
    elif a.cmd == "review":
        accounts.sync(con)
        res = review.review(con, a.account, a.days, a.min_group)
        if as_json:
            dump(res)
        else:
            for aid, r in res["accounts"].items():
                print(f"{aid}: {r['posts']} posts, {r['with_metrics']} with metrics, median reach {r['median_reach'] or '—'}")
                for f in r["findings"]:
                    print(f"  - {f}")
            print(f"report → {res['report']}")
    elif a.cmd == "import-log":
        mapping = dict(x.split("=", 1) for x in a.map)
        accounts.sync(con)
        for plat in db.PLATFORMS:  # default: the only account on that platform
            ids = [r[0] for r in con.execute("SELECT id FROM accounts WHERE platform = ?", (plat,))]
            if plat not in mapping and len(ids) == 1:
                mapping[plat] = ids[0]
        dump(content.import_content_log(con, Path(a.file), mapping))
    elif a.cmd == "schedule":
        dump(schedule.install(a.hour) if a.install else schedule.uninstall() if a.uninstall
             else {**schedule.status(), "would_run_daily_at": f"{a.hour:02d}:00", "install_with": "./studio hq schedule --install"})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
