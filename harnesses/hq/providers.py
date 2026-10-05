"""Where the owner's post metrics come from — one provider per platform, chosen in studio.json:

    "metrics": {"instagram": "auto", "x": "auto", "linkedin": "manual"}

  instagram-graph  Instagram Graph API (Business/Creator account + a Meta app): views, reach, likes, comments, shares,
                   saves. Needs IG_ACCESS_TOKEN and IG_USER_ID in the environment (never in a committed file).
  ytdlp            the post's public counters via yt-dlp (no login): likes/comments everywhere, views where the platform
                   exposes them (not Instagram reels). Video posts only on X.
  manual           nothing automatic: the post goes on the pending list (data/hq/pending-metrics.md) and the owner or an
                   agent adds numbers from the app / an analytics export (`./studio hq metrics add|import`).
  auto             instagram: instagram-graph if its env vars are set, else ytdlp · x: ytdlp · everything else: manual

Every provider returns {metric: value} plus (source, quality); a provider that can't read a post raises ProviderError.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request

from core.common import STUDIO, load_json

GRAPH = "https://graph.facebook.com/{version}/{path}"
GRAPH_METRICS = "views,reach,likes,comments,shares,saved,total_interactions"


class ProviderError(RuntimeError):
    pass


def configured(platform: str) -> str:
    cfg = load_json(STUDIO / "studio.json") if (STUDIO / "studio.json").exists() else {}
    choice = (cfg.get("metrics") or {}).get(platform, "auto")
    if choice != "auto":
        return choice
    if platform == "instagram":
        return "instagram-graph" if os.environ.get("IG_ACCESS_TOKEN") and os.environ.get("IG_USER_ID") else "ytdlp"
    return "ytdlp" if platform == "x" else "manual"


def fetch(platform: str, url: str, provider: str | None = None) -> tuple[dict, str, str]:
    """(metrics, source, quality) for one post, or ProviderError."""
    name = provider or configured(platform)
    if name == "manual":
        raise ProviderError("manual provider: add the numbers with ./studio hq metrics add")
    if name == "ytdlp":
        return _ytdlp(url), "yt-dlp", "verified"
    if name == "instagram-graph":
        return _instagram_graph(url), "instagram-graph", "verified"
    raise ProviderError(f"unknown metrics provider '{name}'")


def _ytdlp(url: str) -> dict:
    from core import refs

    try:
        meta = refs.probe(url)
    except (RuntimeError, SystemExit) as e:
        raise ProviderError(f"yt-dlp couldn't read the post: {str(e).splitlines()[0][:160]}") from e
    m = {"views": meta.get("view_count"), "likes": meta.get("like_count"), "comments": meta.get("comment_count"),
         "reposts": meta.get("repost_count")}
    m = {k: v for k, v in m.items() if v is not None}
    if not m:
        raise ProviderError("yt-dlp returned no public counters for this post")
    return m


def _graph_get(path: str, params: dict) -> dict:
    token = os.environ.get("IG_ACCESS_TOKEN")
    if not token:
        raise ProviderError("IG_ACCESS_TOKEN is not set")
    q = urllib.parse.urlencode({**params, "access_token": token})
    url = GRAPH.format(version=os.environ.get("IG_GRAPH_VERSION", "v23.0"), path=path) + "?" + q
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")[:300]
        raise ProviderError(f"Graph API {e.code}: {body}") from e
    except urllib.error.URLError as e:
        raise ProviderError(f"Graph API unreachable: {e.reason}") from e


def _shortcode(url: str) -> str:
    parts = [p for p in urllib.parse.urlparse(url).path.split("/") if p]
    return parts[1] if len(parts) >= 2 and parts[0] in ("p", "reel", "reels", "tv") else ""


def _media_id(url: str) -> str:
    """Find the media id for a permalink among the account's media (pages through up to 500 posts)."""
    user = os.environ.get("IG_USER_ID")
    if not user:
        raise ProviderError("IG_USER_ID is not set")
    code, after = _shortcode(url), None
    for _ in range(20):
        params = {"fields": "id,permalink", "limit": 25, **({"after": after} if after else {})}
        page = _graph_get(f"{user}/media", params)
        for m in page.get("data", []):
            if code and code == _shortcode(m.get("permalink", "")):
                return m["id"]
        after = page.get("paging", {}).get("cursors", {}).get("after")
        if not after or not page.get("paging", {}).get("next"):
            break
    raise ProviderError(f"post {url} not found among the account's media")


def _instagram_graph(url: str) -> dict:
    data = _graph_get(f"{_media_id(url)}/insights", {"metric": GRAPH_METRICS}).get("data", [])
    vals = {d["name"]: (d.get("values") or [{}])[0].get("value", d.get("total_value", {}).get("value")) for d in data}
    m = {"views": vals.get("views"), "reach": vals.get("reach"), "likes": vals.get("likes"), "comments": vals.get("comments"),
         "shares": vals.get("shares"), "saves": vals.get("saved")}
    return {k: v for k, v in m.items() if v is not None}
