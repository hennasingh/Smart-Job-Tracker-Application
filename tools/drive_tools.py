# tools/drive_tools.py
#
# Three ADK-compatible tools for the drive_agent:
#   1. ensure_sheet_headers  — make sure the Sheet has the right column headings
#   2. upsert_job_row        — add or update a job row (keyed on company + role)
#   3. get_all_jobs          — read all rows back as a list of dicts

import os
from datetime import datetime, timezone

from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

TOKEN_PATH = "token.json"
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID", "")
SHEET_NAME = "Job Applications"

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/calendar",
]

HEADERS = ["Company", "Role", "Status", "Date", "Source Email Subject", "Last Updated"]


# ---------------------------------------------------------------------------
# Shared helper
# ---------------------------------------------------------------------------

def _get_sheets_service():
    """Load saved OAuth2 credentials and return an authenticated Sheets client."""
    creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    return build("sheets", "v4", credentials=creds)


def _read_all_rows(service) -> list[list]:
    """Return every row (including header) from the Jobs sheet."""
    result = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=SPREADSHEET_ID, range=f"{SHEET_NAME}!A:F")
        .execute()
    )
    return result.get("values", [])


# ---------------------------------------------------------------------------
# Tool 1: ensure_sheet_headers
# ---------------------------------------------------------------------------

def ensure_sheet_headers() -> dict:
    """
    Ensure the first row of the Google Sheet contains the correct column headers.
    Creates or overwrites the header row if it is missing or incorrect.

    Returns:
        A dict with keys "status" and "message".
    """
    try:
        service = _get_sheets_service()
        rows = _read_all_rows(service)

        if rows and rows[0] == HEADERS:
            return {"status": "success", "message": "Headers already present"}

        service.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=f"{SHEET_NAME}!A1",
            valueInputOption="RAW",
            body={"values": [HEADERS]},
        ).execute()

        return {"status": "success", "message": "Headers created/updated"}

    except Exception as e:
        return {"status": "error", "message": str(e)}


# ---------------------------------------------------------------------------
# Tool 2: upsert_job_row
# ---------------------------------------------------------------------------

def upsert_job_row(
    company: str,
    role: str,
    status: str,
    date: str,
    source_subject: str,
) -> dict:
    """
    Add a new job row to the Google Sheet, or update it if an entry for the
    same company + role already exists.

    Args:
        company:        Company name (e.g. "Google").
        role:           Job title / role (e.g. "Software Engineer").
        status:         One of: applied | interview_scheduled | offer | rejected | unknown.
        date:           Date string from the email (e.g. "Mon, 11 May 2026 …").
        source_subject: Email subject line, for traceability.

    Returns:
        A dict with "status", "action" ("added" or "updated"), and the row number.
    """
    try:
        service = _get_sheets_service()
        ensure_sheet_headers()

        rows = _read_all_rows(service)
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        new_row = [company, role, status, date, source_subject, now]

        # Search for an existing row with matching company + role (skip header)
        for i, row in enumerate(rows[1:], start=2):  # 1-indexed; row 1 is header
            existing_company = row[0] if len(row) > 0 else ""
            existing_role = row[1] if len(row) > 1 else ""

            if (
                existing_company.strip().lower() == company.strip().lower()
                and existing_role.strip().lower() == role.strip().lower()
            ):
                service.spreadsheets().values().update(
                    spreadsheetId=SPREADSHEET_ID,
                    range=f"{SHEET_NAME}!A{i}:F{i}",
                    valueInputOption="RAW",
                    body={"values": [new_row]},
                ).execute()
                return {"status": "success", "action": "updated", "row": i}

        # No match — append a new row
        service.spreadsheets().values().append(
            spreadsheetId=SPREADSHEET_ID,
            range=f"{SHEET_NAME}!A:F",
            valueInputOption="RAW",
            insertDataOption="INSERT_ROWS",
            body={"values": [new_row]},
        ).execute()

        return {"status": "success", "action": "added", "row": len(rows) + 1}

    except Exception as e:
        return {"status": "error", "message": str(e)}


# ---------------------------------------------------------------------------
# Tool 3: get_all_jobs
# ---------------------------------------------------------------------------

def get_all_jobs() -> dict:
    """
    Read all job rows from the Google Sheet and return them as a list of dicts.

    Each dict uses the sheet column headers as keys:
      Company | Role | Status | Date | Source Email Subject | Last Updated

    Returns:
        A dict with "status", "count", and "jobs" (list of dicts).
    """
    try:
        service = _get_sheets_service()
        rows = _read_all_rows(service)

        if len(rows) <= 1:
            return {"status": "success", "count": 0, "jobs": []}

        headers = rows[0]
        jobs = []
        for row in rows[1:]:
            # Pad short rows so zip always produces all keys
            padded = row + [""] * (len(headers) - len(row))
            jobs.append(dict(zip(headers, padded)))

        return {"status": "success", "count": len(jobs), "jobs": jobs}

    except Exception as e:
        return {"status": "error", "message": str(e)}
