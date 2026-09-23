import re

# Counterintuitive but measured, not assumed: smaller chunks made retrieval rank
# WORSE for known-answer test cases (multilingual-e5-base needs enough surrounding
# context to place a chunk in the right topic; an isolated sentence embeds vaguely).
# 2500 roughly matches this document's natural FAQ-section size and put 5/6 known
# answers in the top 4 by cosine rank, vs. 900 putting them at rank 7-15+. Re-check
# with src/eval/metrics.py before changing this again.
MAX_CHARS = 2500
OVERLAP = 300


def chunk_text(text: str) -> list[str]:
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list[str] = []
    buf = ""

    for para in paras:
        if len(buf) + len(para) + 2 <= MAX_CHARS:
            buf = f"{buf}\n\n{para}" if buf else para
            continue
        if buf:
            chunks.append(buf)
            tail = buf[-OVERLAP:]
            buf = f"{tail}\n\n{para}"
        else:
            buf = para
        while len(buf) > MAX_CHARS:
            chunks.append(buf[:MAX_CHARS])
            buf = buf[MAX_CHARS - OVERLAP:]

    if buf:
        chunks.append(buf)
    return chunks
