"""Quality-control pack for the critic: sampled frames, a contact sheet and automatic checklist measurements.

  python -m pipeline.qc_frames <project> [--video work/preview.mp4]

Writes work/qc/*.jpg, work/qc/contact.jpg and work/qc.json. Automatic checks (brain/../AI_STUDIO_PLAN §10):
  hook_text_first_frame, max_gap_s, filler_words_left, max_static_s, length vs target, loudness, true peak.
The critic still has to LOOK at the frames for framing, caption accuracy and brand fit.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

from pipeline.common import Project, ffmpeg, get_logger, load_json, save_json
from pipeline.detect_fillers import FILLERS, norm
from pipeline.timeline import layout

log = get_logger("qc_frames")


def loudness(video: Path) -> dict:
    res = subprocess.run(["ffmpeg", "-hide_banner", "-nostdin", "-i", str(video), "-af", "ebur128=peak=true", "-f", "null", "-"],
                         capture_output=True, text=True)
    s = res.stderr[res.stderr.rfind("Summary:"):]
    i = re.search(r"I:\s+(-?[\d.]+) LUFS", s)
    p = re.search(r"Peak:\s+(-?[\d.]+) dBFS", s)
    return {"integrated_lufs": float(i.group(1)) if i else None, "true_peak_dbfs": float(p.group(1)) if p else None}


def visual_changes(edl: dict) -> list[float]:
    """Output times where something changes visually: cuts, zoom changes, graphics in/out, caption chunks."""
    fps = edl["output"]["fps"]
    lay = layout(edl["segments"], fps)
    ev = [0.0]
    for s in lay:
        ev.append(s["out_start"])
        z = s.get("zoom") or {}
        if z and abs(z.get("to", 1) - z.get("from", 1)) >= 0.04:
            ev += [s["out_start"] + (s["out_end"] - s["out_start"]) / 2]
    for g in edl["graphics"]:
        ev += [g["start"], g["end"]]
    for s in edl["audio"].get("sfx", []):
        ev.append(s["at"])
    ev.append(lay[-1]["out_end"] if lay else 0)
    return sorted(set(round(e, 2) for e in ev))


def qc(project: Project, video: Path | None = None, every: float = 1.5) -> dict:
    edl = load_json(project.root / "edl.json")
    video = video or (project.out / "final.mp4" if (project.out / "final.mp4").exists() else project.work / "preview.mp4")
    qdir = project.work / "qc"
    qdir.mkdir(parents=True, exist_ok=True)
    for old in qdir.glob("*.jpg"):
        old.unlink()
    ffmpeg(["-i", video, "-vf", f"fps=1/{every},scale=360:-2", "-q:v", "5", qdir / "f%03d.jpg"], log)
    ffmpeg(["-i", video, "-frames:v", "1", "-vf", "scale=540:-2", qdir / "first.jpg"], log)
    n = len(list(qdir.glob("f*.jpg")))
    cols = 6
    ffmpeg(["-i", qdir / "f%03d.jpg", "-vf", f"tile={cols}x{max(1, -(-n // cols))}:padding=6:color=white", "-frames:v", "1", qdir / "contact.jpg"], log)

    fps = edl["output"]["fps"]
    lay = layout(edl["segments"], fps)
    dur = lay[-1]["out_end"]
    words = edl["captions"]["words"]
    gaps = [round(b["start"] - a["end"], 3) for a, b in zip(words, words[1:])]
    changes = visual_changes(edl)
    static = max((b - a for a, b in zip(changes, changes[1:])), default=dur)
    plan = project.plan()
    target = (plan or {}).get("target_length_s")
    loud = loudness(video)
    hook = [g for g in edl["graphics"] if g["type"] == "hook_text" and g["start"] <= 0.001]
    first_word = words[0]["start"] if words else None
    checks = {
        "hook_text_first_frame": bool(hook),
        "hook_text_words": len(hook[0]["text"].split()) if hook else None,
        "speech_starts_at_s": first_word,
        "max_gap_s": max(gaps, default=0),
        "gaps_over_300ms": sum(g > 0.305 for g in gaps),  # 5 ms tolerance for frame snapping
        "filler_words_left": [w["text"] for w in words if norm(w["text"]) in FILLERS],
        "max_static_s": round(static, 2),
        "length_s": round(dur, 2),
        "target_length_s": target,
        **loud,
    }
    fails = []
    if not checks["hook_text_first_frame"]:
        fails.append("no on-screen hook text at 0s")
    if checks["hook_text_words"] and checks["hook_text_words"] > 7:
        fails.append(f"hook text is {checks['hook_text_words']} words (max 7)")
    if first_word is not None and first_word > 0.5:
        fails.append(f"speech starts late ({first_word:.2f}s)")
    if checks["gaps_over_300ms"]:
        fails.append(f"{checks['gaps_over_300ms']} caption gaps > 300ms (max {checks['max_gap_s']}s)")
    if checks["filler_words_left"]:
        fails.append(f"fillers left: {checks['filler_words_left']}")
    if static > 4.0:
        fails.append(f"{static:.1f}s with no visual change (max 4s)")
    if target and not (0.75 * target <= dur <= 1.25 * target):
        fails.append(f"length {dur:.1f}s vs target {target}s")
    if loud["integrated_lufs"] is not None and abs(loud["integrated_lufs"] + 14) > 1.5:
        fails.append(f"loudness {loud['integrated_lufs']} LUFS (want −14 ±1.5)")
    if loud["true_peak_dbfs"] is not None and loud["true_peak_dbfs"] > -0.5:
        fails.append(f"true peak {loud['true_peak_dbfs']} dBFS (clipping risk)")
    res = {"video": str(video.relative_to(project.root)), "frames": sorted(str(p.relative_to(project.root)) for p in qdir.glob("*.jpg")),
           "contact_sheet": str((qdir / "contact.jpg").relative_to(project.root)), "checks": checks, "auto_fails": fails}
    save_json(project.work / "qc.json", res)
    log.info(("auto checks FAILED: " + "; ".join(fails)) if fails else "auto checks passed — critic to review frames")
    return res


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("--video", type=Path)
    a = ap.parse_args(argv)
    p = Project(a.project)
    print(json.dumps(qc(p, p.root / a.video if a.video else None)["checks"], indent=2))


if __name__ == "__main__":
    main()
