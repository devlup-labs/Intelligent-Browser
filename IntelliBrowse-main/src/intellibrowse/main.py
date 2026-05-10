"""
FastAPI application — HTTP + WebSocket interface for the agent.

Endpoints:
  POST /task — submit a task, runs the agent, returns result
  WS /ws — stream step-by-step updates in real time
"""

import asyncio
import json
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from intellibrowse.browser.manager import BrowserManager
from intellibrowse.agent.graph import run_agent
from intellibrowse.utils.logger import get_logger

logger = get_logger(__name__)


# ── Lifespan ──────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown — nothing persistent needed."""
    logger.info("IntelliBrowse starting up")
    yield
    logger.info("IntelliBrowse shutting down")


# ── App ───────────────────────────────────────────────────────────────

app = FastAPI(
    title="IntelliBrowse",
    description="Agentic browser — describe tasks in plain English",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Static files + Frontend ───────────────────────────────────────────

# Resolve static dir: project_root/static/
_static_dir = Path(__file__).resolve().parent.parent.parent / "static"
if _static_dir.is_dir():
    app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")


@app.get("/")
async def root():
    """Serve the frontend."""
    index_path = _static_dir / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {"message": "IntelliBrowse API — visit /docs for API docs"}


# ── Request / Response Models ─────────────────────────────────────────

class TaskRequest(BaseModel):
    task: str


class TaskResponse(BaseModel):
    status: str
    result: str
    steps_taken: int


# ── HTTP endpoint (synchronous, returns when done) ────────────────────

@app.post("/task", response_model=TaskResponse)
async def submit_task(request: TaskRequest):
    """Run a task and return the result when complete."""
    logger.info("received task: %s", request.task)

    async with BrowserManager() as bm:
        final = await run_agent(request.task, bm.page)

    # Extract result from the nested state output
    result = _extract_final(final)
    return TaskResponse(
        status=result.get("status", "unknown"),
        result=result.get("final_result", ""),
        steps_taken=result.get("current_step", 0),
    )


# ── WebSocket endpoint (streams step updates) ─────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    """Stream step-by-step agent updates over WebSocket."""
    await ws.accept()
    logger.info("WebSocket connected")

    try:
        # Receive the task
        data = await ws.receive_text()
        request = json.loads(data)
        task = request.get("task", "")

        if not task:
            await ws.send_json({"error": "no task provided"})
            return

        logger.info("WS task: %s", task)

        async with BrowserManager() as bm:
            async def on_step(step_data: dict):
                """Send each step update to the WebSocket."""
                # Filter out large fields for the wire
                safe = {
                    k: v for k, v in step_data.items()
                    if k not in ("screenshot_b64", "page_state") and v
                }
                # Include a trimmed page_state
                if "page_state" in step_data:
                    safe["page_state_preview"] = str(step_data["page_state"])[:500]
                try:
                    await ws.send_json(safe)
                except Exception:
                    pass  # Client may have disconnected

            final = await run_agent(task, bm.page, on_step=on_step)

        result = _extract_final(final)
        await ws.send_json({"type": "complete", **result})

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error("WebSocket error: %s", e)
        try:
            await ws.send_json({"type": "error", "error": str(e)})
        except Exception:
            pass


def _extract_final(state: dict) -> dict:
    """Extract the final result from the nested LangGraph output."""
    # LangGraph astream returns {node_name: output} — find the last meaningful one
    for key in ("evaluate", "act"):
        if key in state and isinstance(state[key], dict):
            return state[key]
    # Fallback — return flattened
    flat = {}
    for v in state.values():
        if isinstance(v, dict):
            flat.update(v)
    return flat


# ── Health check ──────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok"}
