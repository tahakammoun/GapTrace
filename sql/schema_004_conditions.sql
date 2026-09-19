-- requirements.text splits into legal_text (verbatim-ish source wording) and
-- requirement (the checkable statement), plus an optional machine-checkable
-- condition for requirements that only apply given some fact about the target
-- (processing basis, presence of a DPO, cross-border transfers, ...).
ALTER TABLE requirements RENAME COLUMN text TO legal_text;
ALTER TABLE requirements ADD COLUMN IF NOT EXISTS requirement TEXT;
ALTER TABLE requirements ADD COLUMN IF NOT EXISTS condition TEXT;

-- A finding's status (addressed/partial/not_found) only means something once
-- applicability is known: a conditional requirement whose condition doesn't
-- hold for this target is not_applicable, not not_found.
ALTER TABLE findings ADD COLUMN IF NOT EXISTS applicability TEXT
  CHECK (applicability IN ('applicable', 'not_applicable', 'unknown')) DEFAULT 'applicable';
