CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS collections (
  id          SERIAL PRIMARY KEY,
  name        TEXT NOT NULL UNIQUE,
  title       TEXT,
  language    TEXT NOT NULL DEFAULT 'de',
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS documents (
  id             SERIAL PRIMARY KEY,
  collection_id  INT NOT NULL REFERENCES collections(id) ON DELETE CASCADE,
  filename       TEXT NOT NULL,
  title          TEXT,
  checksum       TEXT,
  ingested_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (collection_id, filename)
);

CREATE TABLE IF NOT EXISTS chunks (
  id           SERIAL PRIMARY KEY,
  document_id  INT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  ordinal      INT NOT NULL,
  page         INT,
  section      TEXT,
  content      TEXT NOT NULL,
  embedding    vector(768)
);

CREATE INDEX IF NOT EXISTS idx_documents_collection ON documents(collection_id);
CREATE INDEX IF NOT EXISTS idx_chunks_document ON chunks(document_id);