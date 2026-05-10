"""
Act node — execute the planned action on the browser.

Only ONE action per step — this prevents the executor boundary violation
that plagued the previous project.
"""

from playwright.async_api import Page

from intellibrowse.agent.state import AgentState
from intellibrowse.browser.actions import execute_action
from intellibrowse.utils.logger import get_logger

logger = get_logger(__name__)


async def act(state: AgentState, page: Page) -> dict:
    """
    Execute the planned action. Returns partial state update.
    """
    step = state.get("current_step", 0)
    action_json = state.get("action_json", {})

    action_name = action_json.get("action", "")
    target = action_json.get("target")
    value = action_json.get("value")

    logger.info("[step %d] acting: %s(target=%s, value=%s)", step, action_name, target, value)

    # Handle the "done" action — task completion
    if action_name == "done":
        result = value or "Task completed"
        logger.info("[step %d] DONE — %s", step, result)
        return {
            "action_result": result,
            "status": "done",
            "final_result": result,
        }

    # Build kwargs for the action
    kwargs: dict = {}
    if target is not None:
        if action_name in ("navigate",):
            kwargs["url"] = str(target)
        elif action_name in ("scroll",):
            kwargs["direction"] = str(value or "down")
        elif action_name in ("wait",):
            kwargs["seconds"] = float(value or 2)
        elif action_name not in ("go_back", "screenshot", "done"):
            kwargs["index"] = int(target)

    if value is not None and action_name in ("type", "press_key", "select_option"):
        kwargs["value" if action_name == "select_option" else
               "text" if action_name == "type" else
               "key"] = str(value)

    # Execute
    try:
        result = await execute_action(page, action_name, **kwargs)
    except Exception as e:
        result = f"FAILED: exception during {action_name}: {e}"
        logger.error("[step %d] action exception: %s", step, e)

    return {"action_result": result}
