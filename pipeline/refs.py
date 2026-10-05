"""Reference library: videos you study for hooks, pacing and visuals. Nothing is deleted unless you say so.

    ./studio ref add <url>            download → references/<id>/source.mp4 + info.json (kept)
    ./studio ref analyze <id|file>    transcript + cuts + hook frames + contact sheet + metrics → analysis.md
    ./studio ref list                 what's in the library
    ./studio ref rm <id> --yes        delete one reference (only when the owner asks; without --yes it only shows what would go)

Layout: references/<id>/{source.mp4, info.json, audio.wav, transcript.json, transcript.txt, cuts.json,
hook.jpg, contact.jpg, metrics.json, analysis.md, clips/}
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path

import numpy as np

from pipeline import download
from pipeline.common import STUDIO, ffmpeg, ffprobe, get_logger, run, save_json

log = get_logger("refs")
REFS = STUDIO / "references"
INFO_KEYS = ("id", "title", "channel", "uploader", "webpage_url", "duration", "view_count", "like_count",
             "comment_count", "upload_date", "description")


# ---------------------------------------------------------------- add

def add(url: str, root: Path = REFS) -> Path:
    """Download into references/<id>/ and keep it. Re-running skips files already there."""
    meta = json.loads(run([*download.ytdlp_cmd(), *download.js_args(), "--no-update", "--no-playlist",
                           "--skip-download", "--dump-json", url], log).stdout.splitlines()[-1])
    ref = root / re.sub(r"[^\w-]", "_", meta["id"])
    ref.mkdir(parents=True, exist_ok=True)
    save_json(ref / "info.json", {k: meta.get(k) for k in INFO_KEYS} | {"description": (meta.get("description") or "")[:2000]})
    src = finished_source(ref)
    if src:
        log.info(f"already downloaded: {src}")
        return ref
    run([*download.ytdlp_cmd(), *download.js_args(), "--no-update", "--no-playlist", "--no-progress", "--retries", "10",
         "-f", download.VIDEO_FORMAT, "--merge-output-format", "mp4", "-o", str(ref / "source.%(ext)s"), url], log)
    log.info(f"saved → {ref}/source.mp4 ({meta.get('title')})")
    return ref


def resolve(ref: str) -> Path:
    """<id> in references/, a reference folder, or a video file (analysed in place, outputs next to it)."""
    p = Path(ref)
    if (REFS / ref).is_dir():
        return REFS / ref
    if p.is_dir():
        return p
    if p.is_file():
        return p
    raise SystemExit(f"no reference '{ref}' (see ./studio ref list)")


VIDEO_EXT = (".mp4", ".mkv", ".webm", ".mov")


def finished_source(ref: Path) -> Path | None:
    """The merged download (source.mp4 …), ignoring metadata, partial files and per-format fragments (source.f399.mp4)."""
    return next((s for s in sorted(ref.glob("source.*")) if s.suffix in VIDEO_EXT and s.name.count(".") == 1), None)


def source_of(ref: Path) -> Path:
    if ref.is_file():
        return ref
    src = finished_source(ref)
    if not src:
        raise SystemExit(f"{ref} has no source video yet (./studio ref add <url>)")
    return src


# ---------------------------------------------------------------- analyze

def scene_cuts(src: Path, threshold: float = 0.3) -> list[float]:
    res = subprocess.run(["ffmpeg", "-hide_banner", "-nostdin", "-i", str(src), "-an", "-vf",
                          f"scale=320:-2,select='gt(scene,{threshold})',showinfo", "-f", "null", "-"],
                         capture_output=True, text=True)
    return [round(float(m), 3) for m in re.findall(r"pts_time:([\d.]+)", res.stderr)]


def frame_at(src: Path, t: float, width: int = 360) -> np.ndarray:
    import cv2

    raw = subprocess.run(["ffmpeg", "-hide_banner", "-nostdin", "-loglevel", "error", "-ss", f"{max(0, t):.3f}", "-i", str(src),
                          "-frames:v", "1", "-vf", f"scale={width}:-2", "-f", "image2pipe", "-vcodec", "png", "-"],
                         capture_output=True).stdout
    img = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)
    return img if img is not None else np.zeros((640, width, 3), np.uint8)


def sheet(src: Path, times: list[float], out: Path, cols: int, width: int = 360) -> Path:
    import cv2

    frames = []
    for t in times:
        f = frame_at(src, t, width)
        label = f"{int(t // 60)}:{t % 60:05.2f}"
        cv2.rectangle(f, (0, 0), (len(label) * 15 + 16, 36), (0, 0, 0), -1)
        cv2.putText(f, label, (8, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2)
        frames.append(f)
    h = max(f.shape[0] for f in frames)
    frames = [cv2.copyMakeBorder(f, 0, h - f.shape[0], 0, 0, cv2.BORDER_CONSTANT) for f in frames]
    while len(frames) % cols:
        frames.append(np.zeros_like(frames[0]))
    rows = [np.hstack(frames[i:i + cols]) for i in range(0, len(frames), cols)]
    cv2.imwrite(str(out), np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 85])
    return out


def loudness(src: Path) -> float | None:
    res = subprocess.run(["ffmpeg", "-hide_banner", "-nostdin", "-i", str(src), "-vn", "-af", "ebur128", "-f", "null", "-"],
                         capture_output=True, text=True)
    m = re.findall(r"I:\s+(-?[\d.]+) LUFS", res.stderr)
    return float(m[-1]) if m else None


def analyze(ref: Path, force: bool = False) -> Path:
    from pipeline.providers.transcription import get_transcriber

    src = source_of(ref)
    out = ref if ref.is_dir() else ref.parent / f"{ref.stem}_analysis"
    out.mkdir(parents=True, exist_ok=True)
    info = ffprobe(src)
    dur = float(info["format"]["duration"])
    v = next(s for s in info["streams"] if s["codec_type"] == "video")
    w, h = int(v["width"]), int(v["height"])

    tj = out / "transcript.json"
    if force or not tj.exists():
        wav = out / "audio.wav"
        ffmpeg(["-i", src, "-vn", "-ac", "1", "-ar", "16000", wav], log)
        tr = get_transcriber()
        log.info(f"transcribing {dur:.0f}s with {tr.name}…")
        save_json(tj, tr.transcribe(wav, None, "", out))
    t = json.loads(tj.read_text())
    words = t.get("words", [])
    (out / "transcript.txt").write_text("\n".join(f"[{s['start']:7.2f}] {s['text']}" for s in t.get("segments", [])) + "\n")

    cj = out / "cuts.json"
    if force or not cj.exists():
        save_json(cj, scene_cuts(src))
    cuts = json.loads(cj.read_text())

    sheet(src, [0.0, 0.5, 1.0, 1.5, 2.0, 3.0], out / "hook.jpg", cols=6)
    shots = [0.0] + cuts
    picks = shots if len(shots) <= 24 else [shots[round(i * (len(shots) - 1) / 23)] for i in range(24)]
    sheet(src, [p + 0.15 for p in picks], out / "contact.jpg", cols=6, width=240)

    first = words[0]["start"] if words else None
    hook_words = [x["text"] for x in words if x["start"] < 3.0]
    shot_lens = np.diff([0.0] + cuts + [dur])
    m = {
        "duration_s": round(dur, 2), "resolution": f"{w}x{h}", "orientation": "vertical" if h > w else "horizontal" if w > h else "square",
        "words": len(words), "wpm": round(len(words) / dur * 60, 1) if dur else 0,
        "first_word_s": first, "hook_first_3s": " ".join(hook_words),
        "cuts": len(cuts), "avg_shot_s": round(float(shot_lens.mean()), 2), "cuts_first_5s": sum(c < 5 for c in cuts),
        "longest_shot_s": round(float(shot_lens.max()), 2), "loudness_lufs": loudness(src),
    }
    save_json(out / "metrics.json", m)

    meta = json.loads((ref / "info.json").read_text()) if ref.is_dir() and (ref / "info.json").exists() else {}
    md = out / "analysis.md"
    auto = f"""# {meta.get('title') or src.stem}

{meta.get('channel') or meta.get('uploader') or ''} · {meta.get('webpage_url') or src.name} · {meta.get('view_count') or '?'} views

## Numbers (auto)
| | |
|---|---|
| Length | {m['duration_s']} s · {m['resolution']} ({m['orientation']}) |
| Speech | {m['words']} words · {m['wpm']} wpm · first word at {first if first is not None else '—'} s |
| Pacing | {m['cuts']} cuts · avg shot {m['avg_shot_s']} s · {m['cuts_first_5s']} cuts in first 5 s · longest shot {m['longest_shot_s']} s |
| Loudness | {m['loudness_lufs']} LUFS |

**First 3 s (spoken):** {m['hook_first_3s'] or '—'}

Files: `hook.jpg` (0–3 s), `contact.jpg` (one frame per shot), `transcript.txt`.
"""
    keep = ""
    if md.exists():  # keep the hand-written breakdown below the auto block
        old = md.read_text()
        i = old.find("\n## Breakdown")
        keep = old[i:] if i >= 0 else ""
    md.write_text(auto + (keep or "\n## Breakdown\n_(to be written: hook, visual hooks, structure, what to steal)_\n"))
    log.info(f"analysis → {md}")
    return md


# ---------------------------------------------------------------- list / rm

def list_refs() -> None:
    rows = sorted(p for p in REFS.iterdir() if p.is_dir()) if REFS.exists() else []
    if not rows:
        print("(no references yet: ./studio ref add <url>)")
    for p in rows:
        meta = json.loads((p / "info.json").read_text()) if (p / "info.json").exists() else {}
        size = sum(f.stat().st_size for f in p.rglob("*") if f.is_file()) / 1e6
        state = "analysed" if (p / "metrics.json").exists() else "downloaded" if any(p.glob("source.mp4")) else "incomplete"
        print(f"{p.name:<14} {state:<10} {size:7.1f} MB  {(meta.get('duration') or 0):>5}s  {(meta.get('title') or '')[:60]}")


def remove(ref_id: str, yes: bool) -> None:
    p = REFS / ref_id
    if not p.is_dir() or p.resolve().parent != REFS.resolve():
        raise SystemExit(f"no reference '{ref_id}'")
    files = [f for f in p.rglob("*") if f.is_file()]
    size = sum(f.stat().st_size for f in files) / 1e6
    if not yes:
        print(f"would delete references/{ref_id}/ ({len(files)} files, {size:.1f} MB). Re-run with --yes to delete.")
        return
    shutil.rmtree(p)
    print(f"deleted references/{ref_id}/ ({size:.1f} MB)")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="studio ref", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("add")
    a.add_argument("urls", nargs="+")
    a.add_argument("--analyze", action="store_true", help="analyse right after downloading")
    z = sub.add_parser("analyze")
    z.add_argument("refs", nargs="+")
    z.add_argument("--force", action="store_true")
    sub.add_parser("list")
    r = sub.add_parser("rm")
    r.add_argument("id")
    r.add_argument("--yes", action="store_true")
    args = ap.parse_args(argv)
    if args.cmd == "add":
        for u in args.urls:
            ref = add(u)
            print(ref)
            if args.analyze:
                print(analyze(ref))
    elif args.cmd == "analyze":
        for x in args.refs:
            print(analyze(resolve(x), args.force))
    elif args.cmd == "list":
        list_refs()
    elif args.cmd == "rm":
        remove(args.id, args.yes)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
