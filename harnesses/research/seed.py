"""Import a creator-research document (markdown, the format of docs/research/*-creators.md) into the database.

  ./studio research import-seed docs/research/2026-10-05-instagram-ai-tech-creators.md [--platform instagram]

Reads: the source-code table (A/H/S/… → name + date), section A (creator database), the profile notes,
section B (why each high-signal creator matters) and section E (the research set → status 'tracked').
Every number becomes a creator snapshot tagged with its source and date; all are 'estimated' (third-party).
Safe to re-run: creators are updated, identical snapshots are not added twice.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

from core import db

MONTHS = {m: i for i, m in enumerate(("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"), 1)}
SOURCES = {  # code → slug used in creator_snapshots.source
    "A": "apify", "H": "hafi", "S": "socialpruf", "F": "feedspot", "V": "viralist", "C": "creatordb",
    "HA": "hypeauditor", "CREATORFLOW": "creatorflow",
}
CLUSTER = {
    "ai tools": "ai-tools", "tech education": "ai-tools", "ai/ml": "ai-engineering", "ai engineering": "ai-engineering",
    "software engineering": "developer", "coding/programming": "developer", "developer education": "developer",
    "ai productivity": "ai-productivity", "ai automation": "ai-productivity", "tech news": "ai-news",
    "build in public": "builders", "ai builder": "builders", "builder / maker": "builders", "indie hacker": "builders",
    "saas builder": "builders", "startup/founder": "builders", "technical founder": "builders", "ai startup": "builders",
}


def number(s: str | None) -> float | None:
    if not s:
        return None
    m = re.search(r"([\d.,]+)\s*([KkMm]?)", s.replace("\\", ""))
    if not m or s.strip().upper().startswith("N/A"):
        return None
    v = float(m.group(1).replace(",", ""))
    return v * {"k": 1e3, "m": 1e6}.get(m.group(2).lower(), 1)


def cells(line: str) -> list[str]:
    parts = re.split(r"(?<!\\)\|", line.strip().strip("|"))
    return [p.strip().replace("\\|", "|") for p in parts]


def tables(md: str) -> list[tuple[str, list[str], list[list[str]]]]:
    """(heading, header, rows) for every markdown table, heading = nearest ## / ### above it."""
    out, heading, i, lines = [], "", 0, md.splitlines()
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("#"):
            heading = ln.lstrip("#").strip()
        if ln.startswith("|") and i + 1 < len(lines) and re.match(r"^\|\s*:?-", lines[i + 1]):
            header, rows, i = cells(ln), [], i + 2
            while i < len(lines) and lines[i].startswith("|"):
                rows.append(cells(lines[i]))
                i += 1
            out.append((heading, header, rows))
            continue
        i += 1
    return out


def handle_of(cell: str) -> str | None:
    m = re.search(r"@([\w.\\]+)", cell)
    return db.norm_handle(m.group(1)) if m else None


def parse_source_dates(rows: list[list[str]], doc_date: str) -> dict[str, str]:
    """code → ISO date from the 'Source codes' table (falls back to the document date)."""
    dates = {}
    for r in rows:
        code, date = r[0].strip(), r[-1]
        m = re.search(r"(\d{1,2})\s+([A-Za-z]{3})\w*\s+(\d{4})", date)
        dates[code] = f"{m.group(3)}-{MONTHS[m.group(2).lower()]:02d}-{int(m.group(1)):02d}" if m else doc_date
    return dates


def parse_figure(cell: str, source_dates: dict[str, str], doc_date: str) -> tuple[float | None, str, str, str]:
    """'20.6K (S Oct-26)' → (20600, 'socialpruf', '2026-10-01', raw note)."""
    value = number(cell)
    m = re.search(r"\(([^)]*)\)", cell)
    inside = m.group(1) if m else ""
    code = (inside.split() or ["?"])[0].rstrip(",")
    source = SOURCES.get(code.upper(), code.lower() or "seed-research")
    date = source_dates.get(code, doc_date)
    mm = re.search(r"([A-Za-z]{3})-(\d{2})", inside)
    if mm and mm.group(1).lower() in MONTHS:
        exact = source_dates.get(code, "")
        prefix = f"20{mm.group(2)}-{MONTHS[mm.group(1).lower()]:02d}"
        date = exact if exact.startswith(prefix) else f"{prefix}-01"
    return value, source, date, cell


def parse(md: str) -> dict:
    """{doc_date, creators: {handle: {...fields, snapshots: [...]}}, research_set: [...]}"""
    dm = re.search(r"^([A-Z][a-z]{2}) (\d{1,2}), (\d{4})", md, re.M)
    doc_date = f"{dm.group(3)}-{MONTHS[dm.group(1).lower()]:02d}-{int(dm.group(2)):02d}" if dm else db.now()[:10]
    all_tables = tables(md)
    source_dates = {}
    for heading, header, rows in all_tables:
        if header and header[0].lower() == "code":
            source_dates = parse_source_dates(rows, doc_date)
    typical_date = source_dates.get("A", doc_date)

    creators: dict[str, dict] = {}
    research_set: list[str] = []
    for heading, header, rows in all_tables:
        h = [x.lower() for x in header]
        if "username" in h and "typical reel views" in h:  # section A
            ix = {k: h.index(k) for k in h}
            for r in rows:
                handle = handle_of(r[ix["username"]])
                if not handle:
                    continue
                niche = r[ix["primary niche"]]
                c = creators.setdefault(handle, {"snapshots": []})
                c.update(name=re.sub(r"\s*\(.*?\)\s*$", "", r[ix["creator"]]).strip() or handle,
                         seed_rank=int(number(r[ix["rank"]]) or 0) or None, primary_niche=niche,
                         cluster=CLUSTER.get(niche.lower()), original=r[ix["original"]].lower() or None,
                         signal=r[ix["signal"]].split(" (")[0])
                followers, src, date, raw = parse_figure(r[ix["followers"]], source_dates, doc_date)
                typical, ratio = number(r[ix["typical reel views"]]), number(r[ix["views / followers"]])
                if followers is not None:
                    c["snapshots"].append({"source": src, "captured_at": date, "followers": int(followers), "note": f"seed: {raw}"})
                if typical is not None:
                    c["snapshots"].append({"source": "apify", "captured_at": typical_date, "typical_views": int(typical),
                                           "reach_ratio": ratio, "note": "seed: avg Reel views in the Apify sample; ratio uses followers at that sample"})
                peak_cell = r[ix["highest reel views"]]
                peak = number(peak_cell)
                if peak is not None:
                    inside = (re.search(r"\(([^)]*)\)", peak_cell) or [None, ""])[1]
                    c["snapshots"].append({"source": "viralist" if "viralist" in inside.lower() else "self-reported",
                                           "captured_at": doc_date, "peak_views": int(peak), "note": f"seed: {peak_cell}"})
        elif "username" in h and "posting frequency" in h:  # profile notes
            ix = {k: h.index(k) for k in h}
            for r in rows:
                handle = handle_of(r[ix["username"]])
                if not handle or handle not in creators:
                    continue
                c = creators[handle]
                sec = r[ix["secondary niche"]]
                country = r[ix["country"]]
                c.update(secondary_niche=None if sec == "N/A" else sec, country=None if country == "N/A" else country,
                         account_type=r[ix["account type"]], notes=r[ix["note"]].replace("\\", ""))
                posts = number(r[ix["posts"]])
                freq_cell = r[ix["posting frequency"]].replace("\\", "")
                fm = re.search(r"([\d.]+)/wk", freq_cell)
                code = (re.search(r",?\s*([A-Z]{1,2})\)\s*$", freq_cell) or [None, None])[1]
                if posts is not None:
                    c["snapshots"].append({"source": "seed-research", "captured_at": doc_date, "posts": int(posts),
                                           "note": "seed: total posts on profile"})
                if fm:
                    c["snapshots"].append({"source": SOURCES.get(code or "", "seed-research"), "captured_at": source_dates.get(code, doc_date),
                                           "posts_per_week": float(fm.group(1)), "note": f"seed: {freq_cell}"})
        elif "creator" in h and "why include" in h:  # section E
            for r in rows:
                handle = handle_of(r[h.index("creator")])
                if handle:
                    research_set.append(handle)
                    creators.setdefault(handle, {"snapshots": []}).setdefault("why", r[h.index("why include")])

    # section B: "- **Instagram:** [@x]…" then "- **Why study them:** …"
    current = None
    for ln in md.splitlines():
        if "**Instagram:**" in ln:
            current = handle_of(ln)
        elif current and "**Why study them:**" in ln and current in creators:
            creators[current]["why"] = ln.split("**Why study them:**", 1)[1].strip()
    return {"doc_date": doc_date, "creators": creators, "research_set": research_set}


def import_seed(path: Path, platform: str = "instagram", con=None) -> dict:
    data = parse(Path(path).read_text())
    con = con or db.connect()
    added_snaps = 0
    with con:
        for handle, c in data["creators"].items():
            snaps = c.pop("snapshots", [])
            status = "tracked" if handle in data["research_set"] else None
            fields = {k: v for k, v in c.items() if v not in (None, "")}
            hid = db.ensure_handle(con, platform, handle, **fields, **({"status": status} if status else {}),
                                   in_research_set=int(handle in data["research_set"]))
            for s in snaps:
                dup = con.execute("SELECT 1 FROM creator_snapshots WHERE handle_id = ? AND source = ? AND captured_at = ? AND note = ?",
                                  (hid, s["source"], s["captured_at"], s["note"])).fetchone()
                if not dup:
                    db.add_creator_snapshot(con, hid, quality="estimated", **s)
                    added_snaps += 1
    return {"creators": len(data["creators"]), "research_set": len(data["research_set"]), "snapshots_added": added_snaps,
            "doc_date": data["doc_date"], "source": str(path)}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="studio research import-seed", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("doc")
    ap.add_argument("--platform", default="instagram", choices=db.PLATFORMS)
    a = ap.parse_args(argv)
    import json
    print(json.dumps(import_seed(Path(a.doc), a.platform), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
