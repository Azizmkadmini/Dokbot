from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    openai_api_key: str
    openai_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"

    chroma_persist_dir: str = "./chroma_db"
    chunk_size: int = 500
    chunk_overlap: int = 50
    top_k: int = 5
    score_threshold: float = 0.3

    system_prompt: str = (
        "You are a helpful customer support assistant. "
        "Answer questions using ONLY the context provided. "
        "If the answer is not in the context, say you don't know and suggest contacting support. "
        "Be concise, friendly, and professional. Reply in the same language as the user."
    )

    cors_origins: list[str] = ["*"]
    api_key_header: str = "X-API-Key"
    admin_api_key: str = "change-me-in-production"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()
