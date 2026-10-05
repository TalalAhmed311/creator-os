-- creator-os schema v1. Every number is stored with where it came from (source) and when (captured_at),
-- and whether it is a platform's own figure ('verified') or a third-party/derived one ('estimated').

CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT);

-- The owner's own accounts. id = file stem of brain/accounts/<id>.md (e.g. instagram-buildwith.talal).
CREATE TABLE accounts (
  id           TEXT PRIMARY KEY,
  platform     TEXT NOT NULL CHECK (platform IN ('instagram', 'linkedin', 'x', 'tiktok', 'youtube')),
  handle       TEXT,
  status       TEXT NOT NULL DEFAULT 'active',
  purpose      TEXT,
  audience     TEXT,
  pillars      TEXT,          -- JSON list
  formats      TEXT,          -- JSON list
  cadence      TEXT,
  goals        TEXT,
  voice        TEXT,
  profile_path TEXT,
  updated_at   TEXT
);

-- People studied by the research harness.
CREATE TABLE creators (
  id              INTEGER PRIMARY KEY,
  name            TEXT NOT NULL,
  primary_niche   TEXT,
  secondary_niche TEXT,
  cluster         TEXT,
  country         TEXT,
  account_type    TEXT,
  original        TEXT,       -- yes | unclear | no
  relevance       REAL,       -- 1-5, fit with the owner's content
  status          TEXT NOT NULL DEFAULT 'candidate' CHECK (status IN ('candidate', 'tracked', 'dropped')),
  signal          TEXT,       -- HIGH | Medium | Low | Watch
  seed_rank       INTEGER,
  in_research_set INTEGER NOT NULL DEFAULT 0,
  why             TEXT,
  notes           TEXT,
  added_at        TEXT,
  updated_at      TEXT
);

CREATE TABLE creator_handles (
  id         INTEGER PRIMARY KEY,
  creator_id INTEGER NOT NULL REFERENCES creators (id) ON DELETE CASCADE,
  platform   TEXT NOT NULL,
  handle     TEXT NOT NULL,
  url        TEXT,
  UNIQUE (platform, handle)
);

CREATE TABLE creator_snapshots (
  id             INTEGER PRIMARY KEY,
  handle_id      INTEGER NOT NULL REFERENCES creator_handles (id) ON DELETE CASCADE,
  captured_at    TEXT NOT NULL,
  source         TEXT NOT NULL,
  quality        TEXT NOT NULL CHECK (quality IN ('verified', 'estimated')),
  followers      INTEGER,
  posts          INTEGER,
  typical_views  INTEGER,
  peak_views     INTEGER,
  reach_ratio    REAL,        -- typical views / followers at the same snapshot
  posts_per_week REAL,
  note           TEXT
);

-- Any post: a studied creator's (handle_id) or the owner's (account_id) — exactly one.
CREATE TABLE posts (
  id              INTEGER PRIMARY KEY,
  platform        TEXT NOT NULL,
  url             TEXT NOT NULL UNIQUE,
  external_id     TEXT,
  handle_id       INTEGER REFERENCES creator_handles (id) ON DELETE CASCADE,
  account_id      TEXT REFERENCES accounts (id),
  format          TEXT,       -- reel | carousel | text | thread | doc | video | image
  posted_at       TEXT,
  title           TEXT,
  text            TEXT,
  topic           TEXT,
  pillar          TEXT,
  duration_s      REAL,
  media_path      TEXT,
  transcript_path TEXT,
  project_id      TEXT,
  added_at        TEXT,
  CHECK ((handle_id IS NULL) <> (account_id IS NULL))
);

CREATE TABLE metric_snapshots (
  id             INTEGER PRIMARY KEY,
  post_id        INTEGER NOT NULL REFERENCES posts (id) ON DELETE CASCADE,
  captured_at    TEXT NOT NULL,
  source         TEXT NOT NULL,
  quality        TEXT NOT NULL CHECK (quality IN ('verified', 'estimated')),
  views          INTEGER,
  likes          INTEGER,
  comments       INTEGER,
  shares         INTEGER,
  saves          INTEGER,
  reposts        INTEGER,
  impressions    INTEGER,
  reach          INTEGER,
  avg_watch_pct  REAL,
  profile_visits INTEGER,
  follows        INTEGER
);

-- Latest snapshot per post.
CREATE VIEW latest_metrics AS
SELECT m.* FROM metric_snapshots m
WHERE m.id = (SELECT m2.id FROM metric_snapshots m2 WHERE m2.post_id = m.post_id
              ORDER BY m2.captured_at DESC, m2.id DESC LIMIT 1);

CREATE TABLE analyses (
  id            INTEGER PRIMARY KEY,
  post_id       INTEGER NOT NULL UNIQUE REFERENCES posts (id) ON DELETE CASCADE,
  hook_type     TEXT,
  hook_text     TEXT,
  visual_hook   TEXT,
  structure     TEXT,
  pacing        TEXT,
  cta           TEXT,
  why_it_worked TEXT,
  auto_metrics  TEXT,         -- JSON from the reference analyser (wpm, cuts, first word …)
  analysis_path TEXT,
  updated_at    TEXT
);

CREATE TABLE insights (
  id           INTEGER PRIMARY KEY,
  platform     TEXT,          -- NULL = any platform
  topic        TEXT,
  kind         TEXT NOT NULL CHECK (kind IN ('hook', 'structure', 'format', 'visual', 'topic', 'cadence', 'cta', 'other')),
  pattern      TEXT NOT NULL,
  how_to_apply TEXT,
  confidence   TEXT NOT NULL DEFAULT 'low' CHECK (confidence IN ('low', 'medium', 'high')),
  seen         INTEGER NOT NULL DEFAULT 1,
  status       TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'retired')),
  created_at   TEXT,
  updated_at   TEXT
);

CREATE TABLE insight_evidence (
  insight_id INTEGER NOT NULL REFERENCES insights (id) ON DELETE CASCADE,
  post_id    INTEGER NOT NULL REFERENCES posts (id) ON DELETE CASCADE,
  PRIMARY KEY (insight_id, post_id)
);

-- Writer output. Draft-only: status moves draft → approved → published by the owner's hand.
CREATE TABLE drafts (
  id            INTEGER PRIMARY KEY,
  account_id    TEXT NOT NULL REFERENCES accounts (id),
  platform      TEXT NOT NULL,
  format        TEXT NOT NULL,
  title         TEXT,
  idea          TEXT,
  project_id    TEXT NOT NULL,
  path          TEXT NOT NULL,
  reference_url TEXT,
  status        TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'approved', 'published', 'dropped')),
  post_id       INTEGER REFERENCES posts (id),
  created_at    TEXT,
  updated_at    TEXT
);

CREATE TABLE draft_insights (
  draft_id   INTEGER NOT NULL REFERENCES drafts (id) ON DELETE CASCADE,
  insight_id INTEGER NOT NULL REFERENCES insights (id) ON DELETE CASCADE,
  PRIMARY KEY (draft_id, insight_id)
);

CREATE INDEX idx_snap_handle ON creator_snapshots (handle_id, captured_at);
CREATE INDEX idx_metric_post ON metric_snapshots (post_id, captured_at);
CREATE INDEX idx_posts_handle ON posts (handle_id);
CREATE INDEX idx_posts_account ON posts (account_id);
