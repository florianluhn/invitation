import secrets
import uuid
import bleach
from datetime import datetime


def generate_id():
    return str(uuid.uuid4())


def generate_token():
    return secrets.token_hex(32)


def generate_short_token():
    """Generate an 8-character URL-safe short token for SMS RSVP links."""
    return secrets.token_urlsafe(6)[:8]


def now_iso():
    return datetime.utcnow().isoformat() + "Z"


def sanitize(text):
    """Sanitize user input to prevent XSS."""
    if text is None:
        return ""
    return bleach.clean(str(text).strip())


def format_date(date_str):
    """Format a date string for display."""
    try:
        dt = datetime.fromisoformat(date_str)
        return dt.strftime("%B %d, %Y")
    except (ValueError, TypeError):
        return date_str


def format_time(time_str):
    """Format a time string for display."""
    try:
        dt = datetime.strptime(time_str, "%H:%M")
        return dt.strftime("%I:%M %p")
    except (ValueError, TypeError):
        return time_str
