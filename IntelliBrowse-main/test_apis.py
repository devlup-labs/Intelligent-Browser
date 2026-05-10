"""Quick test — hit each LLM provider with a simple prompt and report results."""

import asyncio
import os
import sys

# Ensure the package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from dotenv import load_dotenv
load_dotenv()

from intellibrowse.config import settings
from intellibrowse.models.providers import get_client


PROVIDERS = ["groq", "gemini", "nvidia", "openrouter"]
TEST_PROMPT = [
    {"role": "user", "content": "Reply with exactly: HELLO INTELLIBROWSE. Nothing else."}
]


async def test_provider(name: str):
    config = settings.providers.get(name)
    if not config or not config.api_key or config.api_key.endswith("..."):
        return name, "SKIPPED", "No API key configured"

    try:
        client = get_client(name)
        response = await client.chat.completions.create(
            model=config.model,
            messages=TEST_PROMPT,
            temperature=0,
            max_tokens=50,
        )
        text = (response.choices[0].message.content or "").strip()
        if not text:
            return name, "FAILED", f"Empty response (model: {config.model})"
        return name, "OK", f'"{text}" (model: {config.model})'
    except Exception as e:
        return name, "FAILED", f"{type(e).__name__}: {e}"


async def main():
    print("=" * 60)
    print("IntelliBrowse — LLM API Test")
    print("=" * 60)

    results = await asyncio.gather(*[test_provider(p) for p in PROVIDERS])

    for name, status, detail in results:
        icon = "✅" if status == "OK" else "⏭️" if status == "SKIPPED" else "❌"
        print(f"\n{icon} {name.upper():12s} [{status}]")
        print(f"   {detail}")

    print("\n" + "=" * 60)
    ok_count = sum(1 for _, s, _ in results if s == "OK")
    print(f"Result: {ok_count}/{len(PROVIDERS)} providers working")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
