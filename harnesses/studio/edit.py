"""Edit Bay orchestrator: runs the deterministic steps of /edit, cached and resumable.

  python -m harnesses.studio.edit prepare <project|video> [--audio mic.wav] [--pillar build-in-public] [--slug name]
      ingest → sync → clean → transcribe → silences → fillers → align → frames → face track → draft edl.json
  python -m harnesses.studio.edit preview <project>     # validate → rough cut → half-res render → qc pack
  python -m harnesses.studio.edit final <project>       # full render → cover → fcpxml → qc pack

Each step records progress in memory/working/<project_id>.md so /resume knows where to pick up.
Agents review and edit edl.json between `prepare` and `preview` (and between preview loops).
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from core import memory
from core.common import PROJECTS, Project, get_logger, save_json
from harnesses.studio import DEFAULT_PRESET
from harnesses.studio.ingest import VIDEO_EXT

log = get_logger("edit")


def _step(project: Project, name: str, fn, *args, **kw):
    t0 = time.time()
    res = fn(*args, **kw)
    log.info(f"✓ {name} ({time.time() - t0:.1f}s)")
    try:
        memory.progress(project.id, name)
    except FileNotFoundError:
        pass
    return res


def resolve_project(target: str, pillar: str | None, slug: str | None, audio: Path | None) -> tuple[Project, Path | None]:
    p = Path(target).expanduser()
    if p.is_file() and p.suffix.lower() in VIDEO_EXT:
        pillar = pillar or "build-in-public"
        proj = Project.create(pillar, slug or p.stem)
        return proj, p.resolve()
    proj = Project(target)
    if not proj.root.exists():
        raise SystemExit(f"no project or video at {target}")
    return proj.ensure(), None


def prepare(target: str, audio: Path | None = None, pillar: str | None = None, slug: str | None = None,
            transcriber: str | None = None, video_in: Path | None = None, broll: list[Path] | None = None) -> dict:
    from harnesses.studio import (align_script, auto_edl, clean_audio, detect_fillers, detect_silence, extract_frames,
                                  face_track, ingest, sync_audio, transcribe)

    proj, video = resolve_project(target, pillar, slug, audio)
    video = video or (video_in.resolve() if video_in else None)
    plan = proj.plan()
    pillar = (plan or {}).get("pillar") or pillar or "build-in-public"
    memory.create_working(proj.id, pillar, "edit", goal=f"Edit {proj.id} into a finished 9:16 reel.")
    for s in ["ingest", "sync audio", "clean audio", "transcribe", "silences", "fillers", "align script",
              "frames", "face track", "draft edl", "preview", "critic", "final"]:
        memory.progress(proj.id, s, done=False)

    _step(proj, "ingest", ingest.ingest, proj, video, audio.resolve() if audio else None, [b.resolve() for b in broll or []])
    _step(proj, "sync audio", sync_audio.sync, proj)
    _step(proj, "clean audio", clean_audio.clean, proj)
    _step(proj, "transcribe", transcribe.transcribe, proj, transcriber)
    _step(proj, "silences", detect_silence.detect, proj)
    _step(proj, "fillers", detect_fillers.detect, proj)
    _step(proj, "align script", align_script.run_align, proj)
    _step(proj, "frames", extract_frames.extract, proj)
    _step(proj, "face track", face_track.track, proj)
    edl_p = proj.root / "edl.json"
    if edl_p.exists():
        log.info("edl.json already exists — keeping it (use auto_edl --force to rebuild)")
        memory.progress(proj.id, "draft edl")
    else:
        edl = _step(proj, "draft edl", auto_edl.build, proj, (plan or {}).get("edit_preset") or DEFAULT_PRESET.get(pillar))
        save_json(edl_p, edl)
    summary = {"project": proj.id, "path": str(proj.root), "edl": str(edl_p)}
    print(json.dumps(summary, indent=2))
    return summary


def preview(target: str) -> dict:
    from harnesses.studio import qc_frames, render
    from harnesses.studio.validate import validate_file

    proj = Project(target)
    errs = validate_file(proj.root / "edl.json")
    if errs:
        raise SystemExit("edl.json invalid:\n" + "\n".join(errs))
    _step(proj, "preview", render.render, proj, preview=True)
    res = qc_frames.qc(proj, proj.work / "preview.mp4")
    print(json.dumps({"preview": str(proj.work / "preview.mp4"), "auto_fails": res["auto_fails"],
                      "contact_sheet": str(proj.root / res["contact_sheet"])}, indent=2))
    return res


def final(target: str) -> dict:
    from harnesses.studio import export_nle, make_cover, qc_frames, render

    proj = Project(target)
    _step(proj, "final", render.render, proj, preview=False)
    make_cover.make_cover(proj)
    export_nle.export(proj)
    res = qc_frames.qc(proj, proj.out / "final.mp4")
    out = {k: str(proj.out / k) for k in ("final.mp4", "cover.png", "caption.txt", "project.fcpxml")}
    print(json.dumps({**out, "auto_fails": res["auto_fails"], "checks": res["checks"]}, indent=2))
    return res


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("target", help="project id/path, or a video file to start a new project")
    p.add_argument("--video", type=Path, help="camera footage for an existing project")
    p.add_argument("--audio", type=Path, help="separate mic recording")
    p.add_argument("--broll", type=Path, nargs="*", default=[], help="B-roll / screen recordings (→ raw/broll/)")
    p.add_argument("--pillar", choices=["build-in-public", "ai-explained", "resources"])
    p.add_argument("--slug")
    p.add_argument("--transcriber", help="auto | mlx-whisper | whisper-cpp | sidecar | none (default: studio.json)")
    for name in ("preview", "final"):
        sub.add_parser(name).add_argument("target")
    a = ap.parse_args(argv)
    if a.cmd == "prepare":
        prepare(a.target, a.audio, a.pillar, a.slug, a.transcriber, a.video, a.broll)
    elif a.cmd == "preview":
        preview(a.target)
    else:
        final(a.target)


if __name__ == "__main__":
    main()
