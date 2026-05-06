import chromadb
from chromadb.config import Settings as ChromaSettings
from functools import lru_cache
from app.core.config import get_settings


@lru_cache
def get_chroma_client() -> chromadb.ClientAPI:
    settings = get_settings()
    return chromadb.PersistentClient(
        path=settings.chroma_persist_dir,
        settings=ChromaSettings(anonymized_telemetry=False),
    )


def get_collection(client: chromadb.ClientAPI, tenant_id: str) -> chromadb.Collection:
    """One collection per tenant (client/business)."""
    return client.get_or_create_collection(
        name=f"tenant_{tenant_id}",
        metadata={"hnsw:space": "cosine"},
    )
