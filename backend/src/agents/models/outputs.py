from pydantic import BaseModel, Field
from typing import List, Literal, Optional

class ExecutionOutput(BaseModel):

    status: Literal["SUCCESS", "FAILURE", "PARTIAL_FAILURE"] = Field(..., description="The execution status of the task.")
    step_description: str = Field(description="Brief description of the attempted step.")
    result_summary: str = Field(description="Concise summary of what happened.")
    error_details: Optional[str] = Field(default=None, description="Detailed explanation if status is not SUCCESS.")
    suggestions_for_planner: Optional[str] = Field(default=None, description="Recommendations for next step adaptation.")
    outputs_created: List[str] = Field(default_factory=list, description="List of any files/results produced.")
    next_step_context: Optional[str] = Field(default=None, description="Any important context for the next step.")


class CurrentTask(BaseModel):

    task_name: str = Field(..., description="Specific name for the task to execute.")
    task_id: int = Field(..., description="Sequential number for the task.")
    agent_name: str = Field(..., description="Name of the agent from the provided list that should execute this task.")
    task_thought: str = Field(..., description="Your reasoning for why this task is necessary and how it fits the overall plan.")
    task_description: str = Field(..., description="Clear, detailed description of what needs to be accomplished in this specific task.")
    subtasks: List[str] = Field(default_factory=list, description="A list of granular steps or actions to be taken within this task.")
    expected_outputs: str = Field(..., description="What specific outputs or results this task should produce.")
    depends_on_previous: Optional[str] = Field(default=None, description="How this task builds on previous execution results. Only for subsequent calls.")


class PlannerOutput(BaseModel):

    overall_task_name: str = Field(..., description="A complete, descriptive name for the entire user request.")
    current_task: CurrentTask = Field(..., description="The specific task to be executed in the current step.")
    
    session_type: Literal["INITIAL_PLANNING", "ITERATIVE_PLANNING"] = Field(..., description="Indicates if this is the first plan or an adaptation.")
    master_thought: Optional[str] = Field(default=None, description="Comprehensive analysis of the user request and high-level approach. Required for initial planning.")
    estimated_steps: Optional[str] = Field(default=None, description="Rough estimate of how many major steps the entire request will take. Required for initial planning.")
    
    progress_analysis: Optional[str] = Field(default=None, description="Analysis based on the executor's previous result_summary and what has been completed.")
    adaptation_reasoning: Optional[str] = Field(default=None, description="Explanation of how you are adapting the plan based on the executor's feedback.")
    remaining_work: Optional[str] = Field(default=None, description="An estimate of what still needs to be done after the current task is completed.")