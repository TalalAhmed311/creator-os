"""Run `./studio hq sync` every day with launchd (macOS). Nothing is installed unless you pass --install.

  ./studio hq schedule              show the plan (plist path, time, script) — changes nothing
  ./studio hq schedule --install [--hour 9]   write ~/Library/LaunchAgents/com.creator-os.hq-sync.plist and load it
  ./studio hq schedule --uninstall  unload and remove it
"""
from __future__ import annotations

import plistlib
import subprocess
from pathlib import Path

from core.common import STUDIO

LABEL = "com.creator-os.hq-sync"
PLIST = Path.home() / "Library" / "LaunchAgents" / f"{LABEL}.plist"
SCRIPT = STUDIO / "scripts" / "hq-daily.sh"


def plist(hour: int = 9) -> dict:
    return {"Label": LABEL, "ProgramArguments": ["/bin/bash", str(SCRIPT)],
            "StartCalendarInterval": {"Hour": hour, "Minute": 0}, "RunAtLoad": False,
            "StandardOutPath": str(STUDIO / "data" / "hq" / "launchd.log"),
            "StandardErrorPath": str(STUDIO / "data" / "hq" / "launchd.log")}


def status() -> dict:
    loaded = subprocess.run(["launchctl", "list", LABEL], capture_output=True).returncode == 0
    return {"label": LABEL, "plist": str(PLIST), "installed": PLIST.exists(), "loaded": loaded, "script": str(SCRIPT),
            "log": str(STUDIO / "data" / "hq" / "sync.log")}


def install(hour: int = 9) -> dict:
    PLIST.parent.mkdir(parents=True, exist_ok=True)
    (STUDIO / "data" / "hq").mkdir(parents=True, exist_ok=True)
    if PLIST.exists():
        subprocess.run(["launchctl", "unload", str(PLIST)], capture_output=True)
    PLIST.write_bytes(plistlib.dumps(plist(hour)))
    subprocess.run(["launchctl", "load", str(PLIST)], check=True)
    return status()


def uninstall() -> dict:
    if PLIST.exists():
        subprocess.run(["launchctl", "unload", str(PLIST)], capture_output=True)
        PLIST.unlink()
    return status()
