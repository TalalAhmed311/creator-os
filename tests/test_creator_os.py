"""creator-os: database, research, writer and HQ harnesses — all offline, in a temp database and project folder."""
import csv
import datetime as dt
import json
from pathlib import Path

import pytest

from core import accounts, db
from core.common import load_json, save_json

ROOT = Path(__file__).resolve().parent.parent
SEED = ROOT / "docs" / "research" / "2026-10-05-instagram-ai-tech-creators.md"


@pytest.fixture
def con(tmp_path, monkeypatch, mem):
    """Fresh database + projects + accounts in tmp_path (mem isolates the memory engine)."""
    import core.common as common
    monkeypatch.setenv("CREATOR_OS_DB", str(tmp_path / "data" / "test.db"))
    monkeypatch.setattr(common, "PROJECTS", tmp_path / "projects")
    acc = tmp_path / "accounts"
    acc.mkdir()
    (acc / "instagram-me.md").write_text("---\nplatform: instagram\nhandle: me\npillars: [build-in-public, resources]\n"
                                         "formats: [reel, carousel]\n---\n# notes\nAI + products.\n")
    (acc / "x-curio.md").write_text("---\nplatform: x\nhandle: TODO   # later\npillars: [build-in-public]\n---\nCurio only.\n")
    monkeypatch.setattr(accounts, "ACCOUNTS", acc)
    c = db.connect()
    accounts.sync(c)
    return c


def _creator_post(c, handle, url, views):
    hid = db.ensure_handle(c, "instagram", handle)
    pid = db.upsert_post(c, url, "instagram", handle_id=hid)
    db.add_metrics(c, pid, "test", "verified", views=views)
    return pid


# ---------------------------------------------------------------- database

def test_migrate_is_idempotent(con):
    assert db.schema_version(con) == 1
    db.migrate(con)
    assert db.schema_version(con) == 1


def test_post_needs_exactly_one_author(con):
    import sqlite3
    with pytest.raises(sqlite3.IntegrityError):
        db.upsert_post(con, "https://x.com/a/status/1", "x")


def test_seed_import(con):
    from harnesses.research import creators, seed
    res = seed.import_seed(SEED, con=con)
    assert res["creators"] == 75 and res["research_set"] == 20 and res["snapshots_added"] > 150
    assert seed.import_seed(SEED, con=con)["snapshots_added"] == 0  # re-run adds nothing
    rows = creators.listing(con, status="tracked")
    assert len(rows) == 20
    dq = db.find_handle(con, "instagram", "daniallqureshi")
    snaps = db.dicts(con.execute("SELECT * FROM creator_snapshots WHERE handle_id = ?", (dq["id"],)))
    assert {s["quality"] for s in snaps} == {"estimated"}          # all third-party
    assert any(s["source"] == "apify" and s["typical_views"] == 114600 and s["captured_at"] == "2026-03-31" for s in snaps)
    assert any(s["source"] == "socialpruf" and s["followers"] == 26200 for s in snaps)
    assert db.find_handle(con, "instagram", "olivermerrick___")      # escaped underscores
    assert db.find_handle(con, "instagram", "thevarunmayya")["status"] == "tracked"


def test_outlier_scores(con):
    for i, v in enumerate([100, 120, 80, 1000]):
        _creator_post(con, "alice", f"https://www.instagram.com/reel/a{i}/", v)
    rows = db.with_outlier_scores(con, db.post_table(con, "p.url = ?", ("https://www.instagram.com/reel/a3/",)))
    assert rows[0]["outlier"] == round(1000 / 110, 2) and "median of 4" in rows[0]["outlier_basis"]
    hid = db.ensure_handle(con, "instagram", "bob")
    db.add_creator_snapshot(con, hid, "test", "estimated", typical_views=500)
    _creator_post(con, "bob", "https://www.instagram.com/reel/b1/", 1500)
    rows = db.with_outlier_scores(con, db.post_table(con, "p.url = ?", ("https://www.instagram.com/reel/b1/",)))
    assert rows[0]["outlier"] == 3.0 and rows[0]["outlier_basis"] == "typical views snapshot"


def test_export_restore_roundtrip(con, tmp_path, monkeypatch):
    from core.db import cli
    _creator_post(con, "alice", "https://www.instagram.com/reel/z/", 10)
    counts = cli.export(con, tmp_path / "exp")
    monkeypatch.setenv("CREATOR_OS_DB", str(tmp_path / "fresh.db"))
    fresh = db.connect()
    assert cli.restore(fresh, tmp_path / "exp") == counts
    with pytest.raises(SystemExit):
        cli.restore(fresh, tmp_path / "exp")  # never into a non-empty database


# ---------------------------------------------------------------- research

def test_text_post_and_insights(con):
    from harnesses.research import insights, posts
    r = posts.add(con, "https://www.linkedin.com/posts/carol_abc", handle="carol", text="I shipped X in 3 days.",
                  metrics={"likes": 400, "comments": 50}, source="browser", quality="verified")
    assert r["ref"] is None and r["metrics_source"] == "browser"
    p1 = _creator_post(con, "alice", "https://www.instagram.com/reel/i1/", 900)
    p2 = _creator_post(con, "alice", "https://www.instagram.com/reel/i2/", 700)
    a = insights.add(con, "Open with the result and the time it took", "hook", "instagram", evidence=[p1], confidence="medium")
    b = insights.add(con, "Open with the result and the time it took them", "hook", "instagram", evidence=[p2])
    assert b == {"insight_id": a["insight_id"], "merged": True}
    top = insights.ranked(con, platform="instagram")
    assert top[0]["seen"] == 2 and top[0]["confidence"] == "medium" and len(top[0]["evidence"]) == 2
    with pytest.raises(SystemExit):
        insights.add(con, "x", "hook", evidence=[999])


def test_research_report_keeps_summary(con, tmp_path):
    from harnesses.research import report
    out = report.build(con, "test", out_dir=tmp_path)
    out.write_text(out.read_text().replace("_(analyst: 3–5 lines", "Make more result-first reels._(x"))
    out = report.build(con, "test", out_dir=tmp_path)
    assert "Make more result-first reels." in out.read_text()


# ---------------------------------------------------------------- accounts & writer

def test_accounts_parse(con):
    a = accounts.get(con, "x-curio")
    assert a["platform"] == "x" and a["handle"] is None and a["pillars"] == ["build-in-public"]
    assert "Curio only." in a["body"]
    with pytest.raises(SystemExit):
        accounts.get(con, "nope")


def _post(**kw):
    base = {"platform": "x", "account": "x-curio", "format": "thread",
            "hooks": [{"type": "result_first", "text": "Curio hit 100 users"}, {"type": "mistake", "text": "I broke prod"},
                      {"type": "question", "text": "Why do waitlists fail?"}],
            "chosen_hook": 0, "thread": ["Curio hit 100 users in 9 days. Here's what worked:", "1. Shipped daily."],
            "insights_used": [1]}
    return {**base, **kw}


def test_post_rules():
    from harnesses.writer.drafts import check_post
    assert check_post(_post()) == ([], [])
    errs, _ = check_post(_post(thread=["x" * 281, "ok"]))
    assert any("281 characters" in e for e in errs)
    errs, _ = check_post(_post(thread=["only one"]))
    assert any("≥ 2 posts" in e for e in errs)
    _, warns = check_post(_post(platform="linkedin", format="text", thread=None, body="See https://a.b\nmore", hooks=_post()["hooks"],
                                chosen_hook=None))
    assert any("first_comment" in w for w in warns)


def test_draft_lifecycle(con):
    from harnesses.hq import content
    from harnesses.writer import drafts
    d = drafts.new(con, "x-curio", "thread", "100 users", insight_ids=[])
    proj = Path(db.db_path()).parent.parent / "projects" / d["project_id"]
    assert (proj / "context.json").exists() and (proj / "post.json").exists()
    assert not drafts.check(con, d["draft_id"])["ok"]                  # skeleton isn't a draft yet
    save_json(proj / "post.json", _post())
    res = drafts.check(con, d["draft_id"])
    assert res["ok"] and (proj / "post.md").exists() and "1/2" in (proj / "post.md").read_text()
    with pytest.raises(SystemExit):
        drafts.new(con, "x-curio", "reel", "nope")                     # not an X format
    with pytest.raises(SystemExit):
        drafts.set_status(con, d["draft_id"], "published")             # only hq log publishes
    content.log(con, "x-curio", "https://x.com/me/status/42", draft_id=d["draft_id"], metrics={"views": 300})
    got = drafts.get(con, d["draft_id"])
    assert got["status"] == "published" and got["post_id"]


# ---------------------------------------------------------------- HQ

def test_due_and_sync(con, tmp_path):
    from harnesses.hq import content, providers
    posted = dt.datetime(2026, 10, 1, 9, 0)
    content.log(con, "instagram-me", "https://www.instagram.com/reel/me1/", posted_at=posted.isoformat())
    content.log(con, "x-curio", "https://x.com/me/status/7", posted_at=posted.isoformat())
    assert content.due(con, posted + dt.timedelta(hours=12)) == []
    due = content.due(con, posted + dt.timedelta(days=3, hours=1))
    assert {d["checkpoint_days"] for d in due} == {3}

    def fake(platform, url):
        if platform == "x":
            raise providers.ProviderError("no counters")
        return {"likes": 10}, "yt-dlp", "verified"
    res = content.sync(con, now=posted + dt.timedelta(days=3, hours=1), fetcher=fake)
    assert len(res["synced"]) == 1
    reasons = {p["platform"]: p["reason"] for p in res["pending"]}
    assert "views not readable" in reasons["instagram"] and "no counters" in reasons["x"]
    assert "hq metrics add" in content.pending_path().read_text()
    assert [d["platform"] for d in content.due(con, posted + dt.timedelta(days=3, hours=2))] == ["x"]


def test_import_csv_aliases(con, tmp_path):
    from harnesses.hq import content
    f = tmp_path / "export.csv"
    with f.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["Post URL", "Impressions", "Reactions", "Comments", "Reposts"])
        w.writerow(["https://www.linkedin.com/posts/me_1", "1,200", "40", "5", "2"])
    res = content.import_csv(con, f, "linkedin-export", account_id="instagram-me")
    assert res["snapshots_added"] == 1 and res["posts_created"] == 1
    m = db.dicts(con.execute("SELECT * FROM latest_metrics"))[0]
    assert m["impressions"] == 1200 and m["likes"] == 40 and m["reposts"] == 2


def test_review_findings(con):
    from harnesses.hq import content, review
    for i, (fmt, views) in enumerate([("reel", 1000), ("reel", 1200), ("carousel", 300), ("carousel", 400), ("reel", 900)]):
        content.log(con, "instagram-me", f"https://www.instagram.com/p/r{i}/", fmt=fmt,
                    posted_at=f"2026-09-{10 + i:02d}T10:00:00", metrics={"views": views})
    res = review.review(con, "instagram-me")
    a = res["accounts"]["instagram-me"]
    assert a["posts"] == 5 and a["median_reach"] == 900
    assert any(f.startswith("format: 'reel'") for f in a["findings"])
    assert Path(res["report"]).exists() or (ROOT / res["report"]).exists()


def test_import_old_content_log(con, tmp_path):
    from harnesses.hq import content
    f = tmp_path / "log.csv"
    f.write_text("date,project_id,pillar,hook_type,hook_text,length_s,platform,url,views,avg_watch_pct,likes,comments,saves,shares,notes\n"
                 "2026-09-01,,build-in-public,mistake,x,30,instagram,https://www.instagram.com/reel/old/,5000,41%,300,20,50,10,\n")
    res = content.import_content_log(con, f, {"instagram": "instagram-me"})
    assert res["imported"] == 1
    m = db.dicts(con.execute("SELECT * FROM latest_metrics"))[0]
    assert m["views"] == 5000 and m["avg_watch_pct"] == 41


def test_studio_json_metrics_provider(monkeypatch):
    from harnesses.hq import providers
    monkeypatch.delenv("IG_ACCESS_TOKEN", raising=False)
    assert providers.configured("instagram") in ("ytdlp", "manual", "instagram-graph")
    assert providers._shortcode("https://www.instagram.com/reel/ABC123/?igsh=x") == "ABC123"
    with pytest.raises(providers.ProviderError):
        providers.fetch("linkedin", "https://www.linkedin.com/posts/x", provider="manual")


def test_cli_routes_exist():
    import importlib

    from core.cli import ROUTES
    for name in ("db", "research", "write", "hq"):
        assert hasattr(importlib.import_module(ROUTES[name][0]), "main")


def test_writer_context_markdown(con):
    from harnesses.writer import context
    ctx = context.build(con, "instagram-me")
    md = context.markdown(ctx)
    assert "instagram-me" in md and "reel, carousel" in md and json.dumps(ctx, default=str)


def test_post_schema_fixture():
    from core.common import validate
    validate(_post(), "post")
    assert load_json(ROOT / "core" / "schemas" / "post.schema.json")["required"]


def test_cli_end_to_end(con, capsys):
    """The commands agents actually run: write new → validate → hq log → hq posts → hq review → research insight."""
    from harnesses.hq import cli as hq
    from harnesses.research import cli as research
    from harnesses.writer import cli as write
    assert write.main(["new", "x-curio", "--format", "thread", "--title", "first 100 users", "--json"]) == 0
    d = json.loads(capsys.readouterr().out)
    proj = Path(db.db_path()).parent.parent / d["path"]
    save_json(proj, _post())
    assert write.main(["validate", str(d["draft_id"])]) == 0
    assert "copy-paste version" in capsys.readouterr().out
    assert write.main(["status", str(d["draft_id"]), "approved"]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "approved"
    assert hq.main(["log", "x-curio", "https://x.com/me/status/1", "--draft", str(d["draft_id"]), "--views", "500", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["metrics_snapshot"]
    assert hq.main(["posts", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)[0]["reach_value"] == 500
    assert hq.main(["review", "--account", "x-curio"]) == 0
    assert "x-curio: 1 posts" in capsys.readouterr().out
    assert research.main(["creators", "add", "x", "dan", "--name", "Dan", "--relevance", "5", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "candidate"
    assert research.main(["creators", "track", "dan", "--platform", "x", "--why", "test"]) == 0


def test_harnesses_only_import_core():
    """Architecture rule: a harness imports core, never another harness; core imports no harness except cli/deps."""
    import re
    pat = re.compile(r"^\s*(?:from|import) harnesses\.(\w+)", re.M)
    for f in (ROOT / "harnesses").rglob("*.py"):
        if "node_modules" in f.parts:
            continue
        own = f.relative_to(ROOT / "harnesses").parts[0]
        others = {m for m in pat.findall(f.read_text()) if m != own}
        assert not others, f"{f.relative_to(ROOT)} imports harness(es) {others}"
    for f in (ROOT / "core").rglob("*.py"):
        if f.name not in ("cli.py", "deps.py") or f.parent.name != "core":
            assert not pat.search(f.read_text()), f"{f.relative_to(ROOT)} imports a harness"
