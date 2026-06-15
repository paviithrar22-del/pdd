#!/bin/bash
# ─────────────────────────────────────────────────────────────────
# Cloudflare Tunnel Setup — Free HTTPS for your Oracle VM
# Gives you a permanent HTTPS URL like: cybershield.yourdomain.com
# or a temporary URL (*.trycloudflare.com) for quick testing
# ─────────────────────────────────────────────────────────────────

echo "[1/3] Installing cloudflared..."
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64.deb -o cloudflared.deb
sudo dpkg -i cloudflared.deb
rm cloudflared.deb

echo ""
echo "[2/3] Starting quick tunnel (temporary URL for testing)..."
echo "      Your backend will be available at a *.trycloudflare.com URL"
echo "      Copy that URL and update your Vercel/frontend config."
echo ""
echo "      To stop: Ctrl+C"
echo "      For a permanent URL, run: cloudflared tunnel login"
echo ""

# Quick tunnel — gives you a public URL instantly, no account needed
cloudflared tunnel --url http://localhost:8000
