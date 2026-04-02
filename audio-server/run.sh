#!/bin/bash
cd "$(dirname "$0")"
source ~/.zshrc 2>/dev/null || true
echo "Starting audio analysis server..."
python3 server.py
