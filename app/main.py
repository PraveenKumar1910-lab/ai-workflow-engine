# app/main.py
from typing import Any, Dict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .engine import GraphEngine, ToolRegistry
from .models import (
    GraphCreateRequest,
    GraphCreatedResponse,
    GraphRunRequest,
    GraphRunResponse,
    StepLogModel,
)
from .workflows import code_review


tool_registry = ToolRegistry()

# Register tools for the example workflow
tool_registry.register("extract_functions", code_review.extract_functions_tool)
tool_registry.register("check_complexity", code_review.check_complexity_tool)
tool_registry.register("detect_issues", code_review.detect_issues_tool)
tool_registry.register("suggest_improvements", code_review.suggest_improvements_tool)

engine = GraphEngine(tool_registry=tool_registry)

# Pre-create example graph on startup
CODE_REVIEW_GRAPH_ID = code_review.build_default_code_review_graph(engine)

app = FastAPI(
    title="Mini Agent Workflow Engine",
    description="A simple graph engine for the AI Engineering assignment",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/graph/default/code-review")
async def get_default_code_review_graph() -> Dict[str, str]:
    """
    Return the ID of the pre-built code-review workflow graph.
    """
    return {"graph_id": CODE_REVIEW_GRAPH_ID}


@app.post("/graph/create", response_model=GraphCreatedResponse)
async def create_graph(payload: GraphCreateRequest) -> GraphCreatedResponse:
    """
    Create a graph from JSON description of nodes and edges.
    """
    try:
        nodes_config: Dict[str, Dict[str, Any]] = {
            node_id: {"tool_name": cfg.tool_name}
            for node_id, cfg in payload.nodes.items()
        }
        graph = engine.create_graph(
            name=payload.name,
            nodes_config=nodes_config,
            edges=payload.edges,
            start_node=payload.start_node,
            max_steps=payload.max_steps,
        )
        return GraphCreatedResponse(graph_id=graph.id, name=graph.name)
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/graph/run", response_model=GraphRunResponse)
async def run_graph(payload: GraphRunRequest) -> GraphRunResponse:
    """
    Run a graph from a given graph_id and initial state.
    Returns final state and execution log.
    """
    try:
        run = await engine.run_graph(
            graph_id=payload.graph_id,
            initial_state=payload.initial_state,
        )
        return GraphRunResponse(
            run_id=run.id,
            graph_id=run.graph_id,
            status=run.status,
            current_node=run.current_node,
            state=run.state,
            log=[
                StepLogModel(
                    step_index=entry.step_index,
                    node_id=entry.node_id,
                    state_snapshot=entry.state_snapshot,
                )
                for entry in run.log
            ],
            error=run.error,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@app.get("/graph/state/{run_id}", response_model=GraphRunResponse)
async def get_run_state(run_id: str) -> GraphRunResponse:
    """
    Return the current state of a workflow run.
    (In this implementation, runs are executed synchronously,
    so this returns the final state once run is complete.)
    """
    try:
        run = engine.get_run(run_id)
        return GraphRunResponse(
            run_id=run.id,
            graph_id=run.graph_id,
            status=run.status,
            current_node=run.current_node,
            state=run.state,
            log=[
                StepLogModel(
                    step_index=entry.step_index,
                    node_id=entry.node_id,
                    state_snapshot=entry.state_snapshot,
                )
                for entry in run.log
            ],
            error=run.error,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@app.get("/health")
async def healthcheck() -> Dict[str, str]:
    return {"status": "ok"}
