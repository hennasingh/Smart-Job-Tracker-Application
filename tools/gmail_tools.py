# tools/gmail_tools.py
#
# Three ADK-compatible tools for the gmail_agent:
#   1. scan_recruiter_emails  — search inbox for job/recruiter emails
#   2. get_email_details      — fetch full email body by message ID
#   3. extract_job_details    — parse company, role, and status from email content

import re
import base64

from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

TOKEN_PATH = "token.json"

# Scopes tell Google what permissions we need
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/calendar",
]


def _get_gmail_service():
    """
    Load saved OAuth2 credentials from token.json and return an
    authenticated Gmail API service client.

    Raises FileNotFoundError if token.json has not been created yet
    (run authenticate.py first).
    """
    creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    return build("gmail", "v1", credentials=creds)


def _decode_body(payload: dict) -> str:
    """
    Recursively walk a Gmail message payload and extract the first
    plain-text body part.  Falls back to an empty string if none found.
    """
    mime_type = payload.get("mimeType", "")

    # Leaf node with a plain-text body
    if mime_type == "text/plain":
        data = payload.get("body", {}).get("data", "")
        if data:
            return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")

    # Multipart: recurse into each part
    for part in payload.get("parts", []):
        result = _decode_body(part)
        if result:
            return result

    return ""


# ---------------------------------------------------------------------------
# Tool 1: scan_recruiter_emails
# ---------------------------------------------------------------------------

def scan_recruiter_emails(days: int = 30, max_results: int = 50) -> dict:
    """
    Search Gmail for recruiter and job-application emails received within
    the last `days` days (default 30).

    Returns a list of emails, each containing:
      - message_id : used to fetch full details with get_email_details()
      - subject
      - sender
      - date
      - snippet  : short 200-character preview of the email body

    Args:
        days:        How many days back to search (default 30).
        max_results: Maximum number of emails to return (default 50).

    Returns:
        A dict with keys "status", "count", and "emails".
    """
    try:
        service = _get_gmail_service()

        query = (
            "("
            "subject:(application OR interview OR opportunity OR "
            "position OR role OR hiring OR offer OR rejection OR recruiter) "
            "OR from:(recruiter OR talent OR careers OR hiring)"
            ") "
            f"newer_than:{days}d"
        )

        results = service.users().messages().list(
            userId="me",
            q=query,
            maxResults=max_results,
        ).execute()

        messages = results.get("messages", [])

        if not messages:
            return {"status": "success", "count": 0, "emails": []}

        emails = []
        for msg in messages:
            # get the full email details
            email_data = service.users().messages().get(
                userId="me",
                id=msg["id"],
                format="metadata", # metadata only — faster, no need for full body
                metadataHeaders=["Subject", "From", "Date"],
            ).execute()

            headers = {
                h["name"]: h["value"]
                for h in email_data.get("payload", {}).get("headers", [])
            }

            emails.append({
                "message_id": msg["id"],
                "subject":    headers.get("Subject", "(no subject)"),
                "sender":     headers.get("From", ""),
                "date":       headers.get("Date", ""),
                "snippet":    email_data.get("snippet", ""),
            })

        return {"status": "success", "count": len(emails), "emails": emails}

    except Exception as e:
        return {"status": "error", "message": str(e)}


# ---------------------------------------------------------------------------
# Tool 2: get_email_details
# ---------------------------------------------------------------------------

def get_email_details(message_id: str) -> dict:
    """
    Fetch the full details of a single email by its message ID.

    Use this after scan_recruiter_emails() to get the complete body of
    an email so you can properly classify it.

    Args:
        message_id: The Gmail message ID returned by scan_recruiter_emails().

    Returns:
        A dict with keys "status", "message_id", "subject", "sender",
        "date", "snippet", and "body" (full plain-text body).
    """
    try:
        service = _get_gmail_service()

        email_data = service.users().messages().get(
            userId="me",
            id=message_id,
            format="full",
        ).execute()

        headers = {
            h["name"]: h["value"]
            for h in email_data.get("payload", {}).get("headers", [])
        }

        body = _decode_body(email_data.get("payload", {}))

        return {
            "status":     "success",
            "message_id": message_id,
            "subject":    headers.get("Subject", "(no subject)"),
            "sender":     headers.get("From", ""),
            "date":       headers.get("Date", ""),
            "snippet":    email_data.get("snippet", ""),
            "body":       body or "(body not available)",
        }

    except Exception as e:
        return {"status": "error", "message_id": message_id, "message": str(e)}


# ---------------------------------------------------------------------------
# Tool 3: extract_job_details
# ---------------------------------------------------------------------------

def extract_job_details(subject: str, sender: str, body: str) -> dict:
    """
    Parse a job-related email and extract structured information.

    Analyses the subject line, sender, and body to determine:
      - company  : organisation that sent the email
      - role     : job title or position mentioned
      - status   : one of "applied" | "interview_scheduled" | "offer" |
                   "rejected" | "unknown"

    This tool uses keyword heuristics. The agent should use its own
    judgement to refine or override these results when the context is clear.

    Args:
        subject: Email subject line.
        sender:  Full "From" header (e.g. "Alice <alice@company.com>").
        body:    Plain-text email body (from get_email_details).

    Returns:
        A dict with keys "company", "role", "status", "confidence",
        and "raw_subject".
    """
    combined = f"{subject} {body}".lower()

    # ------------------------------------------------------------------ status
    status = "unknown"
    confidence = "low"

    REJECTED_SIGNALS = [
        "not moving forward", "other candidates", "not selected",
        "decided not to", "unfortunately", "will not be", "not a match",
        "not be moving", "rejected", "unsuccessful",
    ]
    OFFER_SIGNALS = [
        "pleased to offer", "job offer", "offer letter", "we'd like to offer",
        "we would like to offer", "formal offer", "offer of employment",
    ]
    INTERVIEW_SIGNALS = [
        "interview", "schedule a call", "schedule time", "speak with you",
        "chat with you", "meet with you", "next steps", "technical screen",
        "phone screen", "video call", "zoom", "google meet", "teams call",
    ]
    APPLIED_SIGNALS = [
        "application received", "thank you for applying",
        "we received your application", "application submitted",
        "we've got your application", "application confirmation",
    ]

    if any(sig in combined for sig in REJECTED_SIGNALS):
        status, confidence = "rejected", "high"
    elif any(sig in combined for sig in OFFER_SIGNALS):
        status, confidence = "offer", "high"
    elif any(sig in combined for sig in INTERVIEW_SIGNALS):
        status, confidence = "interview_scheduled", "medium"
    elif any(sig in combined for sig in APPLIED_SIGNALS):
        status, confidence = "applied", "high"

    # ----------------------------------------------------------------- company
    company = ""

    # Try to extract from the email address domain
    email_match = re.search(r"[\w.+-]+@([\w-]+)\.(com|io|co|org|net|ai|dev|tech)", sender)
    if email_match:
        raw_domain = email_match.group(1)
        # Strip common mail-service subdomains (mail, jobs, careers, …)
        raw_domain = re.sub(r"^(mail|jobs|careers|talent|recruiting|hr)\.", "", raw_domain)
        company = raw_domain.replace("-", " ").title()

    # Fallback: look for "at <Company>" in the subject
    if not company:
        at_match = re.search(r"\bat\s+([A-Z][A-Za-z0-9& ]+)", subject)
        if at_match:
            company = at_match.group(1).strip()

    # -------------------------------------------------------------------- role
    role = ""

    ROLE_PATTERNS = [
        # "Software Engineer at Google"
        r"([A-Z][A-Za-z /&-]+(?:Engineer|Developer|Manager|Analyst|Designer|"
        r"Scientist|Architect|Lead|Director|Intern|Associate|Specialist|"
        r"Consultant|Recruiter|Head|VP|Officer))\b",
        # "for the Senior Backend Developer role/position"
        r"(?:for\s+(?:the\s+)?)([\w ]+?)\s+(?:role|position|opportunity)\b",
    ]
    for pattern in ROLE_PATTERNS:
        m = re.search(pattern, subject, re.IGNORECASE)
        if m:
            role = m.group(1).strip()
            break

    return {
        "company":     company,
        "role":        role,
        "status":      status,
        "confidence":  confidence,
        "raw_subject": subject,
    }


# ---------------------------------------------------------------------------
# Tool 4: fetch_and_classify_email  (combined — saves one LLM turn per email)
# ---------------------------------------------------------------------------

def fetch_and_classify_email(message_id: str) -> dict:
    """
    Fetch the full body of an email AND run heuristic classification in a
    single call.  Use this instead of calling get_email_details() and
    extract_job_details() separately — it halves the number of tool calls
    needed per email.

    Args:
        message_id: The Gmail message ID from scan_recruiter_emails().

    Returns:
        A merged dict with all fields from get_email_details() plus the
        classification fields: company, role, job_status, confidence.
    """
    details = get_email_details(message_id)
    if details.get("status") == "error":
        return details

    classification = extract_job_details(
        subject=details.get("subject", ""),
        sender=details.get("sender", ""),
        body=details.get("body", ""),
    )

    return {
        **details,
        "company":    classification["company"],
        "role":       classification["role"],
        "job_status": classification["status"],   # renamed to avoid clash with http status
        "confidence": classification["confidence"],
    }
