#!/usr/bin/env bash
# Daily HQ metrics sync (run by launchd — see `./studio hq schedule`). Secrets such as IG_ACCESS_TOKEN / IG_USER_ID
# live outside the repo in ~/.config/creator-os/env (KEY=value lines), never in a committed file.
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f "$HOME/.config/creator-os/env" ] && set -a && . "$HOME/.config/creator-os/env" && set +a
mkdir -p data/hq
{ echo "== $(date '+%F %T')"; ./studio hq sync; } >> data/hq/sync.log 2>&1
