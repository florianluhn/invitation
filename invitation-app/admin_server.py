#!/usr/bin/env python3
"""Admin server - accessible only from local network. Port configurable via ADMIN_PORT in .env."""

from flask import Flask
from app.config import SECRET_KEY, UPLOADS_DIR, ADMIN_PORT
from app.admin.routes import admin_bp

app = Flask(__name__)
app.secret_key = SECRET_KEY

# Serve uploaded images
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    from flask import send_from_directory
    return send_from_directory(UPLOADS_DIR, filename)

app.register_blueprint(admin_bp)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=ADMIN_PORT, debug=False)
