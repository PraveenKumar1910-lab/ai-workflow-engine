# app/engine.py
from __future__ import annotations

from typing import Any, Awaitable, Callable, Dict, List, Optional
from dataclasses import dataclass, field
import uuid
import asyncio


ToolFn = Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]]]


class ToolRegistry:
    """
    Simple in-memory registry mapping tool names to async callables.
    """

    def __init__(self) -> None:
        self._tools: Dict[str, ToolFn] = {}

    def register(self, name: str, fn: Callable[[Dict[str, Any]], Any]) -> None:
        """
        Register a tool.
        Supports both sync and async functions; wraps sync ones into async.
        """
        if asyncio.iscoroutinefunction(fn):
            async_fn: ToolFn = fn  # type: ignore[assignment]
        else:
            async def async_wrapper(state: Dict[str, Any]) -> Dict[str, Any]:
                result = fn(state)
                return result

            async_fn = async_wrapper

        self._tools[name] = async_fn

    def get(self, name: str) -> ToolFn:
        if name not in self._tools:
            raise KeyError(f"Tool '{name}' not registered")
        return self._tools[name]


@dataclass
class Node:
    id: str
    tool_name: str


@dataclass
class StepLog:
    step_index: int
    node_id: str
    state_snapshot: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Graph:
    id: str
    name: str
    nodes: Dict[str, Node]
    edges: Dict[str, Optional[str]]  # node_id -> next_node_id (or None)
    start_node: str
    max_steps: int = 100


@dataclass
class GraphRun:
    id: str
    graph_id: str
    status: str  # "running" | "completed" | "failed"
    current_node: Optional[str]
    state: Dict[str, Any] = field(default_factory=dict)
    log: List[StepLog] = field(default_factory=list)
    error: Optional[str] = None


class GraphEngine:
    """
    Core workflow engine.
    - state: dict flowing through nodes
    - edges: mapping node -> next node
    - branching/looping: nodes can set state["_next_node"] to override edges
    """

    def __init__(self, tool_registry: ToolRegistry) -> None:
        self.tool_registry = tool_registry
        self.graphs: Dict[str, Graph] = {}
        self.runs: Dict[str, GraphRun] = {}

    def create_graph(
        self,
        name: str,
        nodes_config: Dict[str, Dict[str, Any]],
        edges: Dict[str, Optional[str]],
        start_node: str,
        max_steps: int = 100,
    ) -> Graph:
        if start_node not in nodes_config:
            raise ValueError("start_node must be one of nodes_config keys")

        nodes: Dict[str, Node] = {}
        for node_id, cfg in nodes_config.items():
            tool_name = cfg.get("tool_name")
            if not tool_name:
                raise ValueError(f"Node '{node_id}' missing 'tool_name'")
            # Validate that tool exists
            self.tool_registry.get(tool_name)
            nodes[node_id] = Node(id=node_id, tool_name=tool_name)

        graph_id = str(uuid.uuid4())
        graph = Graph(
            id=graph_id,
            name=name,
            nodes=nodes,
            edges=edges,
            start_node=start_node,
            max_steps=max_steps,
        )
        self.graphs[graph_id] = graph
        return graph

    async def run_graph(
        self, graph_id: str, initial_state: Dict[str, Any]
    ) -> GraphRun:
        if graph_id not in self.graphs:
            raise KeyError(f"Graph '{graph_id}' not found")

        graph = self.graphs[graph_id]
        run_id = str(uuid.uuid4())
        run = GraphRun(
            id=run_id,
            graph_id=graph_id,
            status="running",
            current_node=graph.start_node,
            state=dict(initial_state),
        )
        self.runs[run_id] = run

        try:
            step_index = 0
            current_node_id: Optional[str] = graph.start_node

            while current_node_id is not None and step_index < graph.max_steps:
                run.current_node = current_node_id
                node = graph.nodes[current_node_id]
                tool = self.tool_registry.get(node.tool_name)

                # Execute node
                new_state = await tool(run.state)
                if not isinstance(new_state, dict):
                    raise TypeError(
                        f"Tool '{node.tool_name}' must return a dict, "
                        f"got {type(new_state)}"
                    )
                run.state = new_state

                # Log snapshot (shallow copy)
                run.log.append(
                    StepLog(
                        step_index=step_index,
                        node_id=current_node_id,
                        state_snapshot=dict(run.state),
                    )
                )

                # Branching / looping support:
                # a node can set _next_node in state to override edges mapping
                override = run.state.pop("_next_node", None)
                if override is not None:
                    current_node_id = override
                else:
                    current_node_id = graph.edges.get(current_node_id)

                step_index += 1

            if step_index >= graph.max_steps:
                run.status = "failed"
                run.error = "Max steps exceeded (possible infinite loop)"
            else:
                run.status = "completed"
                run.current_node = None

        except Exception as exc:
            run.status = "failed"
            run.error = str(exc)

        return run

    def get_run(self, run_id: str) -> GraphRun:
        if run_id not in self.runs:
            raise KeyError(f"Run '{run_id}' not found")
        return self.runs[run_id]
