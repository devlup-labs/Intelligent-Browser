"""
Working memory — the current step's context that goes into the prompt.

This is the most ephemeral layer: it's rebuilt from scratch each step.
It combines page state, the current plan step, and any relevant domain memory.
"""


def build_working_context(
    page_state: str,
    task: str,
    current_step: int,
    task_plan_summary: str | None = None,
    domain_hints: list[str] | None = None,
) -> str:
    """
    Build the working memory string injected into the user prompt each step.

    This is cheap — just string concatenation, no LLM calls.
    """
    parts = [
        f"## Current Task\n{task}",
        f"\n## Step {current_step + 1}",
    ]

    if task_plan_summary:
        parts.append(f"\n## Plan Overview\n{task_plan_summary}")

    if domain_hints:
        parts.append("\n## Domain Tips (from past experience)")
        for hint in domain_hints:
            parts.append(f"  - {hint}")

    parts.append(f"\n## Current Page State\n{page_state}")

    return "\n".join(parts)
