from __future__ import annotations

import re
import time
import logging
from typing import Generator

import tiktoken
from openai import OpenAI
from chromadb import Collection

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()
_openai = OpenAI(api_key=settings.openai_api_key)
_enc = tiktoken.get_encoding("cl100k_base")


# ── Chunking ─────────────────────────────────────────────────────────────────

def _split_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Token-aware recursive text splitter."""
    tokens = _enc.encode(text)
    chunks: list[str] = []
    start = 0
    while start < len(tokens):
        end = min(start + chunk_size, len(tokens))
        chunks.append(_enc.decode(tokens[start:end]))
        start += chunk_size - overlap
    return [c.strip() for c in chunks if c.strip()]


# ── Embeddings ────────────────────────────────────────────────────────────────

def embed_texts(texts: list[str]) -> list[list[float]]:
    response = _openai.embeddings.create(
        model=settings.openai_embedding_model,
        input=texts,
    )
    return [item.embedding for item in response.data]


# ── Ingestion ─────────────────────────────────────────────────────────────────

def ingest_chunks(
    collection: Collection,
    text: str,
    source_id: str,
    source_name: str,
    chunk_size: int | None = None,
    overlap: int | None = None,
) -> int:
    chunk_size = chunk_size or settings.chunk_size
    overlap = overlap or settings.chunk_overlap

    chunks = _split_text(text, chunk_size, overlap)
    if not chunks:
        return 0

    embeddings = embed_texts(chunks)
    ids = [f"{source_id}__chunk_{i}" for i in range(len(chunks))]
    metadatas = [{"source_id": source_id, "source_name": source_name, "chunk_index": i} for i in range(len(chunks))]

    # Upsert so re-ingesting same source is idempotent
    collection.upsert(ids=ids, embeddings=embeddings, documents=chunks, metadatas=metadatas)
    logger.info("Ingested %d chunks from source '%s'", len(chunks), source_name)
    return len(chunks)


def delete_source(collection: Collection, source_id: str) -> None:
    results = collection.get(where={"source_id": source_id})
    if results["ids"]:
        collection.delete(ids=results["ids"])
        logger.info("Deleted %d chunks for source '%s'", len(results["ids"]), source_id)


# ── Retrieval ─────────────────────────────────────────────────────────────────

def retrieve(collection: Collection, query: str, top_k: int | None = None) -> list[dict]:
    top_k = top_k or settings.top_k
    query_embedding = embed_texts([query])[0]

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(top_k, collection.count() or 1),
        include=["documents", "metadatas", "distances"],
    )

    docs = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        score = 1 - dist  # cosine similarity
        if score >= settings.score_threshold:
            docs.append({"text": doc, "source": meta.get("source_name", ""), "score": round(score, 3)})

    return docs


# ── Generation ────────────────────────────────────────────────────────────────

def build_context(docs: list[dict]) -> str:
    return "\n\n---\n\n".join(f"[Source: {d['source']}]\n{d['text']}" for d in docs)


def chat(
    collection: Collection,
    question: str,
    history: list[dict] | None = None,
    stream: bool = False,
) -> dict:
    t0 = time.perf_counter()
    docs = retrieve(collection, question)
    context = build_context(docs) if docs else ""

    messages = [{"role": "system", "content": settings.system_prompt}]
    if context:
        messages.append({"role": "system", "content": f"Use this context to answer:\n\n{context}"})
    if history:
        messages.extend(history[-6:])  # keep last 3 turns
    messages.append({"role": "user", "content": question})

    response = _openai.chat.completions.create(
        model=settings.openai_model,
        messages=messages,
        temperature=0.2,
        max_tokens=600,
    )

    answer = response.choices[0].message.content
    latency_ms = round((time.perf_counter() - t0) * 1000)
    cost_usd = _estimate_cost(response.usage)

    return {
        "answer": answer,
        "sources": [{"source": d["source"], "score": d["score"]} for d in docs],
        "latency_ms": latency_ms,
        "cost_usd": cost_usd,
        "tokens": {"prompt": response.usage.prompt_tokens, "completion": response.usage.completion_tokens},
    }


def _estimate_cost(usage) -> float:
    # gpt-4o-mini pricing (May 2026)
    input_cost = (usage.prompt_tokens / 1_000_000) * 0.15
    output_cost = (usage.completion_tokens / 1_000_000) * 0.60
    return round(input_cost + output_cost, 6)
