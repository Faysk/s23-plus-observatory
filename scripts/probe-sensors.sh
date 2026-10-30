#!/data/data/com.termux/files/usr/bin/bash
# Sem root; sem serial, localização, SSID, IP, MAC, chamadas, SMS ou conteúdo de ficheiros pessoais.
set -u
echo '=== S23+ Observatory / mapa de acesso a sensores ==='
for prop in ro.product.model ro.build.version.release ro.product.cpu.abi; do
  printf 'getprop %-28s = ' "$prop"
  getprop "$prop" 2>/dev/null || echo 'N/A'
done
printf '\n=== /proc (permissões) ===\n'
for path in /proc/stat /proc/meminfo /proc/net/dev /proc/uptime; do
  if [ -r "$path" ] && head -n 1 "$path" >/dev/null 2>&1; then
    echo "OK: $path"
  else
    echo "BLOQUEADO: $path"
  fi
done
printf '\n=== CPU cpufreq / sensores (sem inferir unidade) ===\n'
found=0
for path in /sys/devices/system/cpu/cpu*/cpufreq/scaling_cur_freq; do
  if [ -e "$path" ]; then
    found=$((found+1))
    printf '%s: ' "$path"
    cat "$path" 2>/dev/null || echo 'BLOQUEADO'
  fi
  [ "$found" -ge 12 ] && break
done
[ "$found" -eq 0 ] && echo 'Sem arquivos legíveis de cpufreq'
printf '\n=== Battery sysfs ===\n'
for field in capacity temp status health voltage_now current_now; do
  path="/sys/class/power_supply/battery/$field"
  if [ -e "$path" ]; then
    printf '%s: ' "$field"
    cat "$path" 2>/dev/null || echo 'BLOQUEADO'
  else
    echo "$field: AUSENTE"
  fi
done
printf '\n=== Termux:API (bateria) ===\n'
if command -v termux-battery-status >/dev/null; then
  timeout 5 termux-battery-status 2>/dev/null | python -c 'import sys,json;d=json.load(sys.stdin); print({k:d.get(k) for k in ("percentage","status","health","plugged","temperature")})' 2>/dev/null || echo 'API indisponível'
else
  echo 'termux-api não instalado'
fi
printf '\n=== Thermal zones: tipos, sem atribuir componentes ===\n'
count=0
for path in /sys/class/thermal/thermal_zone*/type; do
  [ -e "$path" ] || continue
  count=$((count+1))
  printf 'zona%-2d: ' "$count"
  cat "$path" 2>/dev/null || echo 'BLOQUEADO'
  [ "$count" -ge 20 ] && break
done
[ "$count" -eq 0 ] && echo 'Nenhuma zona visível'
echo '=== FIM (sem dados pessoais ou identificadores de rede) ==='
