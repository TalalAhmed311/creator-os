"""Render: rough cut → Remotion (reframe, zooms, collage layout, captions, graphics) → audio mix (music ducking, SFX,
two-pass loudnorm to −14 LUFS) → mux.

  python -m harnesses.studio.render <project> --preview     # fast half-res → work/preview.mp4 (always do this first)
  python -m harnesses.studio.render <project>               # full → out/final.mp4 + out/caption.txt
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path

from core.common import BRAIN, STUDIO, Project, ffmpeg, get_logger, load_json, save_json, validate
from harnesses.studio import REMOTION
from harnesses.studio.collage import build_layout_props
from harnesses.studio.rough_cut import rough_cut

log = get_logger("render")
DEFAULT_BRAND = {"primary": "#5B5BF7", "accent": "#FFD23F", "text": "#FFFFFF", "shadow": "#000000", "handle": ""}


def brand() -> dict:
    p = BRAIN / "brand.json"
    return {**DEFAULT_BRAND, **(load_json(p) if p.exists() else {})}


def _crop_samples(crop: dict | None, t0: float, t1: float) -> list[dict]:
    if not crop or not crop.get("points"):
        return []
    pts = crop["points"]
    inside = [p for p in pts if t0 - 0.4 <= p["t"] <= t1 + 0.4]
    if not inside:  # segment shorter than the sample spacing: nearest point
        near = min(pts, key=lambda p: abs(p["t"] - t0))
        inside = [near]
    return [{"t": p["t"], "cx": p["cx"], "cy": p["cy"]} for p in inside]


def build_props(project: Project, edl: dict, tl: dict) -> dict:
    crop_p = project.work / "crop_path.json"
    crop = load_json(crop_p) if crop_p.exists() else None
    segs = []
    for s in tl["segments"]:
        broll = s.get("overlay_broll")
        segs.append({
            "start": s["out_start"], "end": s["out_end"], "srcIn": s["in"],
            "reframe": s.get("reframe") or "face_track", "zoom": s.get("zoom"),
            "crop": _crop_samples(crop, s["in"], s["out"]) if s.get("reframe", "face_track") == "face_track" else [],
            "broll": {"file": broll["file"], "in": broll.get("in", 0), "mode": broll.get("mode", "full")} if broll else None,
        })
    cap = edl["captions"]
    return {
        "video": "work/rough.mp4", "fps": tl["fps"], "width": tl["width"], "height": tl["height"],
        "duration": tl["duration"], "videoW": tl["rough_w"], "videoH": tl["rough_h"], "segments": segs,
        "captions": {"enabled": cap.get("enabled", True), "style": cap["style"], "size": cap.get("size", 1.0),
                     "maxWords": cap.get("max_words", 3),
                     "words": [{k: w[k] for k in ("text", "start", "end", "highlight") if k in w} for w in cap["words"]]},
        "graphics": edl["graphics"],
        "layout": build_layout_props(project, edl.get("layout")),
        "brand": brand(),
    }


def remotion(args: list[str], log_name: str) -> None:
    npx = shutil.which("npx") or "npx"
    res = subprocess.run([npx, "remotion", *args], cwd=REMOTION, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"remotion {log_name} failed:\n{(res.stderr or res.stdout)[-3000:]}")


def remotion_render(project: Project, props: dict, out: Path, preview: bool) -> None:
    props_p = project.work / ("props_preview.json" if preview else "props.json")
    save_json(props_p, props)
    args = ["render", "src/index.ts", "Reel", str(out), f"--props={props_p}", f"--public-dir={project.root}",
            "--muted", "--codec=h264", "--log=error", "--timeout=120000", "--concurrency=50%"]
    args += ["--scale=0.5", "--crf=30"] if preview else ["--crf=17"]
    log.info("remotion: rendering " + ("preview (half-res)" if preview else "full-res") + "…")
    remotion(args, "render")


def _measure_loudness(wav: Path, target: float) -> dict:
    res = subprocess.run(["ffmpeg", "-hide_banner", "-nostdin", "-i", str(wav), "-af",
                          f"loudnorm=I={target}:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"],
                         capture_output=True, text=True, check=True)
    return json.loads(re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", res.stderr, re.S).group(0))


def mix_audio(project: Project, edl: dict, duration: float, out: Path) -> dict:
    """voice + (ducked) music + sfx → two-pass loudnorm. Returns the loudnorm measurement."""
    au = edl["audio"]
    inputs = ["-i", project.work / "rough_voice.wav"]
    fg, mix = ["[0:a]aformat=sample_rates=48000:channel_layouts=mono,asplit=2[voice][sc]"], ["[voice]"]
    k = 1
    if au.get("music"):
        m = au["music"]
        inputs += ["-stream_loop", "-1", "-i", STUDIO / m["file"]]
        chain = f"[{k}:a]aformat=sample_rates=48000:channel_layouts=mono,atrim=start={m.get('start_at', 0)},asetpts=PTS-STARTPTS," \
                f"atrim=0:{duration:.3f},volume={m.get('gain_db', -18)}dB,afade=t=out:st={max(0, duration - 1.5):.3f}:d=1.5"
        if m.get("duck", True):
            fg.append(chain + "[mraw]")
            fg.append("[mraw][sc]sidechaincompress=threshold=0.03:ratio=6:attack=15:release=350[music]")
        else:
            fg.append(chain + "[music]")
            fg.append("[sc]anullsink")
        mix.append("[music]")
        k += 1
    else:
        fg.append("[sc]anullsink")
    for s in au.get("sfx", []):
        inputs += ["-i", STUDIO / s["file"]]
        fg.append(f"[{k}:a]aformat=sample_rates=48000:channel_layouts=mono,volume={s.get('gain_db', -8)}dB,"
                  f"adelay={int(s['at'] * 1000)}:all=1[sfx{k}]")
        mix.append(f"[sfx{k}]")
        k += 1
    fg.append("".join(mix) + f"amix=inputs={len(mix)}:normalize=0:duration=first,atrim=0:{duration:.3f}[pre]")
    pre = project.work / "mix_pre.wav"
    ffmpeg([*inputs, "-filter_complex", ";".join(fg), "-map", "[pre]", "-c:a", "pcm_s24le", pre], log)
    target = au.get("loudness_lufs", -14)
    m = _measure_loudness(pre, target)
    ln = (f"loudnorm=I={target}:TP=-1.5:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
          f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
    ffmpeg(["-i", pre, "-af", f"{ln},aresample=48000", "-ac", "2", "-c:a", "pcm_s16le", out], log)
    return m


def write_caption(project: Project) -> None:
    plan = project.plan()
    cap = project.out / "caption.txt"
    if plan:
        tags = " ".join(h if h.startswith("#") else f"#{h}" for h in plan.get("hashtags", []))
        cap.write_text(plan.get("caption_draft", "").strip() + ("\n\n" + tags if tags else "") + "\n")
    elif not cap.exists():
        cap.write_text("(no plan.json — the showrunner writes the caption)\n")


def render(project: Project, preview: bool = False) -> Path:
    edl = load_json(project.root / "edl.json")
    validate(edl, "edl")
    tl = rough_cut(project)
    props = build_props(project, edl, tl)
    silent = project.work / ("preview_silent.mp4" if preview else "final_silent.mp4")
    remotion_render(project, props, silent, preview)
    mix = project.work / "mix.wav"
    m = mix_audio(project, edl, tl["duration"], mix)
    final = project.work / "preview.mp4" if preview else project.out / "final.mp4"
    final.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg(["-i", silent, "-i", mix, "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-shortest", "-movflags", "+faststart", final], log)
    if not preview:
        write_caption(project)
    log.info(f"→ {final.relative_to(project.root)} ({tl['duration']:.1f}s; pre-norm loudness {m['input_i']} LUFS)")
    return final


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("--preview", action="store_true")
    a = ap.parse_args(argv)
    render(Project(a.project), a.preview)


if __name__ == "__main__":
    main()
