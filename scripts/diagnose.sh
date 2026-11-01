#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
echo '=== S23+ Observatory / diagnóstico seguro ==='
echo 'Python:'; python --version || true
echo 'SO:'; getprop ro.build.version.release 2>/dev/null || true
echo 'Modelo:'; getprop ro.product.model 2>/dev/null || true
echo 'API de bateria:'
if command -v termux-battery-status >/dev/null; then
  timeout 5 termux-battery-status 2>/dev/null | python -c 'import sys,json; data=json.load(sys.stdin); print("Acessível:", sorted(k for k in data if k in ("percentage","status","temperature","health","plugged")))' || echo 'App Termux:API não responde / permissão indisponível.'
else
  echo 'termux-api (pacote) não instalado; bateria pode usar sysfs.'
fi
echo 'Snapshot: '
if command -v curl >/dev/null; then curl -fsS --max-time 3 http://127.0.0.1:8783/s23/api/health || true; fi
printf '\nFim. Não contém SSID, localização, números de série nem chaves.\n'
