"""Mark words to cut: filler sounds, filler phrases, stutters and false starts/retakes.

  python -m pipeline.detect_fillers <project>

Writes work/fillers.json: [{"i": word_index, "text", "start", "end", "kind"}]
kinds: filler (um/uh), phrase (you know, I mean), stutter (the the), retake (earlier attempt of a repeated line)
"""
from __future__ import annotations

import argparse
import re

from pipeline.common import Project, get_logger, is_fresh, load_json, save_json

log = get_logger("detect_fillers")
FILLERS = {"um", "umm", "uh", "uhh", "uh-huh", "erm", "er", "ah", "hmm", "hm", "mm", "mhm", "eh"}
PHRASES = [("you", "know"), ("i", "mean"), ("sort", "of"), ("kind", "of")]


def norm(w: str) -> str:
    return re.sub(r"[^a-z0-9'-]", "", w.lower())


def find_fillers(words: list[dict], retake_window_s: float = 20.0, min_ngram: int = 3) -> list[dict]:
    toks = [norm(w["text"]) for w in words]
    marks: dict[int, str] = {}

    for i, t in enumerate(toks):
        if t in FILLERS:
            marks[i] = "filler"
    # filler phrases — only when set off by commas/pauses ("you know," not "do you know how")
    for i in range(len(toks) - 1):
        for a, b in PHRASES:
            if toks[i] == a and toks[i + 1] == b:
                pause_before = i == 0 or words[i]["start"] - words[i - 1]["end"] > 0.15 or words[i - 1]["text"].endswith(",")
                comma_after = words[i + 1]["text"].endswith(",")
                if pause_before and comma_after:
                    marks[i] = marks[i + 1] = "phrase"
    # stutters: immediate repeats of 1–2 words ("I I", "it's it's", "we we built")
    for n in (2, 1):
        for i in range(len(toks) - 2 * n + 1):
            if toks[i:i + n] == toks[i + n:i + 2 * n] and all(toks[i:i + n]) and not any(j in marks for j in range(i, i + n)):
                for j in range(i, i + n):
                    marks[j] = "stutter"
    # retakes: the same opening spoken again soon after → the earlier attempt (up to the restart)
    # is a false start. Keep the last take. Two tiers so ordinary repeated phrases survive:
    #   short false start: 3-gram repeats within 15 words / 8 s   ("so what I — so what I built was")
    #   whole-line retake: 6-gram repeats within 45 words / 30 s  (re-reading a script line)
    tiers = [(min_ngram, 15, 8.0), (6, 45, min(30.0, retake_window_s * 1.5))]
    for n, max_words, max_s in tiers:
        i = 0
        while i <= len(toks) - n:
            gram = toks[i:i + n]
            restart = None
            if all(gram) and not any(k in marks for k in range(i, i + n)):
                for j in range(i + 1, min(len(toks) - n + 1, i + max_words + 1)):
                    if words[j]["start"] - words[i]["start"] > max_s:
                        break
                    if toks[j:j + n] == gram:
                        restart = j
            if restart is not None:
                for k in range(i, restart):
                    marks.setdefault(k, "retake")
                i = restart
            else:
                i += 1

    return [{"i": i, "text": words[i]["text"], "start": words[i]["start"], "end": words[i]["end"], "kind": k}
            for i, k in sorted(marks.items())]


def detect(project: Project, force: bool = False) -> list[dict]:
    tr = project.work / "transcript.json"
    out = project.work / "fillers.json"
    if not force and is_fresh(out, [tr]):
        return load_json(out)
    marks = find_fillers(load_json(tr)["words"])
    save_json(out, marks)
    kinds = {}
    for m in marks:
        kinds[m["kind"]] = kinds.get(m["kind"], 0) + 1
    log.info(f"marked {len(marks)} words: {kinds or 'none'}")
    return marks


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args(argv)
    detect(Project(a.project), a.force)


if __name__ == "__main__":
    main()
