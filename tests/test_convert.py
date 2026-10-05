from pathlib import Path

import pytest

from pipeline.common import ffprobe
from pipeline.convert import convert, output_path

MEDIA = Path(__file__).parent / "media"


@pytest.mark.parametrize("fmt", ["mp3", "wav", "m4a"])
def test_convert_video_to_audio(tmp_path, fmt):
    out = convert(MEDIA / "cam.mp4", fmt, tmp_path)
    assert out == (tmp_path / f"cam.{fmt}").resolve()
    streams = ffprobe(out)["streams"]
    assert [s["codec_type"] for s in streams] == ["audio"]


def test_raw_inputs_go_to_work_not_raw(tmp_path):
    src = tmp_path / "proj" / "raw" / "cam.mov"
    assert output_path(src, "mp3", None) == tmp_path / "proj" / "work" / "cam.mp3"


def test_skips_existing_without_force(tmp_path):
    out = convert(MEDIA / "cam.mp4", "mp3", tmp_path)
    mtime = out.stat().st_mtime_ns
    assert convert(MEDIA / "cam.mp4", "mp3", tmp_path).stat().st_mtime_ns == mtime


def test_refuses_same_file(tmp_path):
    with pytest.raises(ValueError):
        convert(MEDIA / "mic.wav", "wav")
