"""Validate contract files against core/schemas/.

  python -m harnesses.studio.validate <file.json> [--schema plan|edl|carousel]
  python -m harnesses.studio.validate <project>          # validates plan.json / edl.json / carousel.json if present
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import jsonschema

from core.common import Project, load_json, validate
from harnesses.studio.collage import check_layout

KNOWN = {"plan.json": "plan", "edl.json": "edl", "carousel.json": "carousel"}


def check_edl_semantics(edl: dict) -> list[str]:
    """Checks JSON Schema can't express."""
    errs = []
    for i, s in enumerate(edl["segments"]):
        if s["out"] <= s["in"]:
            errs.append(f"segments[{i}]: out ({s['out']}) must be > in ({s['in']})")
        if s["src"] not in edl["sources"] or not edl["sources"][s["src"]]:
            errs.append(f"segments[{i}]: unknown src '{s['src']}'")
    total = sum(s["out"] - s["in"] for s in edl["segments"])
    for i, w in enumerate(edl["captions"]["words"]):
        if w["end"] < w["start"]:
            errs.append(f"captions.words[{i}] ends before it starts")
        if w["start"] > total + 0.5:
            errs.append(f"captions.words[{i}] starts after the end of the cut ({w['start']:.2f}s > {total:.2f}s)")
    for i, g in enumerate(edl["graphics"]):
        if g["end"] <= g["start"]:
            errs.append(f"graphics[{i}]: end must be > start")
    return errs + check_layout(edl)


def validate_file(path: Path, schema: str | None = None) -> list[str]:
    schema = schema or KNOWN.get(path.name)
    if not schema:
        return [f"{path}: can't infer schema; pass --schema"]
    data = load_json(path)
    try:
        validate(data, schema)
    except jsonschema.ValidationError as e:
        loc = "/".join(map(str, e.absolute_path)) or "(root)"
        return [f"{path.name}: {loc}: {e.message}"]
    if schema == "edl":
        return [f"{path.name}: {m}" for m in check_edl_semantics(data)]
    if schema == "plan" and data.get("chosen_hook") is not None and data["chosen_hook"] >= len(data["hooks"]):
        return [f"{path.name}: chosen_hook out of range"]
    return []


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("target")
    ap.add_argument("--schema", choices=["plan", "edl", "carousel"])
    a = ap.parse_args(argv)
    t = Path(a.target)
    files = [t] if t.suffix == ".json" else [f for f in (Project(a.target).root / n for n in KNOWN) if f.exists()]
    if not files:
        print("nothing to validate")
        return 1
    errs = [e for f in files for e in validate_file(f, a.schema)]
    for f in files:
        if not any(e.startswith(f.name) for e in errs):
            print(f"✓ {f.name}")
    for e in errs:
        print(f"✗ {e}")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
