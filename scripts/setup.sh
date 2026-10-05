#!/usr/bin/env bash
# Install the studio core and verify it. Safe to re-run.
#   scripts/setup.sh                   core only (no transcription model, no torch)
#   scripts/setup.sh --with transcribe  + mlx-whisper transcription pack
#   scripts/setup.sh --with vision      + OpenCV face tracking / cover picking
#   scripts/setup.sh --with face        + mediapipe face tracking pack
#   scripts/setup.sh --with download    + yt-dlp (./studio yt, ./studio clip <url>)
set -euo pipefail
cd "$(dirname "$0")/.."
WITH=()
while [ $# -gt 0 ]; do case "$1" in --with) WITH+=("$2"); shift 2;; *) echo "unknown arg $1"; exit 2;; esac; done

command -v brew >/dev/null || { echo "Homebrew is required: https://brew.sh"; exit 1; }
for pkg in ffmpeg node uv; do command -v "$pkg" >/dev/null || brew install "$pkg"; done

PY=""
for c in python3.12 "$HOME/.local/bin/python3.12" /opt/homebrew/bin/python3.12 python3.13; do
  if command -v "$c" >/dev/null 2>&1; then PY="$c"; break; fi
done
[ -n "$PY" ] || { uv python install 3.12; PY=$(uv python find 3.12); }
[ -x .venv/bin/python ] || "$PY" -m venv .venv

# uv downloads in parallel; retry because a dropped connection restarts the failed wheel.
# Wheels you fetched by hand (e.g. curl -C - for resumable downloads) can go in .wheels/.
export UV_HTTP_TIMEOUT=300
mkdir -p .wheels
uvi() {
  for attempt in 1 2 3 4 5; do
    uv pip install --python .venv/bin/python --find-links .wheels "$@" && return 0
    echo "  install attempt $attempt failed — retrying…"; sleep 3
  done
  return 1
}

echo "== core python packages"
uvi -r requirements/core.txt
for w in "${WITH[@]:-}"; do
  case "$w" in
    transcribe) uvi -r requirements/transcribe-mlx.txt && uvi --no-deps mlx-whisper ;;
    vision)     uvi -r requirements/vision.txt ;;
    face)       uvi -r requirements/face-mediapipe.txt ;;
    download)   uvi -r requirements/download.txt ;;
    "") ;;
    *) echo "unknown feature pack: $w (transcribe | vision | face | download)"; exit 2 ;;
  esac
done
[ -d "/Applications/Google Chrome.app" ] || echo "!! install Google Chrome — carousels render with headless Chrome"

echo "== remotion"
(cd harnesses/studio/remotion && npm install --no-audit --no-fund --silent && npx tsc --noEmit)

mkdir -p memory/working memory/long-term/pillars memory/long-term/projects projects assets/{music,sfx,fonts,logos,broll,models}
echo "== schemas"
for f in plan edl carousel; do .venv/bin/python -m harnesses.studio.validate "tests/fixtures/$f.json"; done
echo
./studio doctor
