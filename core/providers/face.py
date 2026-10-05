"""FaceDetector interface + backends (auto order: mediapipe → opencv → center).

A detector takes an RGB frame (numpy HxWx3) and returns the largest face as normalised
(cx, cy, h) or None.
"""
from __future__ import annotations

import importlib.util
import urllib.request
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

from core.common import ASSETS
from core.providers import ProviderUnavailable, config

if TYPE_CHECKING:
    import numpy as np

MP_MODEL_URL = "https://storage.googleapis.com/mediapipe-models/face_detector/blaze_face_short_range/float16/latest/blaze_face_short_range.tflite"


class FaceDetector(Protocol):
    name: str

    def available(self) -> tuple[bool, str]: ...

    def load(self) -> None: ...

    def detect(self, rgb: "np.ndarray") -> tuple[float, float, float] | None: ...


class MediapipeFace:
    name = "mediapipe"

    def available(self):
        if importlib.util.find_spec("mediapipe"):
            return True, "installed"
        return False, "install: uv pip install -r requirements/face-mediapipe.txt"

    def load(self):
        import mediapipe as mp
        from mediapipe.tasks.python import BaseOptions, vision

        model = ASSETS / "models" / "blaze_face_short_range.tflite"
        if not model.exists():
            model.parent.mkdir(parents=True, exist_ok=True)
            urllib.request.urlretrieve(MP_MODEL_URL, model)
        self.mp = mp
        self.det = vision.FaceDetector.create_from_options(
            vision.FaceDetectorOptions(base_options=BaseOptions(model_asset_path=str(model)), min_detection_confidence=0.5))

    def detect(self, rgb):
        import numpy as np

        H, W = rgb.shape[:2]
        res = self.det.detect(self.mp.Image(image_format=self.mp.ImageFormat.SRGB, data=np.ascontiguousarray(rgb)))
        boxes = [(d.bounding_box.origin_x, d.bounding_box.origin_y, d.bounding_box.width, d.bounding_box.height) for d in res.detections]
        return _largest(boxes, W, H)


class OpenCVFace:
    """OpenCV YuNet DNN detector (tiny ONNX model, auto-downloaded); Haar cascade if the model can't be fetched."""
    name = "opencv"
    YUNET_URL = "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx"

    def available(self):
        if importlib.util.find_spec("cv2"):
            return True, "installed (YuNet face detector)"
        return False, "install: uv pip install --python .venv/bin/python -r requirements/vision.txt"

    def load(self):
        import os
        os.environ.setdefault("OPENCV_LOG_LEVEL", "ERROR")
        import cv2
        cv2.setLogLevel(0) if hasattr(cv2, "setLogLevel") else None
        self.cv2 = cv2
        self.yunet = None
        model = ASSETS / "models" / "face_detection_yunet_2023mar.onnx"
        try:
            if not model.exists():
                model.parent.mkdir(parents=True, exist_ok=True)
                urllib.request.urlretrieve(self.YUNET_URL, model)
            self.yunet = cv2.FaceDetectorYN.create(str(model), "", (320, 320), 0.7)
        except Exception:  # noqa: BLE001 — offline: try the classic cascade
            xml = Path(getattr(getattr(cv2, "data", None), "haarcascades", "")) / "haarcascade_frontalface_default.xml"
            if not xml.exists():
                raise
            self.haar = cv2.CascadeClassifier(str(xml))

    def detect(self, rgb):
        H, W = rgb.shape[:2]
        if self.yunet is not None:
            bgr = self.cv2.cvtColor(rgb, self.cv2.COLOR_RGB2BGR)
            self.yunet.setInputSize((W, H))
            _, faces = self.yunet.detect(bgr)
            boxes = [tuple(f[:4]) for f in faces] if faces is not None else []
        else:
            gray = self.cv2.cvtColor(rgb, self.cv2.COLOR_RGB2GRAY)
            boxes = [tuple(b) for b in self.haar.detectMultiScale(gray, 1.1, 5, minSize=(W // 20, W // 20))]
        return _largest(boxes, W, H)


class CenterOnly:
    name = "center"

    def available(self):
        return True, "always available — no tracking, centre crop"

    def load(self):
        pass

    def detect(self, rgb):
        return None


def _largest(boxes, W, H):
    if not boxes:
        return None
    x, y, w, h = max(boxes, key=lambda b: b[2] * b[3])
    return (x + w / 2) / W, (y + h / 2) / H, h / H


BACKENDS: dict[str, FaceDetector] = {b.name: b for b in (MediapipeFace(), OpenCVFace(), CenterOnly())}
AUTO_ORDER = ["mediapipe", "opencv", "center"]


def get_face_detector(name: str | None = None) -> FaceDetector:
    name = name or config()["face_detector"]
    candidates = AUTO_ORDER if name == "auto" else [name]
    for n in candidates:
        if n not in BACKENDS:
            raise ProviderUnavailable(f"unknown face detector '{n}'")
        ok, why = BACKENDS[n].available()
        if ok:
            try:
                BACKENDS[n].load()
                return BACKENDS[n]
            except Exception as e:  # noqa: BLE001 — broken install → try the next one in auto mode
                if name != "auto":
                    raise ProviderUnavailable(f"face detector '{n}' failed to load: {e}") from e
        elif name != "auto":
            raise ProviderUnavailable(f"face detector '{n}' unavailable: {why}")
    return BACKENDS["center"]
