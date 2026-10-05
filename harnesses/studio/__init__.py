"""Studio harness: raw footage → finished reel (Edit Bay), carousels (Design Desk), Web Studio, Remotion."""
from pathlib import Path

HERE = Path(__file__).resolve().parent
REMOTION = HERE / "remotion"
DEFAULT_PRESET = {"build-in-public": "bip-raw", "ai-explained": "ai-explained", "resources": "talking-head-basic"}
