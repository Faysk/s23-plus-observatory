#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p "$HOME/.termux/boot"
BOOT="$HOME/.termux/boot/start-s23-observatory"
printf '#!/data/data/com.termux/files/usr/bin/bash\ncd %q\nbash scripts/start-background.sh\n' "$ROOT" > "$BOOT"
chmod 700 "$BOOT"
echo "Boot script criado em: $BOOT"
echo 'Para funcionar após reiniciar: instale o app Termux:Boot da mesma origem F-Droid, abra-o pelo menos uma vez, desative otimizações de bateria do Termux/Boot.'
echo 'Para DESATIVAR: rm ~/.termux/boot/start-s23-observatory'
