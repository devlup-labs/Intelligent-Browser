"""
Configuration — loads env vars and defines constants for the entire app.
"""

import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


# ── Model Provider Configs ────────────────────────────────────────────

@dataclass(frozen=True)
class ProviderConfig:
    """Configuration for a single LLM provider."""
    name: str
    api_key: str
    base_url: str
    model: str
    supports_vision: bool = False
    temperature: float = 0.0
    max_tokens: int = 1024


def _parse_gemini_keys() -> list[str]:
    """
    Parse Gemini API keys from env.
    Supports both:
      GEMINI_API_KEY=single_key
      GEMINI_API_KEYS=key1,key2,key3
    """
    # Check for comma-separated keys first
    multi = os.getenv("GEMINI_API_KEYS", "")
    if multi:
        return [k.strip() for k in multi.split(",") if k.strip()]

    # Fall back to single key
    single = os.getenv("GEMINI_API_KEY", "")
    if single:
        return [single]

    return []


def _get_providers() -> dict[str, ProviderConfig]:
    """Build provider configs from environment variables."""
    gemini_keys = _parse_gemini_keys()

    providers = {
        "groq": ProviderConfig(
            name="groq",
            api_key=os.getenv("GROQ_API_KEY", ""),
            base_url="https://api.groq.com/openai/v1",
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            supports_vision=True,
        ),
        "nvidia": ProviderConfig(
            name="nvidia",
            api_key=os.getenv("NVIDIA_API_KEY", ""),
            base_url="https://integrate.api.nvidia.com/v1",
            model="mistralai/mistral-large-3-675b-instruct-2512",
            supports_vision=False,
        ),
        "openrouter": ProviderConfig(
            name="openrouter",
            api_key=os.getenv("OPENROUTER_API_KEY", ""),
            base_url="https://openrouter.ai/api/v1",
            model="stepfun/step-3.5-flash",
            supports_vision=False,
        ),
    }

    # Add Gemini configs — one per key for round-robin
    if gemini_keys:
        # Primary "gemini" entry uses the first key
        providers["gemini"] = ProviderConfig(
            name="gemini",
            api_key=gemini_keys[0],
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
            model="gemini-2.5-flash",
            supports_vision=True,
        )
        # Store all keys for round-robin
        for i, key in enumerate(gemini_keys):
            providers[f"gemini_{i}"] = ProviderConfig(
                name=f"gemini_{i}",
                api_key=key,
                base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
                model="gemini-2.5-flash",
                supports_vision=True,
            )

    return providers


# ── App Settings ──────────────────────────────────────────────────────

@dataclass(frozen=True)
class Settings:
    """Global application settings."""

    # Browser
    headless: bool = field(default_factory=lambda: os.getenv("HEADLESS", "true").lower() == "true")
    viewport_width: int = field(default_factory=lambda: int(os.getenv("VIEWPORT_WIDTH", "1280")))
    viewport_height: int = field(default_factory=lambda: int(os.getenv("VIEWPORT_HEIGHT", "720")))

    # Agent
    max_steps: int = field(default_factory=lambda: int(os.getenv("MAX_STEPS", "25")))
    history_window: int = field(default_factory=lambda: int(os.getenv("HISTORY_WINDOW", "5")))
    temperature: float = field(default_factory=lambda: float(os.getenv("TEMPERATURE", "0")))

    # Memory
    memory_store_path: str = field(default_factory=lambda: os.getenv("MEMORY_STORE_PATH", "memory_store/domains.json"))

    # Providers (populated after init)
    providers: dict[str, ProviderConfig] = field(default_factory=_get_providers)

    # Gemini key count
    gemini_key_count: int = field(default_factory=lambda: len(_parse_gemini_keys()))


# Singleton — import this everywhere
settings = Settings()
