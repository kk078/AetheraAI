-- Aethera AI Worker - D1 schema
-- Apply with: wrangler d1 execute aethera-ai-db --file=./schema.sql

CREATE TABLE IF NOT EXISTS conversations (
  id          TEXT PRIMARY KEY,
  user_id     TEXT NOT NULL,
  title       TEXT DEFAULT '',
  created_at  TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS messages (
  id               INTEGER PRIMARY KEY AUTOINCREMENT,
  conversation_id  TEXT NOT NULL,
  role             TEXT NOT NULL,
  content          TEXT NOT NULL,
  created_at       TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id);

-- Phase 3 reference datasets (seeded separately; sample data for now).
CREATE TABLE IF NOT EXISTS code_set (
  code        TEXT NOT NULL,
  code_type   TEXT NOT NULL,
  description TEXT NOT NULL,
  parent      TEXT DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_code_set_code ON code_set(code);
CREATE INDEX IF NOT EXISTS idx_code_set_parent ON code_set(parent);

CREATE TABLE IF NOT EXISTS fee_rvu (
  cpt         TEXT PRIMARY KEY,
  work_rvu    REAL NOT NULL,
  pe_rvu_nf   REAL NOT NULL,
  mp_rvu_nf   REAL NOT NULL,
  status      TEXT DEFAULT 'A',
  description TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS gpci (
  locality   TEXT PRIMARY KEY,
  work_gpci  REAL NOT NULL,
  pe_gpci    REAL NOT NULL,
  mp_gpci    REAL NOT NULL,
  name       TEXT DEFAULT '',
  state      TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS denial_code (
  code            TEXT PRIMARY KEY,
  ctype           TEXT NOT NULL,
  description     TEXT NOT NULL,
  category        TEXT DEFAULT 'unknown',
  appeal_priority TEXT DEFAULT 'medium'
);

-- Phase 5: CMS/regulatory updates fetched by Cron Triggers.
CREATE TABLE IF NOT EXISTS knowledge_updates (
  id             TEXT PRIMARY KEY,
  source         TEXT NOT NULL,
  source_key     TEXT NOT NULL,
  title          TEXT NOT NULL,
  summary        TEXT DEFAULT '',
  url            TEXT DEFAULT '',
  category       TEXT DEFAULT 'healthcare_regulatory',
  published_date TEXT DEFAULT '',
  fetched_at     TEXT NOT NULL DEFAULT (datetime('now')),
  applied        INTEGER DEFAULT 0
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_ku_source_key ON knowledge_updates(source, source_key);
CREATE INDEX IF NOT EXISTS idx_ku_fetched ON knowledge_updates(fetched_at);

-- Phase 6 batch A: NCCI edits, MS-DRGs, APCs.
CREATE TABLE IF NOT EXISTS cci_edit (
  col1 TEXT NOT NULL, col2 TEXT NOT NULL,
  modifier_indicator INTEGER NOT NULL, rationale TEXT DEFAULT ''
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_cci_pair ON cci_edit(col1, col2);
CREATE INDEX IF NOT EXISTS idx_cci_col1 ON cci_edit(col1);
CREATE INDEX IF NOT EXISTS idx_cci_col2 ON cci_edit(col2);

CREATE TABLE IF NOT EXISTS ms_drg (
  drg TEXT PRIMARY KEY, description TEXT NOT NULL, weight REAL NOT NULL,
  gmlos REAL DEFAULT 0, type TEXT DEFAULT 'MEDICAL', severity TEXT DEFAULT 'none'
);
CREATE TABLE IF NOT EXISTS drg_dx (
  dx TEXT PRIMARY KEY, base_drg TEXT NOT NULL, description TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS apc (
  apc TEXT PRIMARY KEY, description TEXT NOT NULL, status_indicator TEXT DEFAULT 'S',
  payment_rate REAL NOT NULL, weight REAL DEFAULT 0, device_intensive INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS cpt_apc (
  cpt TEXT PRIMARY KEY, apc TEXT NOT NULL, description TEXT DEFAULT ''
);
