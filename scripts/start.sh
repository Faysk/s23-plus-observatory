#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
exec python run.py --bind 127.0.0.1 --port 8783 --interval 30
