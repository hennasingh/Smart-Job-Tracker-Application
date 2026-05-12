# Smart Job Tracker Application

An AI-powered job application tracker that automatically scans your Gmail for recruiter and application emails, extracts structured job data, and persists it to a Google Sheet — all via a conversational agent interface.

Built with [Google Agent Development Kit (ADK)](https://google.github.io/adk-docs/) and Gemini 2.5 Flash.

---

## How It Works

The application uses a **SequentialAgent** pipeline with three specialised sub-agents that run in order each time you start a session:

```
Gmail Agent → Drive Agent → Summary Agent
```

| Agent | Responsibility |
|---|---|
| **Gmail Agent** | Scans your inbox for recruiter and job-application emails; extracts company, role, and application status from each |
| **Drive Agent** | Upserts the extracted job data into a Google Sheet (adds new rows or updates existing ones) |
| **Summary Agent** | Reads the full pipeline output and produces a clean Markdown digest grouped by application status |

### Application Statuses

Jobs are classified into one of five statuses:

- `applied` — application confirmation received
- `interview_scheduled` — interview or screening call mentioned
- `offer` — offer letter or formal offer detected
- `rejected` — rejection language detected
- `unknown` — email matched as job-related but status could not be determined

---

## Prerequisites

- Python 3.14+
- [`uv`](https://docs.astral.sh/uv/) package manager
- A Google Cloud project with the following APIs enabled:
  - Gmail API
  - Google Sheets API
  - Google Calendar API
- OAuth 2.0 credentials (`credentials.json`) downloaded from the Google Cloud Console
- A Google Sheet to use as the job tracker (you will need its Spreadsheet ID)

---

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/hennasingh/Smart-Job-Tracker-Application.git
cd Smart-Job-Tracker-Application
```

### 2. Install dependencies

```bash
uv sync
```

### 3. Configure Google Cloud credentials

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create (or select) a project and enable the **Gmail API**, **Google Sheets API**, and **Google Calendar API**
3. Under **APIs & Services → Credentials**, create an **OAuth 2.0 Client ID** (Desktop app)
4. Download the credentials file and save it as `credentials.json` in the project root

### 4. Authenticate

Run the one-time authentication script to generate `token.json`:

```bash
uv run python authenticate.py
```

This opens your browser for the Google OAuth consent flow. On success, `token.json` is saved to the project root — the agents will use it automatically on subsequent runs.

### 5. Configure environment variables

Create a `.env` file in the project root:

```env
SPREADSHEET_ID=your_google_sheet_id_here
GOOGLE_GENAI_USE_VERTEXAI=FALSE
GOOGLE_API_KEY=your_gemini_api_key_here
```

- **`SPREADSHEET_ID`** — The ID from your Google Sheet URL:
  `https://docs.google.com/spreadsheets/d/<SPREADSHEET_ID>/edit`
- **`GOOGLE_API_KEY`** — Your Gemini API key from [Google AI Studio](https://aistudio.google.com/)

---

## Running the Application

Start the ADK web interface:

```bash
uv run adk web
```

Then open [http://localhost:8000](http://localhost:8000) in your browser and start a conversation with the `job_tracker` agent.

**Example prompt:**

> "Scan my inbox for job applications from the last 30 days and update my tracker."

The agent will scan Gmail, update your Google Sheet, and respond with a formatted summary.

### Running Individual Sub-Agents (for testing)

```bash
# Test the Gmail scanning agent alone
uv run adk run agents.sub_agents.gmail_agent

# Test the Google Sheets agent alone
uv run adk run agents.sub_agents.drive_agent
```

---

## Project Structure

```
Smart-Job-Tracker-Application/
├── agents/
│   ├── agent.py                  # Root SequentialAgent (entry point)
│   └── sub_agents/
│       ├── gmail_agent.py        # Scans Gmail and classifies emails
│       ├── drive_agent.py        # Writes job data to Google Sheets
│       └── summary_agent.py      # Produces the final Markdown report
├── tools/
│   ├── gmail_tools.py            # Gmail API tools (scan, fetch, classify)
│   └── drive_tools.py            # Sheets API tools (headers, upsert, read)
├── authenticate.py               # One-time OAuth2 setup script
├── pyproject.toml
└── .env                          # Your local config (not committed)
```

---

## Google Sheet Schema

The agent writes to a sheet tab named `job_applications` with the following columns:

| Column | Description |
|---|---|
| Company | Organisation name (extracted from sender email domain) |
| Role | Job title or position |
| Status | `applied` / `interview_scheduled` / `offer` / `rejected` / `unknown` |
| Date | Date from the original email |
| Source Email Subject | Subject line of the email, for traceability |
| Last Updated | UTC timestamp of the most recent upsert |

Rows are keyed on **Company + Role** — re-running the agent will update existing entries rather than create duplicates.

---

## Required Google OAuth Scopes

| Scope | Purpose |
|---|---|
| `gmail.readonly` | Read emails to find job applications |
| `spreadsheets` | Read and write the job tracker Google Sheet |
| `calendar` | Reserved for future interview scheduling features |

---

## Dependencies

| Package | Purpose |
|---|---|
| `google-adk` | Agent Development Kit — agent orchestration framework |
| `google-api-python-client` | Gmail and Sheets API client |
| `google-auth-oauthlib` | OAuth 2.0 authentication flow |
| `google-auth-httplib2` | HTTP transport for Google auth |
| `python-dotenv` | Load environment variables from `.env` |
