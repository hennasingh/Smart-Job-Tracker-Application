# tools/calendar_tools.py
#
# Two ADK-compatible tools for the calendar_agent:
#   1. check_existing_event  — avoid duplicate calendar entries
#   2. create_interview_event — book a 1-hour slot in the preferred IST windows

import re
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from zoneinfo import ZoneInfo

from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

TOKEN_PATH = "token.json"
CALENDAR_NAME = "Job Interviews"
INTERVIEW_DURATION_HOURS = 1

IST = ZoneInfo("Asia/Kolkata")

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/calendar",
]

# Preferred interview windows in IST: (start_hour, start_min, end_hour, end_min)
PREFERRED_WINDOWS = [
    (11, 0, 14, 0),   # 11:00–14:00 IST  (05:30–08:30 UTC)
    (18, 0, 20, 0),   # 18:00–20:00 IST  (12:30–14:30 UTC)
]


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _get_calendar_service():
    """Load saved OAuth2 credentials and return an authenticated Calendar client."""
    creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    return build("calendar", "v3", credentials=creds)


def _get_or_create_job_calendar(service) -> str:
    """
    Return the calendar ID of the 'Job Interviews' calendar.
    Creates it (with IST timezone) if it doesn't already exist.
    """
    cal_list = service.calendarList().list().execute()
    for cal in cal_list.get("items", []):
        if cal.get("summary") == CALENDAR_NAME:
            return cal["id"]

    # Doesn't exist yet — create it
    new_cal = service.calendars().insert(
        body={"summary": CALENDAR_NAME, "timeZone": "Asia/Kolkata"}
    ).execute()
    return new_cal["id"]


def _parse_email_date(date_str: str) -> datetime:
    """
    Parse an email Date header (RFC 2822 or ISO) into an aware datetime.
    Falls back to today in IST if parsing fails.
    """
    # Try RFC 2822 (standard email Date header)
    try:
        return parsedate_to_datetime(date_str)
    except Exception:
        pass

    # Try ISO 8601 variants
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(date_str[:len(fmt)], fmt)
            return dt.replace(tzinfo=ZoneInfo("UTC")) if dt.tzinfo is None else dt
        except ValueError:
            continue

    # Fallback: today in IST
    return datetime.now(IST)


def _find_free_slot(service, calendar_id: str, target_date: datetime) -> datetime | None:
    """
    Walk preferred IST windows on target_date (then up to 6 future business days)
    and return the first UTC datetime of a free 1-hour slot.
    Returns None if no slot is found within the search window.
    """
    utc = timezone.utc

    for day_offset in range(7):
        check_day = target_date + timedelta(days=day_offset)

        # Skip weekends
        if check_day.weekday() >= 5:
            continue

        for (start_h, start_m, end_h, end_m) in PREFERRED_WINDOWS:
            window_start = datetime(
                check_day.year, check_day.month, check_day.day,
                start_h, start_m, tzinfo=IST
            ).astimezone(utc)

            window_end = datetime(
                check_day.year, check_day.month, check_day.day,
                end_h, end_m, tzinfo=IST
            ).astimezone(utc)

            # Query busy times for the calendar in this window
            fb_result = service.freebusy().query(
                body={
                    "timeMin": window_start.isoformat(),
                    "timeMax": window_end.isoformat(),
                    "items": [{"id": calendar_id}],
                }
            ).execute()
            busy_slots = fb_result["calendars"][calendar_id]["busy"]

            # Slide a 1-hour window across the free period
            slot_start = window_start
            while slot_start + timedelta(hours=INTERVIEW_DURATION_HOURS) <= window_end:
                slot_end = slot_start + timedelta(hours=INTERVIEW_DURATION_HOURS)
                conflict = any(
                    not (
                        slot_end <= datetime.fromisoformat(b["start"])
                        or slot_start >= datetime.fromisoformat(b["end"])
                    )
                    for b in busy_slots
                )
                if not conflict:
                    return slot_start
                slot_start += timedelta(hours=1)

    return None


# ---------------------------------------------------------------------------
# Tool 1: check_existing_event
# ---------------------------------------------------------------------------

def check_existing_event(company: str, role: str) -> dict:
    """
    Check whether a calendar event already exists for a given company and role
    in the 'Job Interviews' calendar, to avoid creating duplicates.

    Args:
        company: Company name (e.g. "Google").
        role:    Job title (e.g. "Software Engineer").

    Returns:
        A dict with "status", "exists" (bool), and "events" (list of matches).
    """
    try:
        service = _get_calendar_service()
        calendar_id = _get_or_create_job_calendar(service)

        results = (
            service.events()
            .list(
                calendarId=calendar_id,
                q=f"{company} {role}",
                maxResults=10,
                singleEvents=True,
            )
            .execute()
        )

        items = results.get("items", [])
        company_l = company.lower()
        role_l = role.lower()

        matching = [
            {
                "summary": e.get("summary", ""),
                "start": e.get("start", {}).get("dateTime", ""),
            }
            for e in items
            if company_l in e.get("summary", "").lower()
            or role_l in e.get("summary", "").lower()
        ]

        return {
            "status": "success",
            "exists": len(matching) > 0,
            "count": len(matching),
            "events": matching,
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}


# ---------------------------------------------------------------------------
# Tool 2: create_interview_event
# ---------------------------------------------------------------------------

def create_interview_event(
    company: str,
    role: str,
    interview_date: str,
    notes: str = "",
) -> dict:
    """
    Create a 1-hour interview event in the 'Job Interviews' calendar.

    Scheduling rules:
    - Preferred windows (IST): 11:00–14:00 and 18:00–20:00
    - Picks the earliest free slot in those windows on `interview_date`
    - If both windows are fully booked, tries the next business day (up to 7 days)

    Args:
        company:         Company name.
        role:            Job title / role.
        interview_date:  Date string from the email (RFC 2822 or ISO format).
        notes:           Optional extra context (e.g. source email subject).

    Returns:
        A dict with "status", "scheduled_time_ist", and "event_link".
    """
    try:
        service = _get_calendar_service()
        calendar_id = _get_or_create_job_calendar(service)

        target_date = _parse_email_date(interview_date)

        slot_start = _find_free_slot(service, calendar_id, target_date)
        if slot_start is None:
            return {
                "status": "error",
                "message": (
                    "No free slot found in preferred IST windows "
                    "within the next 7 business days."
                ),
            }

        slot_end = slot_start + timedelta(hours=INTERVIEW_DURATION_HOURS)

        event_body = {
            "summary": f"Interview: {role} at {company}",
            "description": (
                f"Job application interview\n\n"
                f"Role: {role}\n"
                f"Company: {company}\n\n"
                f"{notes}"
            ).strip(),
            "start": {"dateTime": slot_start.isoformat(), "timeZone": "UTC"},
            "end": {"dateTime": slot_end.isoformat(), "timeZone": "UTC"},
        }

        created = (
            service.events().insert(calendarId=calendar_id, body=event_body).execute()
        )

        # Format scheduled time in IST for the response
        slot_ist = slot_start.astimezone(IST).strftime("%Y-%m-%d %H:%M IST")

        return {
            "status": "success",
            "scheduled_time_ist": slot_ist,
            "event_link": created.get("htmlLink", ""),
            "event_id": created.get("id", ""),
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}
