"""/log and the learning loop (§14.7).

  python -m pipeline.content_log add <project_id> --url URL --platform tiktok --views 1200 --avg-watch 41 \
        [--likes N --comments N --saves N --shares N --notes "..."]
  python -m pipeline.content_log analyze          # compare hook types / pillars / lengths → JSON findings
  python -m pipeline.content_log count             # rows logged (strategist runs analyze every 5)

Hook type, hook text, pillar and length are filled from the project's plan.json / edl.json automatically.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from statistics import mean, median

from pipeline.common import BRAIN, Project, load_json, today
from pipeline.timeline import total_duration

LOG = BRAIN / "content-log.csv"
FIELDS = ["date", "project_id", "pillar", "hook_type", "hook_text", "length_s", "platform", "url", "views",
          "avg_watch_pct", "likes", "comments", "saves", "shares", "notes"]


def rows() -> list[dict]:
    if not LOG.exists():
        return []
    with LOG.open() as f:
        return list(csv.DictReader(f))


def add(project_id: str, **stats) -> dict:
    proj = Project(project_id)
    plan = proj.plan() or {}
    row = {k: "" for k in FIELDS}
    row.update(date=today(), project_id=proj.id, pillar=plan.get("pillar", ""))
    if plan.get("hooks") and plan.get("chosen_hook") is not None:
        h = plan["hooks"][plan["chosen_hook"]]
        row.update(hook_type=h["type"], hook_text=h["on_screen"])
    edl_p = proj.root / "edl.json"
    if edl_p.exists():
        edl = load_json(edl_p)
        row["length_s"] = f"{total_duration(edl['segments'], edl['output']['fps']):.1f}"
    elif (proj.root / "carousel.json").exists():
        row["length_s"] = str(len(load_json(proj.root / "carousel.json")["slides"])) + " slides"
    row.update({k: ("" if v is None else str(v)) for k, v in stats.items() if k in FIELDS})
    new = not LOG.exists() or LOG.stat().st_size == 0
    with LOG.open("a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new:
            w.writeheader()
        w.writerow(row)
    return row


def _num(v: str) -> float | None:
    try:
        return float(str(v).replace("%", "").replace(",", ""))
    except ValueError:
        return None


def analyze(min_group: int = 2) -> dict:
    data = rows()
    out: dict = {"posts": len(data), "by": {}}
    if not data:
        return out

    def group(key_fn, name):
        g = defaultdict(list)
        for r in data:
            k = key_fn(r)
            if k:
                g[k].append(r)
        res = {}
        for k, rs in g.items():
            watch = [x for x in (_num(r["avg_watch_pct"]) for r in rs) if x is not None]
            views = [x for x in (_num(r["views"]) for r in rs) if x is not None]
            saves = [x for x in (_num(r["saves"]) for r in rs) if x is not None]
            res[k] = {"n": len(rs), "avg_watch_pct": round(mean(watch), 1) if watch else None,
                      "median_views": median(views) if views else None, "avg_saves": round(mean(saves), 1) if saves else None}
        out["by"][name] = res

    def length_bucket(r):
        n = _num(r["length_s"].split()[0]) if r["length_s"] else None
        if n is None or "slides" in r["length_s"]:
            return None
        return "<20s" if n < 20 else "20-35s" if n < 35 else "35-50s" if n < 50 else "50s+"

    group(lambda r: r["hook_type"], "hook_type")
    group(lambda r: r["pillar"], "pillar")
    group(lambda r: r["platform"], "platform")
    group(length_bucket, "length")
    findings = []
    for dim, groups in out["by"].items():
        valid = {k: v for k, v in groups.items() if v["n"] >= min_group and v["avg_watch_pct"] is not None}
        if len(valid) >= 2:
            best = max(valid, key=lambda k: valid[k]["avg_watch_pct"])
            worst = min(valid, key=lambda k: valid[k]["avg_watch_pct"])
            if valid[worst]["avg_watch_pct"] > 0:
                ratio = valid[best]["avg_watch_pct"] / valid[worst]["avg_watch_pct"]
                if ratio >= 1.2:
                    findings.append(f"{dim}: '{best}' gets {ratio:.1f}× the watch time of '{worst}' "
                                    f"({valid[best]['avg_watch_pct']}% vs {valid[worst]['avg_watch_pct']}%, n={valid[best]['n']}/{valid[worst]['n']})")
    out["findings"] = findings
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("add")
    a.add_argument("project_id")
    a.add_argument("--url", required=True)
    a.add_argument("--platform", required=True, choices=["instagram", "tiktok", "youtube", "linkedin"])
    for k in ("views", "avg-watch", "likes", "comments", "saves", "shares"):
        a.add_argument(f"--{k}")
    a.add_argument("--notes", default="")
    sub.add_parser("analyze")
    sub.add_parser("count")
    args = ap.parse_args(argv)
    if args.cmd == "add":
        row = add(args.project_id, url=args.url, platform=args.platform, views=args.views, avg_watch_pct=args.avg_watch,
                  likes=args.likes, comments=args.comments, saves=args.saves, shares=args.shares, notes=args.notes)
        print(json.dumps(row, indent=2))
        n = len(rows())
        if n % 5 == 0:
            print(f"\n{n} posts logged — time for the strategist to run `analyze` and update lessons.md")
    elif args.cmd == "analyze":
        print(json.dumps(analyze(), indent=2))
    else:
        print(len(rows()))


if __name__ == "__main__":
    main()
