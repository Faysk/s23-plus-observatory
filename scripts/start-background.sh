#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
STATE="$HOME/.local/state/s23-observatory"
mkdir -p "$STATE"
PIDFILE="$STATE/server.pid"
if curl -fsS --max-time 2 http://127.0.0.1:8783/api/health >/dev/null; then
  echo 'Observatory já está respondendo em localhost:8783'
  exit 0
fi
nohup python run.py --bind 127.0.0.1 --port 8783 --interval 30 > "$STATE/server.log" 2>&1 < /dev/null &
PID=$!
echo "$PID" > "$PIDFILE"
sleep 2
if kill -0 "$PID" 2>/dev/null; then
  echo "Processo iniciado (PID $PID). Log: $STATE/server.log"
  echo 'A primeira leitura de CPU e rede pode exigir um segundo ciclo de coleta.'
else
  echo "Falha ao iniciar. Verifique: tail -n 40 '$STATE/server.log'" >&2
  exit 1
fi
