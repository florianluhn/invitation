import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from pathlib import Path

from app.config import GMAIL_ADDRESS, GMAIL_APP_PASSWORD, ADMIN_EMAIL, PUBLIC_DOMAIN, UPLOADS_DIR, ADMIN_PORT


def _create_smtp():
    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
    return server


def send_invitation(to_email, to_name, subject, html_content, photo_filename=None):
    """Send an HTML invitation email."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = GMAIL_ADDRESS
    msg["To"] = to_email

    # Plain text fallback
    text_content = (
        f"You're invited! Please view this email in an HTML-capable email client "
        f"or visit your RSVP link to see the full invitation."
    )
    msg.attach(MIMEText(text_content, "plain"))
    msg.attach(MIMEText(html_content, "html"))

    # Attach photo as inline image if present
    if photo_filename:
        photo_path = UPLOADS_DIR / photo_filename
        if photo_path.exists():
            with open(photo_path, "rb") as f:
                img = MIMEImage(f.read())
                img.add_header("Content-ID", "<event_photo>")
                img.add_header("Content-Disposition", "inline", filename=photo_filename)
                msg.attach(img)

    server = _create_smtp()
    try:
        server.sendmail(GMAIL_ADDRESS, to_email, msg.as_string())
    finally:
        server.quit()


def send_admin_notification(invitee_name, event_title, new_status, event_id):
    """Send an RSVP notification to the admin."""
    subject = f"RSVP Update: {invitee_name} - {event_title}"

    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 500px; margin: 0 auto; padding: 20px;">
        <h2 style="color: #333;">RSVP Update</h2>
        <p><strong>{invitee_name}</strong> has responded to <strong>{event_title}</strong>.</p>
        <p>New status: <strong style="color: #4A90D9;">{new_status.upper()}</strong></p>
        <p style="margin-top: 20px;">
            <a href="http://localhost:{ADMIN_PORT}/events/{event_id}"
               style="background: #4A90D9; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
                View Event Dashboard
            </a>
        </p>
    </div>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = GMAIL_ADDRESS
    msg["To"] = ADMIN_EMAIL

    msg.attach(MIMEText(f"{invitee_name} responded '{new_status}' to {event_title}", "plain"))
    msg.attach(MIMEText(html, "html"))

    try:
        server = _create_smtp()
        try:
            server.sendmail(GMAIL_ADDRESS, ADMIN_EMAIL, msg.as_string())
        finally:
            server.quit()
    except Exception as e:
        print(f"Failed to send admin notification: {e}")


def render_invitation_email(template_html, event, invitee, rsvp_url, photo_url=None):
    """Render an invitation template with event data.

    Args:
        photo_url: If provided, used as the photo src (for web display).
                   If None, defaults to cid:event_photo (for inline email).
    """
    from app.utils.helpers import format_date, format_time

    replacements = {
        "{{title}}": event["title"],
        "{{host}}": event["host"],
        "{{date}}": format_date(event["date"]),
        "{{time}}": format_time(event["time"]),
        "{{location}}": event["location"],
        "{{message}}": event["message"],
        "{{guest_name}}": invitee["name"],
        "{{rsvp_url}}": rsvp_url,
    }

    html = template_html
    for placeholder, value in replacements.items():
        html = html.replace(placeholder, value or "")

    # Handle photo
    if event.get("photo"):
        src = photo_url if photo_url else "cid:event_photo"
        html = html.replace("{{photo_url}}", src)
        html = html.replace("{{photo_display}}", "block")
    else:
        html = html.replace("{{photo_display}}", "none")

    return html
