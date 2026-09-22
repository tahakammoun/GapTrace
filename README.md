# GapTrace

Compliance gap-checker: given a target document and a regulation, produce a traceable
matrix of requirement → status → evidence → confidence.

**Status:** in development.

## Progress
- [x] Project skeleton, dependencies, tooling
- [x] Postgres + pgvector, collections schema
- [x] Requirements catalog (DSGVO Art. 12–14)
- [ ] Target ingest and coverage checking
- [ ] Evaluation harness and baseline
- [ ] Review queue and matrix export
- [ ] Second regulation, routing, CI, deployment