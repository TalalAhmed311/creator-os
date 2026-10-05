from conftest import words_from

from pipeline.auto_edl import build_segments
from pipeline.timeline import layout, map_words, snap


def test_segments_cut_fillers_and_long_gaps():
    words = words_from("hello there um this is great", gap=0.05)
    words[4]["start"] += 1.0; words[4]["end"] += 1.0  # "is" after a 1 s pause
    words[5]["start"] += 1.0; words[5]["end"] += 1.0
    segs = build_segments(words, {2}, [(None, 0, len(words) - 1)], "bip-raw", 10.0)
    assert len(segs) == 3  # [hello there] | [this] | [is great]
    assert all(b["in"] >= a["out"] for a, b in zip(segs, segs[1:]))
    # the cut filler is never inside a segment
    um = words[2]
    assert not any(s["in"] < (um["start"] + um["end"]) / 2 < s["out"] for s in segs)


def test_layout_is_frame_snapped_and_contiguous():
    lay = layout([{"src": "cam", "in": 1.013, "out": 2.51}, {"src": "cam", "in": 4.0, "out": 4.9}], 30)
    for s in lay:
        assert abs(s["in"] * 30 - round(s["in"] * 30)) < 1e-6
    assert lay[1]["out_start"] == lay[0]["out_end"]
    assert snap(1.013, 30) == 1.0


def test_map_words_to_output_time():
    lay = layout([{"src": "cam", "in": 10.0, "out": 11.0}, {"src": "cam", "in": 20.0, "out": 21.0}], 30)
    out = map_words([{"text": "a", "start": 10.2, "end": 10.5}, {"text": "cut", "start": 15, "end": 15.3},
                     {"text": "b", "start": 20.1, "end": 20.4}], lay)
    assert [w["text"] for w in out] == ["a", "b"]
    assert out[0]["start"] == 0.2 and out[1]["start"] == 1.1


def test_refresh_captions_keeps_hand_edits(tmp_path):
    from pipeline.auto_edl import refresh_captions
    from pipeline.common import Project, save_json
    proj = Project(tmp_path / "p").ensure()
    words = words_from("we use claude code daily")
    save_json(proj.work / "transcript.json", {"words": words})
    edl = {"project_id": "p", "output": {"width": 1080, "height": 1920, "fps": 30}, "sources": {"cam": "raw/cam.mp4"},
           "segments": [{"src": "cam", "in": 0.0, "out": 5.0}],
           "captions": {"style": "bip-raw", "words": [{"text": "Claude", "start": 0.7, "end": 1.0, "src_start": words[2]["start"], "highlight": True}]},
           "graphics": [], "audio": {"loudness_lufs": -14}}
    save_json(proj.root / "edl.json", edl)
    out = refresh_captions(proj)
    w = [x for x in out["captions"]["words"] if x["src_start"] == words[2]["start"]][0]
    assert w["text"] == "Claude" and w["highlight"] is True
    assert len(out["captions"]["words"]) == 5
