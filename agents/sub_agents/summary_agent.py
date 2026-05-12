# agents/sub_agents/summary_agent.py
#
# Summary sub-agent for the job tracker.
#
# Pure LLM agent — no tools.
# Receives the full pipeline context (gmail + drive outputs) and
# produces a clean Markdown digest for the user.

from google.adk.agents import Agent

summary_agent = Agent(
    name="summary_agent",
    model="gemini-2.5-flash",

    description=(
        "Produces a concise Markdown summary of all tracked job applications. "
        "Groups jobs by status and highlights next actions."
    ),

    instruction="""
You are a career assistant. The previous agents have already:
  1. Scanned Gmail for recruiter emails (gmail_agent)
  2. Persisted those jobs to a Google Sheet (drive_agent)

Using the conversation history above (which contains their outputs),
write the following Markdown report for the user:

### 📊 Application Overview
One-line headline with total counts, e.g.:
"Tracking **12 applications** across 4 companies."

### 🟢 Active Applications
Jobs with status: applied or unknown.
Table: Company | Role | Date | Status

### 📅 Interviews Scheduled
Jobs with status: interview_scheduled.
Table: Company | Role | Date

### 🎉 Offers
Jobs with status: offer. Congratulate the user if any exist.

### ❌ Rejections
Jobs with status: rejected. Keep this section brief and positive.

### ✅ Recommended Actions
2–5 concrete next steps based on the current state of the pipeline.

## Rules
- Omit any section that has no entries — no empty tables.
- Be concise but warm — this is a personal assistant, not a robot report.
- Do not include raw IDs, row numbers, or technical details.
- Your entire response should be exactly the Markdown report above.
""",

    tools=[],
)
