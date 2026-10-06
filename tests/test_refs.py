import json

import pytest

from core import refs


@pytest.fixture
def lib(tmp_path, monkeypatch):
    monkeypatch.setattr(refs, "REFS", tmp_path)
    (tmp_path / "abc").mkdir()
    (tmp_path / "abc" / "source.mp4").write_bytes(b"x" * 10)
    (tmp_path / "abc" / "info.json").write_text(json.dumps({"title": "t", "duration": 5}))
    return tmp_path


def test_rm_without_yes_deletes_nothing(lib, capsys):
    refs.remove("abc", yes=False)
    assert (lib / "abc" / "source.mp4").exists()
    assert "would delete" in capsys.readouterr().out


def test_rm_with_yes(lib):
    refs.remove("abc", yes=True)
    assert not (lib / "abc").exists()


def test_rm_refuses_paths_outside_library(lib, tmp_path):
    with pytest.raises(SystemExit):
        refs.remove("../abc", yes=True)


def test_list(lib, capsys):
    refs.list_refs()
    assert "abc" in capsys.readouterr().out


def test_source_ignores_partial_downloads(tmp_path):
    (tmp_path / "source.f399.mp4.part").write_bytes(b"x")
    with pytest.raises(SystemExit):
        refs.source_of(tmp_path)


def test_metadata_and_fragments_are_not_a_finished_download(tmp_path):
    for n in ("source.info.json", "source.f399.mp4", "source.f140-17.m4a.part"):
        (tmp_path / n).write_bytes(b"x")
    assert refs.finished_source(tmp_path) is None
    (tmp_path / "source.mp4").write_bytes(b"x")
    assert refs.finished_source(tmp_path).name == "source.mp4"


def test_frame_past_the_end_is_the_last_frame(tmp_path):
    """A scene cut near the end + the 0.15 s offset used to crash cv2.imdecode on ffmpeg's empty output."""
    pytest.importorskip("cv2")
    import subprocess
    src = tmp_path / "clip.mp4"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i", "color=c=red:s=64x112:d=1",
                    "-pix_fmt", "yuv420p", str(src)], check=True)
    img = refs.frame_at(src, 5.0, width=64)
    assert img.shape[1] == 64 and img[..., 2].mean() > 150   # red (BGR), not the black placeholder
    refs.sheet(src, [0.0, 0.9, 1.2], tmp_path / "contact.jpg", cols=3, width=64)
    assert (tmp_path / "contact.jpg").stat().st_size > 0
