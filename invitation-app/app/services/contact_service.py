import csv
import io
from app.config import CONTACTS_FILE
from app.utils.file_lock import locked_json_write, read_json
from app.utils.helpers import generate_id, now_iso, sanitize


def get_all_contacts():
    return read_json(CONTACTS_FILE)


def get_contact(contact_id):
    contacts = get_all_contacts()
    for c in contacts:
        if c["id"] == contact_id:
            return c
    return None


def add_contact(name, email, phone=""):
    contact = {
        "id": generate_id(),
        "name": sanitize(name),
        "email": sanitize(email).lower(),
        "phone": sanitize(phone),
        "created_at": now_iso(),
    }
    with locked_json_write(CONTACTS_FILE) as contacts:
        contacts.append(contact)
    return contact


def update_contact(contact_id, name, email, phone=""):
    with locked_json_write(CONTACTS_FILE) as contacts:
        for c in contacts:
            if c["id"] == contact_id:
                c["name"] = sanitize(name)
                c["email"] = sanitize(email).lower()
                c["phone"] = sanitize(phone)
                return c
    return None


def delete_contact(contact_id):
    with locked_json_write(CONTACTS_FILE) as contacts:
        original_len = len(contacts)
        contacts[:] = [c for c in contacts if c["id"] != contact_id]
        return len(contacts) < original_len


def import_contacts_csv(csv_content):
    """Import contacts from CSV content. Returns (added_count, skipped_count)."""
    reader = csv.DictReader(io.StringIO(csv_content))
    added = 0
    skipped = 0

    with locked_json_write(CONTACTS_FILE) as contacts:
        existing_emails = {c["email"].lower() for c in contacts}
        for row in reader:
            name = row.get("name", "").strip()
            email = row.get("email", "").strip().lower()
            phone = row.get("phone", "").strip()
            if not name or not email:
                skipped += 1
                continue
            if email in existing_emails:
                skipped += 1
                continue
            contacts.append({
                "id": generate_id(),
                "name": sanitize(name),
                "email": sanitize(email),
                "phone": sanitize(phone),
                "created_at": now_iso(),
            })
            existing_emails.add(email)
            added += 1

    return added, skipped


def search_contacts(query):
    query = query.lower()
    contacts = get_all_contacts()
    return [c for c in contacts if query in c["name"].lower() or query in c["email"].lower()]
