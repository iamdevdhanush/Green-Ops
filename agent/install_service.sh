#!/bin/bash
# GreenOps Agent Service Installer for Linux

set -e

echo "╔═══════════════════════════════════════╗"
echo "║  GreenOps Agent Service Installer     ║"
echo "╚═══════════════════════════════════════╝"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root (sudo)"
    exit 1
fi

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
INSTALL_DIR="/opt/greenops-agent"
SERVICE_USER="greenops"

echo "[1/6] Creating installation directory..."
mkdir -p "$INSTALL_DIR"
cp -r "$SCRIPT_DIR"/* "$INSTALL_DIR/"

echo "[2/6] Installing Python dependencies..."
cd "$INSTALL_DIR"
pip3 install -r requirements.txt

# Install xprintidle if not present
if ! command -v xprintidle &> /dev/null; then
    echo "Installing xprintidle..."
    apt-get update && apt-get install -y xprintidle
fi

echo "[3/6] Creating service user..."
if ! id "$SERVICE_USER" &>/dev/null; then
    useradd -r -s /bin/false "$SERVICE_USER"
fi

echo "[4/6] Setting permissions..."
chown -R "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR"

echo "[5/6] Creating systemd service..."
cat > /etc/systemd/system/greenops-agent.service << EOF
[Unit]
Description=GreenOps Carbon Governance Agent
After=network.target

[Service]
Type=simple
User=$SERVICE_USER
WorkingDirectory=$INSTALL_DIR
ExecStart=/usr/bin/python3 $INSTALL_DIR/agent.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Security settings
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

echo "[6/6] Enabling and starting service..."
systemctl daemon-reload
systemctl enable greenops-agent.service
systemctl start greenops-agent.service

echo ""
echo "✅ Installation complete!"
echo ""
echo "Service status:"
systemctl status greenops-agent.service --no-pager
echo ""
echo "Useful commands:"
echo "  Start:   sudo systemctl start greenops-agent"
echo "  Stop:    sudo systemctl stop greenops-agent"
echo "  Status:  sudo systemctl status greenops-agent"
echo "  Logs:    sudo journalctl -u greenops-agent -f"
echo "  Config:  sudo nano $INSTALL_DIR/config.json"
echo ""
