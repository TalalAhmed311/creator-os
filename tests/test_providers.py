import pytest

from core.providers import ProviderUnavailable
from core.providers.face import get_face_detector
from core.providers.transcription import BACKENDS, get_transcriber, parse_subtitles
from harnesses.studio.auto_edl import speech_segments

SRT = """1
00:00:01,000 --> 00:00:03,000
This took me three hours

2
00:00:04,000 --> 00:00:05,000
Follow for more
"""


def test_every_backend_implements_the_interface():
    for b in BACKENDS.values():
        ok, why = b.available(None)
        assert isinstance(ok, bool) and why


def test_none_backend_always_available(tmp_path):
    t = get_transcriber("none", tmp_path)
    assert t.transcribe(tmp_path / "x.wav", "en", "", tmp_path) == {"words": [], "segments": []}


def test_sidecar_srt(tmp_path):
    (tmp_path / "raw").mkdir()
    (tmp_path / "raw" / "transcript.srt").write_text(SRT)
    t = get_transcriber("sidecar", tmp_path)
    res = t.transcribe(None, "en", "", tmp_path)
    assert [w["text"] for w in res["words"]][:3] == ["This", "took", "me"]
    assert res["words"][0]["start"] == 1.0 and res["words"][4]["end"] <= 3.0
    assert len(res["segments"]) == 2
    # auto picks sidecar when no local model is installed but a transcript file exists
    assert get_transcriber("auto", tmp_path).name in ("mlx-whisper", "whisper-cpp", "sidecar")


def test_unknown_backend_raises(tmp_path):
    with pytest.raises(ProviderUnavailable):
        get_transcriber("dragon-speech", tmp_path)


def test_parse_vtt():
    words = parse_subtitles("WEBVTT\n\n00:00:00.500 --> 00:00:01.500\n<b>Hello</b> world")
    assert [w["text"] for w in words] == ["Hello", "world"]


def test_silence_only_segments():
    segs = speech_segments([{"start": 0.0, "end": 1.2}, {"start": 4.0, "end": 5.5}], 8.0, "bip-raw")
    assert [(s["in"], s["out"]) for s in segs] == [(1.15, 4.08), (5.45, 8.0)]


def test_face_detector_falls_back():
    assert get_face_detector("auto").name in ("mediapipe", "opencv", "center")
    assert get_face_detector("center").detect(None) is None


def test_mlx_backend_requires_full_runtime(monkeypatch):
    import importlib.util as iu
    real = iu.find_spec
    monkeypatch.setattr(iu, "find_spec", lambda name, *a: None if name == "mlx" else real(name, *a))
    ok, why = BACKENDS["mlx-whisper"].available(None)
    assert not ok and "mlx" in why


def test_merge_fragments():
    from harnesses.studio.transcribe import merge_fragments
    ws = [{"text": t, "start": i, "end": i + 0.5} for i, t in enumerate(["Sign", "-ups", "went", "40", "%", "up", "it", "'s"])]
    assert [w["text"] for w in merge_fragments(ws)] == ["Sign-ups", "went", "40%", "up", "it's"]
