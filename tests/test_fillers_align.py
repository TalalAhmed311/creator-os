from conftest import words_from

from pipeline.align_script import align
from pipeline.detect_fillers import find_fillers


def test_fillers_stutters_and_false_start():
    words = words_from("um so I I built the new onboarding flow uh today")
    kinds = {m["text"]: m["kind"] for m in find_fillers(words)}
    assert kinds["um"] == "filler" and kinds["uh"] == "filler"
    assert kinds["I"] == "stutter"
    assert "onboarding" not in kinds


def test_retake_keeps_last_take():
    words = words_from("so what I built was so what I built was a new dashboard")
    cut = {m["i"] for m in find_fillers(words) if m["kind"] == "retake"}
    assert cut == {0, 1, 2, 3, 4}


def test_ordinary_repetition_is_not_a_retake():
    text = ("I want to show you the app . Then I explain how the signup works and why it matters for users "
            "and the whole team and also for me because honestly it took forever . I want to show you more")
    assert not [m for m in find_fillers(words_from(text)) if m["kind"] == "retake"]


def test_align_picks_last_complete_take():
    plan = {"beats": [
        {"id": "hook", "spoken": "This took me three hours instead of three weeks"},
        {"id": "cta", "spoken": "Follow for day thirteen tomorrow"},
    ]}
    speech = ("this took me three hours instead of uh wait "
              "this took me three hours instead of three weeks "
              "okay "
              "follow for day thirteen tomorrow")
    res = align(plan, words_from(speech))
    hook = res["beats"][0]
    assert len(hook["takes"]) == 2
    chosen = hook["takes"][hook["chosen"]]
    assert chosen["w0"] == 9  # second take
    assert res["beats"][1]["chosen"] is not None


def test_align_matches_number_words_to_digits():
    plan = {"beats": [{"id": "payoff", "spoken": "Signups went from forty percent to seventy two percent completion."}]}
    res = align(plan, words_from("okay so signups went from 40% to 72% completion"))
    assert res["beats"][0]["chosen"] is not None
