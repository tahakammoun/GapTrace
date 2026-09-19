from sentence_transformers import SentenceTransformer

_model = SentenceTransformer("intfloat/multilingual-e5-base")


def embed_passages(texts: list[str]):
    return _model.encode([f"passage: {t}" for t in texts], normalize_embeddings=True, batch_size=32)


def embed_query(text: str):
    return _model.encode(f"query: {text}", normalize_embeddings=True)
