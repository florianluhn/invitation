# Party Invitation App

A self-hosted invitation and RSVP management app designed to run on a Raspberry Pi. Create events, design invitations from templates, manage contacts, send invitations via Gmail email or SMS (using an Android phone as a gateway), and track RSVPs through a public-facing page exposed via Cloudflare Tunnel.

## Architecture

The app runs as **two separate Flask servers** for security:

| Server | Port | Access | Purpose |
|--------|------|--------|---------|
| Admin | 5000 | Local network only | Dashboard, event creation, contacts |
| Public | 8080 | Internet (via Cloudflare Tunnel) | RSVP pages only |

All data is stored in JSON files (no database required).

## Quick Start

### 1. Clone & Setup

```bash
cd /home/pi
git clone <repo-url> invitation-app
cd invitation-app
chmod +x setup.sh
./setup.sh
```

### 2. Configure Gmail

Edit `.env` with your credentials:

```
GMAIL_ADDRESS=your.email@gmail.com
GMAIL_APP_PASSWORD=xxxx-xxxx-xxxx-xxxx
ADMIN_EMAIL=your.email@gmail.com
PUBLIC_DOMAIN=invites.yourdomain.com
SECRET_KEY=some-random-string-here
```

**Getting a Gmail App Password:**
1. Go to [Google Account Security](https://myaccount.google.com/security)
2. Enable 2-Step Verification if not already on
3. Go to [App Passwords](https://myaccount.google.com/apppasswords)
4. Create a new app password for "Mail"
5. Copy the 16-character password into `.env`

### 3. Run

```bash
# Activate virtual environment
source venv/bin/activate

# Start both servers (or use systemd - see below)
python admin_server.py &
python public_server.py &
```

- Admin dashboard: `http://<pi-ip>:5000`
- Public RSVP: `http://<pi-ip>:8080`

## Systemd Services (Auto-Start on Boot)

```bash
# Copy service files
sudo cp invitation-admin.service /etc/systemd/system/
sudo cp invitation-public.service /etc/systemd/system/

# Edit the paths in the service files if your app isn't at /home/pi/invitation-app
sudo nano /etc/systemd/system/invitation-admin.service

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable invitation-admin invitation-public
sudo systemctl start invitation-admin invitation-public

# Check status
sudo systemctl status invitation-admin
sudo systemctl status invitation-public

# View logs
journalctl -u invitation-admin -f
journalctl -u invitation-public -f
```

## Cloudflare Tunnel Setup

This exposes **only** the public RSVP server (port 8080) to the internet.

### Install cloudflared

```bash
# For Raspberry Pi (ARM64)
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64.deb -o cloudflared.deb
sudo dpkg -i cloudflared.deb

# For ARM 32-bit
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm.deb -o cloudflared.deb
sudo dpkg -i cloudflared.deb
```

### Configure the Tunnel

```bash
# 1. Authenticate with Cloudflare
cloudflared tunnel login

# 2. Create a tunnel
cloudflared tunnel create invitations

# 3. Create config file
mkdir -p ~/.cloudflared
cat > ~/.cloudflared/config.yml << EOF
tunnel: invitations
credentials-file: /home/pi/.cloudflared/<TUNNEL-ID>.json

ingress:
  - hostname: invites.yourdomain.com
    service: http://localhost:8080
  - service: http_status:404
EOF

# 4. Add DNS record
cloudflared tunnel route dns invitations invites.yourdomain.com

# 5. Test it
cloudflared tunnel run invitations
```

### Run as a Service

```bash
sudo cp cloudflared.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable cloudflared
sudo systemctl start cloudflared
```

## SMS Invitations (Android SMS Gateway)

The app can send text message invitations using a spare Android phone as an SMS gateway. This is completely free — it sends SMS through your phone's carrier plan.

### Setup

1. **Install the app** on a spare Android phone:
   - Download "SMS Gateway for Android" from the Play Store or from [sms-gate.app](https://sms-gate.app/)
   - Open the app and note the **login**, **password**, and **local URL** it shows

2. **Keep the phone running:**
   - Connect it to power and Wi-Fi on the same network as your Pi
   - Keep the app open (disable battery optimization for it)

3. **Configure `.env`** on the Pi:
   ```
   SMS_GATEWAY_URL=http://192.168.1.100:8080
   SMS_GATEWAY_LOGIN=admin
   SMS_GATEWAY_PASSWORD=your-gateway-password
   ```
   Replace the IP with your Android phone's local IP address.

4. **Add phone numbers** to your contacts in the admin dashboard.

5. **Choose send method** when creating an event:
   - **Email** — HTML invitation via Gmail (default)
   - **SMS** — short text message with RSVP link via the Android phone
   - **Both** — sends both

### How SMS Invitations Work

- SMS messages are kept under 160 characters to fit in one segment
- A short RSVP URL (`/r/abc12345`) is used instead of the full token URL
- The short link redirects to the same full RSVP page guests would see from email
- You can resend email and SMS independently from the event detail page

### Example SMS

```
You're invited to Emma's 7th Birthday!
March 15, 2025 @ 2:00 PM
123 Party Lane
RSVP: https://invites.domain.com/r/xK9m2pLq
```

## Invitation Templates

Five built-in templates in `templates/invitations/`:

| Template | File | Style |
|----------|------|-------|
| Birthday Kid | `birthday_kid.html` | Colorful, playful with emojis |
| Birthday Girl Gabby | `birthday_girl_gabby.html` | Pink/purple Gabby's Dollhouse style |
| Birthday Adult | `birthday_adult.html` | Elegant, dark with gold accents |
| Generic Party | `generic_party.html` | Modern, clean purple gradient |
| Dinner Party | `dinner_party.html` | Sophisticated dark theme |

### Adding Custom Templates

Create a new `.html` file in `templates/invitations/`. Use these placeholders:

- `{{title}}` - Event title
- `{{host}}` - Host name
- `{{date}}` - Formatted date
- `{{time}}` - Formatted time
- `{{location}}` - Event location
- `{{message}}` - Custom message
- `{{guest_name}}` - Invitee's name
- `{{rsvp_url}}` - RSVP link
- `{{photo_url}}` - Embedded photo (use with `cid:event_photo`)
- `{{photo_display}}` - Set to `block` or `none` based on photo presence

## Directory Structure

```
invitation-app/
├── app/
│   ├── admin/                  # Admin app (local only)
│   │   ├── routes.py           # Admin routes
│   │   ├── templates/          # Admin HTML (Jinja2)
│   │   └── static/             # Admin CSS/JS
│   ├── public/                 # Public RSVP app
│   │   ├── routes.py           # RSVP routes
│   │   ├── templates/          # RSVP page templates
│   │   └── static/             # RSVP CSS
│   ├── services/
│   │   ├── email_service.py    # Gmail SMTP
│   │   ├── sms_service.py      # Android SMS Gateway
│   │   ├── event_service.py    # Event CRUD & RSVP
│   │   └── contact_service.py  # Contact CRUD
│   ├── utils/
│   │   ├── file_lock.py        # JSON file locking
│   │   └── helpers.py          # Utilities
│   └── config.py               # Configuration
├── data/                       # JSON data (auto-created)
│   ├── contacts.json
│   ├── config.json
│   └── events/
├── templates/invitations/      # Email templates
├── uploads/                    # Uploaded photos
├── admin_server.py             # Admin entry point (port 5000)
├── public_server.py            # Public entry point (port 8080)
├── setup.sh                    # Setup script
└── .env                        # Gmail & SMS credentials
```

## Security Notes

- RSVP tokens are 64-character cryptographically random hex strings
- The admin server should **never** be exposed to the internet
- Rate limiting on RSVP endpoints (10 requests/minute per IP)
- All user inputs are sanitized with bleach
- The Cloudflare Tunnel only routes to port 8080 (public RSVP server)
