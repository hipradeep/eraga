"""Embedding providers.

Default is **Jina AI** cloud embeddings (`jina-embeddings-v3`, 768-dim via
Matryoshka truncation). The `hash` provider is a deterministic, dependency-free
hashing embedder used by the test suite so the whole pipeline runs offline.

DATA EGRESS: the Jina provider sends chunk text and queries to Jina's API. Use
the `hash` provider if the corpus must not leave your network.
"""

import hashlib
import math
import re
from abc import ABC, abstractmethod
from functools import lru_cache

from app.config import get_settings

settings = get_settings()

_TOKEN = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    return _TOKEN.findall(text.lower())


class BaseEmbedder(ABC):
    @abstractmethod
    async def embed_documents(self, texts: list[str]) -> list[list[float]]: ...

    @abstractmethod
    async def embed_query(self, text: str) -> list[float]: ...

    @property
    @abstractmethod
    def dimension(self) -> int: ...

    @property
    @abstractmethod
    def model_name(self) -> str: ...


class JinaEmbedder(BaseEmbedder):
    """Cloud embeddings via the Jina AI API (jina-embeddings-v3).

    v3 is Matryoshka-trained, so `dimensions` truncates the native 1024-dim
    vector while keeping it usable — we request 768 to stay schema-compatible.
    Task prefixes (`retrieval.query` / `retrieval.passage`) are applied because
    v3 expects them for best asymmetric retrieval quality.
    """

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str,
        dimension: int,
        timeout: int = 60,
    ) -> None:
        if not api_key.strip():
            raise ValueError(
                "JINA_API_KEY is not set - add it to .env, "
                "or set EMBEDDING_PROVIDER to 'hash'"
            )
        self._api_key = api_key.strip()
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._dimension = dimension
        self._timeout = timeout

    @property
    def dimension(self) -> int:
        return self._dimension

    @property
    def model_name(self) -> str:
        return f"jina/{self._model}"

    async def _post(self, texts: list[str], task: str) -> list[list[float]]:
        import httpx

        payload = {
            "model": self._model,
            "input": texts,
            "dimensions": self._dimension,
            "task": task,
        }
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                f"{self._base_url}/embeddings",
                headers={"Authorization": f"Bearer {self._api_key}"},
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
        vectors: list[list[float]] = [item["embedding"] for item in data["data"]]
        self._validate(vectors)
        return vectors

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        return await self._post(texts, task="retrieval.passage")

    async def embed_query(self, text: str) -> list[float]:
        return (await self._post([text], task="retrieval.query"))[0]

    def _validate(self, vectors: list[list[float]]) -> None:
        if not vectors:
            raise RuntimeError("embedding provider returned no vectors")
        actual = len(vectors[0])
        if actual != self._dimension:
            raise ValueError(
                f"embedding dimension mismatch: model '{self._model}' returned {actual}, "
                f"but schema is vector({self._dimension}). Change EMBEDDING_DIM and "
                f"ALTER TABLE document_chunks ALTER COLUMN embedding TYPE vector({actual});"
            )


class HashEmbedder(BaseEmbedder):
    """Deterministic hashing embedder — offline, no model server, test-friendly.

    Projects token hashes into a fixed-width vector with sublinear term weighting.
    Lexically similar texts land near each other, which is enough to exercise and
    verify the retrieval pipeline end to end.
    """

    def __init__(self, dimension: int = 768) -> None:
        self._dimension = dimension

    @property
    def dimension(self) -> int:
        return self._dimension

    @property
    def model_name(self) -> str:
        return f"hash-{self._dimension}"

    def _encode(self, text: str) -> list[float]:
        vector = [0.0] * self._dimension
        tokens = tokenize(text)
        if not tokens:
            return vector
        for token in tokens:
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
            index = int.from_bytes(digest[:4], "big") % self._dimension
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign
        norm = math.sqrt(sum(value * value for value in vector))
        if norm:
            vector = [value / norm for value in vector]
        return vector

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._encode(text) for text in texts]

    async def embed_query(self, text: str) -> list[float]:
        return self._encode(text)


@lru_cache(maxsize=4)
def _cached_embedder(
    provider: str,
    dimension: int,
    jina_api_key: str,
    jina_base_url: str,
    jina_model: str,
    jina_timeout: int,
) -> BaseEmbedder:
    if provider == "hash":
        return HashEmbedder(dimension=dimension)
    return JinaEmbedder(
        api_key=jina_api_key,
        model=jina_model,
        base_url=jina_base_url,
        dimension=dimension,
        timeout=jina_timeout,
    )


def get_embedder(provider: str | None = None) -> BaseEmbedder:
    provider = provider or settings.embedding_provider
    return _cached_embedder(
        provider,
        settings.embedding_dim,
        settings.jina_api_key,
        settings.jina_base_url,
        settings.jina_embedding_model,
        settings.jina_timeout_s,
    )


async def embed_documents(texts: list[str]) -> list[list[float]]:
    return await get_embedder().embed_documents(texts)


async def embed_query(text: str) -> list[float]:
    return await get_embedder().embed_query(text)


async def health() -> tuple[bool, str]:
    """Check the embedding backend; used by /health/models."""
    if settings.embedding_provider == "hash":
        return True, f"hash-{settings.embedding_dim} (offline)"
    if not settings.jina_api_key.strip():
        return False, "JINA_API_KEY not set"
    return True, f"jina/{settings.jina_embedding_model} (key set)"
