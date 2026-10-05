"""One entry point for the whole studio:  ./studio <command> …

  ./studio web                            open the Web Studio (browser editor) at http://127.0.0.1:4545
  ./studio doctor                         dependencies + which backends are active
  ./studio new <pillar> <slug>            new project (+ working memory, memory load)
  ./studio edit <video|project> [--audio mic.wav] [--pillar P]   prepare: ingest → … → draft edl.json
  ./studio preview <project>              half-res render + QC pack
  ./studio final <project>                final render, cover, caption, fcpxml
  ./studio collage <project> --from-plan  images around the speaker on the beats the script marked (--list-themes)
  ./studio carousel <project>             render carousel.json → slides + PDF
  ./studio verify <project>               check carousel links
  ./studio validate <project|file>        schema-check plan/edl/carousel
  ./studio transcribe <project> [--backend …]
  ./studio convert <file…> [--to mp3|wav|m4a] [--out DIR]   extract audio from a video (default mp3)
  ./studio yt <url> [--audio-only] [--out DIR]              download a video (or its audio) into videos/
  ./studio ig <url> [--audio-only] [--browser chrome]       download an Instagram reel/post into inspiration/
  ./studio ref <add|analyze|list|rm> …                     reference library: download + transcript + hook/pacing analysis
  ./studio clip <file|url> --from 1:23 --to 1:45 [--audio mp3|wav|m4a|none] [--keep-video] [--delete-original]
  ./studio memory <subcommand> …          create/append/load/consolidate/remember/search/open
  ./studio log <account> <url> [--draft N] [--views N …]   log a published post (= ./studio hq log)
  ./studio projects                       list projects and their state

creator-os harnesses:
  ./studio db <init|stats|sql|export|restore>          the shared database (data/creator-os.db)
  ./studio research <creators|post|outliers|insight|report|import-seed> …   creator DB + content analysis
  ./studio write <context|new|list|show|status|validate> …                  platform drafts (draft-only)
  ./studio hq <accounts|log|metrics|sync|due|review|schedule> …             own content, daily metrics, learning loop
"""
from __future__ import annotations

import sys

from core.common import PROJECTS

ROUTES = {
    "doctor": ("core.deps", []),
    "web": ("harnesses.studio.webstudio.server", []),
    "new": ("harnesses.studio.new_project", []),
    "edit": ("harnesses.studio.edit", ["prepare"]),
    "prepare": ("harnesses.studio.edit", ["prepare"]),
    "preview": ("harnesses.studio.edit", ["preview"]),
    "final": ("harnesses.studio.edit", ["final"]),
    "collage": ("harnesses.studio.collage", []),
    "carousel": ("harnesses.studio.carousel.render", []),
    "verify": ("harnesses.studio.verify_links", []),
    "validate": ("harnesses.studio.validate", []),
    "transcribe": ("harnesses.studio.transcribe", []),
    "convert": ("core.media.convert", []),
    "yt": ("core.fetch.download", []),
    "download": ("core.fetch.download", []),
    "ig": ("core.fetch.instagram", []),
    "clip": ("core.media.clip", []),
    "ref": ("core.refs", []),
    "memory": ("core.memory", []),
    "log": ("harnesses.hq.cli", ["log"]),
    "cover": ("harnesses.studio.make_cover", []),
    "export": ("harnesses.studio.export_nle", []),
    "qc": ("harnesses.studio.qc_frames", []),
    "db": ("core.db.cli", []),
    "research": ("harnesses.research.cli", []),
    "write": ("harnesses.writer.cli", []),
    "hq": ("harnesses.hq.cli", []),
}


def list_projects() -> None:
    rows = sorted(p for p in PROJECTS.iterdir() if p.is_dir()) if PROJECTS.exists() else []
    if not rows:
        print("(no projects yet)")
    for p in rows:
        has = [n for n in ("plan.json", "edl.json", "carousel.json") if (p / n).exists()]
        outs = [n for n in ("final.mp4", "cover.png", "project.fcpxml", "carousel.pdf") if (p / "out" / n).exists()]
        print(f"{p.name:<44} {', '.join(has) or '—':<30} out: {', '.join(outs) or '—'}")


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(__doc__)
        return 0
    cmd, rest = argv[0], argv[1:]
    if cmd == "projects":
        list_projects()
        return 0
    if cmd not in ROUTES:
        print(f"unknown command '{cmd}'\n{__doc__}")
        return 2
    import importlib

    module, prefix = ROUTES[cmd]
    res = importlib.import_module(module).main(prefix + rest)
    return res if isinstance(res, int) else 0


if __name__ == "__main__":
    raise SystemExit(main())
