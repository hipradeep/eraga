from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "ERAGA"
    environment: str = "dev"
    log_level: str = "INFO"

    # ---- LLM: Groq (OpenAI-compatible, free tier) ----
    llm_provider: str = "groq"  # groq | fake
    llm_temperature: float = 0.0
    llm_timeout_s: int = 180
    groq_api_key: str = ""
    groq_base_url: str = "https://api.groq.com/openai/v1"
    groq_model: str = "openai/gpt-oss-20b"  # or openai/gpt-oss-120b, qwen/qwen3.8-27b

    # ---- Embeddings: Jina AI (cloud, free tier) ----
    # jina-embeddings-v3 is Matryoshka, so `embedding_dim` truncates the native
    # 1024-dim vector to match the vector(768) schema. `hash` is the offline
    # deterministic fallback used by tests.
    embedding_provider: str = "jina"  # jina | hash
    jina_api_key: str = ""
    jina_base_url: str = "https://api.jina.ai/v1"
    jina_embedding_model: str = "jina-embeddings-v3"
    jina_timeout_s: int = 60

    # ---- Reranking: Jina cross-encoder (cloud, free tier) ----
    rerank_provider: str = "jina"  # jina | none
    jina_rerank_model: str = "jina-reranker-v2-base-multilingual"

    embedding_dim: int = 768  # schema dimension, used by Jina and HashEmbedder

    # ---- Infrastructure ----
    database_url: str = "postgresql+asyncpg://eraga:eraga@localhost:55432/eraga"
    redis_url: str = "redis://localhost:6379/0"

    # ---- Retrieval tuning ----
    top_k: int = 8
    rerank_top_n: int = 5
    chunk_size: int = 900
    chunk_overlap: int = 120

    # ---- Security ----
    jwt_secret: str = "change-me-in-production"
    admin_roles: str = "admin"

    @property
    def admin_role_list(self) -> list[str]:
        return [role.strip() for role in self.admin_roles.split(",") if role.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
