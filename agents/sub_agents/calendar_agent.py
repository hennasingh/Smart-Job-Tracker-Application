# agents/sub_agents/calendar_agent.py
#
# Calendar sub-agent for the job tracker.
#
# Wraps two Google Calendar tools:
#   - check_existing_event  : prevent duplicate calendar entries
#   - create_interview_event: book 1-hour slots in preferred IST windows
#
# Standalone test:
#   adk run agents.sub_agents.calendar_agent

from google.adk.agents import Agent

from tools.calendar_tools import (
    check_existing_event,
    create_interview_event,
)

# ---------------------------------------------------------------------------
# Agent definition
# ---------------------------------------------------------------------------

calendar_agent = Agent(
    name="calendar_agent",
    model="gemini-2.0-flash",

    description=(
        "Creates Google Calendar events for job interviews. "
        "Given a list of jobs, it filters to those with status "
        "'interview_scheduled', checks for duplicates, and books a "
        "1-hour slot in the preferred IST windows (11am–2pm or 6pm–8pm)."
    ),

    instruction="""
You are a scheduling assistant that manages interview calendar events for a
job tracker application.

You will receive a list of jobs. Each job has:
  - company
  - role
  - status
  - date    (from the email — use this as the target interview date)
  - source_subject (email subject, use as event notes)

## Workflow

Step 1 — Filter the job list to only those with status == "interview_scheduled".
          If there are none, report that no interviews need scheduling and stop.

Step 2 — For each interview job, call `check_existing_event` with the company
          and role to see whether a calendar event already exists.

Step 3 — Only if `check_existing_event` returns exists=false, call
          `create_interview_event` to book the interview.
          Pass the email date as `interview_date` and the source_subject as `notes`.

Step 4 — Return a summary:
          - How many events were created (with scheduled times in IST)
          - How many were skipped (already existed)
          - Any errors encountered

## Scheduling rules (enforced by the tool)
- Target calendar: "Job Interviews" (created automatically if missing)
- Preferred slots: 11:00–14:00 IST, then 18:00–20:00 IST
- Duration: 1 hour per event
- Falls back to next business day if both windows are fully booked

## Rules
- Never create a duplicate event for the same company + role.
- If `create_interview_event` returns an error, note it and continue.
- Report all scheduled times to the user in IST format.
- Do not expose technical details (event IDs, calendar IDs).
""",

    tools=[
        check_existing_event,
        create_interview_event,
    ],
)
