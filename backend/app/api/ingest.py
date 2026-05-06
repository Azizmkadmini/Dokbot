from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Header
from pydantic import BaseModel, HttpUrl

from app.core.config import get_settings
from app.core.rag import ingest_chunks, delete_source
from app.db.database import get_chroma_client, get_collection
from app.services.ingestion import (
    extract_text_from_pdf,
    extract_text_from_url,
    extract_text_from_plain,
    make_source_id,
)

router = APIRouter(prefix="/ingest", tags=["ingestion"])
settings = get_settings()


def require_admin(x_api_key: str = Header(...)):
    if x_api_key != settings.admin_api_key:
        raise HTTPException(status_code=403, detail="Invalid admin API key")


class UrlIngestRequest(BaseModel):
    tenant_id: str
    url: HttpUrl
    source_name: str | None = None


class DeleteSourceRequest(BaseModel):
    tenant_id: str
    source_id: str


@router.post("/file", summary="Upload a PDF or text file")
async def ingest_file(
    tenant_id: str = Form(...),
    source_name: str = Form(...),
    file: UploadFile = File(...),
    _: str = Depends(require_admin),
):
    content = await file.read()

    if file.filename.endswith(".pdf"):
        text = extract_text_from_pdf(content)
    else:
        text = extract_text_from_plain(content)

    if not text.strip():
        raise HTTPException(status_code=422, detail="Could not extract text from file")

    source_id = make_source_id(file.filename + tenant_id)
    client = get_chroma_client()
    collection = get_collection(client, tenant_id)
    n_chunks = ingest_chunks(collection, text, source_id, source_name or file.filename)

    return {"source_id": source_id, "source_name": source_name, "chunks_ingested": n_chunks}


@router.post("/url", summary="Scrape and ingest a web page")
async def ingest_url(body: UrlIngestRequest, _: str = Depends(require_admin)):
    url_str = str(body.url)
    try:
        text = extract_text_from_url(url_str)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Failed to fetch URL: {exc}")

    if not text.strip():
        raise HTTPException(status_code=422, detail="No text found at URL")

    source_id = make_source_id(url_str + body.tenant_id)
    client = get_chroma_client()
    collection = get_collection(client, body.tenant_id)
    n_chunks = ingest_chunks(collection, text, source_id, body.source_name or url_str)

    return {"source_id": source_id, "source_name": body.source_name or url_str, "chunks_ingested": n_chunks}


@router.delete("/source", summary="Delete all chunks for a source")
async def delete_source_endpoint(body: DeleteSourceRequest, _: str = Depends(require_admin)):
    client = get_chroma_client()
    collection = get_collection(client, body.tenant_id)
    delete_source(collection, body.source_id)
    return {"deleted": True, "source_id": body.source_id}


@router.get("/sources/{tenant_id}", summary="List ingested sources for a tenant")
async def list_sources(tenant_id: str, _: str = Depends(require_admin)):
    client = get_chroma_client()
    collection = get_collection(client, tenant_id)
    results = collection.get(include=["metadatas"])

    sources: dict[str, dict] = {}
    for meta in results["metadatas"]:
        sid = meta["source_id"]
        if sid not in sources:
            sources[sid] = {"source_id": sid, "source_name": meta["source_name"], "chunk_count": 0}
        sources[sid]["chunk_count"] += 1

    return {"tenant_id": tenant_id, "sources": list(sources.values())}
