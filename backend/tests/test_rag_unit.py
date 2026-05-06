"""Unit tests for RAG core logic — no OpenAI calls."""
import os
os.environ.setdefault("OPENAI_API_KEY", "sk-test")
os.environ.setdefault("ADMIN_API_KEY", "test-admin-key")

import pytest
from app.core.rag import _split_text, build_context


def test_split_text_basic():
    text = "word " * 600  # 600 tokens
    chunks = _split_text(text, chunk_size=200, overlap=20)
    assert len(chunks) >= 3
    for chunk in chunks:
        assert len(chunk) > 0


def test_split_text_short():
    text = "Hello world"
    chunks = _split_text(text, chunk_size=500, overlap=50)
    assert len(chunks) == 1
    assert chunks[0] == "Hello world"


def test_split_text_empty():
    chunks = _split_text("", chunk_size=500, overlap=50)
    assert chunks == []


def test_build_context_empty():
    assert build_context([]) == ""


def test_build_context_single():
    docs = [{"text": "RAG is great", "source": "faq.pdf", "score": 0.9}]
    context = build_context(docs)
    assert "RAG is great" in context
    assert "faq.pdf" in context


def test_build_context_multiple():
    docs = [
        {"text": "First chunk", "source": "doc1.pdf", "score": 0.9},
        {"text": "Second chunk", "source": "doc2.pdf", "score": 0.8},
    ]
    context = build_context(docs)
    assert "First chunk" in context
    assert "Second chunk" in context
    assert "---" in context
