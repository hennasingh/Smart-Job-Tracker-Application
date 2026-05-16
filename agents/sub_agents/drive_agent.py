# agents/sub_agents/drive_agent.py
#
# Drive sub-agent for the job tracker.
#
# Tools:
#   - ensure_sheet_headers : guarantee the sheet has correct column headings
#   - batch_upsert_jobs    : upsert all jobs in 2-3 API calls (preferred)
#   - upsert_job_row       : single-row upsert for targeted corrections
#   - get_all_jobs         : read the full sheet back as structured data
#
# Standalone test:
#   adk run agents.sub_agents.drive_agent

from google.adk.agents import Agent

from tools.drive_tools import (
    ensure_sheet_headers,
    batch_upsert_jobs,
    upsert_job_row,
    get_all_jobs,
)

# ---------------------------------------------------------------------------
# Agent definition
# ---------------------------------------------------------------------------

drive_agent = Agent(
    name="drive_agent",
    model="gemini-2.5-flash",

    description=(
        "Writes job application data to the Google Sheet tracker. "
        "Given a list of jobs from the Gmail agent, it upserts all of them "
        "in a single batch call and confirms how many rows were added or updated."
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

Step 2 — Call `batch_upsert_jobs` ONCE, passing the entire list of jobs.
          This handles all updates and inserts in a single operation.
          Do NOT call `upsert_job_row` in a loop — use `batch_upsert_jobs` instead.

Step 3 — Call `get_all_jobs` to retrieve the current snapshot of the sheet.

Step 4 — Return a clear summary:
          - Number of rows added
          - Number of rows updated
          - The full current list of tracked jobs (company, role, status, date)

## Rules
- Always call `ensure_sheet_headers` first, every time.
- Always use `batch_upsert_jobs` for writing — never loop over `upsert_job_row`.
- Only use `upsert_job_row` if you need to correct a single specific row.
- If `batch_upsert_jobs` returns errors for individual jobs, report them.
- Do not expose internal details (row numbers, sheet IDs) to the user.
""",

    tools=[
        ensure_sheet_headers,
        batch_upsert_jobs,
        upsert_job_row,
        get_all_jobs,
    ],
)
