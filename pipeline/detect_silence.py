"""Find dead air in the voice track with ffmpeg silencedetect.

  python -m pipeline.detect_silence <project> [--noise -35] [--min 0.25]

Writes work/silences.json: [{"start": s, "end": e}] in camera time.
"""
from __future__ import annotations

import argparse
import re
import subprocess

from pipeline.common import Project, get_logger, is_fresh, load_json, save_json

log = get_logger("detect_silence")


def detect(project: Project, noise_db: float = -35, min_s: float = 0.25, force: bool = False) -> list[dict]:
    voice = project.work / "voice.wav"
    out = project.work / "silences.json"
    if not force and is_fresh(out, [voice]):
        return load_json(out)
    res = subprocess.run(["ffmpeg", "-hide_banner", "-nostdin", "-i", str(voice), "-af",
                          f"silencedetect=noise={noise_db}dB:d={min_s}", "-f", "null", "-"],
                         capture_output=True, text=True, check=True)
    silences, start = [], None
    for ln in res.stderr.splitlines():
        if m := re.search(r"silence_start: ([\d.]+)", ln):
            start = float(m.group(1))
        elif (m := re.search(r"silence_end: ([\d.]+)", ln)) and start is not None:
            silences.append({"start": round(start, 3), "end": round(float(m.group(1)), 3)})
            start = None
    if start is not None:
        dur = project.media()["cam"]["duration"]
        silences.append({"start": round(start, 3), "end": round(dur, 3)})
    save_json(out, silences)
    total = sum(s["end"] - s["start"] for s in silences)
    log.info(f"{len(silences)} silences, {total:.1f}s of dead air")
    return silences


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("--noise", type=float, default=-35)
    ap.add_argument("--min", type=float, default=0.25)
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args(argv)
    detect(Project(a.project), a.noise, a.min, a.force)


if __name__ == "__main__":
    main()
