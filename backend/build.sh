#!/bin/bash
# build.sh — Full production build for Railway/Render Standard
# Installs CPU-only torch (smaller), transformers, and Playwright

set -e  # Exit on any error

echo "=== Installing CPU-only PyTorch (lighter, no CUDA needed) ==="
pip install torch==2.3.0 --index-url https://download.pytorch.org/whl/cpu

echo "=== Installing remaining Python dependencies ==="
pip install -r requirements.txt

echo "=== Installing Playwright Chromium browser ==="
playwright install chromium
playwright install-deps chromium

echo "=== Build complete ==="
