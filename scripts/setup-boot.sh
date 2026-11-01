#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MODE=loopback
AWAKE=no
for arg in "$@"; do
  case "$arg" in --lan) MODE=lan;; --keep-awake) AWAKE=yes;; *) echo 'Uso: setup-boot.sh [--lan] [--keep-awake]' >&2; exit 2;; esac
done
command -v flock >/dev/null || { echo 'Instale util-linux antes de configurar o boot.' >&2; exit 1; }
command -v sshd >/dev/null || { echo 'Instale openssh antes de configurar o boot.' >&2; exit 1; }
STATE="$HOME/.local/state/s23-observatory"
mkdir -p "$STATE"
printf '%s\n' "$MODE" > "$STATE/boot-mode"
if [ "$AWAKE" = yes ]; then touch "$STATE/keep-awake"; else rm -f "$STATE/keep-awake"; fi
mkdir -p "$HOME/.termux/boot"
BOOT="$HOME/.termux/boot/start-s23-observatory"
printf '#!/data/data/com.termux/files/usr/bin/bash\nbash %q >> %q 2>&1\n' "$ROOT/scripts/resume.sh" "$STATE/boot.log" > "$BOOT"
chmod 700 "$BOOT"
# Preserve the user's bash configuration; only replace our own bounded block.
python - "$ROOT" <<'PY'
import pathlib, shlex, sys
path=pathlib.Path.home()/'.bashrc'
start='# BEGIN S23 OBSERVATORY RESUME'
end='# END S23 OBSERVATORY RESUME'
text=path.read_text(encoding='utf-8') if path.exists() else ''
if start in text:
    if text.count(start)!=1 or text.count(end)!=1 or text.index(end)<text.index(start):
        raise SystemExit('Bloco de retomada inválido; .bashrc preservado para revisão.')
    a=text.index(start); b=text.index(end)+len(end)
    text=text[:a]+text[b:]
command='bash '+shlex.quote(sys.argv[1]+'/scripts/resume.sh')+' >/dev/null 2>&1'
block=start+'\ncase $- in\n  *i*) '+command+' ;;\nesac\n'+end+'\n'
if path.exists():
    backup=path.with_name('.bashrc.before-s23-resume')
    if not backup.exists(): backup.write_bytes(path.read_bytes())
path.write_text(text.rstrip()+'\n\n'+block,encoding='utf-8')
PY
echo "Boot script criado em: $BOOT"
echo "Modo configurado: $MODE; manter acordado: $AWAKE"
echo 'Use Termux:Boot da mesma origem/assinatura do Termux instalado e abra-o uma vez.'
echo 'Abrir um novo terminal Termux também retoma SSH e painel, sem duplicar processos.'
echo 'Para DESATIVAR: rm ~/.termux/boot/start-s23-observatory'
