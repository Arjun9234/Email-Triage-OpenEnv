"""
FastAPI server for Email Triage OpenEnv
"""

import json
import os
import threading
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from server.email_triage_env import (
    EmailTriageEnv,
    Action,
    EmailAction,
    Observation,
)

load_dotenv()

SESSION_STORE_PATH = Path(__file__).resolve().parent / ".runtime" / "sessions.json"
DEFAULT_SESSION_ID = "default"
_store_lock = threading.Lock()

app = FastAPI(
    title="Email Triage OpenEnv",
    description="A benchmark environment for evaluating email triage AI agents",
    version="1.0.0",
)

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for built frontend
try:
    public_path = Path(__file__).resolve().parent.parent / "public"
    if public_path.exists():
        app.mount("/public", StaticFiles(directory=public_path), name="public")
except Exception as e:
    print(f"Warning: Could not mount /public: {e}")

try:
    next_static_path = Path(__file__).resolve().parent.parent / ".next" / "static"
    if next_static_path.exists():
        app.mount("/_next/static", StaticFiles(directory=next_static_path), name="next-static")
except Exception as e:
    print(f"Warning: Could not mount /_next/static: {e}")


@app.on_event("startup")
async def startup_event():
    """Initialize on startup - non-blocking."""
    # Don't block startup with session loading
    # Sessions will be loaded on first request
    pass

# In-memory session cache, persisted to disk after each mutation.
env_sessions: dict[str, EmailTriageEnv] = {}


class ResetRequest(BaseModel):
    """Reset environment request"""
    task: str = "easy"
    session_id: str | None = None


class StepRequest(BaseModel):
    """Step request"""
    action: str
    email_id: str
    details: dict = Field(default_factory=dict)
    session_id: str | None = None


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    message: str


class StateResponse(BaseModel):
    """State response"""
    task: str
    task_description: str
    step_count: int
    max_steps: int
    cumulative_reward: float
    normalized_score: float
    correct_action_count: int
    actions_taken: dict
    progress: str
    done: bool


class TasksResponse(BaseModel):
    """Tasks list response"""
    tasks: list[dict]


def _normalize_session_id(candidate: str | None) -> str:
    """Return a stable session id when client omits one."""

    cleaned = (candidate or "").strip()
    return cleaned or DEFAULT_SESSION_ID


def _ensure_store_dir() -> None:
    SESSION_STORE_PATH.parent.mkdir(parents=True, exist_ok=True)


def _persist_sessions() -> None:
    """Persist all active sessions for recovery after process restart."""

    _ensure_store_dir()
    payload = {
        "sessions": {
            session_id: env.export_session_state()
            for session_id, env in env_sessions.items()
        }
    }
    SESSION_STORE_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _load_sessions() -> None:
    """Restore session cache from disk if available."""

    if not SESSION_STORE_PATH.exists():
        return

    try:
        raw = json.loads(SESSION_STORE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return

    sessions = raw.get("sessions", {}) if isinstance(raw, dict) else {}
    if not isinstance(sessions, dict):
        return

    for session_id, state in sessions.items():
        if not isinstance(session_id, str) or not isinstance(state, dict):
            continue
        try:
            env_sessions[session_id] = EmailTriageEnv.from_session_state(state)
        except ValueError:
            continue


def _get_env_for_session(session_id: str | None) -> tuple[str, EmailTriageEnv]:
    """Resolve environment by session id, raising 400 when missing."""

    normalized = _normalize_session_id(session_id)
    env = env_sessions.get(normalized)
    if env is None:
        raise HTTPException(
            status_code=400,
            detail="Environment not initialized for this session. Call /reset first.",
        )
    return normalized, env


# Lazy load sessions on first request
_sessions_loaded = False


def _ensure_sessions_loaded():
    """Lazy load sessions on first request."""
    global _sessions_loaded
    if not _sessions_loaded:
        _load_sessions()
        _sessions_loaded = True


def main() -> None:
    """Run the FastAPI application with Uvicorn."""

    import uvicorn

    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
    )


@app.get("/health")
async def health():
    """Health check endpoint - simple and non-blocking"""
    return {"status": "healthy", "message": "Email Triage OpenEnv server is running"}


@app.get("/")
async def root():
    """Root endpoint - return simple health status"""
    return {"status": "ok", "message": "Email Triage OpenEnv API"}


@app.post("/reset")
async def reset(request: ResetRequest | None = None) -> dict:
    """
    Reset the environment and start a new task

    Args:
        request: ResetRequest with task name (easy, medium, hard) - optional

    Returns:
        Initial observation
    """
    _ensure_sessions_loaded()
    try:
        # Use defaults if request is None or fields are missing
        task = (request.task if request and request.task else "easy") or "easy"
        session_id = _normalize_session_id(request.session_id if request else None)

        with _store_lock:
            env_sessions[session_id] = EmailTriageEnv(task=task)
            obs = env_sessions[session_id].reset()
            _persist_sessions()

        return {
            "success": True,
            "session_id": session_id,
            "observation": obs.model_dump(),
            "state": env_sessions[session_id].state(),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/step")
async def step(request: StepRequest) -> dict:
    """
    Execute an action in the environment
    
    Args:
        request: StepRequest with action, email_id, and optional details
    
    Returns:
        Observation, reward, and done flag
    """
    try:
        with _store_lock:
            session_id, env = _get_env_for_session(request.session_id)

        # Validate action
        try:
            action_enum = EmailAction[request.action.upper()]
        except KeyError:
            raise ValueError(
                f"Invalid action. Must be one of: {[a.value for a in EmailAction]}"
            )
        
        action = Action(
            action=action_enum,
            email_id=request.email_id,
            details=request.details,
        )

        with _store_lock:
            obs, reward, done, info = env.step(action)
            _persist_sessions()
        
        return {
            "success": True,
            "session_id": session_id,
            "observation": obs.model_dump(),
            "reward": reward.model_dump(),
            "done": done,
            "info": info,
            "state": env.state(),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/state", response_model=StateResponse)
async def get_state(session_id: str | None = None) -> dict:
    """Get current environment state"""
    _, env = _get_env_for_session(session_id)
    return env.state()


@app.get("/grade")
async def grade(session_id: str | None = None) -> dict:
    """Grade the completed task"""
    _, env = _get_env_for_session(session_id)
    return env.grade()


@app.get("/tasks", response_model=TasksResponse)
async def get_tasks():
    """Get available tasks"""
    tasks = [
        {
            "id": task_id,
            "name": config["name"],
            "description": config["description"],
            "email_count": len(config["emails"]),
        }
        for task_id, config in EmailTriageEnv.TASKS.items()
    ]
    
    return TasksResponse(tasks=tasks)


@app.get("/observation")
async def get_observation(session_id: str | None = None) -> dict:
    """Get current observation"""
    _, env = _get_env_for_session(session_id)
    obs = env._get_observation()
    return obs.model_dump()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"FATAL ERROR: {e}", flush=True)
        import traceback
        traceback.print_exc()
        raise
