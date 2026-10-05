import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


@pytest.fixture
def mem(tmp_path, monkeypatch):
    """Isolated memory engine rooted in tmp_path."""
    from pipeline import memory
    long = tmp_path / "memory" / "long-term"
    monkeypatch.setattr(memory, "WORKING", tmp_path / "memory" / "working")
    monkeypatch.setattr(memory, "LONG", long)
    monkeypatch.setattr(memory, "INDEX", long / "index.md")
    monkeypatch.setattr(memory, "PROJECTS", tmp_path / "projects")
    monkeypatch.setattr(memory, "MEMORY", tmp_path / "memory")
    return memory


def words_from(text: str, start: float = 0.0, dur: float = 0.3, gap: float = 0.05):
    out, t = [], start
    for w in text.split():
        out.append({"text": w, "start": round(t, 3), "end": round(t + dur, 3), "prob": 1.0})
        t += dur + gap
    return out
