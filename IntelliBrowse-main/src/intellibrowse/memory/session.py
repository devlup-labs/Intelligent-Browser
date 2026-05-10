"""
Session memory — tracks the last N steps verbatim + compressed summary of older steps.

Maintained in LangGraph state across the observe→plan→act→evaluate loop.
History older than HISTORY_WINDOW steps gets compressed by the LLM.
"""

from intellibrowse.config import settings
from intellibrowse.models.cascade import cascade
from intellibrowse.utils.logger import get_logger

logger = get_logger(__name__)

COMPRESSION_PROMPT = """Summarize these browser automation steps in 2-3 sentences.
Preserve: key URLs visited, data extracted, errors encountered, and what was accomplished.
Be factual and concise.

Steps to summarize:
{steps_text}"""


def record_step(
    history: list[dict],
    step_num: int,
    action: str,
    result: str,
    url: str,
) -> list[dict]:
    """
    Add a step to session history. Returns the updated history list.
    Does NOT mutate the input — returns a new list (LangGraph state is immutable).
    """
    entry = {
        "step": step_num,
        "action": action,
        "result": result[:300],  # Cap result length
        "url": url,
    }
    return [*history, entry]


def format_history(history: list[dict], summary: str) -> str:
    """Format session memory for injection into the prompt."""
    parts = []

    if summary:
        parts.append(f"## Earlier Steps (summary)\n{summary}")

    if history:
        parts.append("\n## Recent Steps")
        for entry in history:
            status = "✅" if "FAILED" not in entry["result"] else "❌"
            parts.append(
                f"  Step {entry['step']}: {entry['action']} → "
                f"{entry['result'][:100]} {status}"
            )

    return "\n".join(parts) if parts else "(no history yet)"


async def maybe_compress(
    history: list[dict],
    existing_summary: str,
) -> tuple[list[dict], str]:
    """
    If history exceeds the window size, compress older steps into the summary.
    Returns (trimmed_history, updated_summary).
    """
    window = settings.history_window

    if len(history) <= window:
        return history, existing_summary

    # Steps to compress (everything before the window)
    to_compress = history[:-window]
    kept = history[-window:]

    # Format old steps for summarization
    steps_text = "\n".join(
        f"Step {e['step']}: {e['action']} → {e['result']}"
        for e in to_compress
    )

    # Combine with existing summary if any
    if existing_summary:
        steps_text = f"Previous summary: {existing_summary}\n\nNew steps:\n{steps_text}"

    # Call LLM to compress
    try:
        messages = [
            {"role": "system", "content": "You are a concise summarizer."},
            {"role": "user", "content": COMPRESSION_PROMPT.format(steps_text=steps_text)},
        ]
        summary, model = await cascade.call(messages)
        logger.info("compressed %d steps into summary (%d chars, via %s)",
                     len(to_compress), len(summary), model)
        return kept, summary.strip()
    except Exception as e:
        # If compression fails, just truncate — don't crash the agent
        logger.warning("compression failed: %s — keeping raw entries", e)
        fallback_summary = existing_summary or ""
        for entry in to_compress:
            fallback_summary += f" Step {entry['step']}: {entry['action']}."
        return kept, fallback_summary.strip()
