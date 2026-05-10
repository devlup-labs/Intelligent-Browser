"""
Evaluate node — update memory, check completion, detect stuck loops.

This node runs after every action and decides whether to:
  - Continue with current subtask
  - Mark subtask as done and request next subtask
  - Detect stuck loops (failures + behavioral patterns)
  - Terminate the task
"""

from playwright.async_api import Page

from intellibrowse.agent.state import AgentState
from intellibrowse.memory.session import record_step, maybe_compress
from intellibrowse.utils.logger import get_logger

logger = get_logger(__name__)

# How many recent actions to keep for loop detection
LOOP_WINDOW = 6


def _detect_loop(action_history: list[str]) -> bool:
    """
    Detect repeating action patterns in the last LOOP_WINDOW actions.
    Example: [click(6), go_back, click(6), go_back] → loop of length 2.
    """
    if len(action_history) < 4:
        return False

    recent = action_history[-LOOP_WINDOW:]

    # Check for loops of length 2 (A,B,A,B) or 3 (A,B,C,A,B,C)
    for loop_len in (2, 3):
        if len(recent) < loop_len * 2:
            continue
        pattern = recent[-loop_len:]
        preceding = recent[-(loop_len * 2):-loop_len]
        if pattern == preceding:
            return True

    # Check if the same action appears 3+ times in the window
    from collections import Counter
    counts = Counter(recent)
    if counts.most_common(1)[0][1] >= 3:
        return True

    return False


async def evaluate(state: AgentState, page: Page) -> dict:
    """
    Evaluate the result of the last action. Returns partial state update.
    """
    step = state.get("current_step", 0)
    action_json = state.get("action_json", {})
    action_result = state.get("action_result", "")
    max_steps = state.get("max_steps", 25)

    # ── Check if subtask was marked done by the act node ──
    if state.get("status") == "done":
        # This was triggered by a done() action — subtask is complete
        subtask = state.get("current_subtask", "")
        result = state.get("final_result", "")
        completed = list(state.get("completed_subtasks", []))
        completed.append(f"{subtask} → {result}")

        logger.info("[step %d] subtask completed: %s", step, result)

        return {
            "completed_subtasks": completed,
            "current_subtask": "",
            "needs_new_subtask": True,
            "status": "running",  # Keep running — generate next subtask
            "final_result": "",
            "consecutive_failures": 0,
            "action_history": [],
        }

    # ── Build action string for tracking ──
    action_str = f"{action_json.get('action')}({action_json.get('target')},{action_json.get('value')})"

    # ── Detect failure ──
    is_failure = "FAILED" in action_result

    # ── Detect exact repeat ──
    last_action = state.get("last_action_str", "")
    is_repeat = action_str == last_action and last_action != ""

    # ── Track action history for loop detection ──
    action_history = list(state.get("action_history", []))
    action_history.append(action_str)
    if len(action_history) > LOOP_WINDOW:
        action_history = action_history[-LOOP_WINDOW:]

    is_loop = _detect_loop(action_history)

    # ── Update consecutive failures counter ──
    consecutive = state.get("consecutive_failures", 0)
    if is_failure or is_repeat:
        consecutive += 1
    elif is_loop:
        consecutive += 2  # Loops are worse
        logger.warning("[step %d] BEHAVIORAL LOOP detected: %s", step, action_history[-4:])
    else:
        consecutive = 0

    # ── Update session history ──
    history = record_step(
        state.get("session_history", []),
        step,
        f"{action_json.get('action', '?')}({action_json.get('target', '')}, {action_json.get('value', '')})",
        action_result,
        page.url,
    )

    # ── Compress history if needed ──
    history, summary = await maybe_compress(
        history,
        state.get("history_summary", ""),
    )

    # ── Check termination conditions ──
    next_step = step + 1
    status = "running"
    final_result = ""

    if next_step >= max_steps:
        status = "failed"
        final_result = f"Reached max steps ({max_steps}) without completing the task"
        logger.warning("[step %d] MAX STEPS REACHED", step)

    if consecutive >= 5:
        # Instead of total failure, try a new subtask approach
        logger.warning("[step %d] STUCK — %d failures, requesting new subtask", step, consecutive)
        completed = list(state.get("completed_subtasks", []))
        completed.append(f"STUCK on: {state.get('current_subtask', '')} (failed after {consecutive} attempts)")
        return {
            "current_step": next_step,
            "session_history": history,
            "history_summary": summary,
            "consecutive_failures": 0,
            "last_action_str": action_str,
            "action_history": [],
            "completed_subtasks": completed,
            "current_subtask": "",
            "needs_new_subtask": True,
            "status": "running",
            "final_result": "",
        }

    logger.info(
        "[step %d] eval: %s | failures=%d | loop=%s | status=%s",
        step,
        "FAIL" if is_failure else "LOOP" if is_loop else "OK",
        consecutive,
        is_loop,
        status,
    )

    return {
        "current_step": next_step,
        "session_history": history,
        "history_summary": summary,
        "consecutive_failures": consecutive,
        "last_action_str": action_str,
        "action_history": action_history,
        "status": status,
        "final_result": final_result or state.get("final_result", ""),
        "needs_new_subtask": False,
    }
