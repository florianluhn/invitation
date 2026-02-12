#!/bin/bash
set -e

echo "=== Party Invitation App Setup ==="
echo ""

APP_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$APP_DIR"

# 1. Python virtual environment
echo "[1/5] Setting up Python virtual environment..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
echo "  Done."

# 2. Create data directories
echo "[2/5] Creating data directories..."
mkdir -p data/events uploads
if [ ! -f data/contacts.json ]; then
    echo "[]" > data/contacts.json
fi
if [ ! -f data/config.json ]; then
    cat > data/config.json << 'CONF'
{
  "app_name": "Party Invitations",
  "public_domain": "invites.yourdomain.com",
  "admin_port": 5001,
  "public_port": 8080
}
CONF
fi
echo "  Done."

# 3. Create .env from example if not present
echo "[3/5] Checking .env configuration..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "  Created .env from .env.example — EDIT IT with your Gmail credentials!"
else
    echo "  .env already exists."
fi

# 4. Install systemd services (optional)
echo "[4/5] Systemd service setup..."
read -p "  Install systemd services? (y/n) " INSTALL_SERVICES
if [ "$INSTALL_SERVICES" = "y" ]; then
    # Generate service files with correct paths
    cat > /tmp/invitation-admin.service << EOF
[Unit]
Description=Invitation App - Admin Server
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$APP_DIR
ExecStart=$APP_DIR/venv/bin/python $APP_DIR/admin_server.py
Restart=always
RestartSec=5
Environment=PATH=$APP_DIR/venv/bin:/usr/bin:/bin

[Install]
WantedBy=multi-user.target
EOF

    cat > /tmp/invitation-public.service << EOF
[Unit]
Description=Invitation App - Public RSVP Server
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$APP_DIR
ExecStart=$APP_DIR/venv/bin/python $APP_DIR/public_server.py
Restart=always
RestartSec=5
Environment=PATH=$APP_DIR/venv/bin:/usr/bin:/bin

[Install]
WantedBy=multi-user.target
EOF

    sudo cp /tmp/invitation-admin.service /etc/systemd/system/
    sudo cp /tmp/invitation-public.service /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable invitation-admin invitation-public
    sudo systemctl start invitation-admin invitation-public
    echo "  Services installed and started."
else
    echo "  Skipped. You can run the servers manually:"
    echo "    python admin_server.py    (default port 5001, configurable in .env)"
    echo "    python public_server.py   (port 8080)"
fi

# 5. Cloudflare Tunnel hint
echo "[5/5] Cloudflare Tunnel..."
echo "  To expose the RSVP pages publicly, set up cloudflared:"
echo "  1. Install: curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64.deb -o cloudflared.deb && sudo dpkg -i cloudflared.deb"
echo "  2. Authenticate: cloudflared tunnel login"
echo "  3. Create tunnel: cloudflared tunnel create invitations"
echo "  4. Configure: see README.md for config.yml setup"
echo "  5. Run: cloudflared tunnel run invitations"
echo ""

echo "=== Setup Complete ==="
echo ""
echo "Admin dashboard: http://localhost:5001"
echo "Public RSVP:     http://localhost:8080"
echo ""
echo "IMPORTANT: Edit .env with your Gmail credentials before sending invitations."
