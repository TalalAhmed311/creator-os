"""Build a draft edl.json deterministically from transcript + fillers + silences (+ alignment/plan).
The editor agent then reviews and refines it (story selection, beat order, zoom emphasis).

  python -m harnesses.studio.auto_edl <project> [--preset bip-raw] [--force]
  python -m harnesses.studio.auto_edl <project> --refresh-captions   # after hand-editing segments

Rules applied (brain/retention-playbook.md): remove gaps > max_gap, filler words, stutters, false starts;
keep the last complete take of each scripted beat; zoom pattern per preset; captions always on.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

from core.common import ASSETS, Project, get_logger, load_json, read_glossary, save_json, validate
from harnesses.studio import DEFAULT_PRESET
from harnesses.studio.collage import layout_from_plan
from harnesses.studio.timeline import beat_ranges, layout, map_words, total_duration

log = get_logger("auto_edl")

PRESETS = {
    #                     max gap kept   pad in/out   zoom pattern
    "bip-raw":            {"max_gap": 0.20, "pad_in": 0.05, "pad_out": 0.08, "zoom": "punch"},
    "ai-explained":       {"max_gap": 0.28, "pad_in": 0.08, "pad_out": 0.12, "zoom": "push"},
    "talking-head-basic": {"max_gap": 0.30, "pad_in": 0.06, "pad_out": 0.10, "zoom": "alternate"},
}
OUTPUT = {"width": 1080, "height": 1920, "fps": 30}
NUM_RE = re.compile(r"\d|%|\$|×")


def _silence_trim(words: list[dict], silences: list[dict]) -> list[dict]:
    """Whisper sometimes stretches a word across the pause that follows it; trim to silence start."""
    out = []
    for w in words:
        w = dict(w)
        for s in silences:
            if w["start"] + 0.1 < s["start"] < w["end"]:
                w["end"] = round(s["start"] + 0.06, 3)
                break
            if s["start"] <= w["start"] < s["end"] - 0.05 and w["end"] > s["end"]:
                w["start"] = round(s["end"] - 0.03, 3)  # word start stretched back into silence
                break
        out.append(w)
    return out


def speech_words(project: Project) -> list[dict]:
    """Transcript words with timings corrected against detected silences (what's actually audible)."""
    tr = load_json(project.work / "transcript.json")
    sil_p = project.work / "silences.json"
    return _silence_trim(tr["words"], load_json(sil_p) if sil_p.exists() else [])


def _keep_ranges(words: list[dict], alignment: dict | None) -> list[tuple[str | None, int, int]]:
    """(beat_id, w0, w1) ranges to keep, in story order."""
    if alignment:
        ranges = []
        for b in alignment["beats"]:
            if b["chosen"] is not None:
                t = b["takes"][b["chosen"]]
                ranges.append((b["id"], t["w0"], t["w1"]))
        if ranges:
            return ranges
    return [(None, 0, len(words) - 1)] if words else []


def build_segments(words: list[dict], cut: set[int], ranges, preset: str, duration: float) -> list[dict]:
    p = PRESETS[preset]
    segs = []
    for beat, w0, w1 in ranges:
        group: list[int] = []

        def flush():
            if not group:
                return
            a, b = group[0], group[-1]
            lo = words[a - 1]["end"] if a > 0 else 0.0           # never include the previous (cut) word
            hi = words[b + 1]["start"] if b + 1 < len(words) else duration
            seg_in = max(lo, words[a]["start"] - p["pad_in"], 0.0)
            seg_out = min(hi, words[b]["end"] + p["pad_out"], duration)
            if seg_out - seg_in > 0.12:
                segs.append({"src": "cam", "in": round(seg_in, 3), "out": round(seg_out, 3), "beat": beat,
                             "reframe": "face_track", "zoom": None, "overlay_broll": None})
            group.clear()

        for i in range(w0, w1 + 1):
            if i in cut:
                flush()
                continue
            if group and (i != group[-1] + 1 or words[i]["start"] - words[group[-1]]["end"] > p["max_gap"]):
                flush()
            group.append(i)
        flush()
    # guarantee no overlaps (padding can collide when a tiny gap was cut)
    for a, b in zip(segs, segs[1:]):
        if b["in"] < a["out"] and b["in"] >= a["in"]:
            mid = round((a["out"] + b["in"]) / 2, 3)
            a["out"], b["in"] = mid, mid
    return [s for s in segs if s["out"] - s["in"] > 0.12]


def speech_segments(silences: list[dict], duration: float, preset: str) -> list[dict]:
    """No transcript: keep everything that isn't silence (jump-cut dead air)."""
    p = PRESETS[preset]
    segs, cur = [], 0.0
    for s in sorted(silences, key=lambda s: s["start"]):
        a, b = cur, s["start"]
        if b - a > 0.2:
            segs.append((max(0.0, a - p["pad_in"]), min(duration, b + p["pad_out"])))
        cur = max(cur, s["end"])
    if duration - cur > 0.2:
        segs.append((max(0.0, cur - p["pad_in"]), duration))
    out = []
    for a, b in segs:
        if out and a <= out[-1]["out"]:
            out[-1]["out"] = round(b, 3)
        else:
            out.append({"src": "cam", "in": round(a, 3), "out": round(b, 3), "beat": None,
                        "reframe": "face_track", "zoom": None, "overlay_broll": None})
    return out


def apply_zooms(segs: list[dict], words: list[dict], preset: str, emphasis: set[int]) -> None:
    mode = PRESETS[preset]["zoom"]
    for n, s in enumerate(segs):
        seg_words = [i for i, w in enumerate(words) if s["in"] <= (w["start"] + w["end"]) / 2 < s["out"]]
        key = any(i in emphasis for i in seg_words)
        if mode == "alternate":
            z = 1.15 if n % 2 else 1.0
            s["zoom"] = {"from": z, "to": z, "ease": "linear"}
        elif mode == "punch":
            if key:
                s["zoom"] = {"from": 1.18, "to": 1.2, "ease": "snap"}
            else:
                z = 1.08 if n % 2 else 1.0
                s["zoom"] = {"from": z, "to": z + 0.02, "ease": "linear"}
        else:  # push: slow continuous push-in, reset on each cut
            s["zoom"] = {"from": 1.0, "to": 1.06 if s["out"] - s["in"] > 2 else 1.03, "ease": "easeInOut"}
        # retention rule: something must change every ≤4 s — long static shots get a slow push-in
        z = s["zoom"]
        if s["out"] - s["in"] > 3.5 and abs(z["to"] - z["from"]) < 0.05:
            s["zoom"] = {"from": z["from"], "to": round(z["from"] + 0.07, 3), "ease": "easeInOut"}


def emphasis_words(words: list[dict]) -> set[int]:
    gl = {g.lower() for g in read_glossary()}
    em = set()
    for i, w in enumerate(words):
        core = re.sub(r"[^\w%$×.-]", "", w["text"]).lower().strip(".")
        if NUM_RE.search(w["text"]) or core in gl:
            em.add(i)
    return em


def build_graphics(plan: dict | None, lay: list[dict], preset: str, total: float) -> list[dict]:
    g = []
    if not plan:
        return g
    beats = beat_ranges(lay)
    if plan.get("chosen_hook") is not None and plan["hooks"]:
        hook = plan["hooks"][plan["chosen_hook"]]
        end = beats.get("hook", (0, 2.8))[1]
        g.append({"type": "hook_text", "text": hook["on_screen"], "start": 0.0, "end": round(min(max(end, 1.5), 3.5, total), 3), "position": "top"})
    if plan.get("day_n") and preset == "bip-raw":
        g.append({"type": "badge", "text": f"Day {plan['day_n']}", "start": 0.0, "end": round(min(2.5, total), 3), "position": "top_left"})
    ser = plan.get("series") or {}
    if ser.get("name") and ser.get("episode"):
        g.append({"type": "series_tag", "text": f"{ser['name']} #{ser['episode']}", "start": 0.0, "end": round(min(3.0, total), 3), "position": "top_right"})
    for b in plan["beats"]:
        if b["id"] not in beats:
            continue
        a, e = beats[b["id"]]
        if b.get("graphic"):
            spec = re.sub(r"^\s*diagram:\s*", "", b["graphic"])
            g.append({"type": "diagram", "spec": spec, "start": round(a, 3), "end": round(e, 3), "position": "middle"})
        if b.get("on_screen") and b["id"] != "hook":
            g.append({"type": "callout", "text": b["on_screen"], "start": round(a, 3), "end": round(min(a + 2.5, e), 3), "position": "top"})
    return g


def pick_audio(preset: str) -> dict:
    music = None
    for folder in (ASSETS / "music" / preset, ASSETS / "music"):
        tracks = sorted(p for p in folder.glob("*") if p.suffix.lower() in {".mp3", ".wav", ".m4a", ".aac", ".flac"}) if folder.exists() else []
        if tracks:
            music = {"file": str(tracks[0].relative_to(ASSETS.parent)), "gain_db": -18, "duck": True}
            break
    return {"music": music, "sfx": [], "loudness_lufs": -14}


def add_sfx(edl: dict, lay: list[dict]) -> None:
    """bip-raw: a whoosh on each snap punch-in, if the owner has put one in assets/sfx/."""
    if edl.get("edit_preset") != "bip-raw":
        return
    whoosh = next(iter(sorted((ASSETS / "sfx").glob("whoosh*"))), None)
    if not whoosh:
        return
    for s in lay:
        if s.get("zoom") and s["zoom"].get("ease") == "snap" and s["out_start"] > 0.5:
            edl["audio"]["sfx"].append({"file": str(whoosh.relative_to(ASSETS.parent)), "at": round(s["out_start"], 3), "gain_db": -10})


def build(project: Project, preset: str | None = None) -> dict:
    media = project.media()
    plan = project.plan()
    tr = load_json(project.work / "transcript.json")
    fillers = load_json(project.work / "fillers.json") if (project.work / "fillers.json").exists() else []
    silences = load_json(project.work / "silences.json") if (project.work / "silences.json").exists() else []
    alignment = load_json(project.work / "alignment.json") if (project.work / "alignment.json").exists() and plan else None
    preset = preset or (plan or {}).get("edit_preset") or "talking-head-basic"
    fps = OUTPUT["fps"]

    words = _silence_trim(tr["words"], silences)
    em = emphasis_words(words)
    cut = {f["i"] for f in fillers}
    if words:
        segs = build_segments(words, cut, _keep_ranges(words, alignment), preset, media["cam"]["duration"])
    else:
        segs = speech_segments(silences, media["cam"]["duration"], preset)
    if not segs:
        raise SystemExit("nothing left to keep — the voice track is all silence?")
    apply_zooms(segs, words, preset, em)
    lay = layout(segs, fps)
    total = lay[-1]["out_end"]
    kept = [dict(w, highlight=i in em) for i, w in enumerate(words) if i not in cut]

    sync_p = project.work / "sync.json"
    edl = {
        "project_id": project.id,
        "edit_preset": preset,
        "output": dict(OUTPUT),
        "sources": {"cam": media["cam"]["path"],
                    "mic": media["mic"]["path"] if media.get("mic") else None,
                    "mic_offset_ms": load_json(sync_p)["mic_offset_ms"] if sync_p.exists() else None},
        "segments": segs,
        "captions": {"style": preset, "enabled": bool(words), "size": 1.0, "max_words": 3,
                     "words": map_words(kept, lay)},
        "graphics": build_graphics(plan, lay, preset, total),
        "audio": pick_audio(preset),
        "notes": [],
    }
    add_sfx(edl, lay)
    if plan:  # beats the script marked for a collage
        lay_c, notes = layout_from_plan(project, plan, beat_ranges(lay), edl["captions"]["words"])
        if lay_c:
            edl["layout"] = lay_c
        edl["notes"] += notes
    target = (plan or {}).get("target_length_s")
    src_dur = media["cam"]["duration"]
    edl["notes"].append(f"auto: {src_dur:.1f}s source → {total:.1f}s cut, {len(segs)} segments, {len(cut)} words removed")
    if target and total > target * 1.25:
        edl["notes"].append(f"TOO LONG: {total:.0f}s vs target {target}s — editor must drop weaker lines")
    elif not target and total > 45:
        edl["notes"].append(f"TOO LONG for a reel ({total:.0f}s) — editor should pick the strongest 20–45s story")
    if not words:
        edl["notes"].append(f"NO TRANSCRIPT (backend: {tr.get('backend', '?')}) — cut by silence only, captions off. "
                            "Plug in a transcriber (python -m core.deps) or drop raw/transcript.srt, then re-run.")
    if not any(g["type"] == "hook_text" for g in edl["graphics"]):
        edl["notes"].append("NO HOOK TEXT — editor should add a hook_text graphic (≤7 words) at 0s")
    if alignment:
        missing = [b["id"] for b in alignment["beats"] if b["chosen"] is None]
        if missing:
            edl["notes"].append(f"beats not found in footage: {', '.join(missing)}")
    validate(edl, "edl")
    return edl


def refresh_captions(project: Project) -> dict:
    """Recompute captions from the (hand-edited) segments; keeps highlight choices by source time."""
    edl = load_json(project.root / "edl.json")
    words_all = speech_words(project)
    fillers = {f["i"] for f in (load_json(project.work / "fillers.json") if (project.work / "fillers.json").exists() else [])}
    # keep hand edits (text fixes + highlight toggles) keyed by the word's source time
    prev = {round(w["src_start"], 3): w for w in edl["captions"]["words"] if "src_start" in w}
    em = emphasis_words(words_all)
    words = []
    for i, w in enumerate(words_all):
        if i in fillers:
            continue
        old = prev.get(round(w["start"], 3))
        words.append(dict(w, text=old["text"] if old else w["text"],
                          highlight=old.get("highlight", False) if old else i in em))
    lay = layout(edl["segments"], edl["output"]["fps"])
    edl["captions"]["words"] = map_words(words, lay)
    total = total_duration(edl["segments"], edl["output"]["fps"])
    for g in edl["graphics"]:
        g["end"] = round(min(g["end"], total), 3)
    validate(edl, "edl")
    save_json(project.root / "edl.json", edl)
    log.info(f"captions refreshed: {len(edl['captions']['words'])} words over {total:.1f}s")
    return edl


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("--preset", choices=list(PRESETS))
    ap.add_argument("--force", action="store_true", help="overwrite an existing edl.json")
    ap.add_argument("--refresh-captions", action="store_true")
    a = ap.parse_args(argv)
    proj = Project(a.project)
    if a.refresh_captions:
        refresh_captions(proj)
        return
    out = proj.root / "edl.json"
    if out.exists() and not a.force:
        raise SystemExit("edl.json exists (maybe hand-edited). Use --force to rebuild or --refresh-captions.")
    edl = build(proj, a.preset)
    save_json(out, edl)
    for n in edl["notes"]:
        log.info(n)


if __name__ == "__main__":
    main()
