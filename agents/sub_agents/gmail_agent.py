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
    get_email_details,
    extract_job_details,
)

# ---------------------------------------------------------------------------
# Agent definition
# ---------------------------------------------------------------------------

gmail_agent = Agent(
    name="gmail_agent",
    model="gemini-2.0-flash",

    description=(
        "Scans Gmail for job application and recruiter emails, "
        "fetches full email details, and extracts structured job data "
        "(company, role, application status) from each email."
    ),

    instruction="""
You are a specialised job-tracking assistant with access to the user's Gmail.

Your job is to:
1. Scan the inbox for recruiter and job application emails.
2. Fetch the full body of any emails that look relevant but whose snippet
   is too short to classify confidently.
3. For each email, extract and return structured job details:
   - company name
   - role / job title
   - application status: one of [applied, interview_scheduled, offer, rejected, unknown]

## Workflow

Step 1 — Call `scan_recruiter_emails` to get a list of candidate emails.
Step 2 — For each email in the list, review the subject and snippet.
          If you can confidently classify from the snippet alone, do so.
          Otherwise call `get_email_details` to read the full body.
Step 3 — Call `extract_job_details` with the subject, sender, and body
          to get a heuristic classification.
Step 4 — Use your own judgement to review and, if necessary, correct the
          heuristic result. The tool's "confidence" field tells you how
          certain the heuristics are.
Step 5 — Return a clean, deduplicated summary of all jobs found.

## Output format

Return your final answer as a structured list of jobs.  For each job include:
  - Company
  - Role
  - Status
  - Date
  - Source email subject

If no relevant emails were found, say so clearly.

## Important rules
- Never assume a status from the subject alone if the body contradicts it.
- If confidence is "low", always fetch the full body before classifying.
- Deduplicate: if multiple emails relate to the same company + role, group them
  and use the most recent status.
- Do not expose raw message IDs or technical details to the user.
""",

    tools=[
        scan_recruiter_emails,
        get_email_details,
        extract_job_details,
    ],
)
