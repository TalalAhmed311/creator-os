"""Download an Instagram reel/post (or just its audio) for inspiration.

    ./studio ig <url>                      → inspiration/<title> [<id>].mp4
    ./studio ig <url> --audio-only         → inspiration/<title> [<id>].mp3
    ./studio ig <url> --browser chrome     use your logged-in browser cookies (if Instagram asks for login)

Inspiration only: study it, don't repost it. To transcribe and break it down use `./studio ref add <url>`.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from pipeline.common import STUDIO, get_logger
from pipeline.download import fetch

log = get_logger("instagram")
DEFAULT_OUT = STUDIO / "inspiration"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="studio ig", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("url")
    ap.add_argument("--audio-only", action="store_true", help="save only the audio as mp3")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT, help="folder (default: inspiration/)")
    ap.add_argument("--browser", help="read cookies from this browser (chrome, safari, firefox…) when login is required")
    a = ap.parse_args(argv)
    extra = ["--cookies-from-browser", a.browser] if a.browser else []
    print(fetch(a.url, a.out, a.audio_only, extra))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
