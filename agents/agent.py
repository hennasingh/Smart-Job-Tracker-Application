# agents/agent.py
#
# Root orchestrator for the job tracker.
#
# This agent sequences four sub-agents to deliver a full end-to-end pipeline:
#   1. gmail_agent    — scan inbox, extract structured job data
#   2. drive_agent    — upsert jobs into the Google Sheet
#   3. calendar_agent — create interview events in "Job Interviews" calendar
#   4. summary_agent  — produce a Markdown digest for the user
#
# Usage:
#   adk run agents.agent
#   adk web   (interactive dev UI)

from google.adk.agents import Agent

from agents.sub_agents.gmail_agent import gmail_agent
from agents.sub_agents.drive_agent import drive_agent
from agents.sub_agents.calendar_agent import calendar_agent
from agents.sub_agents.summary_agent import summary_agent

# ---------------------------------------------------------------------------
# Root agent definition
# ---------------------------------------------------------------------------

root_agent = Agent(
    name="job_tracker",
    model="gemini-2.0-flash",

    description=(
        "End-to-end job application tracker. Scans Gmail for recruiter emails, "
        "writes structured job data to a Google Sheet, books interview events "
        "in Google Calendar, and produces a clean Markdown summary."
    ),

    instruction="""
You are the orchestrator of a job application tracking system.
Your job is to coordinate four specialist sub-agents in strict sequence
and deliver a final report to the user.

## Pipeline (execute in this exact order)

### Step 1 — Gmail scan
Transfer to `gmail_agent`.
It will scan the inbox, fetch email details, and extract a structured list
of jobs (company, role, status, date, source_subject).
Capture its full output — you will pass it to the next agents.

### Step 2 — Persist to Google Sheets
Transfer to `drive_agent`.
Pass it the complete list of jobs from Step 1.
It will upsert each job into the "Job Applications" Google Sheet and return:
  - how many rows were added
  - how many rows were updated
  - the full current snapshot of all tracked jobs

### Step 3 — Schedule interviews
Transfer to `calendar_agent`.
Pass it the list of jobs from Step 1 (it will filter for interview_scheduled).
It will check for duplicates and create 1-hour calendar events in the
"Job Interviews" calendar during the preferred IST windows.
It returns how many events were created and their scheduled times.

### Step 4 — Produce final summary
Transfer to `summary_agent`.
Pass it:
  - The full job list from Step 2 (current Sheet snapshot)
  - The calendar events created in Step 3
  - The added/updated row counts from Step 2
It will produce a formatted Markdown report for the user.

## Rules
- Always execute all four steps in order — never skip a step.
- If gmail_agent finds no relevant emails, still run steps 2–4 so the user
  gets an up-to-date summary of their existing tracked jobs.
- If drive_agent or calendar_agent encounters errors on individual items,
  continue the pipeline — do not abort.
- Your final message to the user should be exactly the Markdown report
  produced by summary_agent, with no additional wrapper text.
""",

    sub_agents=[
        gmail_agent,
        drive_agent,
        calendar_agent,
        summary_agent,
    ],
)
