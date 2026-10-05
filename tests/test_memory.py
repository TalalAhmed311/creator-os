import json


def test_working_memory_lifecycle_and_consolidation(mem, tmp_path):
    pid = "2026-09-26_bip-day-12"
    (tmp_path / "projects" / pid).mkdir(parents=True)
    p = mem.create_working(pid, "build-in-public", "edit", goal="Ship Day 12 reel")
    assert p.exists()
    mem.progress(pid, "ingest", done=False)
    mem.progress(pid, "transcribe", done=False)
    mem.progress(pid, "ingest")
    mem.append(pid, "decisions", "Chose hook #2 (result-first) — sounds most like me", agent="showrunner")
    mem.append(pid, "feedback", "Captions too big → reduced to 80%")
    mem.append(pid, "ideas", "Pricing tangent could be its own reel")
    front, sections = mem.read_working(pid)
    assert front["status"] == "in_progress"
    assert "- [x] ingest" in sections["Progress"] and "- [ ] transcribe" in sections["Progress"]
    assert any("(showrunner) Chose hook #2" in ln for ln in sections["Decisions (with reason)"])

    opened = mem.list_open()
    assert opened[0]["project_id"] == pid and opened[0]["next_steps"] == ["transcribe"]

    res = mem.consolidate(pid, facts=[
        {"kind": "preference", "text": "Prefers smaller captions (80% size), white + one accent colour", "tags": ["captions"]},
        {"kind": "idea", "text": "Pricing tangent as its own reel", "tags": ["pricing"], "pillar": "build-in-public"},
        {"kind": "pillar", "text": "Day 12 posted: new onboarding flow"},
    ], summary="Day 12 onboarding reel")
    assert not (mem.WORKING / f"{pid}.md").exists()
    assert (tmp_path / "projects" / pid / "working-memory.md").exists()
    assert (mem.LONG / "projects" / f"{pid}.md").exists()
    index = (mem.LONG / "index.md").read_text()
    assert "Day 12 onboarding reel" in index and "preferences.md" in index
    assert mem.list_open() == []

    hits = mem.search("captions")
    assert hits and any("smaller captions" in h["snippet"] for h in hits)
    assert any("Pricing" in b for b in mem.memory_load("build-in-public"))


def test_dedupe_bumps_seen_and_flags_promotion(mem):
    r1 = mem.add_fact("preference", "Prefers smaller captions, around 80% size", ["captions"])
    r2 = mem.add_fact("preference", "prefers smaller captions around 80% size", ["captions"])
    r3 = mem.add_fact("preference", "Prefers smaller captions — around 80% size", ["captions"])
    assert (r1["action"], r2["action"], r3["action"]) == ("added", "bumped", "bumped")
    assert r3["entry"]["seen"] == 3 and r3["promote"] is True
    lines = [ln for ln in (mem.LONG / "preferences.md").read_text().splitlines() if ln.startswith("- ")]
    assert len(lines) == 1
    assert len(mem.pending_promotions()) == 1
    mem.mark_promoted("preference", "Prefers smaller captions, around 80% size")
    assert mem.pending_promotions() == []
    # index has a single line for the fact, not three
    assert (mem.LONG / "index.md").read_text().count("preferences.md") == 1


def test_contradiction_replaces(mem):
    mem.add_fact("preference", "Likes yellow keyword highlights", ["captions"])
    r = mem.add_fact("preference", "Hates yellow captions; use brand purple", ["captions"], replaces="Likes yellow keyword highlights")
    assert r["action"] == "replaced"
    body = (mem.LONG / "preferences.md").read_text()
    assert "Hates yellow" in body and body.count("- ") == 1


def test_consolidate_without_project_folder_archives_to_long_term(mem):
    mem.create_working("2026-09-26_res-x", "resources", "carousel")
    out = mem.consolidate("2026-09-26_res-x")
    assert out["archived_working"].endswith("2026-09-26_res-x.working.md")
