# PAI

Document question answering over German documents. Ingest PDFs, retrieve relevant
passages, answer with citations. Low-confidence cases go to a human review queue
instead of being guessed at. Everything is measured against a hand-written gold set
that runs in CI.

## Stack

- Python 3.12, managed with uv
- FastAPI + uvicorn for the HTTP layer
- Postgres 16 + pgvector, in Docker
- sentence-transformers, multilingual-e5-base (768 dims), running locally
- Gemini Flash via Google AI Studio free tier; Groq as second provider
- pytest, ruff

## Layout

src/ingest       parse PDFs, chunk, embed, ingest pipeline
src/retrieval    vector search, BM25, hybrid, reranking
src/generation   prompt construction, answer generation, citation parsing
src/llm          provider clients, disk cache, retry/backoff, token counting
src/api          FastAPI app
src/eval         metric calculations
config/          one YAML per collection
data/raw/        source PDFs (gitignored)
eval/gold/       hand-written eval sets, one JSONL per collection
eval/results/    generated run output (gitignored)
sql/             schema definitions
scripts/         one-off utilities, not part of the system

## Rules

1. No LangChain, no LlamaIndex, no vector-store wrappers. The retrieval loop is
   hand-written. I need to be able to explain every line of it.
2. The engine is corpus-agnostic. Nothing specific to TU Darmstadt documents belongs
   in src/. Documents belong to a named collection; collection settings live in
   config/<name>.yaml.
3. eval/gold/*.jsonl is written by hand. Never generate, extend or edit it with a
   model. This is absolute.
4. Every model call goes through src/llm/client.py, so it is cached and rate-limited
   in one place.
5. Nothing is "done" until `uv run python eval/run.py` passes the thresholds.
6. One change per commit, with a message describing the change.

## Working style

- Propose the approach before writing code for anything in retrieval, generation,
  eval or the confidence logic. I want to choose the design in those areas.
- Scaffolding, Docker, CI config and the review UI can be written directly.
- Prefer a small, readable implementation over a general one. No plugin
  architectures, no abstractions with a single implementation.
- If a change touches retrieval or prompting, re-run the eval and tell me what moved.
- DO NOT DO ANYTHING WITHOUT EXPLAINING THE WHY AND THE HOW THIS IS A LEARNING PROJECT SO THE GOAL IS TO LEARN
