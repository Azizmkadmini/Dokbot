from __future__ import annotations

import json
import os
import time
from collections import defaultdict
from pathlib import Path

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from app.core.config import get_settings

router = APIRouter(prefix="/analytics", tags=["analytics"])
settings = get_settings()

LOGS_DIR = Path("./logs")
LOGS_DIR.mkdir(exist_ok=True)


def require_admin(x_api_key: str = Header(...)):
    if x_api_key != settings.admin_api_key:
        raise HTTPException(status_code=403, detail="Invalid admin API key")


class LogEntry(BaseModel):
    tenant_id: str
    question: str
    answer: str
    latency_ms: int
    cost_usd: float
    tokens: dict
    sources: list[dict]
    timestamp: float = 0.0

    def model_post_init(self, _):
        if not self.timestamp:
            self.timestamp = time.time()


@router.post("/log", summary="Log a conversation turn (called internally)")
async def log_entry(entry: LogEntry):
    log_file = LOGS_DIR / f"{entry.tenant_id}.jsonl"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(entry.model_dump_json() + "\n")
    return {"logged": True}


@router.get("/{tenant_id}", summary="Get usage analytics for a tenant")
async def get_analytics(tenant_id: str, _: str = Depends(require_admin)):
    log_file = LOGS_DIR / f"{tenant_id}.jsonl"
    if not log_file.exists():
        return {"tenant_id": tenant_id, "total_questions": 0, "total_cost_usd": 0, "avg_latency_ms": 0}

    entries = []
    with open(log_file, encoding="utf-8") as f:
        for line in f:
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    if not entries:
        return {"tenant_id": tenant_id, "total_questions": 0}

    total_cost = sum(e.get("cost_usd", 0) for e in entries)
    avg_latency = sum(e.get("latency_ms", 0) for e in entries) / len(entries)
    total_tokens = sum(e.get("tokens", {}).get("prompt", 0) + e.get("tokens", {}).get("completion", 0) for e in entries)

    return {
        "tenant_id": tenant_id,
        "total_questions": len(entries),
        "total_cost_usd": round(total_cost, 4),
        "avg_latency_ms": round(avg_latency),
        "total_tokens": total_tokens,
        "recent_questions": [e["question"] for e in entries[-5:]],
    }
