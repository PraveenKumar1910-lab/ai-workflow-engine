# Mini Agent Workflow Engine (AI Engineering Assignment)

This project implements a minimal workflow / graph engine in Python with FastAPI.

It is designed to satisfy the assignment requirements:

- Nodes: Python functions that read/modify a shared state.
- State: A dictionary flowing from node to node.
- Edges: Mapping of which node runs after which.
- Branching: Nodes can set `_next_node` in the state to override the default edge.
- Looping: The example workflow loops until a `quality_score` threshold is met.

## Tech Stack

- Python 3.10+
- FastAPI
- Pydantic

## How to Run

```bash
# create and activate a virtualenv (optional but recommended)
python -m venv .venv
source .venv/bin/activate          # on Windows: .venv\Scripts\activate

pip install fastapi "uvicorn[standard]"

# run the app
uvicorn app.main:app --reload
