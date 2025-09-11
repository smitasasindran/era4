import faiss
import numpy as np
from typing import List, Dict

from openai import OpenAI

client = OpenAI()


def openai_embed(texts: List[str]) -> np.ndarray:
    resp = client.embeddings.create(model="text-embedding-3-small", input=texts)
    return np.array([d.embedding for d in resp.data])


# Suppose you already have transcripts: a list of dicts
# transcripts = [{"text": "some snippet", "start": 72, "end": 85}, ...]

# 1. Embed the transcript texts
def build_faiss_index(transcripts: List[Dict], embed_fn) -> (faiss.IndexFlatIP, List[Dict]):
    """
    Build a FAISS index from transcript snippets.
    :param transcripts: list of {"text": str, "start": int, "end": int}
    :param embed_fn: function that takes a list of texts and returns embeddings (np.array)
    """
    print(f"Transcripts are: {transcripts[0]}")
    texts = [t.text for t in transcripts]
    embeddings = embed_fn(texts)  # shape (N, D)

    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)  # cosine similarity if normalized
    faiss.normalize_L2(embeddings)
    index.add(embeddings)

    return index, transcripts


# 2. Search function
def search_transcripts(query: str, index, transcripts: List[Dict], embed_fn, k=5):
    query_emb = embed_fn([query])
    faiss.normalize_L2(query_emb)

    D, I = index.search(query_emb, k)
    results = []
    for score, idx in zip(D[0], I[0]):
        if idx == -1:
            continue
        snippet = transcripts[idx]
        results.append({
            "text": snippet["text"],
            "start": snippet["start"],
            "end": snippet["end"],
            "score": float(score)
        })
    return results
