"""Base agent with Anthropic client, retry logic, and prompt caching."""

import asyncio
import hashlib
import time
from abc import ABC, abstractmethod
from typing import Any

import anthropic
from anthropic.types import MessageParam

from src.utils.logger import log


class BaseAgent(ABC):
    """Abstract base for all content factory agents with shared LLM capabilities."""

    def __init__(
        self,
        api_key: str,
        model: str = "claude-sonnet-4-6",
        max_tokens: int = 2000,
        temperature: float = 0.3,
        max_retries: int = 3,
        backoff_factor: float = 2.0,
        initial_delay: float = 1.0,
    ):
        self.client = anthropic.AsyncAnthropic(api_key=api_key)
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.initial_delay = initial_delay

    @abstractmethod
    def system_prompt(self) -> str:
        """Return the system prompt for this agent."""

    @abstractmethod
    async def run(self, **kwargs) -> Any:
        """Execute the agent's task."""

    def _build_messages(self, user_content: str | list[dict]) -> list[MessageParam]:
        """Build message list. If user_content is a list, it includes images."""
        if isinstance(user_content, list):
            return [{"role": "user", "content": user_content}]
        return [{"role": "user", "content": user_content}]

    async def _call_llm(
        self,
        user_content: str | list[dict],
        system_override: str | None = None,
        model_override: str | None = None,
        max_tokens_override: int | None = None,
    ) -> str:
        """Call the Anthropic API with retry logic and exponential backoff."""
        system_prompt = system_override or self.system_prompt()
        model = model_override or self.model
        max_tokens = max_tokens_override or self.max_tokens
        messages = self._build_messages(user_content)

        last_error = None
        for attempt in range(self.max_retries):
            try:
                start = time.monotonic()
                response = await self.client.messages.create(
                    model=model,
                    max_tokens=max_tokens,
                    temperature=self.temperature,
                    system=system_prompt,
                    messages=messages,
                )
                elapsed = time.monotonic() - start
                log.debug(f"[{self.__class__.__name__}] API call: {elapsed:.1f}s, model={model}, tokens={response.usage.output_tokens if response.usage else '?'}")
                return response.content[0].text

            except anthropic.RateLimitError as e:
                last_error = e
                delay = self.initial_delay * (self.backoff_factor ** attempt)
                log.warning(f"[{self.__class__.__name__}] Rate limited (attempt {attempt + 1}/{self.max_retries}), retrying in {delay:.1f}s...")
                await asyncio.sleep(delay)

            except anthropic.APIStatusError as e:
                if e.status_code < 500:
                    log.error(f"[{self.__class__.__name__}] API error: {e.status_code} - {e.message}")
                    raise
                last_error = e
                delay = self.initial_delay * (self.backoff_factor ** attempt)
                log.warning(f"[{self.__class__.__name__}] Server error {e.status_code} (attempt {attempt + 1}/{self.max_retries}), retrying in {delay:.1f}s...")
                await asyncio.sleep(delay)

            except Exception as e:
                last_error = e
                delay = self.initial_delay * (self.backoff_factor ** attempt)
                log.warning(f"[{self.__class__.__name__}] {type(e).__name__}: {e} (attempt {attempt + 1}/{self.max_retries})")
                await asyncio.sleep(delay)

        raise RuntimeError(f"[{self.__class__.__name__}] All {self.max_retries} retries exhausted. Last error: {last_error}")

    @staticmethod
    def _hash_content(content: str) -> str:
        return hashlib.sha256(content.encode()).hexdigest()[:16]
