#!/usr/bin/env python3
"""Public RSVP server - exposed via Cloudflare Tunnel. Port configurable via PUBLIC_PORT in .env."""

from flask import Flask, send_from_directory
from app.config import SECRET_KEY, UPLOADS_DIR, PUBLIC_PORT
from app.public.routes import public_bp

app = Flask(__name__)
app.secret_key = SECRET_KEY

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOADS_DIR, filename)

app.register_blueprint(public_bp)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PUBLIC_PORT, debug=False)
