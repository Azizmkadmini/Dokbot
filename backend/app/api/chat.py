from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.rag import chat
from app.db.database import get_chroma_client, get_collection

router = APIRouter(prefix="/chat", tags=["chat"])


class Message(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    tenant_id: str
    question: str
    history: list[Message] = []


class ChatResponse(BaseModel):
    answer: str
    sources: list[dict]
    latency_ms: int
    cost_usd: float
    tokens: dict


@router.post("", response_model=ChatResponse, summary="Ask a question to the RAG bot")
async def chat_endpoint(body: ChatRequest):
    client = get_chroma_client()
    collection = get_collection(client, body.tenant_id)

    if collection.count() == 0:
        raise HTTPException(
            status_code=404,
            detail=f"No documents ingested for tenant '{body.tenant_id}'. Please ingest content first.",
        )

    history = [{"role": m.role, "content": m.content} for m in body.history]

    try:
        result = chat(collection, body.question, history)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    return ChatResponse(**result)
