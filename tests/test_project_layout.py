from pipeline.common import Project


def test_ensure_creates_drop_folders_and_guide(tmp_path):
    proj = Project(tmp_path / "2026-01-01_bip-x").ensure()
    for d in ("raw", "raw/broll", "raw/images", "work", "out"):
        assert (proj.root / d).is_dir()
    guide = (proj.root / "README.md").read_text()
    assert "2026-01-01_bip-x" in guide and "raw/images/" in guide


def test_ensure_keeps_an_edited_guide(tmp_path):
    proj = Project(tmp_path / "p").ensure()
    (proj.root / "README.md").write_text("my notes")
    proj.ensure()
    assert (proj.root / "README.md").read_text() == "my notes"
