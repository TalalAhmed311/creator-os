"""Sample frames for agents to look at: every N seconds plus scene changes (ffmpeg scene score).

  python -m harnesses.studio.extract_frames <project> [--every 2] [--src cam|<path>]

Writes work/frames/*.jpg and work/frames.json [{"t", "file", "reason"}]
"""
from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path

from core.common import Project, ffmpeg, get_logger, is_fresh, load_json, save_json

log = get_logger("extract_frames")


def scene_changes(video: Path, threshold: float = 0.3) -> list[float]:
    """Cut points via ffmpeg's scene-change score (no extra Python deps)."""
    res = subprocess.run(["ffmpeg", "-hide_banner", "-nostdin", "-i", str(video), "-an", "-vf",
                          f"scale=320:-2,select='gt(scene,{threshold})',showinfo", "-f", "null", "-"],
                         capture_output=True, text=True)
    return [float(m.group(1)) for m in re.finditer(r"pts_time:([\d.]+)", res.stderr)]


def grab(video: Path, t: float, dest: Path, width: int = 480) -> None:
    ffmpeg(["-ss", f"{t:.3f}", "-i", video, "-frames:v", "1", "-vf", f"scale={width}:-2", "-q:v", "4", dest])


def extract(project: Project, every: float = 2.0, video: Path | None = None, force: bool = False) -> list[dict]:
    media = project.media()
    video = video or project.root / media["cam"]["path"]
    fdir = project.work / "frames"
    out = project.work / "frames.json"
    if not force and is_fresh(out, [video]):
        return load_json(out)
    fdir.mkdir(parents=True, exist_ok=True)
    for old in fdir.glob("*.jpg"):
        old.unlink()
    # regular samples in one pass
    ffmpeg(["-i", video, "-vf", f"fps=1/{every},scale=480:-2", "-q:v", "4", fdir / "t%05d.jpg"], log)
    frames = [{"t": round(i * every, 2), "file": str(p.relative_to(project.root)), "reason": "interval"}
              for i, p in enumerate(sorted(fdir.glob("t*.jpg")))]
    for t in scene_changes(video):
        dest = fdir / f"scene_{t:08.2f}.jpg"
        grab(video, t + 0.05, dest)
        frames.append({"t": round(t, 2), "file": str(dest.relative_to(project.root)), "reason": "scene_change"})
    frames.sort(key=lambda f: f["t"])
    save_json(out, frames)
    log.info(f"{len(frames)} frames → {fdir.relative_to(project.root)}")
    return frames


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("--every", type=float, default=2.0)
    ap.add_argument("--video", type=Path)
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args(argv)
    extract(Project(a.project), a.every, a.video, a.force)


if __name__ == "__main__":
    main()
