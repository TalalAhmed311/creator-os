"""Pick the strongest frame from the first part of the cut (sharp, face big and centred) + hook text → out/cover.png

  python -m harnesses.studio.make_cover <project> [--text "custom hook"] [--at 3.2]
"""
from __future__ import annotations

import argparse

from core.common import Project, ffmpeg, get_logger, load_json, save_json
from harnesses.studio.render import brand, remotion
from harnesses.studio.timeline import out_to_src

log = get_logger("make_cover")


def score_frames(video, times: list[float]) -> list[tuple[float, float]]:
    """Score candidate frames: sharpness + face size + how centred the face is (face detector interface)."""
    try:
        import cv2
    except ImportError:  # no OpenCV: fall back to a frame ~1/3 into the opening
        return [(times[len(times) // 3], 0.0)] if times else []
    from core.providers.face import get_face_detector

    det = get_face_detector()
    cap = cv2.VideoCapture(str(video))
    scores = []
    for t in times:
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
        ok, frame = cap.read()
        if not ok:
            continue
        small = cv2.resize(frame, (360, int(360 * frame.shape[0] / frame.shape[1])))
        sharp = cv2.Laplacian(cv2.cvtColor(small, cv2.COLOR_BGR2GRAY), cv2.CV_64F).var()
        face = det.detect(cv2.cvtColor(small, cv2.COLOR_BGR2RGB))
        fscore = (face[2] * 4 + 1 - abs(face[0] - 0.5) * 2) if face else 0.0
        scores.append((t, min(sharp, 400) / 400 + fscore))
    cap.release()
    return sorted(scores, key=lambda s: s[1], reverse=True)


def make_cover(project: Project, text: str | None = None, at: float | None = None) -> str:
    edl = load_json(project.root / "edl.json")
    tl = load_json(project.work / "timeline.json")
    rough = project.work / "rough.mp4"
    if at is None:
        span = min(tl["duration"] * 0.5, 15)
        times = [0.3 + i * 0.5 for i in range(int(span / 0.5))]
        best = score_frames(rough, times)
        at = best[0][0] if best else 0.5
    frame = project.work / "cover_frame.jpg"
    # 9:16 crop of the rough frame, centred on the tracked face when we have one
    cx = 0.5
    crop_p = project.work / "crop_path.json"
    src = out_to_src(at, tl["segments"])
    if crop_p.exists() and src:
        pts = load_json(crop_p)["points"]
        if pts:
            cx = min(pts, key=lambda p: abs(p["t"] - src[1]))["cx"]
    x = f"max(0\\,min(iw-ih*9/16\\,iw*{cx:.4f}-ih*9/32))"
    ffmpeg(["-ss", f"{at:.3f}", "-i", rough, "-frames:v", "1", "-vf", f"crop=ih*9/16:ih:{x}:0,scale=1080:1920", "-q:v", "2", frame], log)
    plan = project.plan() or {}
    hook = text
    if not hook:
        g = next((g for g in edl["graphics"] if g["type"] == "hook_text"), None)
        hook = g["text"] if g else (plan["hooks"][plan["chosen_hook"]]["on_screen"] if plan.get("hooks") and plan.get("chosen_hook") is not None else "")
    badge = next((g["text"] for g in edl["graphics"] if g["type"] in ("badge", "series_tag")), None)
    props = {"image": "work/cover_frame.jpg", "hook": hook, "badge": badge, "brand": brand(), "style": edl["captions"]["style"]}
    props_p = save_json(project.work / "cover_props.json", props)
    out = project.out / "cover.png"
    remotion(["still", "src/index.ts", "Cover", str(out), f"--props={props_p}", f"--public-dir={project.root}", "--log=error"], "still")
    log.info(f"cover from {at:.1f}s → {out.relative_to(project.root)}")
    return str(out)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("--text")
    ap.add_argument("--at", type=float)
    a = ap.parse_args(argv)
    make_cover(Project(a.project), a.text, a.at)


if __name__ == "__main__":
    main()
