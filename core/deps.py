"""Dependency doctor: what's installed, which backend each interface will use, how to add the rest.

  python -m core.deps           # table
  python -m core.deps --json    # for agents
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import subprocess
from pathlib import Path

from core.common import STUDIO
from core.providers import config

CORE_MODULES = {
    "numpy": "numpy", "scipy": "scipy", "jsonschema": "jsonschema", "rapidfuzz": "rapidfuzz",
    "opentimelineio": "opentimelineio",
}
CHROME = Path("/Applications/Google Chrome.app")


def _mod(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def _fcpxml() -> bool:
    if not _mod("opentimelineio"):
        return False
    import opentimelineio as otio
    return "fcpx_xml" in otio.adapters.available_adapter_names()


def _ffmpeg_ok() -> bool:
    if not shutil.which("ffmpeg"):
        return False
    return "loudnorm" in subprocess.run(["ffmpeg", "-hide_banner", "-filters"], capture_output=True, text=True).stdout


def report(project_root: Path | None = None) -> dict:
    from core.providers import face, transcription

    core_missing = [k for k, m in CORE_MODULES.items() if not _mod(m)]
    items = [
        {"area": "system", "name": "ffmpeg", "ok": _ffmpeg_ok(), "hint": "brew install ffmpeg"},
        {"area": "system", "name": "node", "ok": bool(shutil.which("node")), "hint": "brew install node"},
        {"area": "system", "name": "remotion", "ok": (STUDIO / "harnesses/studio/remotion" / "node_modules" / "remotion").exists(), "hint": "cd harnesses/studio/remotion && npm install"},
        {"area": "system", "name": "chrome (carousel rendering)", "ok": CHROME.exists(),
         "hint": "install Google Chrome (used headless for slides)"},
        {"area": "python", "name": "core packages", "ok": not core_missing,
         "hint": f"missing {', '.join(core_missing)} → uv pip install --python .venv/bin/python -r requirements/core.txt"},
        {"area": "python", "name": "fcpxml export adapter", "ok": _fcpxml(), "hint": "uv pip install otio-fcpx-xml-adapter"},
    ]
    cfg = config()
    tr_rows = []
    for name in transcription.AUTO_ORDER:
        ok, why = transcription.BACKENDS[name].available(project_root)
        tr_rows.append({"name": name, "ok": ok, "status": why})
    face_rows = []
    for name in face.AUTO_ORDER:
        ok, why = face.BACKENDS[name].available()
        face_rows.append({"name": name, "ok": ok, "status": why})
    pick = lambda rows, want, order: want if want != "auto" else next(r["name"] for r in rows if r["ok"])  # noqa: E731
    return {
        "ready": all(i["ok"] for i in items),
        "items": items,
        "transcriber": {"configured": cfg["transcriber"], "will_use": pick(tr_rows, cfg["transcriber"], transcription.AUTO_ORDER), "backends": tr_rows},
        "face_detector": {"configured": cfg["face_detector"], "will_use": pick(face_rows, cfg["face_detector"], face.AUTO_ORDER), "backends": face_rows},
        "config_file": str((STUDIO / "studio.json").relative_to(STUDIO)),
        "creator_os": creator_os(),
    }


def creator_os() -> dict:
    """Database, accounts and metrics providers — informational, never blocks 'ready'."""
    from core import accounts, db
    from harnesses.hq import providers

    con = db.connect()
    rows = {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in ("creators", "posts", "insights", "drafts")}
    accs = accounts.sync(con)
    return {"database": str(db.db_path()), "rows": rows, "accounts": accs,
            "metrics": {p: providers.configured(p) for p in sorted({a["platform"] for a in accs})}}


def print_report(r: dict) -> None:
    mark = lambda ok: "\033[32m✓\033[0m" if ok else "\033[31m✗\033[0m"  # noqa: E731
    print("Studio dependencies\n")
    for i in r["items"]:
        print(f"  {mark(i['ok'])} {i['name']:<30}" + ("" if i["ok"] else f"  {i['hint']}"))
    for key, title in (("transcriber", "Transcriber"), ("face_detector", "Face detector")):
        sec = r[key]
        print(f"\n{title} — configured: {sec['configured']} → using: \033[1m{sec['will_use']}\033[0m")
        for b in sec["backends"]:
            print(f"  {mark(b['ok'])} {b['name']:<14} {b['status']}")
    c = r["creator_os"]
    print(f"\ncreator-os — {c['database']}")
    print("  " + " · ".join(f"{n} {k}" for k, n in c["rows"].items()))
    for a in c["accounts"]:
        print(f"  {a['id']:<28} {a['platform']:<10} @{a['handle'] or 'TODO':<18} {a['status'] or ''}  metrics: {c['metrics'].get(a['platform'])}")
    print(f"\nChange backends in {r['config_file']} (\"transcriber\": \"auto\" | \"mlx-whisper\" | \"whisper-cpp\" | \"sidecar\" | \"none\").")
    print("Studio ready." if r["ready"] else "Some required pieces are missing (✗ above).")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--project")
    a = ap.parse_args(argv)
    root = None
    if a.project:
        from core.common import Project
        root = Project(a.project).root
    r = report(root)
    print(json.dumps(r, indent=2)) if a.json else print_report(r)
    return 0 if r["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
