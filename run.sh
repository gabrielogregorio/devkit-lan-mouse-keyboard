#!/usr/bin/env bash
# Run in the foreground (handy for testing / first run).
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$REPO/venv/bin/python" "$REPO/server/main.py"
