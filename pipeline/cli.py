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
  ./studio log <add|analyze|count> …      content log / learning loop
  ./studio projects                       list projects and their state
"""
from __future__ import annotations

import sys

from pipeline.common import PROJECTS

ROUTES = {
    "doctor": ("pipeline.deps", []),
    "web": ("webstudio.server", []),
    "new": ("pipeline.new_project", []),
    "edit": ("pipeline.edit", ["prepare"]),
    "prepare": ("pipeline.edit", ["prepare"]),
    "preview": ("pipeline.edit", ["preview"]),
    "final": ("pipeline.edit", ["final"]),
    "collage": ("pipeline.collage", []),
    "carousel": ("carousel.render", []),
    "verify": ("pipeline.verify_links", []),
    "validate": ("pipeline.validate", []),
    "transcribe": ("pipeline.transcribe", []),
    "convert": ("pipeline.convert", []),
    "yt": ("pipeline.download", []),
    "download": ("pipeline.download", []),
    "ig": ("pipeline.instagram", []),
    "clip": ("pipeline.clip", []),
    "ref": ("pipeline.refs", []),
    "memory": ("pipeline.memory", []),
    "log": ("pipeline.content_log", []),
    "cover": ("pipeline.make_cover", []),
    "export": ("pipeline.export_nle", []),
    "qc": ("pipeline.qc_frames", []),
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
