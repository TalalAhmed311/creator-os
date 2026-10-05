"""Design Desk renderer: carousel.json + theme pack → HTML/CSS → PNG slides (headless Chrome) + PDF.

  python -m carousel.render <project> [--size 1080x1350|1080x1080] [--pdf]

Reads projects/<id>/carousel.json (schema: pipeline/schemas/carousel.schema.json)
Writes out/slides/01.png … and out/carousel.pdf (LinkedIn), plus work/slides_html/*.html for inspection.
"""
from __future__ import annotations

import argparse
import base64
import html
import mimetypes
import random
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from pipeline.common import BRAIN, STUDIO, Project, get_logger, load_json, validate

log = get_logger("carousel")
THEMES = BRAIN / "carousel-themes"
TEMPLATE = Path(__file__).with_name("template.html")

EQUATIONS = [  # plain Unicode (no LaTeX markup) so they read as handwriting on the board
    "e^(iπ) + 1 = 0", "∇ · E = ρ/ε₀", "P(A|B) = P(B|A)P(A) / P(B)", "softmax(zᵢ) = eᶻⁱ / Σ eᶻʲ",
    "Attention(Q,K,V) = softmax(QKᵀ/√d)V", "∂L/∂w = (ŷ − y)x", "f(x) = Σ aₙxⁿ", "H = −Σ p log p",
    "∫ e^(−x²) dx = √π", "y = σ(Wx + b)", "θ ← θ − η∇L(θ)", "det(A − λI) = 0", "KL(p‖q) = Σ p log(p/q)",
    "a² + b² = c²", "(1 + 1/n)ⁿ → e", "x̂ = (x − μ)/σ", "∇²φ = 0", "E = mc²", "p(x) ∝ e^(−E(x))",
    "cos θ = a·b / ‖a‖‖b‖", "Σₖ k = n(n+1)/2", "A = UΣVᵀ",
]


def _data_uri(path: Path) -> str:
    mime = mimetypes.guess_type(path.name)[0] or "image/png"
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode()}"


def math_wall_svg(w: int, h: int, seed: int = 7) -> str:
    rnd = random.Random(seed)
    items = []
    for _ in range(60):
        x, y = rnd.uniform(-100, w), rnd.uniform(20, h)
        size = rnd.uniform(26, 62)
        rot = rnd.uniform(-8, 8)
        op = rnd.uniform(0.10, 0.28)
        eq = html.escape(rnd.choice(EQUATIONS))
        items.append(f'<text x="{x:.0f}" y="{y:.0f}" font-size="{size:.0f}" transform="rotate({rot:.1f} {x:.0f} {y:.0f})" '
                     f'fill="#F4F1E8" fill-opacity="{op:.2f}" font-family="Caveat, cursive">{eq}</text>')
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}">{"".join(items)}</svg>'
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()


def background_css(theme: dict, w: int, h: int, image: Path | None) -> str:
    c = theme["colors"]
    bg = theme["background"]
    if image:
        dark = bg.get("darken", 0.35)
        return (f"background: linear-gradient(rgba(0,0,0,{dark}), rgba(0,0,0,{dark})), url('{_data_uri(image)}') center/cover no-repeat, {c['bg']};"
                + (f" --bgblur: {bg.get('blur_px', 0)}px;" if bg.get("blur_px") else ""))
    gen = bg.get("generator")
    if gen == "math-wall":
        return (f"background: radial-gradient(ellipse at center, rgba(0,0,0,0) 40%, rgba(0,0,0,.55) 100%), "
                f"url('{math_wall_svg(w, h)}'), {c['bg']};")
    if gen == "blueprint":
        return (f"background: linear-gradient(rgba(255,255,255,.14) 2px, transparent 2px) 0 0/120px 120px, "
                f"linear-gradient(90deg, rgba(255,255,255,.14) 2px, transparent 2px) 0 0/120px 120px, "
                f"linear-gradient(rgba(255,255,255,.06) 1px, transparent 1px) 0 0/24px 24px, "
                f"linear-gradient(90deg, rgba(255,255,255,.06) 1px, transparent 1px) 0 0/24px 24px, {c['bg']};")
    if gen == "terminal":
        return (f"background: repeating-linear-gradient(0deg, rgba(57,255,136,.035) 0 2px, transparent 2px 5px), "
                f"radial-gradient(ellipse at 50% 40%, #102015 0%, {c['bg']} 70%);")
    return f"background: radial-gradient(circle at 90% 5%, {c['accent']}22 0, transparent 45%), {c['bg']};"


def _fonts_link(theme: dict) -> str:
    fams = {theme["fonts"]["title"], theme["fonts"]["body"]}
    q = "&".join(f"family={f.replace(' ', '+')}:wght@400;500;700;800;900" for f in sorted(fams))
    return f'<link rel="stylesheet" href="https://fonts.googleapis.com/css2?{q}&display=block">'


def display_url(url: str, max_len: int = 40) -> str:
    """Readable link for a slide: no scheme/www; long paths shortened to domain/…/last-part."""
    u = re.sub(r"^https?://(www\.)?", "", url).rstrip("/")
    if len(u) <= max_len:
        return u
    parts = u.split("/")
    short = f"{parts[0]}/…/{parts[-1]}" if len(parts) > 2 else u
    return short if len(short) <= max_len + 4 else parts[0]


def slide_body(s: dict, i: int, n: int, theme: dict, handle: str, project: Project) -> str:
    e = lambda k: html.escape(s.get(k) or "")  # noqa: E731
    counter = f'<div class="counter">{i}/{n}</div>'
    foot = f'<div class="handle">{html.escape(handle)}</div>' if handle else ""
    if s["kind"] == "hook":
        return (f'<div class="hook"><div class="kicker">{e("subtitle")}</div><h1>{e("title")}</h1>'
                f'<div class="swipe">swipe →</div></div>{foot}{counter}')
    if s["kind"] == "cta":
        return (f'<div class="cta"><h1>{e("title") or "Save this for later"}</h1>'
                f'<p>{e("subtitle") or "Follow for more"}</p></div>{foot}{counter}')
    img = ""
    if s.get("image"):
        p = (project.root / s["image"]) if (project.root / s["image"]).exists() else STUDIO / s["image"]
        if p.exists():
            img = f'<img class="shot" src="{_data_uri(p)}">'
    tag = f'<span class="tag">{e("tag")}</span>' if s.get("tag") else ""
    url = display_url(s.get("url") or "")
    return (f'<div class="num">{i - 1:02d}</div><div class="card">{tag}<h2>{e("name")}</h2>{img}'
            f'<p class="value">{e("value")}</p>'
            + (f'<p class="who"><b>For:</b> {e("for_who")}</p>' if s.get("for_who") else "")
            + (f'<p class="url">{html.escape(url)}</p>' if url else "")
            + f"</div>{foot}{counter}")


def build_html(carousel: dict, theme: dict, project: Project, w: int, h: int) -> list[str]:
    tpl = TEMPLATE.read_text()
    image = None
    if carousel.get("background"):
        cand = [project.root / carousel["background"], STUDIO / carousel["background"]]
        image = next((p for p in cand if p.exists()), None)
    elif theme["background"].get("image"):
        p = THEMES / theme["name"] / theme["background"]["image"]
        image = p if p.exists() else None
    c, f = theme["colors"], theme["fonts"]
    vars_ = {
        "W": str(w), "H": str(h), "FONTS": _fonts_link(theme), "BG": background_css(theme, w, h, image),
        "TEXT": c["text"], "MUTED": c["muted"], "ACCENT": c["accent"], "CARD": c["card"],
        "TITLE_FONT": f["title"], "BODY_FONT": f["body"], "TITLE_WEIGHT": str(f.get("title_weight", 800)),
        "BODY_WEIGHT": str(f.get("body_weight", 500)), "TITLE_SIZE": str(theme.get("title_size", 100)),
        "CARD_STYLE": theme.get("card_style", "soft"),
    }
    pages = []
    n = len(carousel["slides"])
    for i, s in enumerate(carousel["slides"], 1):
        page = tpl
        for k, v in {**vars_, "BODY": slide_body(s, i, n, theme, carousel.get("handle", ""), project), "KIND": s["kind"]}.items():
            page = page.replace("{{" + k + "}}", v)
        pages.append(page)
    return pages


CHROME_CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
]


def chrome_bin() -> str:
    for c in CHROME_CANDIDATES:
        if Path(c).exists():
            return c
    found = shutil.which("chromium") or shutil.which("google-chrome")
    if not found:
        raise SystemExit("no Chrome/Chromium found — install Google Chrome to render carousels")
    return found


def _chrome(args: list[str], profile: Path, output: Path, timeout: float = 90) -> None:
    """Headless Chrome sometimes lingers after writing its output, so we watch for the file
    (size stable for ~0.5 s) and then shut Chrome down ourselves."""
    import time

    if output.exists():
        output.unlink()
    proc = subprocess.Popen([chrome_bin(), "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run",
                             "--no-default-browser-check", f"--user-data-dir={profile}", "--force-device-scale-factor=1",
                             "--virtual-time-budget=5000", *args], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    t0, last = time.time(), -1
    try:
        while time.time() - t0 < timeout:
            if proc.poll() is not None and output.exists():
                return
            if output.exists():
                size = output.stat().st_size
                if size > 0 and size == last:
                    return
                last = size
            time.sleep(0.5)
        raise SystemExit(f"Chrome timed out rendering {output.name}")
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(5)
            except subprocess.TimeoutExpired:
                proc.kill()


def render(project: Project, size: str | None = None, pdf: bool = True) -> list[Path]:
    """HTML/CSS slides → PNG (and a PDF for LinkedIn) with headless Chrome — no extra Python deps."""
    carousel = load_json(project.root / "carousel.json")
    validate(carousel, "carousel")
    size = size or carousel.get("size", "1080x1350")
    w, h = map(int, size.split("x"))
    theme_dir = THEMES / carousel["theme"]
    if not (theme_dir / "theme.json").exists():
        raise SystemExit(f"unknown theme '{carousel['theme']}' — available: {', '.join(p.name for p in THEMES.iterdir() if p.is_dir())}")
    theme = load_json(theme_dir / "theme.json")
    pages = build_html(carousel, theme, project, w, h)
    hdir, sdir = project.work / "slides_html", project.out / "slides"
    hdir.mkdir(parents=True, exist_ok=True)
    sdir.mkdir(parents=True, exist_ok=True)
    for old in sdir.glob("*.png"):
        old.unlink()
    outs = []
    with tempfile.TemporaryDirectory() as profile:
        for i, content in enumerate(pages, 1):
            hp = hdir / f"{i:02d}.html"
            hp.write_text(content)
            out = sdir / f"{i:02d}.png"
            _chrome([f"--window-size={w},{h}", f"--screenshot={out}", hp.as_uri()], Path(profile), out)
            outs.append(out)
        if pdf:
            imgs = "".join(f'<img src="{_data_uri(p)}">' for p in outs)
            doc = hdir / "carousel_pdf.html"
            doc.write_text(f"<html><head><style>@page{{size:{w}px {h}px;margin:0}}html,body{{margin:0}}"
                           f"img{{display:block;width:{w}px;height:{h}px;break-after:page}}</style></head><body>{imgs}</body></html>")
            _chrome(["--no-pdf-header-footer", f"--print-to-pdf={project.out / 'carousel.pdf'}", doc.as_uri()], Path(profile),
                    project.out / "carousel.pdf")
    if carousel.get("caption_draft"):
        tags = " ".join(t if t.startswith("#") else f"#{t}" for t in carousel.get("hashtags", []))
        (project.out / "caption.txt").write_text(carousel["caption_draft"].strip() + ("\n\n" + tags if tags else "") + "\n")
    log.info(f"{len(outs)} slides ({size}, theme {carousel['theme']}) → {sdir.relative_to(project.root)}")
    return outs


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("--size", choices=["1080x1350", "1080x1080"])
    ap.add_argument("--no-pdf", action="store_true")
    a = ap.parse_args(argv)
    render(Project(a.project), a.size, not a.no_pdf)


if __name__ == "__main__":
    main()
