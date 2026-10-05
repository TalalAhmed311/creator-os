"""Pluggable providers: the studio depends on these interfaces, never on a specific library.

  transcription.py — Transcriber: mlx-whisper | whisper.cpp | sidecar file | none
  face.py          — FaceDetector: mediapipe | opencv | center

Selection comes from studio.json ("auto" = first available backend) and can be overridden per call.
`python -m pipeline.deps` shows what is installed and how to add the rest.
"""
from __future__ import annotations

from pipeline.common import STUDIO, load_json

CONFIG = STUDIO / "studio.json"
DEFAULTS = {
    "transcriber": "auto",
    "whisper_model": "mlx-community/whisper-large-v3-turbo",
    "whisper_cpp_model": "assets/models/ggml-large-v3-turbo.bin",
    "language": "en",
    "face_detector": "auto",
}


def config() -> dict:
    return {**DEFAULTS, **(load_json(CONFIG) if CONFIG.exists() else {})}


class ProviderUnavailable(RuntimeError):
    """Raised when a requested backend isn't installed; message says how to install it."""
