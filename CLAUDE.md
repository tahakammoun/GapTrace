# GapTrace

Compliance gap-checker. Given a target document (privacy notice, policy, contract) and a
regulation corpus, produce a traceable compliance matrix: requirement → status
(addressed / partial / not found) → verbatim evidence from the target → confidence.

## Stack
Python 3.12 (uv), FastAPI, Postgres 16 + pgvector (Docker), sentence-transformers
(multilingual-e5-base, local), Gemini Flash via Google AI Studio free tier, Groq as
second provider.

## Layout
src/ingest        parse, chunk, embed, ingest pipeline (targets and regulations)
src/requirements  requirement extraction from regulation text
src/checking      per-requirement retrieval and coverage classification
src/llm           provider clients, disk cache, backoff
src/api           FastAPI app
src/eval          metrics
requirements/     curated requirement catalogs, one JSONL per regulation.
eval/gold/        hand-labelled compliance matrices, one JSONL per target document
data/raw/         source PDFs (gitignored)

## Rules
- No LangChain / LlamaIndex. Retrieval and classification logic stays hand-written.
- The requirements catalog is extracted ONCE, curated by a human, then frozen. Never
  re-extract at request time.
- Evidence quotes must be verbatim substrings of the cited chunk, verified in code.
- Report metrics per status class. A false "addressed" is far worse than a false
  "not found".
- All model calls go through src/llm/client.py so they are cached.
- Nothing is done until the eval passes its thresholds.
- DO NOT DO ANYTHING WITHOUT EXPLAINING THE WHY AND THE HOW THIS IS A LEARNING PROJECT SO THE GOAL IS TO LEARN
