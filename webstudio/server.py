"""Web Studio — a local browser UI for seeing and editing projects.

  ./studio web            → http://127.0.0.1:4545  (local only)

Standard library only. The UI edits the same contracts the agents use (edl.json, carousel.json),
so you and Claude can work on the same project. Heavy work (proxy, render) runs as background jobs
through the normal pipeline tools.
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import os
import re
import subprocess
import sys
import threading
import time
import uuid
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # allow `python webstudio/server.py`
os.chdir(Path(__file__).resolve().parent.parent)

from pipeline.common import ASSETS, BRAIN, PILLARS, PROJECTS, STUDIO, Project, load_json, save_json

STATIC = Path(__file__).with_name("static")
PY = str(STUDIO / ".venv" / "bin" / "python")
ID_RE = re.compile(r"^[A-Za-z0-9_.-]+$")

# ------------------------------------------------------------------ jobs

JOBS: dict[str, dict] = {}
_LOCK = threading.Lock()


def start_job(kind: str, project: str | None, cmd: list[str]) -> dict:
    job = {"id": uuid.uuid4().hex[:10], "kind": kind, "project": project, "cmd": cmd, "status": "running",
           "log": "", "started": time.time(), "ended": None, "result": None}
    with _LOCK:
        # one job of a kind per project at a time
        for j in JOBS.values():
            if j["project"] == project and j["kind"] == kind and j["status"] == "running":
                return j
        JOBS[job["id"]] = job

    def run():
        proc = subprocess.Popen(cmd, cwd=STUDIO, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in proc.stdout:
            if line.startswith("error: unsupported deferred-static-alloca"):  # MLX Metal noise on macOS 26.0
                continue
            job["log"] += line
        proc.wait()
        job["status"] = "done" if proc.returncode == 0 else "failed"
        job["ended"] = time.time()
        m = re.search(r'"project":\s*"([^"]+)"', job["log"])
        if m:
            job["result"] = {"project": m.group(1)}

    threading.Thread(target=run, daemon=True).start()
    return job


def ensure_proxy(proj: Project) -> dict | None:
    """Light 540-px H.264 proxy of the camera, with the cleaned/synced voice as its audio, + a waveform."""
    media_p = proj.work / "media.json"
    if not media_p.exists():
        return None
    proxy, wave = proj.work / "proxy.mp4", proj.work / "waveform.png"
    if proxy.exists() and wave.exists():
        return None
    cam = proj.root / load_json(media_p)["cam"]["path"]
    voice = proj.work / "voice.wav"
    audio_in = ["-i", str(voice)] if voice.exists() else []
    amap = ["-map", "1:a"] if voice.exists() else ["-map", "0:a?"]
    script = (
        f"ffmpeg -hide_banner -loglevel error -y -i {sh(cam)} {' '.join(sh(a) for a in audio_in)} -map 0:v {' '.join(amap)} "
        f"-vf scale=540:-2 -c:v h264_videotoolbox -b:v 2500k -g 15 -c:a aac -b:a 128k -movflags +faststart {sh(proxy)}"
        f" && ffmpeg -hide_banner -loglevel error -y -i {sh(voice if voice.exists() else cam)} -filter_complex "
        f"\"aformat=channel_layouts=mono,showwavespic=s=3000x120:colors=#8b93a7\" -frames:v 1 {sh(wave)}"
    )
    return start_job("proxy", proj.id, ["/bin/sh", "-c", script])


def sh(p) -> str:
    return "'" + str(p).replace("'", "'\\''") + "'"


# ------------------------------------------------------------------ project data

def _read(path: Path):
    return load_json(path) if path.exists() else None


def project_summary(p: Path) -> dict:
    proj = Project(p)
    plan, edl, car = _read(p / "plan.json"), _read(p / "edl.json"), _read(p / "carousel.json")
    kind = "carousel" if car else "reel"
    thumb = next((str(f.relative_to(p)) for f in (p / "out" / "cover.png", p / "out" / "slides" / "01.png",
                                                  p / "work" / "cover_frame.jpg") if f.exists()), None)
    if not thumb:
        frames = sorted((p / "work" / "frames").glob("t*.jpg"))
        thumb = str(frames[min(1, len(frames) - 1)].relative_to(p)) if frames else None
    pillar = (plan or {}).get("pillar") or next((k for k, v in {"build-in-public": "_bip-", "ai-explained": "_aiex-", "resources": "_res-"}.items() if v in p.name), None)
    outs = [n for n in ("final.mp4", "cover.png", "project.fcpxml", "carousel.pdf") if (p / "out" / n).exists()]
    wm = STUDIO / "memory" / "working" / f"{p.name}.md"
    status = "working" if wm.exists() else ("done" if outs else "draft")
    return {"id": p.name, "kind": kind, "pillar": pillar, "thumb": thumb, "outputs": outs, "status": status,
            "has_plan": bool(plan), "has_edl": bool(edl), "title": (plan or {}).get("caption_draft", "")[:80] if plan else
            ((car or {}).get("slides", [{}])[0].get("title", "") if car else ""),
            "mtime": max((f.stat().st_mtime for f in p.glob("*.json")), default=p.stat().st_mtime)}


def project_detail(pid: str) -> dict:
    from pipeline.auto_edl import speech_words

    proj = Project(pid)
    w = proj.work
    job = ensure_proxy(proj)
    tr = _read(w / "transcript.json")
    detail = {
        "id": proj.id, "summary": project_summary(proj.root),
        "plan": _read(proj.root / "plan.json"), "edl": _read(proj.root / "edl.json"),
        "carousel": _read(proj.root / "carousel.json"), "media": _read(w / "media.json"),
        "words": speech_words(proj) if tr else [], "transcriber": (tr or {}).get("backend"),
        "fillers": _read(w / "fillers.json") or [], "crop": _read(w / "crop_path.json"),
        "qc": _read(w / "qc.json"), "alignment": _read(w / "alignment.json"),
        "proxy": "work/proxy.mp4" if (w / "proxy.mp4").exists() else None,
        "waveform": "work/waveform.png" if (w / "waveform.png").exists() else None,
        "preview": "work/preview.mp4" if (w / "preview.mp4").exists() else None,
        "final": "out/final.mp4" if (proj.out / "final.mp4").exists() else None,
        "slides": sorted(str(f.relative_to(proj.root)) for f in (proj.out / "slides").glob("*.png")),
        "script": (proj.root / "script.md").read_text() if (proj.root / "script.md").exists() else None,
        "critic": (proj.root / "critic-report.md").read_text() if (proj.root / "critic-report.md").exists() else None,
        "broll": [str(f.relative_to(proj.root)) for f in sorted((proj.raw / "broll").glob("*"))] if (proj.raw / "broll").exists() else [],
        "jobs": [j for j in JOBS.values() if j["project"] == proj.id and j["status"] == "running"],
    }
    if job:
        detail["jobs"].append(job)
    return detail


def save_edl(pid: str, edl: dict, refresh: bool) -> dict:
    from pipeline.auto_edl import refresh_captions
    from pipeline.common import validate
    from pipeline.validate import check_edl_semantics

    proj = Project(pid)
    for s in edl["segments"]:  # tidy numbers from the UI
        s["in"], s["out"] = round(float(s["in"]), 3), round(float(s["out"]), 3)
    validate(edl, "edl")
    save_json(proj.root / "edl.json", edl)
    if refresh and (proj.work / "transcript.json").exists():
        edl = refresh_captions(proj)
    errs = check_edl_semantics(edl)
    return {"edl": edl, "warnings": errs}


def list_assets() -> dict:
    audio = {".mp3", ".wav", ".m4a", ".aac", ".flac"}
    rel = lambda d: sorted(str(f.relative_to(STUDIO)) for f in (ASSETS / d).rglob("*") if f.suffix.lower() in audio)  # noqa: E731
    return {"music": rel("music"), "sfx": rel("sfx"),
            "themes": sorted(p.name for p in (BRAIN / "carousel-themes").iterdir() if (p / "theme.json").exists())}


# ------------------------------------------------------------------ HTTP

class Handler(BaseHTTPRequestHandler):
    server_version = "WebStudio/1.0"

    def log_message(self, fmt, *args):  # quiet
        if "/api/jobs" not in (args[0] if args else ""):
            sys.stderr.write("[web] " + fmt % args + "\n")

    # -- helpers
    def _json(self, data, status=200):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _err(self, msg, status=400):
        self._json({"error": msg}, status)

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(n) or b"{}")

    def _file(self, path: Path, content_type: str | None = None):
        if not path.exists() or not path.is_file():
            return self._err("not found", 404)
        size = path.stat().st_size
        ctype = content_type or mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        rng = self.headers.get("Range")
        start, end = 0, size - 1
        if rng and (m := re.match(r"bytes=(\d*)-(\d*)", rng)):
            if m.group(1):
                start = int(m.group(1))
                end = int(m.group(2)) if m.group(2) else size - 1
            else:
                start = size - int(m.group(2))
            end = min(end, size - 1)
            self.send_response(HTTPStatus.PARTIAL_CONTENT)
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        else:
            self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(end - start + 1))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        with path.open("rb") as f:
            f.seek(start)
            left = end - start + 1
            while left > 0:
                chunk = f.read(min(1 << 20, left))
                if not chunk:
                    break
                try:
                    self.wfile.write(chunk)
                except (BrokenPipeError, ConnectionResetError):
                    return
                left -= len(chunk)

    def _project(self, pid: str) -> Project | None:
        if not ID_RE.match(pid) or not (PROJECTS / pid).is_dir():
            self._err("unknown project", 404)
            return None
        return Project(pid)

    # -- routes
    def do_GET(self):
        url = urlparse(self.path)
        parts = [unquote(x) for x in url.path.strip("/").split("/") if x]
        try:
            if not parts or parts[0] in ("index.html",):
                return self._file(STATIC / "index.html", "text/html; charset=utf-8")
            if parts[0] == "static" and len(parts) == 2 and ID_RE.match(parts[1]):
                return self._file(STATIC / parts[1])
            if parts[0] == "media" and len(parts) >= 3:
                proj = self._project(parts[1])
                if not proj:
                    return
                f = (proj.root / "/".join(parts[2:])).resolve()
                if proj.root not in f.parents:
                    return self._err("forbidden", 403)
                return self._file(f)
            if parts[0] == "asset" and len(parts) >= 2:  # studio-relative files (music/sfx previews)
                f = (STUDIO / "/".join(parts[1:])).resolve()
                if not any(r in f.parents for r in (ASSETS.resolve(), (STUDIO / "tests" / "media").resolve())):
                    return self._err("forbidden", 403)
                return self._file(f)
            if parts[:2] == ["api", "projects"] and len(parts) == 2:
                rows = [project_summary(p) for p in PROJECTS.iterdir() if p.is_dir() and not p.name.startswith(".")] if PROJECTS.exists() else []
                return self._json(sorted(rows, key=lambda r: r["mtime"], reverse=True))
            if parts[:2] == ["api", "projects"] and len(parts) == 3:
                if self._project(parts[2]):
                    return self._json(project_detail(parts[2]))
                return
            if parts[:2] == ["api", "projects"] and len(parts) == 6 and parts[3:5] == ["carousel", "slide"]:
                proj = self._project(parts[2])
                if not proj:
                    return
                return self._slide_html(proj, int(parts[5]), parse_qs(url.query))
            if parts == ["api", "assets"]:
                return self._json(list_assets())
            if parts[:2] == ["api", "jobs"] and len(parts) == 3:
                j = JOBS.get(parts[2])
                return self._json(j) if j else self._err("unknown job", 404)
            return self._err("not found", 404)
        except Exception as e:  # noqa: BLE001
            return self._err(f"{type(e).__name__}: {e}", 500)

    def _slide_html(self, proj: Project, n: int, q: dict):
        from carousel.render import THEMES, build_html

        car = _read(proj.root / "carousel.json")
        if not car:
            return self._err("no carousel.json", 404)
        size = car.get("size", "1080x1350")
        w, h = map(int, size.split("x"))
        theme = load_json(THEMES / car["theme"] / "theme.json")
        pages = build_html(car, theme, proj, w, h)
        if not 1 <= n <= len(pages):
            return self._err("no such slide", 404)
        body = pages[n - 1].encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_PUT(self):
        parts = [unquote(x) for x in urlparse(self.path).path.strip("/").split("/") if x]
        q = parse_qs(urlparse(self.path).query)
        try:
            if parts[:2] == ["api", "projects"] and len(parts) == 4:
                proj = self._project(parts[2])
                if not proj:
                    return
                data = self._body()
                if parts[3] == "edl":
                    return self._json(save_edl(proj.id, data, q.get("refresh", ["1"])[0] == "1"))
                if parts[3] == "carousel":
                    from pipeline.common import validate
                    validate(data, "carousel")
                    save_json(proj.root / "carousel.json", data)
                    return self._json({"ok": True})
            return self._err("not found", 404)
        except Exception as e:  # noqa: BLE001  (schema errors come back to the UI)
            return self._err(f"{type(e).__name__}: {getattr(e, 'message', e)}", 400)

    def do_POST(self):
        parts = [unquote(x) for x in urlparse(self.path).path.strip("/").split("/") if x]
        try:
            body = self._body()
            if parts == ["api", "import"]:
                video = Path(body.get("video", "")).expanduser()
                if not video.is_file():
                    return self._err(f"video not found: {video}")
                pillar = body.get("pillar") or "build-in-public"
                if pillar not in PILLARS:
                    return self._err("bad pillar")
                cmd = [PY, "-m", "pipeline.edit", "prepare", str(video), "--pillar", pillar]
                if body.get("slug"):
                    cmd += ["--slug", re.sub(r"[^a-zA-Z0-9-]+", "-", body["slug"])]
                if body.get("audio"):
                    audio = Path(body["audio"]).expanduser()
                    if not audio.is_file():
                        return self._err(f"audio not found: {audio}")
                    cmd += ["--audio", str(audio)]
                return self._json(start_job("import", None, cmd))
            if parts == ["api", "new-carousel"]:
                slug = re.sub(r"[^a-zA-Z0-9-]+", "-", body.get("slug") or "resources").strip("-")
                res = subprocess.run([PY, "-m", "pipeline.new_project", "resources", slug, "--task", "carousel"],
                                     cwd=STUDIO, capture_output=True, text=True, check=True)
                pid = res.stdout.strip().splitlines()[-1]
                template = load_json(STUDIO / "tests" / "fixtures" / "carousel.json")
                template.update(project_id=pid, theme=body.get("theme") or "clean-light")
                save_json(PROJECTS / pid / "carousel.json", template)
                return self._json({"project": pid})
            if parts[:2] == ["api", "projects"] and len(parts) == 4:
                proj = self._project(parts[2])
                if not proj:
                    return
                action = parts[3]
                if action == "render":
                    mode = body.get("mode", "preview")
                    if mode not in ("preview", "final"):
                        return self._err("mode must be preview or final")
                    return self._json(start_job(f"render-{mode}", proj.id, [PY, "-m", "pipeline.edit", mode, proj.id]))
                if action == "carousel-render":
                    return self._json(start_job("carousel", proj.id, [PY, "-m", "carousel.render", proj.id]))
                if action == "verify":
                    return self._json(start_job("verify", proj.id, [PY, "-m", "pipeline.verify_links", proj.id]))
                if action == "auto-edl":
                    return self._json(start_job("auto-edl", proj.id, [PY, "-m", "pipeline.auto_edl", proj.id, "--force"]))
                if action == "reveal":
                    subprocess.run(["open", "-R", str(proj.out if proj.out.exists() else proj.root)])
                    return self._json({"ok": True})
            return self._err("not found", 404)
        except subprocess.CalledProcessError as e:
            return self._err(e.stderr or str(e), 500)
        except Exception as e:  # noqa: BLE001
            return self._err(f"{type(e).__name__}: {e}", 500)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=4545)
    ap.add_argument("--no-open", action="store_true")
    a = ap.parse_args(argv)
    PROJECTS.mkdir(exist_ok=True)
    srv = ThreadingHTTPServer(("127.0.0.1", a.port), Handler)
    url = f"http://127.0.0.1:{a.port}/"
    print(f"Web Studio → {url}  (Ctrl+C to stop)")
    if not a.no_open:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
