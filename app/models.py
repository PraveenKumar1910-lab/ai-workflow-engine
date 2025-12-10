# app/models.py
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class GraphNodeConfig(BaseModel):
    tool_name: str = Field(..., description="Name of the registered tool to execute")


class GraphCreateRequest(BaseModel):
    name: str
    nodes: Dict[str, GraphNodeConfig]
    edges: Dict[str, Optional[str]]
    start_node: str
    max_steps: int = 100


class StepLogModel(BaseModel):
    step_index: int
    node_id: str
    state_snapshot: Dict[str, Any]


class GraphRunResponse(BaseModel):
    run_id: str
    graph_id: str
    status: str
    current_node: Optional[str]
    state: Dict[str, Any]
    log: List[StepLogModel]
    error: Optional[str] = None


class GraphCreatedResponse(BaseModel):
    graph_id: str
    name: str


class GraphRunRequest(BaseModel):
    graph_id: str
    initial_state: Dict[str, Any] = Field(
        default_factory=dict,
        description="Initial state dictionary passed to the workflow",
    )
