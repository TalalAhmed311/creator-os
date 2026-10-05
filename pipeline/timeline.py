"""Source-time ↔ output-time mapping shared by auto_edl, rough_cut, render and export_nle.

Segment boundaries are snapped to the output frame grid so video and audio cut at identical times.
"""
from __future__ import annotations


def snap(t: float, fps: float) -> float:
    return round(round(t * fps) / fps, 6)


def layout(segments: list[dict], fps: float) -> list[dict]:
    """Return segments with snapped in/out plus out_start/out_end on the output timeline."""
    res, cur = [], 0.0
    for s in segments:
        i, o = snap(s["in"], fps), snap(s["out"], fps)
        if o <= i:
            o = i + 1 / fps
        d = round(o - i, 6)
        res.append({**s, "in": i, "out": o, "dur": d, "out_start": round(cur, 6), "out_end": round(cur + d, 6)})
        cur += d
    return res


def total_duration(segments: list[dict], fps: float) -> float:
    lay = layout(segments, fps)
    return lay[-1]["out_end"] if lay else 0.0


def src_to_out(t: float, lay: list[dict], src: str = "cam") -> float | None:
    """Map a source time to output time; None if that moment was cut."""
    for s in lay:
        if s["src"] == src and s["in"] - 1e-6 <= t < s["out"] + 1e-6:
            return round(s["out_start"] + (t - s["in"]), 4)
    return None


def out_to_src(t: float, lay: list[dict]) -> tuple[str, float] | None:
    for s in lay:
        if s["out_start"] - 1e-6 <= t < s["out_end"] + 1e-6:
            return s["src"], s["in"] + (t - s["out_start"])
    return None


def map_words(words: list[dict], lay: list[dict], src: str = "cam") -> list[dict]:
    """Map transcript words (source time) to output-time caption words; drops words that were cut."""
    out = []
    for w in words:
        mid = (w["start"] + w["end"]) / 2
        for s in lay:
            if s["src"] == src and s["in"] - 1e-6 <= mid < s["out"] + 1e-6:
                st = max(w["start"], s["in"])
                en = min(w["end"], s["out"])
                out.append({"text": w["text"], "start": round(s["out_start"] + st - s["in"], 3),
                            "end": round(s["out_start"] + en - s["in"], 3), "src_start": w["start"],
                            **({"highlight": w["highlight"]} if "highlight" in w else {})})
                break
    return out


def beat_ranges(lay: list[dict]) -> dict[str, tuple[float, float]]:
    """Output-time range of each scripted beat (segments carry `beat`)."""
    r: dict[str, tuple[float, float]] = {}
    for s in lay:
        if s.get("beat"):
            a, b = r.get(s["beat"], (s["out_start"], s["out_end"]))
            r[s["beat"]] = (min(a, s["out_start"]), max(b, s["out_end"]))
    return r
