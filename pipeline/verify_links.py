"""Verify carousel resources: link is live, GitHub repos are maintained. Writes results into carousel.json.

  python -m pipeline.verify_links <project>            # checks every slide with a url
  python -m pipeline.verify_links --url https://...    # one-off check

Per slide adds "verified": {"ok", "status", "final_url", "checked", "repo": {stars, pushed_at, archived, months_since_push}}
A repo counts as maintained if it was pushed to within the last 12 months and is not archived.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import urllib.error
import urllib.request

from pipeline.common import Project, get_logger, load_json, save_json, today

log = get_logger("verify_links")
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; personal-studio link checker)"}


def check_url(url: str, timeout: float = 12) -> dict:
    for method in ("HEAD", "GET"):
        try:
            req = urllib.request.Request(url, headers=UA, method=method)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return {"ok": 200 <= r.status < 400, "status": r.status, "final_url": r.geturl()}
        except urllib.error.HTTPError as e:
            if method == "HEAD" and e.code in (403, 405, 429, 501):
                continue  # many sites reject HEAD; retry with GET
            return {"ok": False, "status": e.code, "final_url": url}
        except Exception as e:  # noqa: BLE001
            if method == "GET":
                return {"ok": False, "status": None, "final_url": url, "error": type(e).__name__}
    return {"ok": False, "status": None, "final_url": url}


def check_repo(url: str) -> dict | None:
    m = re.match(r"https?://github\.com/([^/]+)/([^/#?]+)", url)
    if not m:
        return None
    api = f"https://api.github.com/repos/{m.group(1)}/{m.group(2).removesuffix('.git')}"
    try:
        with urllib.request.urlopen(urllib.request.Request(api, headers={**UA, "Accept": "application/vnd.github+json"}), timeout=12) as r:
            d = json.load(r)
    except Exception as e:  # noqa: BLE001
        return {"error": type(e).__name__}
    pushed = dt.datetime.fromisoformat(d["pushed_at"].replace("Z", "+00:00"))
    months = (dt.datetime.now(dt.timezone.utc) - pushed).days / 30.4
    return {"stars": d.get("stargazers_count"), "pushed_at": d["pushed_at"][:10], "archived": d.get("archived", False),
            "months_since_push": round(months, 1), "maintained": months <= 12 and not d.get("archived", False),
            "description": d.get("description")}


def verify(url: str) -> dict:
    res = {**check_url(url), "checked": today()}
    repo = check_repo(url)
    if repo:
        res["repo"] = repo
    return res


def verify_project(project: Project) -> list[dict]:
    path = project.root / "carousel.json"
    car = load_json(path)
    report = []
    for s in car["slides"]:
        if s.get("url"):
            v = verify(s["url"])
            s["verified"] = v
            flag = "✓" if v["ok"] and v.get("repo", {}).get("maintained", True) else "✗"
            extra = f" · repo pushed {v['repo'].get('pushed_at')} ★{v['repo'].get('stars')}" if v.get("repo") and "error" not in v["repo"] else ""
            log.info(f"{flag} {s.get('name', s['url'])}: HTTP {v['status']}{extra}")
            report.append({"name": s.get("name"), **v})
    save_json(path, car)
    return report


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("project", nargs="?")
    ap.add_argument("--url")
    a = ap.parse_args(argv)
    if a.url:
        print(json.dumps(verify(a.url), indent=2))
    elif a.project:
        verify_project(Project(a.project))
    else:
        ap.error("give a project or --url")


if __name__ == "__main__":
    main()
