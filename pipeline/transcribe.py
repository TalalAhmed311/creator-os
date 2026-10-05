"""Transcribe the voice track through the Transcriber interface (pipeline/providers/transcription.py).

  python -m pipeline.transcribe <project> [--backend auto|mlx-whisper|whisper-cpp|sidecar|none] [--language en]

Writes work/transcript.json {backend, language, words:[{text,start,end,prob}], segments:[...]} and work/transcript.srt.
The glossary is fed as the prompt and used to restore spelling of product names / tech terms.
With backend "none" the words list is empty and the Edit Bay cuts by silence only.
"""
from __future__ import annotations

import argparse
import re

from pipeline.common import BRAIN, Project, get_logger, is_fresh, load_json, read_glossary, save_json
from pipeline.providers import config
from pipeline.providers.transcription import get_transcriber

log = get_logger("transcribe")
# Nudges Whisper-style models to keep disfluencies so detect_fillers can remove them.
VERBATIM_PROMPT = "Um, so, uh, I was like, you know, building this thing. Hmm."


def glossary_fix(text: str, glossary: list[str]) -> str:
    """Restore canonical spelling for glossary terms (whole-word, case-insensitive)."""
    m = re.match(r"^(\W*)(.*?)([.,!?;:\"')]*)$", text.strip())
    lead, core, trail = m.groups()
    for term in glossary:
        if core.lower() == term.lower():
            return f"{lead}{term}{trail}"
    return text


def merge_fragments(words: list[dict]) -> list[dict]:
    """Glue tokenizer fragments back onto the previous word: 'Sign' + '-ups', '40' + '%', 'it' + "'s"."""
    out: list[dict] = []
    for w in words:
        t = w["text"]
        if out and (re.fullmatch(r"[%.,!?;:)\]]+", t) or re.match(r"^(-\w|'\w)", t)):
            out[-1] = {**out[-1], "text": out[-1]["text"] + t, "end": w["end"]}
        else:
            out.append(dict(w))
    return out


def transcribe(project: Project, backend: str | None = None, language: str | None = None, force: bool = False) -> dict:
    audio = project.work / "voice.wav"
    out = project.work / "transcript.json"
    tr = get_transcriber(backend, project.root)
    language = language or config()["language"]
    if not force and is_fresh(out, [audio, BRAIN / "glossary.txt"]) and load_json(out).get("backend") == tr.name:
        return load_json(out)
    glossary = read_glossary()
    prompt = VERBATIM_PROMPT + (" Terms: " + ", ".join(glossary) + "." if glossary else "")
    log.info(f"backend: {tr.name}")
    res = tr.transcribe(audio, language, prompt, project.root)
    words = [{**w, "text": glossary_fix(w["text"], glossary)} for w in merge_fragments(res["words"])]
    segments = [{**s, "text": " ".join(glossary_fix(t, glossary) for t in s["text"].split())} for s in res["segments"]]
    data = {"backend": tr.name, "language": language, "words": words, "segments": segments}
    save_json(out, data)
    write_srt(segments, project.work / "transcript.srt")
    log.info(f"{len(words)} words, {len(segments)} segments" if words else "no transcript — silence-based edit, captions off")
    return data


def _ts(t: float) -> str:
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def write_srt(segments: list[dict], path) -> None:
    lines = []
    for i, s in enumerate(segments, 1):
        lines += [str(i), f"{_ts(s['start'])} --> {_ts(s['end'])}", s["text"], ""]
    path.write_text("\n".join(lines))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("--backend", help="auto | mlx-whisper | whisper-cpp | sidecar | none (default: studio.json)")
    ap.add_argument("--language")
    ap.add_argument("--model", help="whisper model override, e.g. mlx-community/whisper-small.en-mlx")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args(argv)
    if a.model:
        import os
        os.environ["STUDIO_WHISPER_MODEL"] = a.model
    transcribe(Project(a.project), a.backend, a.language, a.force)


if __name__ == "__main__":
    main()
