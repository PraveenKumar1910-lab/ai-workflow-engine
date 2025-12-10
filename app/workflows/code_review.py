# app/workflows/code_review.py
from __future__ import annotations

from typing import Any, Dict, List
import re


def extract_functions_tool(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Very naive function extraction: looks for `def name(` patterns.
    """
    code: str = state.get("code", "")
    function_names: List[str] = re.findall(r"def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(", code)
    state["functions"] = function_names

    # Initialize some state fields
    state.setdefault("issues", [])
    state.setdefault("quality_score", 0.0)
    state.setdefault("iteration", 0)

    # Count iterations (for loop control)
    state["iteration"] += 1
    return state


def check_complexity_tool(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compute a simple complexity metric based on line count and branching keywords.
    """
    code: str = state.get("code", "")
    lines = [ln for ln in code.splitlines() if ln.strip()]
    line_count = len(lines)
    branching_tokens = sum(
        code.count(tok) for tok in [" if ", " for ", " while ", " and ", " or "]
    )
    complexity_score = line_count + 2 * branching_tokens
    state["complexity_score"] = complexity_score
    return state


def detect_issues_tool(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Detect very basic 'issues' like long lines and TODO comments.
    """
    code: str = state.get("code", "")
    issues: List[str] = state.get("issues", [])
    for idx, line in enumerate(code.splitlines(), start=1):
        if len(line) > 100:
            issues.append(f"Line {idx}: line too long")
        if "TODO" in line:
            issues.append(f"Line {idx}: contains TODO")
    state["issues"] = issues
    state["anomaly_count"] = len(issues)
    return state


def suggest_improvements_tool(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate simple suggestions and update quality_score.
    Handles the loop condition via state["_next_node"].
    """
    suggestions: List[str] = []
    issues: List[str] = state.get("issues", [])
    complexity_score: float = float(state.get("complexity_score", 0.0))

    if complexity_score > 50:
        suggestions.append("Consider splitting large functions into smaller ones.")
    if issues:
        suggestions.append("Fix the listed issues, especially long lines and TODOs.")
    if not suggestions:
        suggestions.append("Code looks reasonably clean.")

    # Simple heuristic:
    # lower complexity + fewer issues → higher quality_score
    base_score = 1.0
    penalty = 0.0
    penalty += min(complexity_score / 100.0, 0.7)
    penalty += min(len(issues) * 0.05, 0.3)
    quality_score = max(0.0, base_score - penalty)

    state["suggestions"] = suggestions
    state["quality_score"] = round(quality_score, 3)

    threshold = float(state.get("threshold", 0.8))
    max_iterations = int(state.get("max_iterations", 5))
    iteration = int(state.get("iteration", 1))

    # Loop until quality_score >= threshold, but cap iterations
    if quality_score < threshold and iteration < max_iterations:
        # Ask engine to jump back to the 'extract' node (loop)
        state["_next_node"] = "extract"
    else:
        # End the graph (engine will follow edges mapping; suggest has None next)
        state["_next_node"] = None

    return state


def build_default_code_review_graph(engine) -> str:
    """
    Helper to create the example code-review workflow and return its graph_id.
    """
    nodes_config = {
        "extract": {"tool_name": "extract_functions"},
        "complexity": {"tool_name": "check_complexity"},
        "issues": {"tool_name": "detect_issues"},
        "suggest": {"tool_name": "suggest_improvements"},
    }
    edges = {
        "extract": "complexity",
        "complexity": "issues",
        "issues": "suggest",
        # 'suggest' has no default next; loop is controlled via _next_node
        "suggest": None,
    }
    graph = engine.create_graph(
        name="code_review_mini_agent",
        nodes_config=nodes_config,
        edges=edges,
        start_node="extract",
        max_steps=50,
    )
    return graph.id
