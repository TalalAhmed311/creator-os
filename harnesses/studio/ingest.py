"""Probe media and bring it into <project>/raw/ (copy-on-write clone; originals never touched).

  python -m harnesses.studio.ingest <project> [--video clip.mp4] [--audio mic.wav] [--broll a.mov ...]

Writes work/media.json: {cam: {...}, mic: {...}|null, broll: [...]}
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
from fractions import Fraction
from pathlib import Path

from core.common import Project, ffprobe, get_logger, load_json, save_json

log = get_logger("ingest")
VIDEO_EXT = {".mp4", ".mov", ".m4v", ".mkv", ".webm", ".avi"}
AUDIO_EXT = {".wav", ".m4a", ".mp3", ".aac", ".flac", ".aif", ".aiff", ".caf"}


def _clone(src: Path, dest: Path) -> None:
    """APFS clone (instant, no extra space) with plain-copy fallback. Never overwrites a different file."""
    if dest.exists():
        if dest.stat().st_size == src.stat().st_size:
            return
        raise SystemExit(f"{dest} already exists with different content — refusing to overwrite raw/")
    dest.parent.mkdir(parents=True, exist_ok=True)
    if subprocess.run(["cp", "-c", str(src), str(dest)], capture_output=True).returncode != 0:
        shutil.copy2(src, dest)
    dest.chmod(0o444)  # raw/ is read-only by convention


def describe(path: Path) -> dict:
    info = ffprobe(path)
    v = next((s for s in info["streams"] if s["codec_type"] == "video" and s.get("disposition", {}).get("attached_pic") != 1), None)
    a = next((s for s in info["streams"] if s["codec_type"] == "audio"), None)
    d = {"file": path.name, "duration": float(info["format"].get("duration", 0)), "has_audio": a is not None}
    if v:
        w, h = int(v["width"]), int(v["height"])
        rot = 0
        for sd in v.get("side_data_list", []):
            if "rotation" in sd:
                rot = int(float(sd["rotation"]))
        rot = int(v.get("tags", {}).get("rotate", rot))
        if abs(rot) % 180 == 90:
            w, h = h, w
        fr = v.get("avg_frame_rate") or v.get("r_frame_rate") or "30/1"
        fps = float(Fraction(fr)) if fr != "0/0" else 30.0
        d.update({"width": w, "height": h, "fps": round(fps, 3), "vcodec": v.get("codec_name"),
                  "orientation": "portrait" if h > w else "landscape" if w > h else "square"})
    if a:
        d.update({"sample_rate": int(a.get("sample_rate", 48000)), "channels": int(a.get("channels", 1)), "acodec": a.get("codec_name")})
    return d


def ingest(project: Project, video: Path | None, audio: Path | None, broll: list[Path]) -> dict:
    project.ensure()
    if video:
        _clone(video, project.raw / f"cam{video.suffix.lower()}")
    if audio:
        _clone(audio, project.raw / f"mic{audio.suffix.lower()}")
    for b in broll:
        _clone(b, project.raw / "broll" / b.name)

    cams = sorted(p for p in project.raw.glob("cam.*") if p.suffix.lower() in VIDEO_EXT)
    if not cams:
        # footage dropped straight into raw/: first video = cam, first audio-only file = mic
        vids = sorted(p for p in project.raw.iterdir() if p.suffix.lower() in VIDEO_EXT)
        if not vids:
            raise SystemExit(f"no video in {project.raw} — pass --video")
        cams = vids[:1]
    cam = cams[0]
    mics = sorted(p for p in project.raw.glob("mic.*") if p.suffix.lower() in AUDIO_EXT | VIDEO_EXT)
    if not mics:
        mics = sorted(p for p in project.raw.iterdir() if p.suffix.lower() in AUDIO_EXT)
    media = {"cam": {**describe(cam), "path": str(cam.relative_to(project.root))},
             "mic": ({**describe(mics[0]), "path": str(mics[0].relative_to(project.root))} if mics else None),
             "broll": [{**describe(b), "path": str(b.relative_to(project.root))}
                       for b in sorted((project.raw / "broll").glob("*")) if b.suffix.lower() in VIDEO_EXT]}
    if "width" not in media["cam"]:
        raise SystemExit(f"{cam.name} has no video stream")
    mp = project.work / "media.json"
    if not mp.exists() or load_json(mp) != media:  # unchanged → keep mtime so downstream caches stay valid
        save_json(mp, media)
    c = media["cam"]
    log.info(f"cam {c['file']}: {c['width']}x{c['height']} {c['fps']}fps {c['duration']:.1f}s "
             f"audio={'yes' if c['has_audio'] else 'no'}; mic={'yes (' + media['mic']['file'] + ')' if media['mic'] else 'no'}")
    return media


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("--video", type=Path)
    ap.add_argument("--audio", type=Path)
    ap.add_argument("--broll", type=Path, nargs="*", default=[])
    a = ap.parse_args(argv)
    ingest(Project(a.project), a.video, a.audio, a.broll)


if __name__ == "__main__":
    main()
