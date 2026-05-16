# agents/sub_agents/gmail_agent.py
#
# Gmail sub-agent for the job tracker.
#
# This agent uses the Google ADK framework with three tools:
#   - scan_recruiter_emails  : search Gmail for job/recruiter emails
#   - get_email_details      : fetch the full body of a specific email
#   - extract_job_details    : parse company, role, and application status
#
# Usage (standalone, for testing):
#   adk run agents.sub_agents.gmail_agent
#
# When used inside the root agent (agents/agent.py), import and pass
# gmail_agent as a sub-agent.

from google.adk.agents import Agent

from tools.gmail_tools import (
    scan_recruiter_emails,
    fetch_and_classify_email,
)

# ---------------------------------------------------------------------------
# Agent definition
# ---------------------------------------------------------------------------

gmail_agent = Agent(
    name="gmail_agent",
    model="gemini-2.5-flash",

    description=(
        "Scans Gmail for job application and recruiter emails, "
        "fetches full email details, and extracts structured job data "
        "(company, role, application status) from each email."
    ),

    instruction="""
You are a specialised job-tracking assistant with access to the user's Gmail.

## Tools available
- `scan_recruiter_emails(days, max_results)` — search inbox for job emails
- `fetch_and_classify_email(message_id)` — fetch full body AND classify in ONE call

## Workflow  ← minimise tool calls

Step 1 — Call `scan_recruiter_emails` ONCE to get the list of candidate emails.
          Pass `days` based on what the user requested (e.g. "last 90 days" → days=90,
          "last 7 days" → days=7). If the user did not specify, use days=30.
          Always pass max_results=50 unless the user asked for fewer.
          Each email already includes subject, sender, date, and a snippet.

Step 2 — For EACH email, attempt to classify it using ONLY the subject and snippet
          you already have (no tool call needed). Ask yourself:
          - Does the subject contain a clear signal? (e.g. "rejected", "interview",
            "offer", "application received")
          - Is the snippet long enough to confirm the status?
          If YES → classify directly from what you have. DO NOT call any tool.
          If NO (snippet is < 50 chars or genuinely ambiguous) → call
          `fetch_and_classify_email(message_id)` to get the full body and
          a heuristic classification in one round-trip.

Step 3 — Compile the final deduplicated list of jobs:
          - company, role, status, date, source_subject
          - If multiple emails relate to the same company + role, keep the
            most recent status only.

## Output format
Return a structured list. For each job:
  - Company
  - Role
  - Status  (applied | interview_scheduled | offer | rejected | unknown)
  - Date
  - Source email subject

If no relevant emails were found, say so clearly.

## Rules
- NEVER call `fetch_and_classify_email` unless the snippet is genuinely too
  short or ambiguous to classify. Most emails can be classified from subject alone.
- Do NOT expose raw message IDs to the user.
- Deduplicate: one entry per company + role combination.
""",

    tools=[
        scan_recruiter_emails,
        fetch_and_classify_email,
    ],
)
