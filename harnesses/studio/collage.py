"""Collage layouts: images around (or behind) you while you talk — a technique the SCRIPT calls for, beat by beat.

  python -m harnesses.studio.collage <project> --from-plan     # rebuild from plan.json beats marked `collage` (after adding images)
  python -m harnesses.studio.collage <project> --theme trio-stack --images assets/broll/llm --from 2 --to 14   # by hand
  python -m harnesses.studio.collage <project> --list-themes
  python -m harnesses.studio.collage <project> --clear

Normally auto_edl builds the layout from plan.json: a beat with `collage.images` (file paths, or descriptions filled by
dropping raw/images/<beat-id>_<n>.jpg) gets a collage over exactly that beat, in the plan's `collage_theme`.
Writes edl.json → layout {theme, blocks[]}. Blocks use OUTPUT time (like graphics). One block per sentence
(≥ --min-block s); images appear in spoken order, filling empty slots first, then replacing the oldest.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import re
import shutil
from pathlib import Path

from core.common import BRAIN, STUDIO, Project, get_logger, load_json, save_json, validate
from harnesses.studio.timeline import beat_ranges, layout, total_duration

log = get_logger("collage")
THEMES = BRAIN / "video-themes"
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
VIDEO_EXT = {".mp4", ".mov", ".m4v", ".webm"}

DEFAULT_THEME = {
    "background": "#000000",
    "gap": 0,
    "slots": [],
    "presenter": {"x": 0, "y": 0, "w": 1, "h": 1, "radius": 0, "border": 0, "border_color": "#000000", "shadow": False,
                  "above_tiles": True},
    "tiles": {"radius": 0, "border": 0, "border_color": "#000000", "shadow": False, "motion": "ken_burns", "ken_burns": 1.06,
              "enter": "pop", "stagger": 0.08, "saturate": 1, "contrast": 1, "brightness": 1, "dim": 0, "scrim": 0},
    "title": {"top": 0.12, "size": 64, "font": "clean", "weight": 800, "color": "#FFFFFF", "stroke": 4, "upper": False},
    "captions_top": 0.6,
    "morph": 0.35,
}


def list_themes() -> list[str]:
    return sorted(p.parent.name for p in THEMES.glob("*/theme.json"))


def load_theme(name: str) -> dict:
    p = THEMES / name / "theme.json"
    if not p.exists():
        raise FileNotFoundError(f"unknown video theme '{name}' (have: {', '.join(list_themes()) or 'none'})")
    theme = copy.deepcopy(DEFAULT_THEME)
    for k, v in load_json(p).items():
        theme[k] = {**theme[k], **v} if isinstance(theme.get(k), dict) else v
    return theme


def tile_file(tile) -> str | None:
    return tile if isinstance(tile, str) else (tile or {}).get("file")


def is_video(path: str) -> bool:
    return Path(path).suffix.lower() in VIDEO_EXT


def stage(project: Project, rel: str) -> str:
    """Remotion serves the project root only: copy studio files (assets/…) into work/layout/. Returns a project-relative path."""
    if (project.root / rel).is_file():
        return rel
    src = STUDIO / rel
    if not src.is_file():
        raise FileNotFoundError(f"collage tile not found: {rel} (looked in the project and the studio root)")
    dst = project.work / "layout" / f"{hashlib.sha1(rel.encode()).hexdigest()[:8]}_{src.name}"
    if not dst.exists() or dst.stat().st_mtime < src.stat().st_mtime:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    return str(dst.relative_to(project.root))


def build_layout_props(project: Project, layout: dict | None) -> dict | None:
    if not layout or not layout.get("blocks"):
        return None
    blocks = []
    for b in sorted(layout["blocks"], key=lambda b: b["start"]):
        tiles = []
        for t in b["tiles"]:
            f = tile_file(t)
            if not f:
                tiles.append(None)
                continue
            d = t if isinstance(t, dict) else {}
            tiles.append({"file": stage(project, f), "video": is_video(f), "in": d.get("in", 0),
                          "fx": d.get("focus_x", 0.5), "fy": d.get("focus_y", 0.5)})
        blocks.append({"start": b["start"], "end": b["end"], "tiles": tiles})
    return {"theme": load_theme(layout["theme"]), "blocks": blocks}


def check_layout(edl: dict) -> list[str]:
    lay = edl.get("layout")
    if not lay:
        return []
    try:
        slots = len(load_theme(lay["theme"])["slots"])
    except FileNotFoundError as e:
        return [f"layout: {e}"]
    errs = []
    total = total_duration(edl["segments"], edl["output"]["fps"])
    prev_end = -1.0
    for i, b in enumerate(sorted(lay["blocks"], key=lambda b: b["start"])):
        if b["end"] <= b["start"]:
            errs.append(f"layout.blocks[{i}]: end must be > start")
        if b["start"] < prev_end - 1e-3:
            errs.append(f"layout.blocks[{i}]: overlaps the previous block")
        if b["start"] > total + 0.5:
            errs.append(f"layout.blocks[{i}] starts after the end of the cut ({b['start']:.2f}s > {total:.2f}s)")
        if len(b["tiles"]) > slots:
            errs.append(f"layout.blocks[{i}]: {len(b['tiles'])} tiles but theme '{lay['theme']}' has {slots} slots")
        prev_end = b["end"]
    return errs


# ---- auto-builder -------------------------------------------------------------------------------------------------

def find_images(project: Project, folder: str | None) -> list[str]:
    dirs = [Path(folder)] if folder else [project.raw / "images", project.raw / "broll"]
    out = []
    for d in dirs:
        d = d if d.is_absolute() else (project.root / d if (project.root / d).exists() else STUDIO / d)
        for f in sorted(d.rglob("*")) if d.is_dir() else []:
            if f.suffix.lower() in IMAGE_EXT | VIDEO_EXT and not f.name.startswith("."):
                base = project.root if f.is_relative_to(project.root) else STUDIO
                out.append(str(f.relative_to(base)))
    return out


def sentence_cuts(words: list[dict], t0: float, t1: float, min_block: float) -> list[float]:
    """Block boundaries: after sentence ends (or long pauses) inside [t0, t1], at least min_block apart."""
    cuts, last = [t0], t0
    for i, w in enumerate(words):
        nxt = words[i + 1] if i + 1 < len(words) else None
        end_of_thought = w["text"].rstrip().endswith((".", "!", "?")) or (nxt and nxt["start"] - w["end"] > 0.45)
        at = nxt["start"] if nxt else w["end"]
        if end_of_thought and t0 < at < t1 - min_block * 0.6 and at - last >= min_block:
            cuts.append(round(at, 3))
            last = at
    if len(cuts) == 1:  # no transcript: even swaps
        n = max(1, int((t1 - t0) // max(min_block, 2.5)))
        cuts = [round(t0 + k * (t1 - t0) / n, 3) for k in range(n)]
    return cuts + [round(t1, 3)]


REVEAL_MIN = 0.9  # s — shortest time an image gets before the next one lands


def word_cuts(words: list[dict], t0: float, t1: float, n: int) -> list[float]:
    """n blocks over [t0, t1], each boundary snapped to the nearest word start."""
    starts = [w["start"] for w in words if t0 < w["start"] < t1]
    cuts = [t0]
    for k in range(1, n):
        target = t0 + k * (t1 - t0) / n
        at = min(starts, key=lambda x: abs(x - target)) if starts else target
        if at - cuts[-1] >= REVEAL_MIN * 0.7 and t1 - at >= REVEAL_MIN * 0.7:
            cuts.append(round(at, 3))
    return cuts + [round(t1, 3)]


def make_blocks(images: list[str], slots: int, cuts: list[float]) -> list[dict]:
    """Spread the images over the blocks in spoken order: image i appears at block ⌊i·n/m⌋, filling empty
    slots first, then replacing the oldest tile. All images in one block = the full grid at once."""
    n, m = len(cuts) - 1, len(images)
    tiles: list[str | None] = [None] * slots
    age = list(range(slots))  # slot fill order; front = oldest
    blocks = []
    for k, (a, b) in enumerate(zip(cuts, cuts[1:])):
        for i in (i for i in range(m) if i * n // m == k):
            slot = tiles.index(None) if None in tiles else age[0]
            tiles[slot] = images[i]
            age.remove(slot)
            age.append(slot)
        blocks.append({"start": a, "end": b, "tiles": list(tiles)})
    return blocks


def beat_images(project: Project, beat_id: str, wants: list[str]) -> tuple[list[str], list[str]]:
    """A want is a file path, or a description the owner fills by dropping raw/images/<beat-id>_<n>.jpg.
    Returns (files in spoken order, descriptions still missing)."""
    dropped = [f for f in find_images(project, None) if re.match(rf"{re.escape(beat_id)}[_-]", Path(f).name)]
    dropped.sort(key=lambda f: [int(x) if x.isdigit() else x for x in re.split(r"(\d+)", Path(f).name)])
    files, missing = [], []
    for w in wants:
        if Path(w).suffix.lower() in IMAGE_EXT | VIDEO_EXT and ((project.root / w).is_file() or (STUDIO / w).is_file()):
            files.append(w)
        elif dropped:
            files.append(dropped.pop(0))
        else:
            missing.append(w)
    return files + dropped, missing


def layout_from_plan(project: Project, plan: dict, beats: dict, words: list[dict],
                     min_block: float = 1.6) -> tuple[dict | None, list[str]]:
    """Collage blocks only over the beats the script marked with `collage`; images swap as the lines are said."""
    marked = [b for b in plan.get("beats", []) if b.get("collage")]
    if not marked:
        return None, []
    theme = plan.get("collage_theme") or "quad-collage"
    slots = len(load_theme(theme)["slots"])
    blocks, notes = [], []
    for b in marked:
        if b["id"] not in beats:
            notes.append(f"collage beat '{b['id']}' is not in the cut")
            continue
        files, missing = beat_images(project, b["id"], b["collage"]["images"])
        if missing:
            notes.append(f"collage beat '{b['id']}': {len(missing)} image(s) to gather → raw/images/{b['id']}_<n>.jpg: "
                         + "; ".join(missing))
        if not files:
            continue
        if b.get("graphic"):
            notes.append(f"collage beat '{b['id']}' also has a graphic — they fight for the frame; keep one")
        a, e = beats[b["id"]]
        bw = [w for w in words if a <= w["start"] < e]
        cuts = sentence_cuts(bw, a, e, min_block)
        want = min(len(files), max(1, int((e - a) // REVEAL_MIN)))
        if len(cuts) - 1 < want:  # fewer sentences than images: land each image on a word, evenly through the beat
            cuts = word_cuts(bw, a, e, want)
        blocks += make_blocks(files, slots, cuts)
    return ({"theme": theme, "blocks": blocks} if blocks else None), notes


def apply(project: Project, theme: str, images: list[str], t0: float | None, t1: float | None,
          min_block: float, hold_hook: bool, force: bool) -> dict:
    edl_p = project.root / "edl.json"
    edl = load_json(edl_p)
    slots = len(load_theme(theme)["slots"])
    if not images:
        raise SystemExit("no images found — drop them in raw/images/ (or pass --images DIR)")
    total = total_duration(edl["segments"], edl["output"]["fps"])
    t0 = max(0.0, t0 or 0.0)
    t1 = min(total, t1 if t1 is not None else total)
    if t1 - t0 < 1.0:
        raise SystemExit(f"collage range too short: {t0:.2f}–{t1:.2f}s")
    cuts = sentence_cuts([w for w in edl["captions"]["words"] if t0 <= w["start"] < t1], t0, t1, min_block)
    new = make_blocks(images, slots, cuts)

    old = edl.get("layout")
    if old and old["theme"] != theme and not force:
        raise SystemExit(f"edl.json already uses theme '{old['theme']}' — pass --force to switch the whole layout")
    keep = [] if force or not old else [b for b in old["blocks"] if b["end"] <= t0 or b["start"] >= t1]
    edl["layout"] = {"theme": theme, "blocks": sorted(keep + new, key=lambda b: b["start"])}

    if hold_hook:  # keep the hook on screen as the collage title
        for g in edl["graphics"]:
            if g["type"] == "hook_text" and g["start"] <= t0 + 0.05 and g["end"] < t1:
                g["end"] = round(t1, 3)
    edl.setdefault("notes", []).append(
        f"collage: {theme}, {len(new)} blocks {t0:.1f}–{t1:.1f}s from {len(images)} images")
    validate(edl, "edl")
    errs = check_layout(edl)
    if errs:
        raise SystemExit("\n".join(errs))
    save_json(edl_p, edl)
    log.info(f"layout → {theme}: {len(new)} blocks over {t0:.1f}–{t1:.1f}s ({len(images)} images, {slots} slots)")
    return edl


def from_plan(project: Project, min_block: float) -> dict:
    plan = project.plan()
    if not plan:
        raise SystemExit("no plan.json — use --theme/--images/--from/--to instead")
    edl = load_json(project.root / "edl.json")
    beats = beat_ranges(layout(edl["segments"], edl["output"]["fps"]))
    lay, notes = layout_from_plan(project, plan, beats, edl["captions"]["words"], min_block)
    for n in notes:
        log.info(n)
    if not lay:
        raise SystemExit("no collage blocks: no beat has a `collage` with images found yet")
    edl["layout"] = lay
    validate(edl, "edl")
    errs = check_layout(edl)
    if errs:
        raise SystemExit("\n".join(errs))
    save_json(project.root / "edl.json", edl)
    log.info(f"layout → {lay['theme']}: {len(lay['blocks'])} blocks from the plan")
    return edl


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("project", nargs="?")
    ap.add_argument("--theme", default="quad-collage")
    ap.add_argument("--images", help="folder of images/clips (project-relative or studio-relative); default raw/images + raw/broll")
    ap.add_argument("--from", dest="t0", type=float, help="output-time start (s), default 0")
    ap.add_argument("--to", dest="t1", type=float, help="output-time end (s), default the end of the cut")
    ap.add_argument("--min-block", type=float, default=1.6, help="shortest time between tile swaps (s)")
    ap.add_argument("--hold-hook", action="store_true", help="keep the hook text on screen over the whole collage (as its title)")
    ap.add_argument("--from-plan", action="store_true", help="rebuild the layout from plan.json beats marked `collage`")
    ap.add_argument("--force", action="store_true", help="replace the whole existing layout")
    ap.add_argument("--clear", action="store_true", help="remove the layout (back to plain full-frame)")
    ap.add_argument("--list-themes", action="store_true")
    a = ap.parse_args(argv)
    if a.list_themes:
        for n in list_themes():
            print(f"{n:<16} {load_json(THEMES / n / 'theme.json').get('description', '')}")
        return
    if not a.project:
        ap.error("project is required")
    proj = Project(a.project)
    if a.clear:
        edl = load_json(proj.root / "edl.json")
        edl.pop("layout", None)
        save_json(proj.root / "edl.json", edl)
        log.info("layout removed")
        return
    if a.from_plan:
        return from_plan(proj, a.min_block)
    apply(proj, a.theme, find_images(proj, a.images), a.t0, a.t1, a.min_block, a.hold_hook, a.force)


if __name__ == "__main__":
    main()
