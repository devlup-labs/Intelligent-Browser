"""
Agent state — TypedDict for LangGraph state graph.

All data that flows between nodes lives here.
LangGraph enforces immutability — nodes return partial updates.
"""

from typing import TypedDict


class AgentState(TypedDict, total=False):
    """Complete state for the agent loop."""

    # ── Task ──
    task: str                           # Original user request (immutable)
    current_subtask: str                # Active subtask (generated one at a time)
    completed_subtasks: list            # List of completed subtask descriptions
    final_goal: str                     # What success looks like

    # ── Step tracking ──
    current_step: int                   # 0-indexed step counter
    max_steps: int                      # Hard cap (default 25)
    status: str                         # "running" | "done" | "failed"
    final_result: str                   # Task outcome message
    needs_new_subtask: bool             # Signal to generate next subtask

    # ── Observation ──
    page_state: str                     # Current DOM state text
    page_url: str                       # Current page URL
    screenshot_b64: str                 # Base64 screenshot (only when needed)

    # ── Action ──
    action_json: dict                   # Parsed ActionOutput as dict
    action_result: str                  # Result string from executing action

    # ── Memory ──
    session_history: list               # Last N steps verbatim
    history_summary: str                # Compressed older steps
    domain_hints: list                  # Long-term patterns for current domain

    # ── Stuck detection ──
    consecutive_failures: int           # How many failures in a row
    last_action_str: str                # String repr of last action (for dedup)
    action_history: list                # Recent action strings for loop detection

    # ── Model tracking ──
    model_used: str                     # Which model answered last
