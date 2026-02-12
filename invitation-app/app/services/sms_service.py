import re
from android_sms_gateway import client, domain
from app.config import SMS_GATEWAY_URL, SMS_GATEWAY_LOGIN, SMS_GATEWAY_PASSWORD
from app.utils.helpers import format_date, format_time


def _ensure_configured():
    if not SMS_GATEWAY_URL or not SMS_GATEWAY_LOGIN or not SMS_GATEWAY_PASSWORD:
        raise RuntimeError(
            "Android SMS Gateway is not configured. "
            "Set SMS_GATEWAY_URL, SMS_GATEWAY_LOGIN, and SMS_GATEWAY_PASSWORD in .env"
        )


def normalize_phone_number(phone):
    """Convert phone number to E.164 format (+1XXXXXXXXXX).

    Handles formats like (555) 123-4567, 555-123-4567, 5551234567, +15551234567.
    Returns None if invalid.
    """
    if not phone:
        return None

    phone = phone.strip()

    # If already E.164 with +, validate digits
    if phone.startswith("+"):
        digits = re.sub(r"\D", "", phone[1:])
        if len(digits) >= 10:
            return f"+{digits}"
        return None

    # Remove all non-digit characters
    digits = re.sub(r"\D", "", phone)

    # 10 digits -> assume US/Canada, prepend +1
    if len(digits) == 10:
        return f"+1{digits}"

    # 11 digits starting with 1 -> US/Canada
    if len(digits) == 11 and digits[0] == "1":
        return f"+{digits}"

    return None


def validate_phone_number(phone):
    """Check if a phone number can be normalized to E.164."""
    return normalize_phone_number(phone) is not None


def format_sms_message(event, short_rsvp_url):
    """Format an SMS invitation message, targeting under 160 characters."""
    title = event["title"]
    date = format_date(event["date"])
    time_str = format_time(event["time"])
    location = event.get("location", "")

    # Truncate long titles
    if len(title) > 40:
        title = title[:37] + "..."

    lines = [
        f"You're invited to {title}!",
        f"{date} @ {time_str}",
    ]

    if location:
        if len(location) > 40:
            location = location[:37] + "..."
        lines.append(location)

    lines.append(f"RSVP: {short_rsvp_url}")

    message = "\n".join(lines)

    # If over 160, drop location to fit in one SMS segment
    if len(message) > 160:
        message = "\n".join([lines[0], lines[1], lines[-1]])

    return message


def send_sms_invitation(to_phone, to_name, event, short_rsvp_url):
    """Send an SMS invitation via the Android SMS Gateway app.

    Args:
        to_phone: Recipient phone number (any common format).
        to_name: Recipient name (for logging).
        event: Event dict.
        short_rsvp_url: Short RSVP URL for SMS.

    Raises:
        ValueError: If the phone number is invalid.
        RuntimeError: If the gateway is not configured.
    """
    _ensure_configured()

    normalized = normalize_phone_number(to_phone)
    if not normalized:
        raise ValueError(f"Invalid phone number for {to_name}: {to_phone}")

    message_text = format_sms_message(event, short_rsvp_url)

    message = domain.Message(
        phone_numbers=[normalized],
        text_message=domain.TextMessage(text=message_text),
    )

    with client.APIClient(
        SMS_GATEWAY_LOGIN,
        SMS_GATEWAY_PASSWORD,
        base_url=SMS_GATEWAY_URL,
    ) as c:
        c.send(message)
