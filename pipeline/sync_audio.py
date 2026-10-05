"""Find the offset between the separate mic and the camera audio by cross-correlation.

  python -m pipeline.sync_audio <project>

Writes work/sync.json: {"mic_offset_ms": float, "confidence": float}
Convention: an event at camera time t happens at mic time t + mic_offset_ms/1000.
(Positive = the mic started recording before the camera.)
"""
from __future__ import annotations

import argparse
import subprocess

import numpy as np
from scipy import signal

from pipeline.common import Project, get_logger, is_fresh, load_json, save_json

log = get_logger("sync_audio")
SR = 8000


def load_mono(path, seconds: float | None = None, sr: int = SR) -> np.ndarray:
    cmd = ["ffmpeg", "-nostdin", "-loglevel", "error", "-i", str(path)]
    if seconds:
        cmd += ["-t", str(seconds)]
    cmd += ["-vn", "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32).copy()


def _envelope(x: np.ndarray) -> np.ndarray:
    """Band-limited, energy-normalised signal: robust to different mics/gain."""
    b, a = signal.butter(4, [200 / (SR / 2), 3000 / (SR / 2)], btype="band")
    y = signal.filtfilt(b, a, x)
    return y / (np.std(y) + 1e-9)


def find_offset(cam: np.ndarray, mic: np.ndarray, sr: int = SR, max_offset_s: float = 60.0) -> tuple[float, float]:
    """Returns (offset_seconds, confidence). offset = mic_time - cam_time for the same event."""
    c, m = _envelope(cam), _envelope(mic)
    corr = signal.correlate(m, c, mode="full", method="fft")
    lags = signal.correlation_lags(len(m), len(c), mode="full")
    window = np.abs(lags) <= max_offset_s * sr
    corr, lags = corr[window], lags[window]
    i = int(np.argmax(np.abs(corr)))
    peak = abs(corr[i])
    # confidence: peak vs the next-best peak outside ±50ms
    mask = np.abs(lags - lags[i]) > 0.05 * sr
    second = np.max(np.abs(corr[mask])) if mask.any() else 0.0
    conf = float(1 - second / peak) if peak else 0.0
    return lags[i] / sr, conf


def sync(project: Project, force: bool = False) -> dict | None:
    media = project.media()
    if not media.get("mic"):
        log.info("no separate mic — skipping")
        return None
    if not media["cam"]["has_audio"]:
        raise SystemExit("camera file has no audio track; can't auto-sync. Set mic_offset_ms by hand in work/sync.json")
    out = project.work / "sync.json"
    cam_p, mic_p = project.root / media["cam"]["path"], project.root / media["mic"]["path"]
    if not force and is_fresh(out, [cam_p, mic_p]):
        return load_json(out)
    span = min(180.0, media["cam"]["duration"] + 60)
    cam = load_mono(cam_p, span)
    mic = load_mono(mic_p, span + 60)
    off, conf = find_offset(cam, mic)
    res = {"mic_offset_ms": round(off * 1000, 1), "confidence": round(conf, 3)}
    if conf < 0.15:
        log.warning(f"low sync confidence ({conf:.2f}) — check the result by ear (clap at the start helps)")
    save_json(out, res)
    log.info(f"mic offset {res['mic_offset_ms']} ms (confidence {conf:.2f})")
    return res


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args(argv)
    sync(Project(a.project), a.force)


if __name__ == "__main__":
    main()
