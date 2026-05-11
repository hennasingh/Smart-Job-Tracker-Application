# backend/api_server.py
#
# Lightweight FastAPI server that exposes the job tracker pipeline via HTTP.
#
# Endpoints:
#   POST /run   — trigger the full orchestrator (Gmail → Sheets → Calendar → Summary)
#   GET  /jobs  — return the current Sheet contents as JSON (no agent run)
#
# Run with:
#   uvicorn backend.api_server:app --reload --port 8000

import sys
import os
import asyncio
import uuid

# Ensure the project root is on sys.path when running from the backend/ dir
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai.types import Content, Part

from agents.agent import root_agent
from tools.drive_tools import get_all_jobs

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Job Tracker API",
    description="Multi-agent job application tracker powered by Google ADK + Gemini.",
    version="0.1.0",
)

# Allow the frontend (any origin during dev) to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

APP_NAME = "job_tracker"


# ---------------------------------------------------------------------------
# Helper: run the orchestrator pipeline
# ---------------------------------------------------------------------------

async def _run_pipeline(user_message: str = "Run the full job tracking pipeline.") -> str:
    """
    Invoke the root_agent via the ADK InMemoryRunner and return its final
    text response.
    """
    session_service = InMemorySessionService()
    session_id = str(uuid.uuid4())
    user_id = "user"

    await session_service.create_session(
        app_name=APP_NAME,
        user_id=user_id,
        session_id=session_id,
    )

    runner = Runner(
        agent=root_agent,
        app_name=APP_NAME,
        session_service=session_service,
    )

    message = Content(role="user", parts=[Part(text=user_message)])
    final_response = ""

    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=message,
    ):
        if event.is_final_response():
            final_response = event.content.parts[0].text if event.content.parts else ""

    return final_response


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

class RunResponse(BaseModel):
    status: str
    summary: str


class JobsResponse(BaseModel):
    status: str
    count: int
    jobs: list[dict]


@app.post("/run", response_model=RunResponse, summary="Run full pipeline")
async def run_pipeline():
    """
    Trigger the complete orchestrator pipeline:
    1. Gmail agent scans for recruiter emails
    2. Drive agent upserts jobs into the Google Sheet
    3. Calendar agent books interview events
    4. Summary agent returns a Markdown digest

    Returns the final Markdown summary from the pipeline.
    """
    try:
        summary = await _run_pipeline()
        return RunResponse(status="success", summary=summary)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/jobs", response_model=JobsResponse, summary="Get all tracked jobs")
async def get_jobs():
    """
    Return the current contents of the 'Job Applications' Google Sheet
    as a JSON list — without triggering the agent pipeline.
    """
    result = get_all_jobs()
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result.get("message", "Unknown error"))
    return JobsResponse(
        status="success",
        count=result["count"],
        jobs=result["jobs"],
    )


@app.get("/health", summary="Health check")
async def health():
    """Simple liveness probe."""
    return {"status": "ok", "service": "job-tracker-api"}
