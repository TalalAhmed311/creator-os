"""Extract / convert audio from any video or audio file.

    ./studio convert videos/intro.mov                 → videos/intro.mp3
    ./studio convert videos/*.mp4 --to wav            → one .wav per file (best for the Edit Bay)
    ./studio convert mic.m4a --to wav --out videos/

Formats: mp3 (VBR ~190 kbps), wav (48 kHz 16-bit), m4a (AAC 192 kbps).
Never writes into projects/*/raw/ (outputs for raw files go to that project's work/) and never overwrites an
existing file unless --force.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from core.common import ffmpeg, ffprobe, get_logger

log = get_logger("convert")

CODECS = {
    "mp3": ["-c:a", "libmp3lame", "-q:a", "2"],
    "wav": ["-c:a", "pcm_s16le", "-ar", "48000"],
    "m4a": ["-c:a", "aac", "-b:a", "192k"],
}


def output_path(src: Path, fmt: str, out_dir: Path | None) -> Path:
    if out_dir is None:
        out_dir = src.parent
        if out_dir.name == "raw":  # owner's raw footage is read-only: put derived files in work/
            out_dir = out_dir.parent / "work"
    return out_dir / f"{src.stem}.{fmt}"


def convert(src: Path, fmt: str = "mp3", out_dir: Path | None = None, force: bool = False) -> Path:
    src = src.resolve()
    if not src.exists():
        raise FileNotFoundError(src)
    if not any(s.get("codec_type") == "audio" for s in ffprobe(src).get("streams", [])):
        raise ValueError(f"{src.name} has no audio track")
    dst = output_path(src, fmt, out_dir).resolve()
    if dst == src:
        raise ValueError(f"{src.name} is already .{fmt}; pass --out to write a copy elsewhere")
    if dst.exists() and not force:
        log.info(f"exists, skipping (use --force): {dst}")
        return dst
    dst.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg(["-i", src, "-vn", "-map", "0:a:0", *CODECS[fmt], dst], log)
    log.info(f"{src.name} → {dst}")
    return dst


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="studio convert", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="+", type=Path)
    ap.add_argument("--to", default="mp3", choices=sorted(CODECS), help="output format (default: mp3)")
    ap.add_argument("--out", type=Path, help="output folder (default: next to the input)")
    ap.add_argument("--force", action="store_true", help="overwrite an existing output file")
    args = ap.parse_args(argv)
    failed = 0
    for f in args.files:
        try:
            print(convert(f, args.to, args.out, args.force))
        except (FileNotFoundError, ValueError, RuntimeError) as e:
            log.error(f"{f}: {e}")
            failed += 1
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
