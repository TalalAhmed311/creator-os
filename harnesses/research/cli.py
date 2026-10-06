"""Research harness — creator database, content analysis, top insights.   ./studio research <command> …

  creators list [--platform P] [--status tracked|candidate|dropped] [--cluster C] [--signal S] [--set] [--q TEXT] [--limit N]
  creators show <handle> [--platform P]
  creators add <platform> <handle> --name N [--niche N] [--cluster C] [--relevance 1-5] [--why TEXT] [--original yes|unclear]
  creators track|drop|candidate <handle> [--platform P] [--why TEXT]
  creators set <handle> [--relevance N] [--niche N] [--cluster C] [--country C] [--notes TEXT]
  creators link <handle> <other-platform> <other-handle>        same person on another platform
  creators snapshot <handle> --source S [--quality verified|estimated] [--followers N] [--typical-views N]
                    [--peak-views N] [--posts N] [--per-week N] [--date YYYY-MM-DD] [--note TEXT]
  import-seed <doc.md> [--platform instagram]                   load a creator-research document

  post add <url> [--handle H] [--text T | --text-file F] [--no-download] [--analyze] [--format F] [--topic T]
                 [--posted-at DATE] [--views N --likes N --comments N --shares N --saves N --reposts N]
                 [--source S] [--quality verified|estimated]
  post metrics <post-id|url> --source S [--quality verified|estimated] [--views N --likes N …] [--date ISO]
                 counters read from the page (e.g. IG play counts, which yt-dlp can't see without a login)
  post analyze <post-id|url> [--force]                          transcript, cuts, hook frames, pacing (video posts)
  post refresh <post-id…> | --handle H | --tracked              new public-counter snapshot (no download)
  post list [--platform P] [--handle H] [--cluster C] [--min-outlier X] [--unanalysed] [--limit N]
  analysis set <post-id|url> [--hook-type T] [--hook-text T] [--visual-hook T] [--structure T] [--pacing T]
                             [--cta T] [--why T]
  outliers [--platform P] [--cluster C] [--min X] [--limit N] [--metric auto|views|likes]
                 posts ranked by views ÷ the creator's normal (auto: likes/reactions where views aren't public)

  insight add "<pattern>" --kind hook|structure|format|visual|topic|cadence|cta|other [--platform P] [--topic T]
                          [--how TEXT] [--evidence 3,7,9] [--confidence low|medium|high]
  insight top [--platform P] [--topic T] [--kind K] [--n 5]
  insight list [--platform P] [--all]
  insight evidence <id> <post-id,post-id…>                      add proving posts to an existing insight
  insight retire <id>
  report <slug> [--platform P] [--topic T] [--n 5]              → data/reports/research/<date>-<slug>.md

Every command takes --json for machine-readable output.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from core import db
from core.common import table
from harnesses.research import creators, insights, posts, report, seed


def _out(data, args, cols=None, widths=None) -> None:
    if args.json or cols is None:
        print(json.dumps(data, indent=2, default=str))
    else:
        print(table(data if isinstance(data, list) else [data], cols, widths))


def _ints(s: str | None) -> list[int]:
    return [int(x) for x in s.split(",") if x.strip()] if s else []


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="studio research", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", action="store_true")
    sub = ap.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("creators").add_subparsers(dest="sub", required=True)
    x = c.add_parser("list")
    x.add_argument("--platform", choices=db.PLATFORMS)
    x.add_argument("--status", choices=("candidate", "tracked", "dropped"))
    x.add_argument("--cluster")
    x.add_argument("--signal")
    x.add_argument("--set", action="store_true", help="only the research set")
    x.add_argument("--q")
    x.add_argument("--limit", type=int)
    x = c.add_parser("show")
    x.add_argument("handle")
    x.add_argument("--platform", default="instagram", choices=db.PLATFORMS)
    x = c.add_parser("add")
    x.add_argument("platform", choices=db.PLATFORMS)
    x.add_argument("handle")
    x.add_argument("--name", required=True)
    x.add_argument("--niche")
    x.add_argument("--cluster")
    x.add_argument("--relevance", type=float)
    x.add_argument("--original", choices=("yes", "unclear", "no"))
    x.add_argument("--country")
    x.add_argument("--why")
    x.add_argument("--notes")
    for name in ("track", "drop", "candidate"):
        x = c.add_parser(name)
        x.add_argument("handle")
        x.add_argument("--platform", default="instagram", choices=db.PLATFORMS)
        x.add_argument("--why")
    x = c.add_parser("set")
    x.add_argument("handle")
    x.add_argument("--platform", default="instagram", choices=db.PLATFORMS)
    x.add_argument("--relevance", type=float)
    x.add_argument("--niche")
    x.add_argument("--cluster")
    x.add_argument("--country")
    x.add_argument("--original", choices=("yes", "unclear", "no"))
    x.add_argument("--notes")
    x.add_argument("--why")
    x = c.add_parser("link")
    x.add_argument("handle")
    x.add_argument("other_platform", choices=db.PLATFORMS)
    x.add_argument("other_handle")
    x.add_argument("--platform", default="instagram", choices=db.PLATFORMS)
    x = c.add_parser("snapshot")
    x.add_argument("handle")
    x.add_argument("--platform", default="instagram", choices=db.PLATFORMS)
    x.add_argument("--source", required=True)
    x.add_argument("--quality", default="estimated", choices=db.QUALITIES)
    for k in ("followers", "typical-views", "peak-views", "posts"):
        x.add_argument(f"--{k}", type=int)
    x.add_argument("--per-week", type=float)
    x.add_argument("--date")
    x.add_argument("--note")

    x = sub.add_parser("import-seed")
    x.add_argument("doc")
    x.add_argument("--platform", default="instagram", choices=db.PLATFORMS)

    p = sub.add_parser("post").add_subparsers(dest="sub", required=True)
    x = p.add_parser("add")
    x.add_argument("url")
    x.add_argument("--handle")
    x.add_argument("--platform", choices=db.PLATFORMS)
    x.add_argument("--text")
    x.add_argument("--text-file")
    x.add_argument("--no-download", action="store_true")
    x.add_argument("--analyze", action="store_true")
    x.add_argument("--format")
    x.add_argument("--topic")
    x.add_argument("--posted-at")
    for k in ("views", "likes", "comments", "shares", "saves", "reposts", "impressions"):
        x.add_argument(f"--{k}", type=int)
    x.add_argument("--source")
    x.add_argument("--quality", choices=db.QUALITIES)
    x = p.add_parser("metrics")
    x.add_argument("post")
    x.add_argument("--source", required=True)
    x.add_argument("--quality", default="verified", choices=db.QUALITIES)
    x.add_argument("--date")
    for k in ("views", "likes", "comments", "shares", "saves", "reposts", "impressions"):
        x.add_argument(f"--{k}", type=int)
    x = p.add_parser("analyze")
    x.add_argument("post")
    x.add_argument("--force", action="store_true")
    x = p.add_parser("refresh")
    x.add_argument("posts", nargs="*", type=int)
    x.add_argument("--handle")
    x.add_argument("--platform", default="instagram", choices=db.PLATFORMS)
    x.add_argument("--tracked", action="store_true", help="every post by a tracked creator")
    x = p.add_parser("list")
    x.add_argument("--platform", choices=db.PLATFORMS)
    x.add_argument("--handle")
    x.add_argument("--cluster")
    x.add_argument("--min-outlier", type=float)
    x.add_argument("--unanalysed", action="store_true")
    x.add_argument("--limit", type=int)
    x.add_argument("--metric", default="auto", choices=("auto", *db.OUTLIER_METRICS))

    x = sub.add_parser("analysis").add_subparsers(dest="sub", required=True).add_parser("set")
    x.add_argument("post")
    for k in ("hook-type", "hook-text", "visual-hook", "structure", "pacing", "cta", "why"):
        x.add_argument(f"--{k}")

    x = sub.add_parser("outliers")
    x.add_argument("--platform", choices=db.PLATFORMS)
    x.add_argument("--cluster")
    x.add_argument("--min", type=float)
    x.add_argument("--limit", type=int, default=20)
    x.add_argument("--metric", default="auto", choices=("auto", *db.OUTLIER_METRICS),
                   help="auto: views, else likes/reactions where views aren't public (LinkedIn)")

    i = sub.add_parser("insight").add_subparsers(dest="sub", required=True)
    x = i.add_parser("add")
    x.add_argument("pattern")
    x.add_argument("--kind", required=True, choices=insights.KINDS)
    x.add_argument("--platform", choices=db.PLATFORMS)
    x.add_argument("--topic")
    x.add_argument("--how")
    x.add_argument("--evidence")
    x.add_argument("--confidence", default="low", choices=tuple(insights.CONF))
    x = i.add_parser("top")
    x.add_argument("--platform", choices=db.PLATFORMS)
    x.add_argument("--topic")
    x.add_argument("--kind", choices=insights.KINDS)
    x.add_argument("--n", type=int, default=5)
    x = i.add_parser("list")
    x.add_argument("--platform", choices=db.PLATFORMS)
    x.add_argument("--all", action="store_true")
    x = i.add_parser("evidence")
    x.add_argument("id", type=int)
    x.add_argument("posts", help="post ids, comma-separated")
    x = i.add_parser("retire")
    x.add_argument("id", type=int)

    x = sub.add_parser("report")
    x.add_argument("slug")
    x.add_argument("--platform", choices=db.PLATFORMS)
    x.add_argument("--topic")
    x.add_argument("--n", type=int, default=5)
    return ap


CREATOR_COLS = ["score", "platform", "handle", "name", "status", "signal", "cluster", "followers", "typical_views",
                "reach_ratio", "posts_in_db"]
POST_COLS = ["id", "author_handle", "format", "posted_at", "views", "likes", "outlier", "outlier_basis", "hook_text", "url"]
WIDTHS = {"name": 22, "hook_text": 40, "url": 48, "posted_at": 10, "outlier_basis": 26, "pattern": 70}


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    as_json = "--json" in argv  # accepted anywhere on the line, not only before the subcommand
    args = parser().parse_args([x for x in argv if x != "--json"])
    args.json = as_json
    con = db.connect()
    cmd, sub = args.cmd, getattr(args, "sub", None)

    if cmd == "creators":
        if sub == "list":
            rows = creators.listing(con, args.platform, args.status, args.cluster, args.signal, args.set, args.q)
            _out(rows[: args.limit] if args.limit else rows, args, CREATOR_COLS, WIDTHS)
        elif sub == "show":
            c = creators.show(con, args.platform, args.handle)
            if args.json:
                _out(c, args)
            else:
                print(f"@{c['handle']} ({c['platform']}) — {c['name']} · {c['status']} · score {c['score']} · {c['signal'] or ''}")
                print(f"{c['primary_niche'] or ''} / {c['secondary_niche'] or ''} · {c['cluster'] or ''} · {c['country'] or ''}")
                print(f"why: {c['why'] or '—'}\nnotes: {c['notes'] or '—'}\n")
                print(table(c["snapshots"], ["captured_at", "source", "quality", "followers", "typical_views", "reach_ratio",
                                             "peak_views", "posts", "posts_per_week"]))
                print()
                print(table(c["posts"], POST_COLS, WIDTHS))
        elif sub == "add":
            with con:
                hid = db.ensure_handle(con, args.platform, args.handle, name=args.name, primary_niche=args.niche,
                                       cluster=args.cluster, relevance=args.relevance, original=args.original,
                                       country=args.country, why=args.why, notes=args.notes)
            _out({"handle_id": hid, "status": db.find_handle(con, args.platform, args.handle)["status"]}, args)
        elif sub in ("track", "drop", "candidate"):
            creators.set_status(con, args.platform, args.handle, {"track": "tracked", "drop": "dropped"}.get(sub, sub), args.why)
            _out({"handle": db.norm_handle(args.handle), "status": db.find_handle(con, args.platform, args.handle)["status"]}, args)
        elif sub == "set":
            h = db.find_handle(con, args.platform, args.handle) or sys.exit(f"no {args.platform} creator @{args.handle}")
            with con:
                db.update_creator(con, h["creator_id"], relevance=args.relevance, primary_niche=args.niche, cluster=args.cluster,
                                  country=args.country, original=args.original, notes=args.notes, why=args.why)
            _out({"handle": h["handle"], "updated": True}, args)
        elif sub == "link":
            _out({"handle_id": creators.link_handle(con, args.platform, args.handle, args.other_platform, args.other_handle)}, args)
        elif sub == "snapshot":
            h = db.find_handle(con, args.platform, args.handle) or sys.exit(f"no {args.platform} creator @{args.handle}")
            with con:
                sid = db.add_creator_snapshot(con, h["id"], args.source, args.quality, args.date, followers=args.followers,
                                              typical_views=args.typical_views, peak_views=args.peak_views, posts=args.posts,
                                              posts_per_week=args.per_week, note=args.note,
                                              reach_ratio=round(args.typical_views / args.followers, 2)
                                              if args.typical_views and args.followers else None)
            _out({"snapshot_id": sid}, args)
    elif cmd == "import-seed":
        _out(seed.import_seed(Path(args.doc), args.platform, con), args)
    elif cmd == "post":
        if sub == "add":
            text = Path(args.text_file).read_text() if args.text_file else args.text
            metrics = {k: getattr(args, k) for k in ("views", "likes", "comments", "shares", "saves", "reposts", "impressions")}
            res = posts.add(con, args.url, args.handle, args.platform, False if args.no_download else None, text, args.posted_at,
                            args.format, args.topic, args.source, args.quality, metrics)
            if args.analyze and res["ref"]:
                res["analysis"] = posts.analyze(con, res["post_id"])["analysis"]
            _out(res, args)
        elif sub == "metrics":
            post = db.find_post(con, args.post) or sys.exit(f"no post {args.post}")
            with con:
                mid = db.add_metrics(con, post["id"], args.source, args.quality, args.date,
                                     **{k: getattr(args, k) for k in db.METRICS if hasattr(args, k)})
            _out({"post_id": post["id"], "snapshot_id": mid}, args)
        elif sub == "analyze":
            _out(posts.analyze(con, args.post, args.force), args)
        elif sub == "refresh":
            ids = list(args.posts)
            if args.handle:
                h = db.find_handle(con, args.platform, args.handle) or sys.exit(f"no {args.platform} creator @{args.handle}")
                ids += [r[0] for r in con.execute("SELECT id FROM posts WHERE handle_id = ?", (h["id"],))]
            if args.tracked:
                ids += [r[0] for r in con.execute("""SELECT p.id FROM posts p JOIN creator_handles h ON h.id = p.handle_id
                                                     JOIN creators c ON c.id = h.creator_id WHERE c.status = 'tracked'""")]
            _out(posts.refresh(con, sorted(set(ids))), args, ["post_id", "ok", "views"])
        elif sub == "list":
            rows = posts.listing(con, args.platform, args.handle, args.cluster, args.min_outlier,
                                 False if args.unanalysed else None, args.limit, args.metric)
            _out(rows, args, POST_COLS, WIDTHS)
    elif cmd == "analysis":
        _out(posts.set_analysis(con, args.post, hook_type=args.hook_type, hook_text=args.hook_text, visual_hook=args.visual_hook,
                                structure=args.structure, pacing=args.pacing, cta=args.cta, why_it_worked=args.why), args)
    elif cmd == "outliers":
        _out(posts.listing(con, args.platform, None, args.cluster, args.min, None, args.limit, args.metric), args, POST_COLS, WIDTHS)
    elif cmd == "insight":
        if sub == "add":
            _out(insights.add(con, args.pattern, args.kind, args.platform, args.topic, args.how, _ints(args.evidence),
                              args.confidence), args)
        elif sub == "top":
            _out(insights.ranked(con, args.platform, args.topic, args.kind, args.n), args,
                 ["id", "rank_score", "kind", "platform", "confidence", "seen", "avg_outlier", "pattern"], WIDTHS)
        elif sub == "list":
            _out(insights.ranked(con, args.platform, include_retired=args.all), args,
                 ["id", "status", "kind", "platform", "confidence", "seen", "pattern"], WIDTHS)
        elif sub == "evidence":
            _out(insights.add_evidence(con, args.id, _ints(args.posts)), args)
        elif sub == "retire":
            insights.retire(con, args.id)
            _out({"insight_id": args.id, "status": "retired"}, args)
    elif cmd == "report":
        print(report.build(con, args.slug, args.platform, args.topic, args.n))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
