"""Transcriber interface + backends.

Every backend returns the same shape (source/camera time, seconds):
  {"words": [{"text", "start", "end", "prob"}], "segments": [{"start", "end", "text"}]}

Backends (auto order): mlx-whisper → whisper.cpp → sidecar → none
  mlx-whisper  local, Apple Silicon. Feature pack: requirements/transcribe-mlx.txt
  whisper-cpp  `brew install whisper-cpp` + a ggml model in assets/models/
  sidecar      a transcript you drop in raw/ (transcript.json / .srt / .vtt — e.g. exported from CapCut)
  none         no words: the Edit Bay still cuts dead air by silence, captions are off
"""
from __future__ import annotations

import importlib.util
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Protocol

from pipeline.common import STUDIO, load_json
from pipeline.providers import ProviderUnavailable, config


class Transcriber(Protocol):
    name: str

    def available(self, project_root: Path | None = None) -> tuple[bool, str]:
        """(usable?, human-readable status or install hint)"""

    def transcribe(self, audio: Path, language: str | None, prompt: str, project_root: Path) -> dict:
        ...


def _words_to_segments(words: list[dict], max_gap: float = 0.8) -> list[dict]:
    segs, cur = [], []
    for w in words:
        if cur and (w["start"] - cur[-1]["end"] > max_gap or re.search(r"[.!?]$", cur[-1]["text"])):
            segs.append(cur)
            cur = []
        cur.append(w)
    if cur:
        segs.append(cur)
    return [{"start": s[0]["start"], "end": s[-1]["end"], "text": " ".join(w["text"] for w in s)} for s in segs]


# ---------------------------------------------------------------- mlx-whisper

class MlxWhisper:
    name = "mlx-whisper"

    RUNTIME = ("mlx_whisper", "mlx", "numba", "tiktoken", "huggingface_hub")

    def available(self, project_root=None):
        missing = [m for m in self.RUNTIME if importlib.util.find_spec(m) is None]
        if not missing:
            return True, f"installed (model {config()['whisper_model']}, downloaded on first use)"
        return False, (f"missing {', '.join(missing)} → uv pip install --python .venv/bin/python -r requirements/transcribe-mlx.txt && "
                       "uv pip install --python .venv/bin/python --no-deps mlx-whisper")

    @staticmethod
    def _pick_device() -> str:
        """Use the GPU when its kernels load; some macOS/chip combos (e.g. M5 on macOS 26.0) can't
        load MLX's newest Metal kernels — fall back to CPU instead of failing."""
        import mlx.core as mx

        try:
            a = mx.ones((256, 256))
            mx.eval(a @ a)
            return "gpu"
        except RuntimeError:
            mx.set_default_device(mx.cpu)
            print("[transcribe] MLX GPU kernels unavailable on this macOS — using CPU (slower). "
                  "Updating macOS usually restores GPU speed.")
            return "cpu"

    def transcribe(self, audio, language, prompt, project_root):
        import mlx_whisper

        self._pick_device()
        model = os.environ.get("STUDIO_WHISPER_MODEL") or config()["whisper_model"]
        res = mlx_whisper.transcribe(str(audio), path_or_hf_repo=model, word_timestamps=True,
                                     language=language, initial_prompt=prompt, condition_on_previous_text=False, verbose=None)
        words = [{"text": w["word"].strip(), "start": round(float(w["start"]), 3), "end": round(float(w["end"]), 3),
                  "prob": round(float(w.get("probability", 1.0)), 3)}
                 for seg in res["segments"] for w in seg.get("words", []) if w["word"].strip()]
        return {"words": words, "segments": _words_to_segments(words)}


# ---------------------------------------------------------------- whisper.cpp

class WhisperCpp:
    name = "whisper-cpp"

    def _bin(self):
        return shutil.which("whisper-cli") or shutil.which("whisper-cpp")

    def _model(self) -> Path:
        return STUDIO / config()["whisper_cpp_model"]

    def available(self, project_root=None):
        if not self._bin():
            return False, "install: brew install whisper-cpp (then put a ggml model in assets/models/)"
        if not self._model().exists():
            return False, f"whisper-cpp found but model missing: {self._model().relative_to(STUDIO)}"
        return True, f"installed ({self._model().name})"

    def transcribe(self, audio, language, prompt, project_root):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td) / "out"
            cmd = [self._bin(), "-m", str(self._model()), "-f", str(audio), "-ojf", "-of", str(base), "--prompt", prompt]
            if language:
                cmd += ["-l", language]
            subprocess.run(cmd, capture_output=True, check=True)
            data = json.loads(base.with_suffix(".json").read_text())
        words: list[dict] = []
        for seg in data.get("transcription", []):
            for tok in seg.get("tokens", []):
                text = tok.get("text", "")
                if not text.strip() or text.startswith("[_"):
                    continue
                t0, t1 = tok["offsets"]["from"] / 1000, tok["offsets"]["to"] / 1000
                if words and not text.startswith(" "):  # sub-word token: glue onto the previous word
                    words[-1]["text"] += text
                    words[-1]["end"] = round(t1, 3)
                else:
                    words.append({"text": text.strip(), "start": round(t0, 3), "end": round(t1, 3), "prob": round(tok.get("p", 1.0), 3)})
        return {"words": words, "segments": _words_to_segments(words)}


# ---------------------------------------------------------------- sidecar file

def _ts(s: str) -> float:
    h, m, rest = s.replace(",", ".").split(":")
    return int(h) * 3600 + int(m) * 60 + float(rest)


def parse_subtitles(text: str) -> list[dict]:
    """SRT or VTT → words with timings spread across each cue by character length."""
    words = []
    for block in re.split(r"\n\s*\n", text.strip()):
        m = re.search(r"(\d+:\d+:\d+[.,]\d+)\s*-->\s*(\d+:\d+:\d+[.,]\d+)", block)
        if not m:
            continue
        t0, t1 = _ts(m.group(1)), _ts(m.group(2))
        line = " ".join(ln for ln in block[m.end():].strip().splitlines())
        toks = re.sub(r"<[^>]+>", "", line).split()
        total = sum(len(t) + 1 for t in toks) or 1
        cur = t0
        for t in toks:
            d = (t1 - t0) * (len(t) + 1) / total
            words.append({"text": t, "start": round(cur, 3), "end": round(cur + d * 0.92, 3), "prob": 0.5})
            cur += d
    return words


class Sidecar:
    name = "sidecar"
    NAMES = ("transcript.json", "transcript.srt", "transcript.vtt")

    def _find(self, project_root: Path | None) -> Path | None:
        if not project_root:
            return None
        for n in self.NAMES:
            for d in (project_root / "raw", project_root):
                if (d / n).exists():
                    return d / n
        return None

    def available(self, project_root=None):
        f = self._find(project_root)
        if f:
            return True, f"using {f.name}"
        return False, "drop raw/transcript.srt (or .vtt / .json) into the project"

    def transcribe(self, audio, language, prompt, project_root):
        f = self._find(project_root)
        if f.suffix == ".json":
            data = load_json(f)
            words = data["words"] if isinstance(data, dict) else data
        else:
            words = parse_subtitles(f.read_text())
        return {"words": words, "segments": _words_to_segments(words)}


# ---------------------------------------------------------------- none

class NoTranscript:
    name = "none"

    def available(self, project_root=None):
        return True, "always available — silence-based cutting, no captions"

    def transcribe(self, audio, language, prompt, project_root):
        return {"words": [], "segments": []}


BACKENDS: dict[str, Transcriber] = {b.name: b for b in (MlxWhisper(), WhisperCpp(), Sidecar(), NoTranscript())}
AUTO_ORDER = ["mlx-whisper", "whisper-cpp", "sidecar", "none"]


def get_transcriber(name: str | None = None, project_root: Path | None = None) -> Transcriber:
    name = name or config()["transcriber"]
    if name == "auto":
        for n in AUTO_ORDER:
            if BACKENDS[n].available(project_root)[0]:
                return BACKENDS[n]
    if name not in BACKENDS:
        raise ProviderUnavailable(f"unknown transcriber '{name}' — choose from {', '.join(BACKENDS)} or auto")
    ok, why = BACKENDS[name].available(project_root)
    if not ok:
        raise ProviderUnavailable(f"transcriber '{name}' unavailable: {why}")
    return BACKENDS[name]
