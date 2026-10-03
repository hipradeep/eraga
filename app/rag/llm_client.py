"""LLM providers.

Default is **Groq** cloud inference (OpenAI-compatible, free tier). The `fake`
provider returns a deterministic extractive answer so the test suite and offline
demos run with no API key and no network.
"""

import json
import logging
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass
from functools import lru_cache

from app.config import get_settings

logger = logging.getLogger("eraga.llm")
settings = get_settings()


@dataclass(slots=True)
class LLMResult:
    text: str
    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


class BaseLLM(ABC):
    cost_per_1k_input: float = 0.0
    cost_per_1k_output: float = 0.0

    @property
    @abstractmethod
    def model_name(self) -> str: ...

    @abstractmethod
    async def complete(self, system: str, user: str) -> LLMResult: ...

    @abstractmethod
    def stream(self, system: str, user: str) -> AsyncIterator[str]: ...

    def estimate_cost(self, result: LLMResult) -> float:
        return (
            result.input_tokens / 1000 * self.cost_per_1k_input
            + result.output_tokens / 1000 * self.cost_per_1k_output
        )


class GroqLLM(BaseLLM):
    """Groq cloud inference over the OpenAI-compatible chat completions API.

    Groq serves open-weight models at very high speed on a free tier. Text
    generation only — embeddings run on Jina (or the offline `HashEmbedder`),
    because Groq exposes no embeddings endpoint.

    DATA EGRESS: prompts (including retrieved document text) are sent to Groq's
    API. Do not point this at a corpus that must not leave your network.
    """

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str,
        temperature: float,
        timeout: int,
    ) -> None:
        if not api_key.strip():
            raise ValueError(
                "GROQ_API_KEY is not set - add it to .env, or set LLM_PROVIDER to 'fake'"
            )
        self._api_key = api_key.strip()
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._temperature = temperature
        self._timeout = timeout

    @property
    def model_name(self) -> str:
        return f"groq/{self._model}"

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    def _payload(self, system: str, user: str, stream: bool) -> dict:
        return {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": self._temperature,
            "stream": stream,
        }

    @staticmethod
    def _usage(data: dict) -> tuple[int, int]:
        usage = data.get("usage") or {}
        return int(usage.get("prompt_tokens") or 0), int(usage.get("completion_tokens") or 0)

    def _client(self):
        import httpx

        return httpx.AsyncClient(timeout=self._timeout)

    async def complete(self, system: str, user: str) -> LLMResult:
        async with self._client() as client:
            response = await client.post(
                f"{self._base_url}/chat/completions",
                headers=self._headers(),
                json=self._payload(system, user, False),
            )
            response.raise_for_status()
            data = response.json()

        choices = data.get("choices") or [{}]
        text = ((choices[0].get("message") or {}).get("content") or "").strip()
        input_tokens, output_tokens = self._usage(data)
        return LLMResult(text=text, input_tokens=input_tokens, output_tokens=output_tokens)

    async def stream(self, system: str, user: str) -> AsyncIterator[str]:
        async with self._client() as client:
            async with client.stream(
                "POST",
                f"{self._base_url}/chat/completions",
                headers=self._headers(),
                json=self._payload(system, user, True),
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    line = line.strip()
                    if not line or not line.startswith("data:"):
                        continue
                    payload = line.removeprefix("data:").strip()
                    if payload == "[DONE]":
                        break
                    chunk = json.loads(payload)
                    choices = chunk.get("choices") or [{}]
                    piece = (choices[0].get("delta") or {}).get("content") or ""
                    if piece:
                        yield piece


class FakeLLM(BaseLLM):
    """Deterministic extractive stand-in used by tests and offline demos."""

    model_name = "fake/extractive"

    def __init__(self, max_sentences: int = 3) -> None:
        self._max_sentences = max_sentences

    def _answer(self, user: str) -> str:
        import re

        context = user.split("CONTEXT:", 1)[-1].split("QUESTION:", 1)[0]
        question = user.split("QUESTION:", 1)[-1].split("ANSWER", 1)[0].strip()
        if not context.strip():
            return "I don't have enough information to answer this."
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", context) if len(s.strip()) > 20]
        picks = sentences[: self._max_sentences]
        return f'Based on the retrieved context, for "{question}": ' + " ".join(picks)

    async def complete(self, system: str, user: str) -> LLMResult:
        text = self._answer(user)
        return LLMResult(text=text, input_tokens=len(user) // 4, output_tokens=len(text) // 4)

    async def stream(self, system: str, user: str) -> AsyncIterator[str]:
        for word in self._answer(user).split(" "):
            yield word + " "


@lru_cache(maxsize=4)
def _cached_llm(
    provider: str,
    groq_api_key: str,
    groq_base_url: str,
    groq_model: str,
    temperature: float,
    timeout: int,
) -> BaseLLM:
    if provider == "fake":
        return FakeLLM()
    return GroqLLM(
        api_key=groq_api_key,
        model=groq_model,
        base_url=groq_base_url,
        temperature=temperature,
        timeout=timeout,
    )


def get_llm(provider: str | None = None) -> BaseLLM:
    provider = provider or settings.llm_provider
    return _cached_llm(
        provider,
        settings.groq_api_key,
        settings.groq_base_url,
        settings.groq_model,
        settings.llm_temperature,
        settings.llm_timeout_s,
    )


async def health() -> tuple[bool, str]:
    if settings.llm_provider == "fake":
        return True, "fake/extractive (offline)"
    if not settings.groq_api_key.strip():
        return False, "GROQ_API_KEY not set"
    return True, f"groq/{settings.groq_model} (key set)"
