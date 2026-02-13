import time
from collections import defaultdict
from flask import Blueprint, render_template, request, redirect, url_for

from app.config import INVITATION_TEMPLATES_DIR
from app.services import event_service, email_service
from app.utils.helpers import format_date, format_time

public_bp = Blueprint(
    "public", __name__,
    template_folder="templates",
    static_folder="static",
    static_url_path="/static",
)

# Simple in-memory rate limiting
_rate_limit = defaultdict(list)
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_MAX = 10  # requests per window


def _check_rate_limit(ip):
    now = time.time()
    _rate_limit[ip] = [t for t in _rate_limit[ip] if now - t < RATE_LIMIT_WINDOW]
    if len(_rate_limit[ip]) >= RATE_LIMIT_MAX:
        return False
    _rate_limit[ip].append(now)
    return True


@public_bp.route("/r/<short_token>")
def rsvp_short(short_token):
    """Short RSVP URL for SMS invitations — redirects to the full RSVP page."""
    ip = request.remote_addr
    if not _check_rate_limit(ip):
        return render_template("rate_limited.html"), 429

    event, invitee = event_service.get_event_by_short_token(short_token)
    if not event or not invitee:
        return render_template("not_found.html"), 404

    return redirect(url_for("public.rsvp_page", token=invitee["token"]))


@public_bp.route("/rsvp/<token>")
def rsvp_page(token):
    ip = request.remote_addr
    if not _check_rate_limit(ip):
        return render_template("rate_limited.html"), 429

    event, invitee = event_service.get_event_by_token(token)
    if not event or not invitee:
        return render_template("not_found.html"), 404

    # Load and render the invitation template for display
    tmpl_path = INVITATION_TEMPLATES_DIR / f"{event['template']}.html"
    if not tmpl_path.exists():
        tmpl_path = INVITATION_TEMPLATES_DIR / "generic_party.html"
    template_html = tmpl_path.read_text()

    # Build photo URL for web display (instead of cid: used in emails)
    photo_url = None
    if event.get("photo"):
        photo_url = f"/uploads/{event['photo']}"

    # Render with event data (no RSVP link needed since they're already here)
    invitation_html = email_service.render_invitation_email(
        template_html, event, invitee,
        rsvp_url="#rsvp-form",
        photo_url=photo_url,
        strip_wrapper=True,
    )

    return render_template(
        "rsvp.html",
        event=event,
        invitee=invitee,
        token=token,
        invitation_html=invitation_html,
        format_date=format_date,
        format_time=format_time,
    )


@public_bp.route("/rsvp/<token>/respond", methods=["POST"])
def rsvp_respond(token):
    ip = request.remote_addr
    if not _check_rate_limit(ip):
        return render_template("rate_limited.html"), 429

    status = request.form.get("status", "")
    print(f"[RSVP] token={token[:12]}... status='{status}' form_data={dict(request.form)}")
    if status not in ("accepted", "declined", "maybe"):
        print(f"[RSVP] Invalid status, redirecting without saving")
        return redirect(url_for("public.rsvp_page", token=token))

    # Check current status before updating to avoid duplicate notifications
    event, current_invitee = event_service.get_event_by_token(token)
    if not event:
        print(f"[RSVP] Event not found for token")
        return render_template("not_found.html"), 404

    old_status = current_invitee.get("status")
    event, invitee = event_service.update_rsvp(token, status)
    if not event:
        print(f"[RSVP] update_rsvp returned None")
        return render_template("not_found.html"), 404

    print(f"[RSVP] Updated: {invitee['name']} {old_status} -> {status} (event: {event['id']})")

    # Only send admin notification if status actually changed
    if status != old_status:
        try:
            email_service.send_admin_notification(
                invitee_name=invitee["name"],
                event_title=event["title"],
                new_status=status,
                event_id=event["id"],
            )
        except Exception:
            pass

    return redirect(url_for("public.rsvp_page", token=token) + "?responded=" + status)
