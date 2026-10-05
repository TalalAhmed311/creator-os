from pathlib import Path

import pytest

from pipeline.clip import clip, in_raw, main, parse_time, stamp
from pipeline.common import ffprobe
from pipeline.download import is_url

MEDIA = Path(__file__).parent / "media"


@pytest.mark.parametrize("s,v", [("90", 90), ("1:30", 90), ("01:02:03.5", 3723.5), ("0:07.25", 7.25)])
def test_parse_time(s, v):
    assert parse_time(s) == pytest.approx(v)


@pytest.mark.parametrize("bad", ["", "1::2", "a:b", "1:2:3:4"])
def test_parse_time_rejects(bad):
    with pytest.raises(ValueError):
        parse_time(bad)


def test_stamp():
    assert stamp(83) == "1m23s" and stamp(7.5) == "7.5s"


def test_clip_audio_and_video_exact_length(tmp_path):
    outs = clip(MEDIA / "cam.mp4", 1.0, 3.5, "wav", keep_video=True, out_dir=tmp_path)
    assert [o.suffix for o in outs] == [".wav", ".mp4"]
    for o in outs:
        assert float(ffprobe(o)["format"]["duration"]) == pytest.approx(2.5, abs=0.08)


def test_clip_rejects_backwards_range(tmp_path):
    with pytest.raises(ValueError):
        clip(MEDIA / "cam.mp4", 3, 1, "mp3", out_dir=tmp_path)


def test_delete_original(tmp_path):
    src = tmp_path / "talk.mp4"
    src.write_bytes((MEDIA / "cam.mp4").read_bytes())
    main([str(src), "--from", "0:01", "--to", "0:02", "--delete-original"])
    assert not src.exists() and (tmp_path / "talk_1s-2s.mp3").exists()


def test_never_deletes_project_raw(tmp_path):
    raw = tmp_path / "projects" / "p" / "raw"
    raw.mkdir(parents=True)
    src = raw / "cam.mp4"
    src.write_bytes((MEDIA / "cam.mp4").read_bytes())
    main([str(src), "--from", "1", "--to", "2", "--delete-original"])
    assert src.exists() and in_raw(src)
    assert (tmp_path / "projects" / "p" / "work" / "cam_1s-2s.mp3").exists()


def test_is_url():
    assert is_url("https://youtu.be/abc") and not is_url("videos/a.mp4")


def test_decimal_times_keep_full_name(tmp_path):
    outs = clip(MEDIA / "cam.mp4", 1.25, 2.5, "mp3", keep_video=True, out_dir=tmp_path)
    assert [o.name for o in outs] == ["cam_1.2s-2.5s.mp3", "cam_1.2s-2.5s.mp4"]
