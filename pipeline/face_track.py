"""Track the speaker's face and produce a smoothed crop centre for 9:16 reframing.

  python -m pipeline.face_track <project> [--sample-fps 5]

Writes work/crop_path.json:
  {"fps": 5, "src_w", "src_h", "points": [{"t", "cx", "cy", "face_h"}]}   (cx/cy/face_h normalised 0–1)
Detector comes from the FaceDetector interface (pipeline/providers/face.py): mediapipe → opencv → center.
"""
from __future__ import annotations

import argparse

import numpy as np

from pipeline.common import Project, get_logger, is_fresh, load_json, save_json
from pipeline.providers.face import get_face_detector

log = get_logger("face_track")


def smooth(values: np.ndarray, fps: float, deadzone: float = 0.03, alpha: float = 0.15) -> np.ndarray:
    """Median filter (kills detector spikes) → dead-zone → exponential smoothing (no jitter)."""
    from scipy.signal import medfilt
    k = max(3, int(fps) | 1)
    v = medfilt(values, kernel_size=k) if len(values) >= k else values.copy()
    out = np.empty_like(v)
    cur = v[0]
    for i, x in enumerate(v):
        if abs(x - cur) > deadzone:
            cur = cur + alpha * (x - cur)
        out[i] = cur
    return out


def track(project: Project, sample_fps: float = 5.0, force: bool = False, backend: str | None = None) -> dict:
    media = project.media()
    video = project.root / media["cam"]["path"]
    out = project.work / "crop_path.json"
    det = get_face_detector(backend)
    if not force and is_fresh(out, [video]) and load_json(out).get("detector") == det.name:
        return load_json(out)
    if det.name == "center":  # nothing to track (or OpenCV not installed): static centre path
        data = {"fps": sample_fps, "detector": "center", "coverage": 0.0, "src_w": media["cam"]["width"],
                "src_h": media["cam"]["height"], "points": [{"t": 0.0, "cx": 0.5, "cy": 0.42, "face_h": 0.0}]}
        save_json(out, data)
        log.info("face detector: center (no tracking)")
        return data
    import cv2

    cap = cv2.VideoCapture(str(video))
    src_fps = cap.get(cv2.CAP_PROP_FPS) or media["cam"]["fps"]
    step = max(1, round(src_fps / sample_fps))
    ts, raw, idx = [], [], 0
    while True:
        ok = cap.grab()
        if not ok:
            break
        if idx % step == 0:
            ok, frame = cap.retrieve()
            if ok:
                h, w = frame.shape[:2]
                scale = 640 / max(h, w)
                small = cv2.resize(frame, (int(w * scale), int(h * scale)))
                ts.append(idx / src_fps)
                raw.append(det.detect(cv2.cvtColor(small, cv2.COLOR_BGR2RGB)))
        idx += 1
    cap.release()
    found = [r for r in raw if r]
    coverage = len(found) / max(1, len(raw))
    if not found:
        log.warning("no face found — reframing will centre-crop")
        pts = [{"t": round(t, 3), "cx": 0.5, "cy": 0.4, "face_h": 0.0} for t in ts]
    else:
        # fill gaps with the last known position (or the first detection)
        last = found[0]
        filled = []
        for r in raw:
            last = r or last
            filled.append(last)
        arr = np.array(filled, dtype=float)
        cx, cy = smooth(arr[:, 0], sample_fps), smooth(arr[:, 1], sample_fps, deadzone=0.04)
        fh = np.convolve(arr[:, 2], np.ones(5) / 5, mode="same") if len(arr) >= 5 else arr[:, 2]
        pts = [{"t": round(t, 3), "cx": round(float(a), 4), "cy": round(float(b), 4), "face_h": round(float(c), 4)}
               for t, a, b, c in zip(ts, cx, cy, fh)]
    data = {"fps": sample_fps, "detector": det.name, "coverage": round(coverage, 3),
            "src_w": media["cam"]["width"], "src_h": media["cam"]["height"], "points": pts}
    save_json(out, data)
    log.info(f"{det.name}: face found in {coverage:.0%} of {len(raw)} samples")
    return data


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("--sample-fps", type=float, default=5.0)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--backend", help="auto | mediapipe | opencv | center")
    a = ap.parse_args(argv)
    track(Project(a.project), a.sample_fps, a.force, a.backend)


if __name__ == "__main__":
    main()
