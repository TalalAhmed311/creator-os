"""Build the voice track on the camera timeline: pick mic (offset-corrected) or camera audio,
denoise, high-pass, and loudness-normalise.

  python -m harnesses.studio.clean_audio <project> [--force] [--no-denoise]

Writes work/voice.wav (48 kHz mono, exactly the camera's duration).
"""
from __future__ import annotations

import argparse

from core.common import Project, ffmpeg, get_logger, is_fresh, load_json

log = get_logger("clean_audio")


def clean(project: Project, force: bool = False, denoise: bool = True) -> str:
    media = project.media()
    out = project.work / "voice.wav"
    dur = media["cam"]["duration"]
    sync_p = project.work / "sync.json"
    if media.get("mic"):
        src = project.root / media["mic"]["path"]
        offset = load_json(sync_p)["mic_offset_ms"] / 1000 if sync_p.exists() else 0.0
    else:
        if not media["cam"]["has_audio"]:
            raise SystemExit("no audio anywhere — camera has no track and no mic file was given")
        src, offset = project.root / media["cam"]["path"], 0.0
    if not force and is_fresh(out, [src, sync_p, project.work / "media.json"]):
        return str(out)

    # align to camera time: cam t  <->  mic t + offset
    chain = []
    if offset > 0:
        chain.append(f"atrim=start={offset:.4f},asetpts=PTS-STARTPTS")
    elif offset < 0:
        chain.append(f"adelay={int(-offset * 1000)}:all=1")
    chain += ["aformat=channel_layouts=mono", "highpass=f=80"]
    if denoise:
        chain.append("afftdn=nf=-25:tn=1")
    chain += ["loudnorm=I=-16:TP=-1.5:LRA=11", "aresample=48000", f"apad=whole_dur={dur:.4f}", f"atrim=0:{dur:.4f}"]
    ffmpeg(["-i", src, "-vn", "-af", ",".join(chain), "-ac", "1", "-ar", "48000", "-c:a", "pcm_s16le", out], log)
    log.info(f"voice.wav from {'mic' if media.get('mic') else 'camera'} (offset {offset * 1000:.0f} ms)")
    return str(out)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--no-denoise", action="store_true")
    a = ap.parse_args(argv)
    clean(Project(a.project), a.force, not a.no_denoise)


if __name__ == "__main__":
    main()
