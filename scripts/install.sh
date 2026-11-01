#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
if ! command -v pkg >/dev/null; then
  echo 'Este instalador foi feito para Termux. Em Linux comum: python3 run.py' >&2
  exit 1
fi
pkg install python util-linux openssh curl -y
python -c 'import sqlite3, http.server; print("Python/SQLite OK")'
mkdir -p "$HOME/.local/share/s23-observatory" "$HOME/.local/state/s23-observatory"
echo
printf 'Instalação concluída. Inicie com: bash scripts/start.sh\n'
printf 'Bateria avançada é opcional: instale o aplicativo Termux:API via F-Droid e execute pkg install termux-api\n'
