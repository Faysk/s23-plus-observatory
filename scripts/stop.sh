#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
PIDFILE="$HOME/.local/state/s23-observatory/server.pid"
if [ ! -s "$PIDFILE" ]; then echo 'Sem PID registrado.'; exit 0; fi
PID="$(cat "$PIDFILE")"
case "$PID" in *[!0-9]*|'') echo 'PID inválido' >&2; exit 1;; esac
if ! kill -0 "$PID" 2>/dev/null; then rm -f "$PIDFILE"; echo 'Processo já parado.'; exit 0; fi
CMDLINE="$(tr '\0' ' ' < "/proc/$PID/cmdline" 2>/dev/null || true)"
case "$CMDLINE" in *'run.py --bind 127.0.0.1 --port 8783'*) kill "$PID"; rm -f "$PIDFILE"; echo 'Parado.';; *) echo 'PID pertence a outro processo. Nenhuma ação executada.' >&2; exit 1;; esac
