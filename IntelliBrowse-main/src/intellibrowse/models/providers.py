"""
LLM provider clients — all OpenAI SDK compatible.
Each provider is just a different (base_url, model, api_key) tuple.
"""

from openai import AsyncOpenAI

from intellibrowse.config import settings, ProviderConfig
from intellibrowse.utils.logger import get_logger

logger = get_logger(__name__)


def build_client(provider: ProviderConfig) -> AsyncOpenAI:
    """Create an async OpenAI-compatible client for any provider."""
    return AsyncOpenAI(
        api_key=provider.api_key,
        base_url=provider.base_url,
    )


# Pre-built clients (lazy — only created when accessed)
_clients: dict[str, AsyncOpenAI] = {}


def get_client(provider_name: str) -> AsyncOpenAI:
    """Get or create a client for the named provider."""
    if provider_name not in _clients:
        config = settings.providers.get(provider_name)
        if not config:
            raise ValueError(f"unknown provider: {provider_name}")
        if not config.api_key:
            raise ValueError(f"no API key for provider: {provider_name}")
        _clients[provider_name] = build_client(config)
        logger.info("created client for %s (%s)", provider_name, config.model)
    return _clients[provider_name]
