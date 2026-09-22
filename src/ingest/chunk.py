import re

MAX_CHARS = 900
OVERLAP = 150


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
