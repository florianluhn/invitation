import os
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
EVENTS_DIR = DATA_DIR / "events"
CONTACTS_FILE = DATA_DIR / "contacts.json"
CONFIG_FILE = DATA_DIR / "config.json"
UPLOADS_DIR = BASE_DIR / "uploads"
INVITATION_TEMPLATES_DIR = BASE_DIR / "templates" / "invitations"
TEMPLATE_IMAGES_DIR = BASE_DIR / "templates" / "images"

# Ensure directories exist
EVENTS_DIR.mkdir(parents=True, exist_ok=True)
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

# Email config
GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS", "")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", GMAIL_ADDRESS)
PUBLIC_DOMAIN = os.getenv("PUBLIC_DOMAIN", "invites.yourdomain.com")
SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")

# Server ports and admin host
ADMIN_PORT = int(os.getenv("ADMIN_PORT", "5001"))
PUBLIC_PORT = int(os.getenv("PUBLIC_PORT", "8080"))
ADMIN_HOST = os.getenv("ADMIN_HOST", "localhost")

# SMS config (Android SMS Gateway)
SMS_GATEWAY_URL = os.getenv("SMS_GATEWAY_URL", "")
SMS_GATEWAY_LOGIN = os.getenv("SMS_GATEWAY_LOGIN", "")
SMS_GATEWAY_PASSWORD = os.getenv("SMS_GATEWAY_PASSWORD", "")

# Secondary sender credentials
GMAIL_ADDRESS_2 = os.getenv("GMAIL_ADDRESS_2", "")
GMAIL_APP_PASSWORD_2 = os.getenv("GMAIL_APP_PASSWORD_2", "")
SMS_GATEWAY_URL_2 = os.getenv("SMS_GATEWAY_URL_2", "")
SMS_GATEWAY_LOGIN_2 = os.getenv("SMS_GATEWAY_LOGIN_2", "")
SMS_GATEWAY_PASSWORD_2 = os.getenv("SMS_GATEWAY_PASSWORD_2", "")

# Sender profiles
SENDER_PROFILES = {
    "primary": {
        "gmail_address": GMAIL_ADDRESS,
        "gmail_password": GMAIL_APP_PASSWORD,
        "sms_url": SMS_GATEWAY_URL,
        "sms_login": SMS_GATEWAY_LOGIN,
        "sms_password": SMS_GATEWAY_PASSWORD,
    },
}

if GMAIL_ADDRESS_2 or SMS_GATEWAY_URL_2:
    SENDER_PROFILES["secondary"] = {
        "gmail_address": GMAIL_ADDRESS_2,
        "gmail_password": GMAIL_APP_PASSWORD_2,
        "sms_url": SMS_GATEWAY_URL_2,
        "sms_login": SMS_GATEWAY_LOGIN_2,
        "sms_password": SMS_GATEWAY_PASSWORD_2,
    }


def get_sender_profile(name="primary"):
    """Get a sender profile by name, falling back to primary."""
    return SENDER_PROFILES.get(name, SENDER_PROFILES["primary"])


# Load app config from JSON
def load_app_config():
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {}

APP_CONFIG = load_app_config()
