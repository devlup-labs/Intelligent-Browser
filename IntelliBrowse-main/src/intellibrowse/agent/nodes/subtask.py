"""
Subtask node — generate the next subtask based on progress and current page.

This is the key architectural change: instead of planning all steps upfront,
we generate ONE subtask at a time with full context of what's been done
and what the page currently looks like.
"""

from playwright.async_api import Page

from intellibrowse.agent.state import AgentState
from intellibrowse.agent.prompts import SUBTASK_PROMPT
from intellibrowse.browser.observation import get_page_state
from intellibrowse.models.cascade import cascade
from intellibrowse.utils.parser import parse_json
from intellibrowse.utils.logger import get_logger

logger = get_logger(__name__)


async def generate_subtask(state: AgentState, page: Page) -> dict:
    """
    Generate the next subtask. Called at start and after each subtask completes.
    """
    task = state["task"]
    completed = state.get("completed_subtasks", [])
    step = state.get("current_step", 0)

    logger.info("[step %d] generating next subtask...", step)

    # Get current page state for context
    try:
        await page.wait_for_load_state("domcontentloaded", timeout=3000)
    except Exception:
        pass
    await page.wait_for_timeout(500)

    page_text, _ = await get_page_state(page)

    # Build progress section
    if completed:
        progress_lines = ["Completed so far:"]
        for i, st in enumerate(completed):
            progress_lines.append(f"  {i+1}. ✅ {st}")
        progress_section = "\n".join(progress_lines)
    else:
        progress_section = "Nothing done yet — this is the first subtask."

    # Build the prompt
    prompt = SUBTASK_PROMPT.format(
        task=task,
        progress_section=progress_section,
        page_state=page_text[:2000],  # Limit page state for planning
    )

    messages = [
        {"role": "system", "content": "You are a task planner for browser automation. Generate exactly one focused subtask."},
        {"role": "user", "content": prompt},
    ]

    # Call the planning model
    raw, model = await cascade.plan(messages)
    parsed = parse_json(raw)

    if parsed is None:
        # Retry with strict prompt
        logger.warning("subtask parse failed — retrying")
        messages.append({"role": "assistant", "content": raw})
        messages.append({"role": "user", "content": "Respond ONLY with the JSON object, no other text."})
        raw2, model = await cascade.call(messages)
        parsed = parse_json(raw2)

    if parsed and parsed.get("task_complete"):
        logger.info("task planner says task is COMPLETE")
        return {
            "status": "done",
            "final_result": f"Task completed. Subtasks done: {len(completed)}",
            "needs_new_subtask": False,
        }

    if parsed:
        subtask = parsed.get("subtask", "")
        condition = parsed.get("success_condition", "")
        logger.info("next subtask (via %s): %s", model, subtask)
        return {
            "current_subtask": f"{subtask} (verify: {condition})",
            "needs_new_subtask": False,
            "page_state": page_text,  # Pass along the fresh page state
        }
    else:
        # Fallback — use the raw task directly
        logger.warning("subtask generation failed — using main task as subtask")
        return {
            "current_subtask": task,
            "needs_new_subtask": False,
        }
