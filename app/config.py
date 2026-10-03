from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "ERAGA"
    environment: str = "dev"
    log_level: str = "INFO"

    database_url: str = "postgresql+asyncpg://eraga:eraga@localhost:5432/eraga"
    redis_url: str = "redis://localhost:6379/0"

    llm_provider: str = "gemini"
    gemini_api_key: str = ""
    openai_api_key: str = ""
    anthropic_api_key: str = ""

    embedding_provider: str = "openai"
    embedding_model: str = "text-embedding-3-small"
    embedding_dim: int = 1536

    top_k: int = 8
    rerank_top_n: int = 5

    jwt_secret: str = "change-me-in-production"
    admin_roles: str = "admin"

    @property
    def admin_role_list(self) -> list[str]:
        return [role.strip() for role in self.admin_roles.split(",") if role.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
