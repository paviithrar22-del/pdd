#!/bin/bash
# ─────────────────────────────────────────────────────────────────
# CyberShield Oracle Cloud Setup Script
# Run this ONCE on a fresh Oracle Cloud ARM (Ampere A1) VM
# Usage: bash oracle_setup.sh
# ─────────────────────────────────────────────────────────────────

set -e  # Exit on error

REPO_URL="https://github.com/YOUR_USERNAME/YOUR_REPO.git"  # <-- UPDATE THIS
APP_DIR="/home/ubuntu/cybershield"

echo "======================================================"
echo " CyberShield — Oracle Cloud Setup"
echo "======================================================"

# 1. System updates and dependencies
echo "[1/7] Installing system packages..."
sudo apt-get update -y
sudo apt-get install -y \
  python3.11 python3.11-venv python3-pip git curl wget \
  libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 \
  libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 \
  libxfixes3 libxrandr2 libgbm1 libasound2 \
  libpango-1.0-0 libcairo2 libx11-xcb1

# 2. Clone the repo
echo "[2/7] Cloning repository..."
if [ -d "$APP_DIR" ]; then
  cd "$APP_DIR" && git pull
else
  git clone "$REPO_URL" "$APP_DIR"
fi
cd "$APP_DIR/backend"

# 3. Python virtual environment
echo "[3/7] Setting up Python virtual environment..."
python3.11 -m venv venv
source venv/bin/activate

# 4. Install dependencies (CPU torch + everything)
echo "[4/7] Installing Python dependencies..."
pip install --upgrade pip
pip install torch==2.3.0 --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt

# 5. Install Playwright browser
echo "[5/7] Installing Playwright Chromium..."
playwright install chromium
playwright install-deps chromium

# 6. Create .env file
echo "[6/7] Creating .env file..."
if [ ! -f ".env" ]; then
  cat > .env << 'ENVEOF'
SECRET_KEY=CHANGE-THIS-TO-RANDOM-STRING-32CHARS
JWT_SECRET=CHANGE-THIS-TO-ANOTHER-RANDOM-STRING
DATABASE_URL=sqlite:///./cybershield.db
DEBUG=false
FRONTEND_URL=https://your-app.vercel.app
SMTP_HOST=smtp-mail.outlook.com
SMTP_PORT=587
SMTP_EMAIL=your-outlook@outlook.com
SMTP_PASSWORD=your-outlook-password
ENVEOF
  echo "  >> .env created. Edit it with: nano $APP_DIR/backend/.env"
fi

# 7. Create systemd service for auto-start
echo "[7/7] Setting up systemd service..."
sudo tee /etc/systemd/system/cybershield.service > /dev/null << SERVICEEOF
[Unit]
Description=CyberShield Backend
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=$APP_DIR/backend
Environment=PATH=$APP_DIR/backend/venv/bin
ExecStart=$APP_DIR/backend/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SERVICEEOF

sudo systemctl daemon-reload
sudo systemctl enable cybershield
sudo systemctl start cybershield

echo ""
echo "======================================================"
echo " Setup Complete!"
echo "======================================================"
echo " Service status: sudo systemctl status cybershield"
echo " View logs:      sudo journalctl -u cybershield -f"
echo " Edit .env:      nano $APP_DIR/backend/.env"
echo ""
echo " Next: Run the Cloudflare tunnel for HTTPS:"
echo "   bash cloudflare_tunnel.sh"
echo "======================================================"
