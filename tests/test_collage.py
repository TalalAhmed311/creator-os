from conftest import words_from

from core.common import Project
from harnesses.studio.collage import beat_images, check_layout, layout_from_plan, load_theme, make_blocks, sentence_cuts


def test_images_appear_in_spoken_order_then_replace_oldest():
    blocks = make_blocks(["a", "b", "c", "d", "e"], 4, [0, 1, 2, 3, 4, 5])
    assert blocks[0]["tiles"] == ["a", None, None, None]
    assert blocks[3]["tiles"] == ["a", "b", "c", "d"]
    assert blocks[4]["tiles"] == ["e", "b", "c", "d"]  # oldest (a) goes first


def test_all_images_in_one_block_is_a_full_grid():
    assert make_blocks(["a", "b", "c", "d"], 4, [0, 3])[0]["tiles"] == ["a", "b", "c", "d"]


def test_sentence_cuts_respect_min_block():
    words = words_from("This is one. Two. And this is three.", gap=0.3)
    cuts = sentence_cuts(words, 0.0, words[-1]["end"], 1.0)
    assert cuts[0] == 0.0 and cuts[-1] == round(words[-1]["end"], 3)
    assert all(b - a >= 0.6 for a, b in zip(cuts, cuts[1:]))


def test_beat_images_mixes_files_and_dropped_images(tmp_path):
    proj = Project(tmp_path / "p").ensure()
    for n in ("list_2.jpg", "list_1.jpg", "other_1.jpg"):
        (proj.raw / "images" / n).write_bytes(b"x")
    files, missing = beat_images(proj, "list", ["a robot reading", "raw/images/other_1.jpg", "a server room", "a cat"])
    assert files == ["raw/images/list_1.jpg", "raw/images/other_1.jpg", "raw/images/list_2.jpg"]
    assert missing == ["a cat"]


def test_layout_only_covers_marked_beats(tmp_path):
    proj = Project(tmp_path / "p").ensure()
    (proj.raw / "images" / "list_1.jpg").write_bytes(b"x")
    plan = {"collage_theme": "quad-collage", "beats": [
        {"id": "hook", "spoken": "hi"},
        {"id": "list", "spoken": "...", "collage": {"images": ["a robot", "a gpu"]}}]}
    lay, notes = layout_from_plan(proj, plan, {"hook": (0, 2), "list": (2, 6)}, words_from("one two three four five six"))
    assert lay["theme"] == "quad-collage"
    assert lay["blocks"][0]["start"] == 2 and lay["blocks"][-1]["end"] == 6
    assert any("a gpu" in n for n in notes)


def test_check_layout_flags_too_many_tiles():
    slots = len(load_theme("trio-stack")["slots"])
    edl = {"segments": [{"src": "cam", "in": 0, "out": 5}], "output": {"fps": 30},
           "layout": {"theme": "trio-stack", "blocks": [{"start": 0, "end": 2, "tiles": ["x"] * (slots + 1)}]}}
    assert any("slots" in e for e in check_layout(edl))
    edl["layout"]["theme"] = "nope"
    assert any("unknown video theme" in e for e in check_layout(edl))


def test_one_long_sentence_still_reveals_images_one_by_one(tmp_path):
    proj = Project(tmp_path / "p").ensure()
    for k in (1, 2, 3):
        (proj.raw / "images" / f"v_{k}.jpg").write_bytes(b"x")
    words = words_from("the trick was letting claude write the boring parts while i designed it", gap=0.1)
    plan = {"beats": [{"id": "v", "spoken": "...", "collage": {"images": ["a", "b", "c"]}}]}
    lay, _ = layout_from_plan(proj, plan, {"v": (0, words[-1]["end"])}, words)
    assert len(lay["blocks"]) == 3
    assert [sum(t is not None for t in b["tiles"]) for b in lay["blocks"]] == [1, 2, 3]
