# agents/sub_agents/drive_agent.py
#
# Drive sub-agent for the job tracker.
#
# Wraps three Google Sheets tools:
#   - ensure_sheet_headers : guarantee the sheet has correct column headings
#   - upsert_job_row       : add or update a job (keyed on company + role)
#   - get_all_jobs         : read the full sheet back as structured data
#
# Standalone test:
#   adk run agents.sub_agents.drive_agent

from google.adk.agents import Agent

from tools.drive_tools import (
    ensure_sheet_headers,
    upsert_job_row,
    get_all_jobs,
)

# ---------------------------------------------------------------------------
# Agent definition
# ---------------------------------------------------------------------------

drive_agent = Agent(
    name="drive_agent",
    model="gemini-2.0-flash",

    description=(
        "Writes job application data to the Google Sheet tracker. "
        "Given a list of jobs from the Gmail agent, it upserts each one "
        "into the sheet and confirms how many rows were added or updated."
    ),

    instruction="""
You are a data-persistence assistant responsible for keeping the job tracker
Google Sheet ("Job Applications") up to date.

You will receive a list of jobs. Each job has:
  - company
  - role
  - status  (applied | interview_scheduled | offer | rejected | unknown)
  - date    (from the email)
  - source_subject (email subject line)

## Workflow

Step 1 — Call `ensure_sheet_headers` once before writing any data.

Step 2 — For each job, call `upsert_job_row` with the job's details.
          The tool will update an existing row (same company + role)
          or append a new one.

Step 3 — After processing all jobs, call `get_all_jobs` to retrieve the
          current snapshot of the sheet.

Step 4 — Return a clear summary:
          - Number of rows added
          - Number of rows updated
          - The full current list of tracked jobs (company, role, status, date)

## Rules
- Always call `ensure_sheet_headers` first, every time.
- Process every job — do not skip any.
- If `upsert_job_row` returns an error for a specific job, note it and
  continue with the remaining jobs.
- Do not expose internal details (row numbers, sheet IDs) to the user.
""",

    tools=[
        ensure_sheet_headers,
        upsert_job_row,
        get_all_jobs,
    ],
)
