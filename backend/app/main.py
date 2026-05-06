from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.api import chat, ingest, analytics

settings = get_settings()

app = FastAPI(
    title="RAG Support API",
    description="Multi-tenant RAG chatbot for customer support. Ingest docs, ask questions.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router)
app.include_router(ingest.router)
app.include_router(analytics.router)


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok", "version": "1.0.0"}
