"""
LangGraph state graph — reactive subtask architecture.

Flow:
  subtask → observe → plan → act → evaluate
                                      ↓
                          (subtask done?) → subtask → ...
                          (task done?)    → END
                          (keep going?)   → observe → ...

Instead of planning all steps upfront, we generate ONE subtask at a time.
After each subtask completes, we generate the next one with full context
of what's been accomplished and what the page looks like now.
"""

from langgraph.graph import StateGraph, END
from playwright.async_api import Page

from intellibrowse.agent.state import AgentState
from intellibrowse.agent.nodes.observe import observe
from intellibrowse.agent.nodes.plan import plan
from intellibrowse.agent.nodes.act import act
from intellibrowse.agent.nodes.evaluate import evaluate
from intellibrowse.agent.nodes.subtask import generate_subtask
from intellibrowse.utils.logger import get_logger

logger = get_logger(__name__)


def _after_evaluate(state: AgentState) -> str:
    """Conditional edge after evaluate: continue, get new subtask, or end."""
    status = state.get("status", "running")

    if status in ("done", "failed"):
        return "end"

    if state.get("needs_new_subtask", False):
        return "subtask"

    return "continue"


def build_graph(page: Page) -> StateGraph:
    """
    Build the LangGraph state graph with the browser page bound to each node.
    """
    graph = StateGraph(AgentState)

    # Async wrappers that bind the page to each node function
    async def _subtask(state):
        return await generate_subtask(state, page)

    async def _observe(state):
        return await observe(state, page)

    async def _plan(state):
        return await plan(state, page)

    async def _act(state):
        return await act(state, page)

    async def _evaluate(state):
        return await evaluate(state, page)

    graph.add_node("subtask", _subtask)
    graph.add_node("observe", _observe)
    graph.add_node("plan", _plan)
    graph.add_node("act", _act)
    graph.add_node("evaluate", _evaluate)

    # Flow: subtask → observe → plan → act → evaluate
    graph.set_entry_point("subtask")
    graph.add_edge("subtask", "observe")
    graph.add_edge("observe", "plan")
    graph.add_edge("plan", "act")
    graph.add_edge("act", "evaluate")

    # Conditional: evaluate → observe (continue) | subtask (new subtask) | END
    graph.add_conditional_edges(
        "evaluate",
        _after_evaluate,
        {
            "continue": "observe",
            "subtask": "subtask",
            "end": END,
        },
    )

    # subtask node can also end the task (when task_complete=true)
    graph.add_conditional_edges(
        "subtask",
        lambda state: "end" if state.get("status") in ("done", "failed") else "continue",
        {"continue": "observe", "end": END},
    )

    return graph


async def run_agent(task: str, page: Page, on_step=None) -> dict:
    """
    Main entry point — run the full agent loop.

    Args:
        task: The user's plain English task description
        page: Playwright page instance
        on_step: Optional async callback(state) called after each node

    Returns:
        Final AgentState as a dict
    """
    logger.info("=" * 60)
    logger.info("TASK: %s", task)
    logger.info("=" * 60)

    # Build the graph — subtask generation is now a node, not upfront
    graph = build_graph(page)
    app = graph.compile()

    # Initial state
    initial_state: AgentState = {
        "task": task,
        "current_subtask": "",
        "completed_subtasks": [],
        "final_goal": "",
        "current_step": 0,
        "max_steps": 25,
        "status": "running",
        "final_result": "",
        "needs_new_subtask": True,  # Start by generating first subtask
        "page_state": "",
        "page_url": "",
        "screenshot_b64": "",
        "action_json": {},
        "action_result": "",
        "session_history": [],
        "history_summary": "",
        "domain_hints": [],
        "consecutive_failures": 0,
        "last_action_str": "",
        "action_history": [],
        "model_used": "",
    }

    # Run the graph
    final_state = None
    async for state in app.astream(initial_state):
        for node_name, node_output in state.items():
            if isinstance(node_output, dict):
                if on_step:
                    await on_step({"node": node_name, **node_output})

        final_state = state

    logger.info("=" * 60)
    logger.info("RESULT: %s", final_state)
    logger.info("=" * 60)

    return final_state
