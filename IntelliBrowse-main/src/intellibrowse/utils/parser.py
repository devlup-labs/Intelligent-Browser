"""
Robust JSON parser — extracts structured output from LLM responses.

LLMs often wrap JSON in prose, markdown fences, or extra text.
This parser tries multiple strategies to extract valid JSON.

This was the #1 failure mode of the previous project — every strategy
here exists because we saw real LLM output that broke simpler parsers.
"""

import json
import re

from intellibrowse.utils.logger import get_logger

logger = get_logger(__name__)


def parse_json(raw: str) -> dict | None:
    """
    Extract a JSON object from LLM output using multiple strategies.

    Tries in order:
      1. Direct json.loads()
      2. Extract from ```json ... ``` fences
      3. Extract from ``` ... ``` fences (no language tag)
      4. Find first { to last } in raw text
      5. Give up — return None

    Returns the parsed dict, or None if all strategies fail.
    """
    if not raw or not isinstance(raw, str):
        return None

    raw = raw.strip()

    # Strategy 1: direct parse (LLM returned clean JSON)
    try:
        result = json.loads(raw)
        if isinstance(result, dict):
            return result
    except json.JSONDecodeError:
        pass

    # Strategy 2: extract from ```json ... ``` fences
    match = re.search(r"```json\s*\n?(.*?)\n?\s*```", raw, re.DOTALL)
    if match:
        try:
            result = json.loads(match.group(1).strip())
            if isinstance(result, dict):
                logger.debug("parsed JSON from ```json fence")
                return result
        except json.JSONDecodeError:
            pass

    # Strategy 3: extract from ``` ... ``` fences (no language tag)
    match = re.search(r"```\s*\n?(.*?)\n?\s*```", raw, re.DOTALL)
    if match:
        try:
            result = json.loads(match.group(1).strip())
            if isinstance(result, dict):
                logger.debug("parsed JSON from ``` fence")
                return result
        except json.JSONDecodeError:
            pass

    # Strategy 4: find first { to last }
    first_brace = raw.find("{")
    last_brace = raw.rfind("}")
    if first_brace != -1 and last_brace > first_brace:
        candidate = raw[first_brace:last_brace + 1]
        try:
            result = json.loads(candidate)
            if isinstance(result, dict):
                logger.debug("parsed JSON from brace extraction")
                return result
        except json.JSONDecodeError:
            pass

    # All strategies failed
    logger.warning("JSON parse failed — raw output (first 300 chars): %s", raw[:300])
    return None
