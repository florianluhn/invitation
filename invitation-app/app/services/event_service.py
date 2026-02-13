from pathlib import Path
from app.config import EVENTS_DIR
from app.utils.file_lock import write_json, read_json
from app.utils.helpers import generate_id, generate_token, generate_short_token, now_iso, sanitize


def _event_path(event_id):
    return EVENTS_DIR / f"{event_id}.json"


def _normalize_invitee(inv):
    """Ensure an invitee dict has all current fields (backward compat)."""
    inv.setdefault("phone", "")
    inv.setdefault("short_token", generate_short_token())
    inv.setdefault("send_method", "email")
    inv.setdefault("sms_sent_at", None)
    # Migrate old sent_at → email_sent_at
    if "sent_at" in inv:
        inv.setdefault("email_sent_at", inv.pop("sent_at"))
    else:
        inv.setdefault("email_sent_at", None)
    return inv


def _normalize_event(event):
    """Normalize all invitees in an event for backward compat."""
    for inv in event.get("invitees", []):
        _normalize_invitee(inv)
    return event


def get_all_events():
    events = []
    for f in sorted(EVENTS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        events.append(_normalize_event(read_json(f)))
    return events


def get_event(event_id):
    path = _event_path(event_id)
    if not path.exists():
        return None
    return _normalize_event(read_json(path))


def create_event(title, host, date, time, location, message, template, photo=None, contacts=None):
    event_id = generate_id()
    invitees = []
    if contacts:
        for c in contacts:
            invitees.append({
                "contact_id": c["id"],
                "name": c["name"],
                "email": c["email"],
                "phone": c.get("phone", ""),
                "token": generate_token(),
                "short_token": generate_short_token(),
                "send_method": c.get("send_method", "email"),
                "status": "pending",
                "responded_at": None,
                "email_sent_at": None,
                "sms_sent_at": None,
            })

    event = {
        "id": event_id,
        "title": sanitize(title),
        "host": sanitize(host),
        "date": sanitize(date),
        "time": sanitize(time),
        "location": sanitize(location),
        "message": sanitize(message),
        "template": sanitize(template),
        "photo": photo,
        "created_at": now_iso(),
        "invitees": invitees,
    }
    write_json(_event_path(event_id), event)
    return event


def delete_event(event_id):
    """Delete an event by removing its JSON file."""
    path = _event_path(event_id)
    if path.exists():
        path.unlink()
        return True
    return False


def update_event(event_id, **kwargs):
    event = get_event(event_id)
    if not event:
        return None
    for key in ("title", "host", "date", "time", "location", "message", "template"):
        if key in kwargs:
            event[key] = sanitize(kwargs[key])
    if "photo" in kwargs:
        event["photo"] = kwargs["photo"]
    write_json(_event_path(event_id), event)
    return event


def add_invitees(event_id, contacts):
    event = get_event(event_id)
    if not event:
        return None
    existing_ids = {inv["contact_id"] for inv in event["invitees"]}
    for c in contacts:
        if c["id"] not in existing_ids:
            event["invitees"].append({
                "contact_id": c["id"],
                "name": c["name"],
                "email": c["email"],
                "phone": c.get("phone", ""),
                "token": generate_token(),
                "short_token": generate_short_token(),
                "send_method": c.get("send_method", "email"),
                "status": "pending",
                "responded_at": None,
                "email_sent_at": None,
                "sms_sent_at": None,
            })
    write_json(_event_path(event_id), event)
    return event


def mark_email_sent(event_id, contact_id):
    event = get_event(event_id)
    if not event:
        return
    for inv in event["invitees"]:
        if inv["contact_id"] == contact_id:
            inv["email_sent_at"] = now_iso()
            break
    write_json(_event_path(event_id), event)


def mark_sms_sent(event_id, contact_id):
    event = get_event(event_id)
    if not event:
        return
    for inv in event["invitees"]:
        if inv["contact_id"] == contact_id:
            inv["sms_sent_at"] = now_iso()
            break
    write_json(_event_path(event_id), event)


def update_rsvp(token, status):
    """Find an invitee by token across all events and update their status.
    Returns (event, invitee) or (None, None)."""
    if status not in ("accepted", "declined", "maybe"):
        return None, None

    for f in EVENTS_DIR.glob("*.json"):
        event = _normalize_event(read_json(f))
        for inv in event.get("invitees", []):
            if inv["token"] == token:
                inv["status"] = status
                inv["responded_at"] = now_iso()
                write_json(f, event)
                return event, inv
    return None, None


def get_event_by_token(token):
    """Find the event and invitee for a given RSVP token."""
    for f in EVENTS_DIR.glob("*.json"):
        event = _normalize_event(read_json(f))
        for inv in event.get("invitees", []):
            if inv["token"] == token:
                return event, inv
    return None, None


def get_event_by_short_token(short_token):
    """Find the event and invitee for a given short RSVP token (SMS links)."""
    for f in EVENTS_DIR.glob("*.json"):
        event = _normalize_event(read_json(f))
        for inv in event.get("invitees", []):
            if inv.get("short_token") == short_token:
                return event, inv
    return None, None


def update_invitee_status(event_id, contact_id, status):
    """Manually update an invitee's status (admin action)."""
    if status not in ("accepted", "declined", "maybe", "pending"):
        return False
    event = get_event(event_id)
    if not event:
        return False
    for inv in event["invitees"]:
        if inv["contact_id"] == contact_id:
            inv["status"] = status
            inv["responded_at"] = now_iso()
            write_json(_event_path(event_id), event)
            return True
    return False


def get_event_stats(event):
    """Get RSVP statistics for an event."""
    invitees = event.get("invitees", [])
    stats = {
        "total": len(invitees),
        "accepted": sum(1 for i in invitees if i["status"] == "accepted"),
        "declined": sum(1 for i in invitees if i["status"] == "declined"),
        "maybe": sum(1 for i in invitees if i["status"] == "maybe"),
        "pending": sum(1 for i in invitees if i["status"] == "pending"),
    }
    return stats
