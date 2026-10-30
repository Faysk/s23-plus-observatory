#!/data/data/com.termux/files/usr/bin/bash
if curl -fsS --max-time 3 http://127.0.0.1:8783/api/health; then printf '\n'; else echo 'Serviço não está respondendo.' >&2; exit 1; fi
