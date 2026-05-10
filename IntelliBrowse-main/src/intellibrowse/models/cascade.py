"""
Model cascade — multi-model failover with Gemini round-robin.

Priority:
  1. Gemini 2.5 Flash (round-robin across multiple API keys)
  2. Groq (Llama 4 Scout) — fallback, fast + free
  3. NVIDIA NIM (Mistral Large 3) — escalation only (finite credits)
"""

from openai import RateLimitError, APIError, APITimeoutError, APIConnectionError

from intellibrowse.config import settings
from intellibrowse.models.providers import get_client
from intellibrowse.utils.logger import get_logger

logger = get_logger(__name__)

# Errors that trigger failover to next provider/key
FAILOVER_ERRORS = (RateLimitError, APITimeoutError, APIConnectionError)


class ModelCascade:
    """
    Call LLMs with automatic failover and Gemini round-robin.

    - call() round-robins across Gemini keys, then falls back to Groq
    - escalate() forces NVIDIA NIM for hard situations
    - plan() uses Gemini (round-robin) for subtask planning
    """

    def __init__(self):
        self._gemini_index = 0  # Current round-robin position
        self._key_count = settings.gemini_key_count
        logger.info("Gemini round-robin initialized with %d keys", self._key_count)

    def _next_gemini(self) -> str:
        """Get next Gemini provider name in round-robin order."""
        if self._key_count == 0:
            return "gemini"
        name = f"gemini_{self._gemini_index}"
        self._gemini_index = (self._gemini_index + 1) % self._key_count
        return name

    def _gemini_providers(self) -> list[str]:
        """
        Get list of Gemini provider names to try, starting from current
        round-robin position. Tries all keys before giving up on Gemini.
        """
        if self._key_count == 0:
            return []
        providers = []
        for i in range(self._key_count):
            idx = (self._gemini_index + i) % self._key_count
            providers.append(f"gemini_{idx}")
        # Advance the pointer for next call
        self._gemini_index = (self._gemini_index + 1) % self._key_count
        return providers

    async def _try_provider(
        self,
        provider_name: str,
        messages: list[dict],
        max_tokens: int | None = None,
        vision: bool = False,
    ) -> tuple[str, str] | None:
        """
        Try a single provider. Returns (text, name) or None on failure.
        """
        config = settings.providers.get(provider_name)
        if not config or not config.api_key:
            return None

        if vision and not config.supports_vision:
            return None

        try:
            client = get_client(provider_name)
            response = await client.chat.completions.create(
                model=config.model,
                messages=messages,
                temperature=config.temperature,
                max_tokens=max_tokens or config.max_tokens,
            )
            text = response.choices[0].message.content or ""
            # Log with the base name (gemini, not gemini_2)
            base_name = provider_name.split("_")[0]
            key_idx = provider_name.split("_")[1] if "_" in provider_name else "0"
            logger.info("response from %s (key %s, %d chars)", base_name, key_idx, len(text))
            return text, provider_name

        except FAILOVER_ERRORS as e:
            logger.warning("%s failed (failover): %s", provider_name, type(e).__name__)
            return None
        except APIError as e:
            logger.error("%s API error: %s", provider_name, e)
            return None

    async def call(
        self,
        messages: list[dict],
        vision: bool = False,
    ) -> tuple[str, str]:
        """
        Primary call — round-robins across Gemini keys, falls back to Groq.

        Returns: (response_text, model_used)
        """
        # Try all Gemini keys in round-robin order
        for gemini_name in self._gemini_providers():
            result = await self._try_provider(gemini_name, messages, vision=vision)
            if result:
                return result

        # Fall back to Groq
        result = await self._try_provider("groq", messages, vision=vision)
        if result:
            return result

        raise RuntimeError("all providers failed — no response generated")

    async def escalate(self, messages: list[dict]) -> tuple[str, str]:
        """
        Force NVIDIA NIM (Mistral Large 3) for hard situations.
        Only called when the agent is stuck (same action repeated).
        """
        result = await self._try_provider("nvidia", messages)
        if result:
            logger.info("ESCALATION response from nvidia (%d chars)", len(result[0]))
            return result

        logger.warning("NVIDIA escalation failed — falling back to normal cascade")
        return await self.call(messages)

    async def plan(self, messages: list[dict]) -> tuple[str, str]:
        """
        Use Gemini for subtask planning (round-robin across keys).
        Falls back to normal cascade if all Gemini keys fail.
        """
        for gemini_name in self._gemini_providers():
            result = await self._try_provider(gemini_name, messages, max_tokens=2048)
            if result:
                base_name = gemini_name.split("_")[0]
                logger.info("plan from %s (%d chars)", base_name, len(result[0]))
                return result

        logger.warning("all Gemini keys failed for planning — falling back")
        return await self.call(messages)


# Singleton
cascade = ModelCascade()
