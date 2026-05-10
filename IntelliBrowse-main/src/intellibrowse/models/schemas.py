"""
Pydantic schemas for LLM input/output validation.
"""

from pydantic import BaseModel, Field


class ActionOutput(BaseModel):
    """What the LLM returns each step — one atomic action."""
    reasoning: str = Field(description="1-2 sentence explanation of why this action")
    action: str = Field(description="Action name: click, type, press_key, navigate, scroll, go_back, select_option, wait, done")
    target: int | str | None = Field(default=None, description="Element index (int) or URL (str)")
    value: str | None = Field(default=None, description="Text to type, key to press, option to select, or final result for done")


class TaskStep(BaseModel):
    """A single step in the initial task plan."""
    description: str
    success_condition: str


class TaskPlan(BaseModel):
    """Initial task decomposition from the planning model."""
    steps: list[TaskStep]
    final_goal: str = Field(description="What success looks like for the overall task")
