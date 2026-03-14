from __future__ import annotations
import asyncio
from typing import Any, Optional
from openai import AsyncOpenAI, OpenAIError

class OpenAIWrapper:
    """Client OpenAI avec logique de réessai et typage JSON."""

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini"):
        # Le client est maintenant initialisé de manière sécurisée
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model

    async def _retry(self, coro_factory, retries: int = 3):
        """Gestion des erreurs API avec backoff exponentiel."""
        for attempt in range(retries):
            try:
                return await coro_factory()
            except OpenAIError as exc:
                if attempt == retries - 1:
                    raise exc
                await asyncio.sleep(1.0 * (2**attempt))

    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.0,
        response_format: Optional[dict[str, Any]] = None,
    ) -> str:
        """Appel simple à l'API Chat Completions."""
        async def _call():
            resp = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                response_format=response_format,
            )
            return resp.choices[0].message.content or ""

        return await self._retry(_call)

    async def chat_completion_json(self, messages: list[dict[str, str]]) -> str:
        """Force explicitement le retour au format JSON."""
        return await self.chat_completion(
            messages,
            response_format={"type": "json_object"}
        )