"""Cut an exact part of a video (local file or URL), keep its audio, optionally drop the original.

    ./studio clip videos/talk.mp4 --from 1:23 --to 1:45                 → videos/talk_1m23s-1m45s.mp3
    ./studio clip videos/talk.mp4 --from 83.5 --to 105 --audio wav --keep-video
    ./studio clip videos/talk.mp4 --from 0:10 --to 0:30 --delete-original
    ./studio clip "https://youtu.be/…" --from 2:00 --to 2:20            (download into references/<id>/ (kept) → clips/)

Times: SS, MM:SS or HH:MM:SS (decimals ok). Cuts are frame-accurate (re-encoded).
Nothing is deleted unless you pass --delete-original (local files only; never projects/*/raw/).
URL downloads are kept in references/<id>/; remove one with `./studio ref rm <id> --yes` when you're done.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from core import refs
from core.common import ffmpeg, ffprobe, get_logger, video_encoder_args
from core.fetch import download
from core.media.convert import CODECS

log = get_logger("clip")


def parse_time(s: str) -> float:
    parts = str(s).strip().split(":")
    if not 1 <= len(parts) <= 3 or any(p == "" for p in parts):
        raise ValueError(f"bad time '{s}' (use SS, MM:SS or HH:MM:SS)")
    secs = 0.0
    for p in parts:
        secs = secs * 60 + float(p)
    if secs < 0:
        raise ValueError(f"bad time '{s}'")
    return secs


def stamp(t: float) -> str:
    m, s = divmod(t, 60)
    s_txt = f"{s:.1f}".rstrip("0").rstrip(".")
    return f"{int(m)}m{s_txt}s" if m else f"{s_txt}s"


def in_raw(path: Path) -> bool:
    return "raw" in path.resolve().parts and "projects" in path.resolve().parts


def clip(src: Path, start: float, end: float, audio: str | None = "mp3", keep_video: bool = False,
         out_dir: Path | None = None) -> list[Path]:
    info = ffprobe(src)
    dur = float(info["format"].get("duration", 0))
    if end <= start:
        raise ValueError(f"--to ({end}s) must be after --from ({start}s)")
    if start >= dur:
        raise ValueError(f"--from {start}s is past the end ({dur:.1f}s)")
    end = min(end, dur)
    has_audio = any(s.get("codec_type") == "audio" for s in info["streams"])
    has_video = any(s.get("codec_type") == "video" for s in info["streams"])
    if out_dir is None:
        out_dir = src.parent.parent / "work" if in_raw(src) else src.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    base = out_dir / f"{src.stem}_{stamp(start)}-{stamp(end)}"
    cut = ["-ss", f"{start:.3f}", "-i", src, "-t", f"{end - start:.3f}"]
    outs = []
    if audio:
        if not has_audio:
            raise ValueError(f"{src.name} has no audio track")
        a = base.parent / f"{base.name}.{audio}"  # not with_suffix: "1m2.5s" has a dot
        ffmpeg([*cut, "-vn", "-map", "0:a:0", *CODECS[audio], a], log)
        outs.append(a)
    if keep_video:
        if not has_video:
            raise ValueError(f"{src.name} has no video track")
        v = base.parent / f"{base.name}.mp4"
        ffmpeg([*cut, *video_encoder_args("high"), "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", v], log)
        outs.append(v)
    for o in outs:
        log.info(f"{o.name} ({end - start:.2f}s)")
    return outs


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="studio clip", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source", help="video/audio file or URL")
    ap.add_argument("--from", dest="start", required=True, help="start time, e.g. 1:23 or 83.5")
    ap.add_argument("--to", dest="end", required=True, help="end time, e.g. 1:45")
    ap.add_argument("--audio", default="mp3", choices=[*sorted(CODECS), "none"], help="audio format to keep (default mp3)")
    ap.add_argument("--keep-video", action="store_true", help="also save the trimmed video as .mp4")
    ap.add_argument("--delete-original", action="store_true", help="delete the full source file after a successful cut")
    ap.add_argument("--out", type=Path, help="output folder (default: next to the source; references/<id>/clips/ for URLs)")
    a = ap.parse_args(argv)
    start, end = parse_time(a.start), parse_time(a.end)
    audio = None if a.audio == "none" else a.audio
    if not audio and not a.keep_video:
        ap.error("nothing to keep: use --audio <fmt> and/or --keep-video")

    if download.is_url(a.source):
        ref = refs.add(a.source)  # kept in the reference library; never auto-deleted
        outs = clip(refs.source_of(ref), start, end, audio, a.keep_video, a.out or ref / "clips")
        if a.delete_original:
            log.warning(f"kept references/{ref.name}/: delete it with ./studio ref rm {ref.name} --yes")
    else:
        src = Path(a.source).resolve()
        if not src.exists():
            raise SystemExit(f"not found: {src}")
        outs = clip(src, start, end, audio, a.keep_video, a.out)
        if a.delete_original:
            if in_raw(src):
                log.warning(f"kept {src.name}: files in projects/*/raw/ are never deleted by tools")
            elif any(o.resolve() == src for o in outs):
                log.warning("kept the original: an output has the same path")
            else:
                src.unlink()
                log.info(f"deleted original {src.name}")
    for o in outs:
        print(o)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
