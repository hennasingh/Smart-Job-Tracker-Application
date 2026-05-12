# agents/agent.py
#
# Root orchestrator for the job tracker (MVP).
#
# Uses SequentialAgent to guarantee all three sub-agents run in order:
#   1. gmail_agent  — scan inbox, extract structured job data
#   2. drive_agent  — upsert jobs into the Google Sheet
#   3. summary_agent — produce a Markdown digest from the pipeline output
#
# SequentialAgent does not use an LLM for routing — it runs sub-agents
# in strict sequence, which avoids the LLM stopping early.
#
# Usage:
#   uv run adk web

from google.adk.agents import SequentialAgent

from agents.sub_agents.gmail_agent import gmail_agent
from agents.sub_agents.drive_agent import drive_agent
from agents.sub_agents.summary_agent import summary_agent

root_agent = SequentialAgent(
    name="job_tracker",
    description=(
        "End-to-end job application tracker. Scans Gmail for recruiter emails, "
        "writes structured job data to a Google Sheet, and produces a clean "
        "Markdown summary."
    ),
    sub_agents=[
        gmail_agent,
        drive_agent,
        summary_agent,
    ],
)
