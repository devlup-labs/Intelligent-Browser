"""
Plan node — call the LLM to decide the next action for the current subtask.

Uses the model cascade:
  - Normal: Gemini → Groq
  - Stuck (same action twice): escalate to NVIDIA
  - Parse failure: retry once with stricter prompt
"""

from playwright.async_api import Page

from intellibrowse.agent.state import AgentState
from intellibrowse.agent.prompts import SYSTEM_PROMPT, build_step_messages
from intellibrowse.memory.session import format_history
from intellibrowse.models.cascade import cascade
from intellibrowse.utils.parser import parse_json
from intellibrowse.utils.logger import get_logger

logger = get_logger(__name__)


async def plan(state: AgentState, page: Page) -> dict:
    """
    Decide the next action. Returns partial state update with action_json.
    """
    step = state.get("current_step", 0)
    logger.info("[step %d] planning next action...", step)

    # Build session context
    session_context = format_history(
        state.get("session_history", []),
        state.get("history_summary", ""),
    )

    # Extract actions that failed or led to wrong pages (for anti-loop warnings)
    failed_actions = []
    for entry in state.get("session_history", []):
        result = entry.get("result", "")
        action = entry.get("action", "")
        if "FAILED" in result or "go_back" in action:
            failed_actions.append(f'{action} → {result[:80]}')

    # Build messages — now focused on current subtask
    messages = build_step_messages(
        system_prompt=SYSTEM_PROMPT,
        task=state["task"],
        page_state=state.get("page_state", ""),
        session_context=session_context,
        current_subtask=state.get("current_subtask", ""),
        completed_subtasks=state.get("completed_subtasks"),
        domain_hints=state.get("domain_hints"),
        screenshot_b64=state.get("screenshot_b64") or None,
        failed_actions=failed_actions if failed_actions else None,
    )

    # Check if stuck — same action repeated
    is_stuck = state.get("consecutive_failures", 0) >= 2

    # Call LLM
    if is_stuck:
        logger.warning("[step %d] STUCK — escalating to NVIDIA", step)
        raw, model = await cascade.escalate(messages)
    else:
        vision = bool(state.get("screenshot_b64"))
        raw, model = await cascade.call(messages, vision=vision)

    # Parse the response
    action = parse_json(raw)

    if action is None:
        # Retry with stricter prompt
        logger.warning("[step %d] JSON parse failed — retrying with strict prompt", step)
        messages.append({"role": "assistant", "content": raw})
        messages.append({
            "role": "user",
            "content": "Your response was not valid JSON. Respond ONLY with the JSON object, no other text.",
        })
        raw2, model = await cascade.call(messages)
        action = parse_json(raw2)

    if action is None:
        # Complete failure — return a noop
        logger.error("[step %d] JSON parse failed twice — skipping step", step)
        action = {
            "reasoning": "Failed to parse LLM output",
            "action": "wait",
            "target": None,
            "value": "1",
        }

    logger.info("[step %d] planned: %s (via %s)", step, action.get("action"), model)

    return {
        "action_json": action,
        "model_used": model,
    }
