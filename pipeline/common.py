"""Shared helpers for every pipeline tool: paths, logging, ffmpeg, JSON, caching, validation."""
from __future__ import annotations

import datetime as _dt
import json
import logging
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Iterable

os.environ.setdefault("OPENCV_LOG_LEVEL", "ERROR")  # keep OpenCV's DNN chatter out of tool output

STUDIO = Path(__file__).resolve().parent.parent
PROJECTS = STUDIO / "projects"
BRAIN = STUDIO / "brain"
MEMORY = STUDIO / "memory"
ASSETS = STUDIO / "assets"
SCHEMAS = Path(__file__).resolve().parent / "schemas"
REMOTION = STUDIO / "remotion"

PILLARS = ("build-in-public", "ai-explained", "resources")
PILLAR_SHORT = {"build-in-public": "bip", "ai-explained": "aiex", "resources": "res"}
DEFAULT_PRESET = {"build-in-public": "bip-raw", "ai-explained": "ai-explained", "resources": "talking-head-basic"}


def get_logger(name: str) -> logging.Logger:
    log = logging.getLogger(name)
    if not log.handlers:
        h = logging.StreamHandler()
        h.setFormatter(logging.Formatter(f"[{name}] %(message)s"))
        log.addHandler(h)
        log.setLevel(logging.INFO)
    return log


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:48] or "untitled"


def today() -> str:
    return _dt.date.today().isoformat()


def now_iso() -> str:
    return _dt.datetime.now().strftime("%Y-%m-%dT%H:%M")


PROJECT_GUIDE = """# {id}

One folder per video. Drop your files here:

| Put this | In |
|---|---|
| Camera video (phone footage, one file) | `raw/` |
| Mic recording (separate mic, one file) | `raw/` |
| B-roll / screen recordings | `raw/broll/` |
| Screenshots, photos, logos | `raw/images/` |

Then run `./studio edit {id}` (or `/studio-edit {id}`). It finds the camera and mic in `raw/` on its own.
Files in `raw/` are never modified.

Everything else is made for you:
- `plan.json`, `script.md`: the plan and the script to read
- `edl.json`: the edit (also editable in `./studio web`)
- `work/`: intermediate files (transcript, cleaned audio, frames); safe to delete, it is rebuilt
- `out/`: finished files (`final.mp4`, `cover.png`, `caption.txt`, `project.fcpxml`)
"""


class Project:
    """A content project folder: projects/<project_id>/{raw/{broll,images},work,out} + README.md drop guide."""

    def __init__(self, ref: str | Path):
        p = Path(ref)
        if not p.is_absolute() and not p.exists():
            p = PROJECTS / str(ref)
        self.root = p.resolve()
        self.id = self.root.name

    @classmethod
    def create(cls, pillar: str, slug: str, date: str | None = None) -> "Project":
        pid = f"{date or today()}_{PILLAR_SHORT.get(pillar, 'x')}-{slugify(slug)}"
        return cls(PROJECTS / pid).ensure()

    @property
    def raw(self) -> Path:
        return self.root / "raw"

    @property
    def work(self) -> Path:
        return self.root / "work"

    @property
    def out(self) -> Path:
        return self.root / "out"

    def ensure(self) -> "Project":
        for d in (self.raw, self.raw / "broll", self.raw / "images", self.work, self.out):
            d.mkdir(parents=True, exist_ok=True)
        guide = self.root / "README.md"
        if not guide.exists():
            guide.write_text(PROJECT_GUIDE.format(id=self.id))
        return self

    def media(self) -> dict:
        return load_json(self.work / "media.json")

    def plan(self) -> dict | None:
        p = self.root / "plan.json"
        return load_json(p) if p.exists() else None


def load_json(path: Path) -> Any:
    return json.loads(Path(path).read_text())


def save_json(path: Path, data: Any) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    tmp.replace(path)
    return path


def is_fresh(output: Path, inputs: Iterable[Path]) -> bool:
    """True when output exists and is newer than every existing input (cache hit)."""
    output = Path(output)
    if not output.exists():
        return False
    mtime = output.stat().st_mtime
    return all(not Path(i).exists() or Path(i).stat().st_mtime <= mtime for i in inputs)


def run(cmd: list[str], log: logging.Logger | None = None, capture: bool = False) -> subprocess.CompletedProcess:
    if log:
        log.debug(" ".join(map(str, cmd)))
    res = subprocess.run([str(c) for c in cmd], capture_output=True, text=True)
    if res.returncode != 0:
        tail = (res.stderr or res.stdout or "")[-2500:]
        raise RuntimeError(f"command failed ({res.returncode}): {' '.join(map(str, cmd[:6]))} ...\n{tail}")
    return res


def ffmpeg(args: list, log: logging.Logger | None = None) -> subprocess.CompletedProcess:
    return run(["ffmpeg", "-hide_banner", "-nostdin", "-y", "-loglevel", "error", *args], log)


def ffprobe(path: Path) -> dict:
    res = run(["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(path)])
    return json.loads(res.stdout)


def video_encoder_args(quality: str = "high") -> list[str]:
    """Hardware H.264 when available, libx264 fallback."""
    enc = run(["ffmpeg", "-hide_banner", "-encoders"]).stdout
    if "h264_videotoolbox" in enc:
        rate = {"high": "16M", "preview": "4M"}[quality]
        return ["-c:v", "h264_videotoolbox", "-b:v", rate, "-pix_fmt", "yuv420p", "-allow_sw", "1"]
    crf = {"high": "18", "preview": "28"}[quality]
    return ["-c:v", "libx264", "-preset", "fast", "-crf", crf, "-pix_fmt", "yuv420p"]


def validate(data: Any, schema_name: str) -> None:
    """Raise jsonschema.ValidationError if data does not match pipeline/schemas/<schema_name>.schema.json."""
    import jsonschema

    schema = load_json(SCHEMAS / f"{schema_name}.schema.json")
    jsonschema.Draft202012Validator(schema).validate(data)


def read_glossary() -> list[str]:
    g = BRAIN / "glossary.txt"
    if not g.exists():
        return []
    return [ln.strip() for ln in g.read_text().splitlines() if ln.strip() and not ln.startswith("#")]


def require_tool(name: str) -> None:
    if not shutil.which(name):
        raise SystemExit(f"missing tool: {name} — run scripts/setup.sh")
