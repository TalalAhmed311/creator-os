"""Fuzzy-align the transcript to plan.json beats and find every take of each beat.

  python -m pipeline.align_script <project> [--threshold 70]

Default pick per beat = the LAST complete take (people re-do lines until they're happy).
Writes work/alignment.json:
  {"beats": [{"id", "script", "takes": [{"w0", "w1", "start", "end", "score", "complete"}], "chosen": idx|null}]}
w0/w1 are inclusive word indices into transcript.words.
"""
from __future__ import annotations

import argparse
import re

from rapidfuzz import fuzz

from pipeline.common import Project, get_logger, is_fresh, load_json, save_json

log = get_logger("align_script")


_UNITS = "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen".split()
_TENS = {w: 10 * i for i, w in enumerate("_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()) if w != "_"}
_NUM = {**{w: i for i, w in enumerate(_UNITS)}, **_TENS, "hundred": 100, "thousand": 1000}


def _numbers_to_digits(tokens: list[str]) -> list[str]:
    """'forty two' → '42', 'a hundred' stays words; so script words match transcripts that print digits."""
    out, i = [], 0
    while i < len(tokens):
        t = tokens[i]
        if t in _TENS and i + 1 < len(tokens) and tokens[i + 1] in _UNITS[1:10]:
            out.append(str(_TENS[t] + _UNITS.index(tokens[i + 1])))
            i += 2
            continue
        out.append(str(_NUM[t]) if t in _NUM and t not in ("hundred", "thousand") else t)
        i += 1
    return out


def toks(text: str) -> list[str]:
    text = text.lower().replace("%", " percent ").replace("$", " dollars ")
    raw = [t for t in re.findall(r"[a-z0-9']+", text) if t not in {"um", "uh", "erm", "hmm"}]
    return _numbers_to_digits(raw)


def find_takes(script: str, words: list[dict], threshold: float = 70.0) -> list[dict]:
    target = toks(script)
    if not target:
        return []
    n = len(target)
    tw = [(" ".join(toks(w["text"])), i) for i, w in enumerate(words)]
    tw = [(t, i) for t, i in tw if t]
    seq = [t for t, _ in tw]
    tstr = " ".join(target)
    first, last = target[0], target[-1]
    cands = []
    lo, hi = max(1, int(n * 0.6)), int(n * 1.5) + 2
    for a in range(len(seq)):
        best = None
        for L in range(lo, min(hi, len(seq) - a) + 1):
            s = fuzz.ratio(tstr, " ".join(seq[a:a + L]))
            if best is None or s > best[0]:
                best = (s, L)
        if best and best[0] >= threshold:
            s, L = best
            cands.append({"a": a, "b": a + L - 1, "score": s})
    # greedy non-overlapping selection by score
    cands.sort(key=lambda c: c["score"], reverse=True)
    chosen = []
    for c in cands:
        if all(c["b"] < o["a"] or c["a"] > o["b"] for o in chosen):
            chosen.append(c)
    chosen.sort(key=lambda c: c["a"])
    takes = []
    for c in chosen:
        w0, w1 = tw[c["a"]][1], tw[c["b"]][1]
        span = seq[c["a"]:c["b"] + 1]
        # complete = covers the start and the end of the line
        complete = c["score"] >= threshold + 8 or (first in span[:3] and last in span[-3:])
        takes.append({"w0": w0, "w1": w1, "start": words[w0]["start"], "end": words[w1]["end"],
                      "score": round(c["score"], 1), "complete": bool(complete)})
    return takes


def align(plan: dict, words: list[dict], threshold: float = 70.0) -> dict:
    beats, prev_end = [], -1.0
    for b in plan["beats"]:
        takes = find_takes(b["spoken"], words, threshold)
        chosen = None
        # last complete take that comes after the previous beat's pick (keeps story order), else best
        order = [i for i, t in enumerate(takes) if t["complete"] and t["start"] >= prev_end] or \
                [i for i, t in enumerate(takes) if t["complete"]] or \
                ([max(range(len(takes)), key=lambda i: takes[i]["score"])] if takes else [])
        if order:
            chosen = order[-1]
            prev_end = takes[chosen]["end"]
        beats.append({"id": b["id"], "script": b["spoken"], "takes": takes, "chosen": chosen})
    return {"beats": beats}


def run_align(project: Project, threshold: float = 70.0, force: bool = False) -> dict | None:
    plan_p, tr_p = project.root / "plan.json", project.work / "transcript.json"
    out = project.work / "alignment.json"
    if not plan_p.exists():
        log.info("no plan.json — skipping script alignment")
        return None
    if not force and is_fresh(out, [plan_p, tr_p]):
        return load_json(out)
    res = align(load_json(plan_p), load_json(tr_p)["words"], threshold)
    save_json(out, res)
    for b in res["beats"]:
        n = len(b["takes"])
        pick = b["takes"][b["chosen"]] if b["chosen"] is not None else None
        log.info(f"{b['id']}: {n} take(s)" + (f", using take {b['chosen'] + 1} @ {pick['start']:.1f}s (score {pick['score']})" if pick else " — NOT FOUND"))
    return res


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("--threshold", type=float, default=70.0)
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args(argv)
    run_align(Project(a.project), a.threshold, a.force)


if __name__ == "__main__":
    main()
