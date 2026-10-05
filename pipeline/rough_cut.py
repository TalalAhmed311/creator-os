"""Apply edl.json segments with ffmpeg: one pass, frame-accurate, CFR.

  python -m pipeline.rough_cut <project> [--force]

Writes work/rough.mp4 (video scaled to cover 9:16, voice muxed), work/rough_voice.wav, work/timeline.json.
Segments are snapped to the output frame grid (pipeline/timeline.py) so audio and video cut identically.
"""
from __future__ import annotations

import argparse

from pipeline.common import Project, ffmpeg, get_logger, is_fresh, load_json, save_json, validate, video_encoder_args
from pipeline.timeline import layout

log = get_logger("rough_cut")


def _scale_filter(src_w: int, src_h: int, W: int, H: int) -> tuple[str, int, int]:
    """Scale so the frame covers WxH (the render step crops/reframes). Keeps even dimensions."""
    s = max(W / src_w, H / src_h)
    w, h = int(round(src_w * s / 2) * 2), int(round(src_h * s / 2) * 2)
    return f"scale={w}:{h}:flags=lanczos", w, h


def rough_cut(project: Project, force: bool = False) -> dict:
    edl_p = project.root / "edl.json"
    edl = load_json(edl_p)
    validate(edl, "edl")
    media = project.media()
    cam = project.root / edl["sources"]["cam"]
    voice = project.work / "voice.wav"
    out_v, out_a, tl_p = project.work / "rough.mp4", project.work / "rough_voice.wav", project.work / "timeline.json"
    if not force and is_fresh(out_v, [edl_p, cam, voice]) and is_fresh(tl_p, [edl_p]):
        return load_json(tl_p)
    if any(s["src"] != "cam" for s in edl["segments"]):
        raise SystemExit("rough_cut only cuts from 'cam'; use overlay_broll for other footage")

    W, H, fps = edl["output"]["width"], edl["output"]["height"], edl["output"]["fps"]
    lay = layout(edl["segments"], fps)
    eps = 0.5 / fps
    # video: CFR first, then keep frames inside [in, out) of any segment
    sel = "+".join(f"between(t,{s['in'] - eps:.6f},{s['out'] - eps:.6f})" for s in lay)
    scale, rw, rh = _scale_filter(media["cam"]["width"], media["cam"]["height"], W, H)
    vf = f"[0:v]setpts=PTS-STARTPTS,fps={fps},select='{sel}',setpts=N/({fps}*TB),{scale},setsar=1[v]"
    # audio: sample-accurate trims (aselect works on whole packets, so use atrim + concat)
    n = len(lay)
    af = f"[1:a]asplit={n}" + "".join(f"[a{i}]" for i in range(n)) + ";"
    af += ";".join(f"[a{i}]atrim=start={s['in']:.6f}:end={s['out']:.6f},asetpts=PTS-STARTPTS[t{i}]" for i, s in enumerate(lay))
    af += ";" + "".join(f"[t{i}]" for i in range(n)) + f"concat=n={n}:v=0:a=1[a]"
    graph = project.work / "rough_filter.txt"
    graph.write_text(vf + ";" + af)
    total = lay[-1]["out_end"]
    ffmpeg(["-i", cam, "-i", voice, "-filter_complex_script", graph, "-map", "[v]", "-map", "[a]",
            *video_encoder_args("high"), "-g", str(int(fps)), "-r", str(fps), "-c:a", "aac", "-b:a", "192k",
            "-t", f"{total:.4f}", "-movflags", "+faststart", out_v], log)
    ffmpeg(["-i", voice, "-filter_complex_script", _audio_only(graph, af), "-map", "[a]", "-c:a", "pcm_s16le", out_a], log)
    tl = {"fps": fps, "width": W, "height": H, "rough_w": rw, "rough_h": rh, "duration": total, "segments": lay}
    save_json(tl_p, tl)
    log.info(f"rough cut: {len(lay)} segments, {total:.1f}s ({rw}x{rh})")
    return tl


def _audio_only(graph_path, af: str):
    p = graph_path.with_name("rough_filter_audio.txt")
    p.write_text(af.replace("[1:a]", "[0:a]"))
    return p


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args(argv)
    rough_cut(Project(a.project), a.force)


if __name__ == "__main__":
    main()
