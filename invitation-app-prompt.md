# Prompt: Build a Self-Hosted Party Invitation App for Raspberry Pi

## Overview

Build a lightweight, self-hosted invitation/event management web application that runs on a Raspberry Pi. The app allows a single admin (me) to create events (e.g. birthday parties), design invitations from templates, manage contacts, send email invitations via Gmail, and track RSVPs on a dashboard. Invitees respond via a public-facing RSVP page exposed through a Cloudflare Tunnel. No database — all data is stored in JSON files.

---

## Tech Stack

- **Backend:** Python (Flask or FastAPI — pick whichever is simpler for this use case)
- **Frontend:** HTML / CSS / JavaScript (server-rendered templates are fine, no framework needed)
- **Data Storage:** JSON files (one file per data type: contacts, events, templates config, etc.)
- **Email:** Gmail SMTP (using an App Password)
- **Public Access:** Cloudflare Tunnel to expose the RSVP pages to the internet
- **Deployment:** Runs on a Raspberry Pi (ARM-compatible, minimal resource usage)

---

## Core Features & Requirements

### 1. Invitation Templates

- Provide a selection of pre-built invitation templates, at minimum:
  - **Birthday Kid** (colorful, playful design)
  - **Birthday Adult** (elegant, clean design)
  - **Generic Party** (neutral, all-purpose)
  - **Dinner Party** (sophisticated)
- Each template is an HTML/CSS email-safe design with placeholder variables.
- Templates should be stored as HTML files in a `/templates/invitations/` directory so new ones can be added easily.

### 2. Simple Design Editor

- When creating an event, the user picks a template and customizes it via a form:
  - Event title
  - Host name
  - Date & time
  - Location / address
  - Custom message / description
  - Optional: upload a photo (e.g. of the birthday person) that gets embedded in the invitation
- Show a **live preview** of the invitation as the user fills in the form.
- No drag-and-drop. Just text fields that populate into the chosen template.

### 3. Contacts Management

- A contacts section where I can:
  - **Add contacts manually** (name, email, optional phone)
  - **Upload contacts via CSV** (columns: name, email, phone)
  - **Edit and delete** existing contacts
  - **Search/filter** contacts by name or email
- Contacts are stored in a `contacts.json` file.
- Contacts are reusable across events.

### 4. Event Creation & Sending Invitations

- When creating an event:
  1. Pick a template
  2. Customize it in the editor (see above)
  3. Select recipients **from the existing contacts list** (multi-select with search/filter, checkboxes or similar)
  4. Preview the final invitation email
  5. Send
- Once sent, an **event** is created and stored in its own JSON file (e.g. `events/{event_id}.json`).
- Each invited contact gets a **unique RSVP token** (long random string, e.g. 32+ hex characters).
- The email contains:
  - The rendered HTML invitation
  - A clear RSVP button/link pointing to: `https://{YOUR_DOMAIN}/rsvp/{token}`
  - Options in the email or on the RSVP page: **Accept**, **Decline**, **Maybe**

### 5. RSVP System (Public-Facing)

- The RSVP page at `/rsvp/{token}` is publicly accessible (via Cloudflare Tunnel).
- It shows:
  - The event details (title, date, time, location, message)
  - The invitation design/template
  - The invitee's name (looked up via token)
  - RSVP buttons: **Accept**, **Decline**, **Maybe**
  - Current status if they've already responded
- Invitees can **change their RSVP status** at any time by revisiting the same link.
- No login required — the unique token serves as authentication.
- Implement **file locking** when writing RSVP updates to prevent concurrent write corruption.

### 6. Admin Dashboard

- A dashboard page showing:
  - List of all events with summary stats (total invited, accepted, declined, maybe, no response)
  - Click into an event to see:
    - Full attendee list with each person's RSVP status
    - Counts/breakdown (accepted, declined, maybe, pending)
    - Ability to **resend** the invitation to specific people
    - Ability to **manually change** someone's status
    - Event details summary
- The dashboard is only accessible locally (not exposed through the Cloudflare Tunnel — see networking section).

### 7. Email Notifications to Admin

- When an invitee RSVPs or **changes** their RSVP status, send a notification email to the admin (me) with:
  - Invitee name
  - Event name
  - New status
  - Link to the event dashboard

### 8. Gmail SMTP Configuration

- Use Gmail SMTP with an App Password.
- Store credentials in a `.env` file or `config.json` (not hardcoded):
  - `GMAIL_ADDRESS`
  - `GMAIL_APP_PASSWORD`
  - `ADMIN_EMAIL` (where to receive notifications — could be the same)
- Send HTML emails with proper MIME setup (multipart/alternative with text fallback).

---

## Data Storage (JSON Files)

All data stored in a `/data/` directory:

```
data/
├── contacts.json          # All contacts
├── config.json            # App config (email, domain, etc.)
└── events/
    ├── {event_id}.json    # One file per event
    └── ...
```

**contacts.json** structure:
```json
[
  {
    "id": "uuid",
    "name": "Jane Doe",
    "email": "jane@example.com",
    "phone": "+1234567890",
    "created_at": "ISO timestamp"
  }
]
```

**Event JSON** structure:
```json
{
  "id": "uuid",
  "title": "Emma's 7th Birthday",
  "host": "John Doe",
  "date": "2025-03-15",
  "time": "14:00",
  "location": "123 Party Lane",
  "message": "Come celebrate with us!",
  "template": "birthday_kid",
  "photo": "optional_filename.jpg",
  "created_at": "ISO timestamp",
  "invitees": [
    {
      "contact_id": "uuid",
      "name": "Jane Doe",
      "email": "jane@example.com",
      "token": "a8f3e2b1c9d4e5f6...",
      "status": "accepted",
      "responded_at": "ISO timestamp",
      "sent_at": "ISO timestamp"
    }
  ]
}
```

---

## Networking & Security

### Cloudflare Tunnel Setup

Include setup instructions for:

1. Installing `cloudflared` on the Raspberry Pi
2. Authenticating with Cloudflare
3. Creating a tunnel
4. Configuring it to route `{YOUR_DOMAIN}` to the local app
5. Running it as a systemd service

### Route Separation (Critical)

- **Public routes** (exposed via tunnel): Only `/rsvp/{token}` and any static assets needed for the RSVP page.
- **Admin routes** (local only): Dashboard, contacts management, event creation, editor, sending — all of these must **not** be accessible from the public internet.
- Implement this by either:
  - Running two separate Flask/FastAPI apps on different ports (preferred: one public on port 8080, one admin on port 5000), with the tunnel only pointing to the public one, OR
  - Using middleware that checks the request origin and blocks external access to admin routes.

### Additional Security

- RSVP tokens must be cryptographically random (use `secrets.token_hex(32)` or equivalent).
- Rate limit the RSVP endpoint to prevent abuse.
- Sanitize all user inputs.

---

## Deployment on Raspberry Pi

Include:

1. A `requirements.txt` with all Python dependencies
2. A setup script or clear instructions for:
   - Installing Python dependencies
   - Setting up the directory structure
   - Configuring the `.env` / `config.json`
   - Setting up Gmail App Password (brief instructions)
   - Installing and configuring `cloudflared`
3. A `systemd` service file to run the app on boot
4. A `systemd` service file for `cloudflared`

---

## UI/UX Guidelines

- Keep the frontend **simple and clean**. No heavy frameworks. Vanilla JS, clean CSS.
- Mobile-responsive (the RSVP page especially, since invitees will likely open it on their phone).
- The admin interface doesn't need to be fancy — functional and clear is fine.
- Use a consistent color scheme and typography.
- RSVP page should feel polished since it's what guests see.

---

## File/Directory Structure

```
invitation-app/
├── app/
│   ├── admin/                  # Admin app (local only)
│   │   ├── routes.py
│   │   ├── templates/          # Admin HTML templates (Jinja2)
│   │   └── static/             # Admin CSS/JS
│   ├── public/                 # Public app (exposed via tunnel)
│   │   ├── routes.py
│   │   ├── templates/          # RSVP page templates
│   │   └── static/             # RSVP page CSS/JS
│   ├── services/
│   │   ├── email_service.py    # Gmail SMTP logic
│   │   ├── event_service.py    # Event CRUD & RSVP logic
│   │   └── contact_service.py  # Contact CRUD logic
│   ├── utils/
│   │   ├── file_lock.py        # JSON file locking utility
│   │   └── helpers.py
│   └── config.py               # App configuration
├── data/                       # JSON data files
│   ├── contacts.json
│   ├── config.json
│   └── events/
├── templates/
│   └── invitations/            # HTML invitation templates
│       ├── birthday_kid.html
│       ├── birthday_adult.html
│       ├── generic_party.html
│       └── dinner_party.html
├── uploads/                    # Uploaded photos
├── .env                        # Gmail credentials
├── requirements.txt
├── setup.sh                    # Setup script
├── admin_server.py             # Entry point for admin app
├── public_server.py            # Entry point for public RSVP app
└── README.md                   # Full documentation
```

---

## Summary of User Flows

### Admin: Create & Send Invitations
1. Open admin dashboard (local network)
2. Go to "New Event"
3. Pick a template → preview loads
4. Fill in event details → preview updates live
5. Select contacts from contact list
6. Preview final email
7. Hit Send → emails go out, event is created

### Invitee: RSVP
1. Receive email with beautiful HTML invitation
2. Click RSVP link → opens `https://invites.domain.com/rsvp/{token}`
3. See event details and RSVP buttons
4. Click Accept / Decline / Maybe
5. See confirmation
6. Can revisit the link later to change their response

### Admin: Track RSVPs
1. Open dashboard
2. See all events with response stats
3. Click into event for detailed attendee breakdown
4. Receive email notification whenever someone RSVPs or changes status

---

Please build this application complete and ready to deploy. Include all files, all templates, all configuration, setup instructions, and a comprehensive README.
