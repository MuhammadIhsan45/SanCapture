#!/bin/bash
# ==============================================================================
# SanCapture - macOS Build & DMG Creation Shell Script
# ==============================================================================

set -e

echo "=========================================="
echo "  SanCapture macOS DMG Build Script       "
echo "=========================================="

# Determine project directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Check Python 3
if ! command -v python3 &> /dev/null; then
    echo "[Error] python3 could not be found. Please install Python 3.10+ from python.org or brew."
    exit 1
fi

echo "[1/3] Checking dependencies..."
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt

echo "[2/3] Building SanCapture.app and SanCapture.dmg..."
python3 build_mac.py

echo "[3/3] Done!"
echo "Check the 'dist' directory for SanCapture.dmg"
