"""Download a video (or just its audio) from YouTube or any site yt-dlp supports.

    ./studio yt <url>                      → videos/<title> [<id>].mp4
    ./studio yt <url> --audio-only         → videos/<title> [<id>].mp3
    ./studio yt <url> --out projects/<id>/raw/broll

To study a video (transcript, hooks, pacing) use `./studio ref add <url>` instead: it keeps it in references/<id>/.
Only download what you have the right to use (your own uploads, Creative Commons, or with permission).
Music is never saved into assets/music/ (studio rule): use tracks you own or royalty-free files.
Uses yt-dlp: the Python package if installed (requirements/download.txt), else the `yt-dlp` command.
"""
from __future__ import annotations

import argparse
import importlib.util
import shutil
import sys
from pathlib import Path

from pipeline.common import STUDIO, get_logger, run

log = get_logger("download")
DEFAULT_OUT = STUDIO / "videos"
MUSIC_DIR = (STUDIO / "assets" / "music").resolve()


def ytdlp_cmd() -> list[str]:
    if importlib.util.find_spec("yt_dlp"):
        return [sys.executable, "-m", "yt_dlp"]
    exe = shutil.which("yt-dlp")
    if exe:
        return [exe]
    raise SystemExit("yt-dlp not found: scripts/setup.sh --with download (or: brew install yt-dlp)")


VIDEO_FORMAT = "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/bv*+ba/b"


def js_args() -> list[str]:
    """YouTube needs a JS runtime; yt-dlp only enables deno by default, so fall back to Node (installed for Remotion)."""
    return ["--js-runtimes", "node"] if not shutil.which("deno") and shutil.which("node") else []


def is_url(s: str) -> bool:
    return s.startswith(("http://", "https://", "www.", "youtu.be/", "youtube.com/"))


def fetch(url: str, out_dir: Path = DEFAULT_OUT, audio_only: bool = False, extra: list[str] | None = None) -> Path:
    out_dir = out_dir.resolve()
    if out_dir == MUSIC_DIR or MUSIC_DIR in out_dir.parents:
        raise SystemExit("not downloading into assets/music/: the studio never downloads music")
    out_dir.mkdir(parents=True, exist_ok=True)
    fmt = (["-x", "--audio-format", "mp3", "--audio-quality", "0"] if audio_only
           else ["-f", VIDEO_FORMAT, "--merge-output-format", "mp4"])
    res = run([*ytdlp_cmd(), *js_args(), "--no-update", "--no-playlist", "--restrict-filenames", "--no-progress", "--retries", "5",
               "-o", str(out_dir / "%(title).80s [%(id)s].%(ext)s"), *fmt,
               *(extra or []), "--print", "after_move:filepath", url], log)
    path = Path(res.stdout.strip().splitlines()[-1])
    if not path.exists():
        raise RuntimeError(f"yt-dlp finished but {path} is missing")
    log.info(f"downloaded → {path}")
    return path


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="studio yt", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("url")
    ap.add_argument("--audio-only", action="store_true", help="save only the audio as mp3")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT, help="folder (default: videos/)")
    a = ap.parse_args(argv)
    print(fetch(a.url, a.out, a.audio_only))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
