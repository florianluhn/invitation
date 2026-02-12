#!/usr/bin/env python3
"""Public RSVP server - runs on port 8080, exposed via Cloudflare Tunnel."""

from flask import Flask, send_from_directory
from app.config import SECRET_KEY, UPLOADS_DIR
from app.public.routes import public_bp

app = Flask(__name__)
app.secret_key = SECRET_KEY

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOADS_DIR, filename)

app.register_blueprint(public_bp)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)
