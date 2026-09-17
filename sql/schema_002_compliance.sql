CREATE TABLE IF NOT EXISTS regulations (
  id           SERIAL PRIMARY KEY,
  name         TEXT NOT NULL UNIQUE,
  title        TEXT,
  version      TEXT NOT NULL DEFAULT 'v1',
  valid_from   DATE,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS requirements (
  id             SERIAL PRIMARY KEY,
  regulation_id  INT NOT NULL REFERENCES regulations(id) ON DELETE CASCADE,
  key            TEXT NOT NULL,
  ref            TEXT NOT NULL,
  text           TEXT NOT NULL,
  obligation     TEXT NOT NULL DEFAULT 'must',
  category       TEXT,
  embedding      vector(768),
  UNIQUE (regulation_id, key)
);

CREATE TABLE IF NOT EXISTS targets (
  id             SERIAL PRIMARY KEY,
  document_id    INT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  regulation_id  INT NOT NULL REFERENCES regulations(id),
  created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (document_id, regulation_id)
);

CREATE TABLE IF NOT EXISTS findings (
  id              SERIAL PRIMARY KEY,
  target_id       INT NOT NULL REFERENCES targets(id) ON DELETE CASCADE,
  requirement_id  INT NOT NULL REFERENCES requirements(id) ON DELETE CASCADE,
  status          TEXT NOT NULL CHECK (status IN ('addressed','partial','not_found')),
  evidence_chunk  INT REFERENCES chunks(id),
  evidence_quote  TEXT,
  rationale       TEXT,
  confidence      REAL,
  human_status    TEXT CHECK (human_status IN ('addressed','partial','not_found')),
  reviewed_at     TIMESTAMPTZ,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (target_id, requirement_id)
);

CREATE INDEX IF NOT EXISTS idx_requirements_regulation ON requirements(regulation_id);
CREATE INDEX IF NOT EXISTS idx_findings_target ON findings(target_id);
