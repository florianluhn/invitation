import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from werkzeug.utils import secure_filename

from app.config import INVITATION_TEMPLATES_DIR, UPLOADS_DIR, PUBLIC_DOMAIN
from app.services import contact_service, event_service, email_service, sms_service
from app.utils.helpers import sanitize

admin_bp = Blueprint(
    "admin", __name__,
    template_folder="templates",
    static_folder="static",
    static_url_path="/admin/static",
)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}


def _allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def _get_template_choices():
    templates = []
    for f in sorted(INVITATION_TEMPLATES_DIR.glob("*.html")):
        name = f.stem
        label = name.replace("_", " ").title()
        templates.append({"value": name, "label": label})
    return templates


# --- Dashboard ---

@admin_bp.route("/")
def dashboard():
    events = event_service.get_all_events()
    events_with_stats = []
    for ev in events:
        stats = event_service.get_event_stats(ev)
        events_with_stats.append({"event": ev, "stats": stats})
    return render_template("dashboard.html", events=events_with_stats)


# --- Event Detail ---

@admin_bp.route("/events/<event_id>")
def event_detail(event_id):
    event = event_service.get_event(event_id)
    if not event:
        flash("Event not found.", "error")
        return redirect(url_for("admin.dashboard"))
    stats = event_service.get_event_stats(event)
    return render_template("event_detail.html", event=event, stats=stats)


# --- Create Event ---

@admin_bp.route("/events/new", methods=["GET"])
def new_event():
    templates = _get_template_choices()
    contacts = contact_service.get_all_contacts()
    all_tags = contact_service.get_all_tags()
    return render_template("event_form.html", templates=templates, contacts=contacts, event=None, all_tags=all_tags)


@admin_bp.route("/events/new", methods=["POST"])
def create_event():
    title = request.form.get("title", "")
    host = request.form.get("host", "")
    date = request.form.get("date", "")
    time = request.form.get("time", "")
    location = request.form.get("location", "")
    message = request.form.get("message", "")
    template = request.form.get("template", "generic_party")
    contact_ids = request.form.getlist("contacts")

    if not title or not date:
        flash("Title and date are required.", "error")
        return redirect(url_for("admin.new_event"))

    # Handle photo upload
    photo_filename = None
    if "photo" in request.files:
        file = request.files["photo"]
        if file and file.filename and _allowed_file(file.filename):
            photo_filename = secure_filename(file.filename)
            file.save(UPLOADS_DIR / photo_filename)

    # Get selected contacts with their send method preference
    all_contacts = contact_service.get_all_contacts()
    selected = []
    for c in all_contacts:
        if c["id"] in contact_ids:
            send_method = request.form.get(f"send_method_{c['id']}", "email")
            # If no phone number, force email
            if not c.get("phone") and send_method in ("sms", "both"):
                send_method = "email"
            contact_with_method = c.copy()
            contact_with_method["send_method"] = send_method
            selected.append(contact_with_method)

    event = event_service.create_event(
        title=title, host=host, date=date, time=time,
        location=location, message=message, template=template,
        photo=photo_filename, contacts=selected,
    )

    flash(f"Event '{title}' created with {len(selected)} invitees.", "success")
    return redirect(url_for("admin.event_detail", event_id=event["id"]))


# --- Edit Event ---

@admin_bp.route("/events/<event_id>/edit", methods=["GET"])
def edit_event(event_id):
    event = event_service.get_event(event_id)
    if not event:
        flash("Event not found.", "error")
        return redirect(url_for("admin.dashboard"))
    templates = _get_template_choices()
    return render_template("event_edit.html", event=event, templates=templates)


@admin_bp.route("/events/<event_id>/edit", methods=["POST"])
def save_event(event_id):
    event = event_service.get_event(event_id)
    if not event:
        flash("Event not found.", "error")
        return redirect(url_for("admin.dashboard"))

    kwargs = {
        "title": request.form.get("title", ""),
        "host": request.form.get("host", ""),
        "date": request.form.get("date", ""),
        "time": request.form.get("time", ""),
        "location": request.form.get("location", ""),
        "message": request.form.get("message", ""),
        "template": request.form.get("template", event["template"]),
    }

    if not kwargs["title"] or not kwargs["date"]:
        flash("Title and date are required.", "error")
        return redirect(url_for("admin.edit_event", event_id=event_id))

    # Handle photo upload (keep existing if not changed)
    if "photo" in request.files:
        file = request.files["photo"]
        if file and file.filename and _allowed_file(file.filename):
            photo_filename = secure_filename(file.filename)
            file.save(UPLOADS_DIR / photo_filename)
            kwargs["photo"] = photo_filename

    event_service.update_event(event_id, **kwargs)
    flash("Event updated.", "success")
    return redirect(url_for("admin.event_detail", event_id=event_id))


# --- Add Invitees ---

@admin_bp.route("/events/<event_id>/invitees/add", methods=["GET"])
def add_invitees_form(event_id):
    event = event_service.get_event(event_id)
    if not event:
        flash("Event not found.", "error")
        return redirect(url_for("admin.dashboard"))

    # Exclude contacts already invited
    existing_ids = {inv["contact_id"] for inv in event["invitees"]}
    all_contacts = contact_service.get_all_contacts()
    available = [c for c in all_contacts if c["id"] not in existing_ids]
    all_tags = contact_service.get_all_tags()

    return render_template("event_add_invitees.html", event=event, contacts=available, all_tags=all_tags)


@admin_bp.route("/events/<event_id>/invitees/add", methods=["POST"])
def save_invitees(event_id):
    event = event_service.get_event(event_id)
    if not event:
        flash("Event not found.", "error")
        return redirect(url_for("admin.dashboard"))

    contact_ids = request.form.getlist("contacts")
    all_contacts = contact_service.get_all_contacts()
    selected = []
    for c in all_contacts:
        if c["id"] in contact_ids:
            send_method = request.form.get(f"send_method_{c['id']}", "email")
            if not c.get("phone") and send_method in ("sms", "both"):
                send_method = "email"
            contact_with_method = c.copy()
            contact_with_method["send_method"] = send_method
            selected.append(contact_with_method)

    if selected:
        event_service.add_invitees(event_id, selected)
        flash(f"Added {len(selected)} invitee(s).", "success")
    else:
        flash("No contacts selected.", "error")

    return redirect(url_for("admin.event_detail", event_id=event_id))


# --- Delete Event ---

@admin_bp.route("/events/<event_id>/delete", methods=["POST"])
def delete_event(event_id):
    event = event_service.get_event(event_id)
    if event:
        event_service.delete_event(event_id)
        flash(f"Event '{event['title']}' deleted.", "success")
    else:
        flash("Event not found.", "error")
    return redirect(url_for("admin.dashboard"))


# --- Send Invitations ---

@admin_bp.route("/events/<event_id>/send", methods=["POST"])
def send_invitations(event_id):
    event = event_service.get_event(event_id)
    if not event:
        flash("Event not found.", "error")
        return redirect(url_for("admin.dashboard"))

    # Load invitation template for email
    tmpl_path = INVITATION_TEMPLATES_DIR / f"{event['template']}.html"
    if not tmpl_path.exists():
        tmpl_path = INVITATION_TEMPLATES_DIR / "generic_party.html"
    template_html = tmpl_path.read_text()

    # Send to specific contacts or all unsent
    contact_ids = request.form.getlist("contact_ids")
    force_email = request.form.get("force_email") == "true"
    force_sms = request.form.get("force_sms") == "true"
    email_only = request.form.get("email_only") == "true"
    sms_only = request.form.get("sms_only") == "true"
    sent_count = 0
    errors = []

    for inv in event["invitees"]:
        if contact_ids and inv["contact_id"] not in contact_ids:
            continue

        send_method = inv.get("send_method", "email")

        # Determine what to send
        should_email = False
        should_sms = False

        if force_email:
            should_email = True
        elif force_sms:
            should_sms = True
        else:
            # Normal send: respect send_method, skip already-sent
            if send_method in ("email", "both") and not inv.get("email_sent_at"):
                if not sms_only:
                    should_email = True
            if send_method in ("sms", "both") and not inv.get("sms_sent_at") and inv.get("phone"):
                if not email_only:
                    should_sms = True

        # Send email
        if should_email:
            rsvp_url = f"https://{PUBLIC_DOMAIN}/rsvp/{inv['token']}"
            html = email_service.render_invitation_email(template_html, event, inv, rsvp_url)
            try:
                email_service.send_invitation(
                    to_email=inv["email"],
                    to_name=inv["name"],
                    subject=f"You're Invited: {event['title']}",
                    html_content=html,
                    photo_filename=event.get("photo"),
                )
                event_service.mark_email_sent(event_id, inv["contact_id"])
                sent_count += 1
            except Exception as e:
                errors.append(f"Email to {inv['name']}: {e}")

        # Send SMS
        if should_sms:
            short_url = f"https://{PUBLIC_DOMAIN}/r/{inv.get('short_token', '')}"
            try:
                sms_service.send_sms_invitation(
                    to_phone=inv["phone"],
                    to_name=inv["name"],
                    event=event,
                    short_rsvp_url=short_url,
                )
                event_service.mark_sms_sent(event_id, inv["contact_id"])
                sent_count += 1
            except Exception as e:
                errors.append(f"SMS to {inv['name']}: {e}")

    if sent_count:
        flash(f"Sent {sent_count} invitation(s).", "success")
    if errors:
        for err in errors:
            flash(err, "error")

    return redirect(url_for("admin.event_detail", event_id=event_id))


# --- Update Invitee Status (Admin) ---

@admin_bp.route("/events/<event_id>/status", methods=["POST"])
def update_status(event_id):
    contact_id = request.form.get("contact_id")
    status = request.form.get("status")
    if event_service.update_invitee_status(event_id, contact_id, status):
        flash("Status updated.", "success")
    else:
        flash("Failed to update status.", "error")
    return redirect(url_for("admin.event_detail", event_id=event_id))


# --- Contacts ---

@admin_bp.route("/contacts")
def contacts():
    query = request.args.get("q", "")
    if query:
        contacts_list = contact_service.search_contacts(query)
    else:
        contacts_list = contact_service.get_all_contacts()
    return render_template("contacts.html", contacts=contacts_list, query=query)


@admin_bp.route("/contacts/add", methods=["POST"])
def add_contact():
    name = request.form.get("name", "")
    email_addr = request.form.get("email", "")
    phone = request.form.get("phone", "")
    tags = request.form.get("tags", "")
    if not name or not email_addr:
        flash("Name and email are required.", "error")
    else:
        contact_service.add_contact(name, email_addr, phone, tags)
        flash(f"Contact '{name}' added.", "success")
    return redirect(url_for("admin.contacts"))


@admin_bp.route("/contacts/<contact_id>/edit", methods=["POST"])
def edit_contact(contact_id):
    name = request.form.get("name", "")
    email_addr = request.form.get("email", "")
    phone = request.form.get("phone", "")
    tags = request.form.get("tags", "")
    if contact_service.update_contact(contact_id, name, email_addr, phone, tags):
        flash("Contact updated.", "success")
    else:
        flash("Contact not found.", "error")
    return redirect(url_for("admin.contacts"))


@admin_bp.route("/contacts/<contact_id>/delete", methods=["POST"])
def delete_contact(contact_id):
    if contact_service.delete_contact(contact_id):
        flash("Contact deleted.", "success")
    else:
        flash("Contact not found.", "error")
    return redirect(url_for("admin.contacts"))


@admin_bp.route("/contacts/import", methods=["POST"])
def import_contacts():
    if "csv_file" not in request.files:
        flash("No file uploaded.", "error")
        return redirect(url_for("admin.contacts"))
    file = request.files["csv_file"]
    if not file.filename or not file.filename.endswith(".csv"):
        flash("Please upload a CSV file.", "error")
        return redirect(url_for("admin.contacts"))
    csv_content = file.read().decode("utf-8")
    added, skipped = contact_service.import_contacts_csv(csv_content)
    flash(f"Imported {added} contact(s), skipped {skipped}.", "success")
    return redirect(url_for("admin.contacts"))


# --- API: Template Preview ---

@admin_bp.route("/api/template-preview/<template_name>")
def template_preview(template_name):
    tmpl_path = INVITATION_TEMPLATES_DIR / f"{sanitize(template_name)}.html"
    if not tmpl_path.exists():
        return "Template not found", 404
    return tmpl_path.read_text()


# --- API: Contacts Search ---

@admin_bp.route("/api/contacts/search")
def search_contacts_api():
    query = request.args.get("q", "")
    results = contact_service.search_contacts(query) if query else contact_service.get_all_contacts()
    return jsonify(results)
