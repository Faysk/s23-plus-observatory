#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
STATE="$HOME/.local/state/s23-observatory"
mkdir -p "$STATE"
# This configuration contains fixed flags, never executable commands.
MODE=loopback
if [ -r "$STATE/boot-mode" ]; then read -r MODE < "$STATE/boot-mode"; fi
case "$MODE" in lan|loopback) ;; *) echo 'Modo de boot inválido.' >&2; exit 2;; esac
if [ -f "$STATE/keep-awake" ] && command -v termux-wake-lock >/dev/null; then
  termux-wake-lock
fi
if ! pgrep -x sshd >/dev/null; then
  sshd || echo 'Não foi possível iniciar o SSH; confira o Termux.' >&2
fi
cd "$ROOT"
if [ "$MODE" = lan ]; then
  bash scripts/start-background.sh --unsafe-lan --bind 0.0.0.0
else
  bash scripts/start-background.sh
fi
