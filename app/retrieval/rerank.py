"""Cross-encoder reranking (optional cloud stage).

RRF fusion is cheap and recall-oriented; a cross-encoder reorders the fused
candidate set by true query-document relevance. Jina's rerank endpoint is free
tier friendly, so it is opt-in via `RERANK_PROVIDER=jina`.
"""

import logging
from abc import ABC, abstractmethod
from functools import lru_cache

from app.config import get_settings

logger = logging.getLogger("eraga.rerank")
settings = get_settings()


class BaseReranker(ABC):
    model_name = "none"

    @abstractmethod
    async def rerank(
        self, query: str, documents: list[str], top_n: int | None = None
    ) -> list[tuple[int, float]]:
        """Return `(original_index, relevance_score)` sorted best-first."""


class JinaReranker(BaseReranker):
    """Cross-encoder reranking via https://api.jina.ai/v1/rerank."""

    def __init__(
        self, api_key: str, model: str, base_url: str, timeout: int = 60
    ) -> None:
        if not api_key.strip():
            raise ValueError(
                "JINA_API_KEY is not set but RERANK_PROVIDER=jina - add it to .env"
            )
        self._api_key = api_key.strip()
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    @property
    def model_name(self) -> str:
        return f"jina/{self._model}"

    async def rerank(
        self, query: str, documents: list[str], top_n: int | None = None
    ) -> list[tuple[int, float]]:
        if not documents:
            return []
        import httpx

        payload: dict = {"model": self._model, "query": query, "documents": documents}
        if top_n:
            payload["top_n"] = top_n
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                f"{self._base_url}/rerank",
                headers={"Authorization": f"Bearer {self._api_key}"},
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
        return [
            (int(item["index"]), float(item["relevance_score"]))
            for item in data.get("results", [])
        ]


class NoopReranker(BaseReranker):
    """Keeps fusion order; used when reranking is disabled."""

    async def rerank(
        self, query: str, documents: list[str], top_n: int | None = None
    ) -> list[tuple[int, float]]:
        limit = min(top_n or len(documents), len(documents))
        total = max(len(documents), 1)
        return [(index, 1.0 - index / total) for index in range(limit)]


@lru_cache(maxsize=2)
def _cached_reranker(
    provider: str, api_key: str, model: str, base_url: str, timeout: int
) -> BaseReranker:
    if provider == "jina":
        return JinaReranker(api_key=api_key, model=model, base_url=base_url, timeout=timeout)
    return NoopReranker()


def get_reranker(provider: str | None = None) -> BaseReranker:
    provider = provider or settings.rerank_provider
    return _cached_reranker(
        provider,
        settings.jina_api_key,
        settings.jina_rerank_model,
        settings.jina_base_url,
        settings.jina_timeout_s,
    )


def rerank_enabled() -> bool:
    return settings.rerank_provider.lower() not in ("", "none")


async def health() -> tuple[bool, str]:
    if not rerank_enabled():
        return True, "disabled (fusion order)"
    if not settings.jina_api_key.strip():
        return False, "JINA_API_KEY not set"
    return True, f"jina/{settings.jina_rerank_model} (key set)"
