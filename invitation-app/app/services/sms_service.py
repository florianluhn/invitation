import re
from android_sms_gateway import client, domain
from app.config import SMS_GATEWAY_URL, SMS_GATEWAY_LOGIN, SMS_GATEWAY_PASSWORD
from app.utils.helpers import format_date, format_time


def _get_sms_credentials(sender_profile=None):
    """Get SMS gateway credentials from sender profile or defaults."""
    if sender_profile and sender_profile.get("sms_url"):
        return sender_profile["sms_url"], sender_profile["sms_login"], sender_profile["sms_password"]
    return SMS_GATEWAY_URL, SMS_GATEWAY_LOGIN, SMS_GATEWAY_PASSWORD


def _ensure_configured(sms_url=None, sms_login=None, sms_password=None):
    url = sms_url or SMS_GATEWAY_URL
    login = sms_login or SMS_GATEWAY_LOGIN
    password = sms_password or SMS_GATEWAY_PASSWORD
    if not url or not login or not password:
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


def format_reminder_sms(event, days_remaining, short_rsvp_url):
    """Format an SMS reminder message, targeting under 160 characters."""
    title = event["title"]
    date = format_date(event["date"])
    time_str = format_time(event["time"])

    if len(title) > 35:
        title = title[:32] + "..."

    if days_remaining == 0:
        days_text = "today"
    elif days_remaining == 1:
        days_text = "tomorrow"
    else:
        days_text = f"in {days_remaining} days"

    lines = [
        f"Reminder: {title} is {days_text}!",
        f"{date} @ {time_str}",
        f"RSVP: {short_rsvp_url}",
    ]

    return "\n".join(lines)


def send_reminder_sms(to_phone, to_name, event, days_remaining, short_rsvp_url, sender_profile=None):
    """Send an SMS reminder via the Android SMS Gateway app."""
    sms_url, sms_login, sms_password = _get_sms_credentials(sender_profile)
    _ensure_configured(sms_url, sms_login, sms_password)

    normalized = normalize_phone_number(to_phone)
    if not normalized:
        raise ValueError(f"Invalid phone number for {to_name}: {to_phone}")

    message_text = format_reminder_sms(event, days_remaining, short_rsvp_url)

    message = domain.Message(
        phone_numbers=[normalized],
        text_message=domain.TextMessage(text=message_text),
    )

    with client.APIClient(sms_login, sms_password, base_url=sms_url) as c:
        c.send(message)


def send_sms_invitation(to_phone, to_name, event, short_rsvp_url, sender_profile=None):
    """Send an SMS invitation via the Android SMS Gateway app."""
    sms_url, sms_login, sms_password = _get_sms_credentials(sender_profile)
    _ensure_configured(sms_url, sms_login, sms_password)

    normalized = normalize_phone_number(to_phone)
    if not normalized:
        raise ValueError(f"Invalid phone number for {to_name}: {to_phone}")

    message_text = format_sms_message(event, short_rsvp_url)

    message = domain.Message(
        phone_numbers=[normalized],
        text_message=domain.TextMessage(text=message_text),
    )

    with client.APIClient(sms_login, sms_password, base_url=sms_url) as c:
        c.send(message)
