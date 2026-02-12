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

# Ensure directories exist
EVENTS_DIR.mkdir(parents=True, exist_ok=True)
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

# Email config
GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS", "")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", GMAIL_ADDRESS)
PUBLIC_DOMAIN = os.getenv("PUBLIC_DOMAIN", "invites.yourdomain.com")
SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")

# SMS config (Android SMS Gateway)
SMS_GATEWAY_URL = os.getenv("SMS_GATEWAY_URL", "")
SMS_GATEWAY_LOGIN = os.getenv("SMS_GATEWAY_LOGIN", "")
SMS_GATEWAY_PASSWORD = os.getenv("SMS_GATEWAY_PASSWORD", "")

# Load app config from JSON
def load_app_config():
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {}

APP_CONFIG = load_app_config()
