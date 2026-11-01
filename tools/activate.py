"""USB activation for the S23 only. Never enables network ADB or changes the S7."""
from __future__ import annotations
import argparse
import hashlib
import ipaddress
import json
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

MODEL = 'SM-S916B'
REMOTE = '/data/local/tmp/s23-android-agent.sh'
SOURCE = Path(__file__).resolve().parents[1] / 'scripts/s23-android-agent.sh'


class ActivationError(RuntimeError):
    pass


class Adb:
    def __init__(self, executable, serial=None):
        self.executable, self.serial = str(executable), serial

    def run(self, args, timeout=20, check=True):
        command = [self.executable] + (['-s', self.serial] if self.serial else []) + list(args)
        result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=timeout)
        if check and result.returncode:
            raise ActivationError('A operação USB falhou. Confira o cabo, o desbloqueio e a autorização de depuração.')
        return result


def select_device(adb):
    output = adb.run(['devices', '-l']).stdout
    candidates = []
    for line in output.splitlines():
        fields = line.split()
        if (len(fields) < 2 or fields[1] != 'device' or fields[0].startswith('emulator-')
                or any(marker in fields[0] for marker in (':', '._adb-', '._tcp'))):
            continue
        device = Adb(adb.executable, fields[0])
        result = device.run(['shell', 'getprop', 'ro.product.model'], check=False)
        if result.returncode == 0 and result.stdout.strip() == MODEL:
            candidates.append(device)
    if len(candidates) != 1:
        raise ActivationError('Conecte um único Galaxy S23+ SM-S916B por USB, desbloqueie-o e autorize este PC. Outros modelos não serão alterados.')
    return candidates[0]


def install_agent(adb, source=SOURCE):
    local_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    old = adb.run(['shell', 'sha256sum', REMOTE], check=False)
    old_hash = old.stdout.split()[0] if old.stdout.split() else None
    if old_hash != local_hash:
        adb.run(['push', str(source), REMOTE + '.new'])
        copied = adb.run(['shell', 'sha256sum', REMOTE + '.new']).stdout.split()
        if not copied or copied[0] != local_hash:
            raise ActivationError('A cópia do agente não passou na verificação SHA-256. Nenhum script novo foi iniciado.')
        adb.run(['shell', 'chmod', '700', REMOTE + '.new'])
        adb.run(['shell', 'mv', REMOTE + '.new', REMOTE])
        # The newly verified lifecycle command checks ownership before stopping any PID.
        adb.run(['shell', 'sh', REMOTE, '--stop'], timeout=15)
    result = adb.run(['shell', 'sh', REMOTE, '--start'], timeout=12)
    if not any(token in result.stdout for token in ('AGENT_STARTED', 'AGENT_ALREADY_ACTIVE')):
        raise ActivationError('O agente não confirmou a inicialização.')
    status = adb.run(['shell', 'sh', REMOTE, '--status'])
    if 'AGENT_ACTIVE' not in status.stdout:
        raise ActivationError('O agente não está ativo após a tentativa de inicialização.')


def complete_snapshot(data):
    if not isinstance(data, dict) or data.get('device', {}).get('model') != MODEL:
        raise ActivationError('A resposta do servidor não pertence ao S23 esperado.')
    stamp = data.get('ageSeconds')
    available = data.get('availability', {})
    return (data.get('quality') == 'ok' and isinstance(stamp, (int, float)) and 0 <= stamp <= 90
            and all(available.get(key) is True for key in ('cpu', 'battery', 'network'))
            and len(data.get('cpu', {}).get('coresPercent', [])) == 8)


def verify_over_usb(adb, wait_seconds=95):
    port = adb.run(['forward', 'tcp:0', 'tcp:8783']).stdout.strip()
    if not port.isdigit() or not 1 <= int(port) <= 65535:
        raise ActivationError('Não foi possível preparar a conferência local por USB.')
    try:
        deadline = time.monotonic() + wait_seconds
        server_seen = False
        last_notice = 0
        while time.monotonic() < deadline:
            try:
                with urllib.request.urlopen(f'http://127.0.0.1:{port}/s23/api/host/snapshot', timeout=3) as response:
                    data = json.load(response)
                server_seen = True
                if complete_snapshot(data):
                    return data
            except (OSError, urllib.error.URLError, ValueError):
                pass
            now = time.monotonic()
            if now - last_notice >= 10:
                print('Aguardando o painel e duas amostras de sensores…', flush=True)
                last_notice = now
            time.sleep(2)
        if server_seen:
            raise ActivationError('O painel responde, mas os sensores ainda não ficaram completos. Confira Sistema e fontes; execute o atalho novamente.')
        raise ActivationError('O painel não respondeu. Abra o Termux e confira o boot configurado; este atalho não informou sucesso.')
    finally:
        adb.run(['forward', '--remove', 'tcp:' + port], check=False)


def panel_url(adb):
    result = adb.run(['shell', 'ip', '-o', '-4', 'addr', 'show', 'wlan0'], check=False)
    match = re.search(r'\binet\s+(\d+\.\d+\.\d+\.\d+)/', result.stdout)
    if match:
        ip = ipaddress.ip_address(match[1])
        if any(ip in ipaddress.ip_network(net) for net in ('10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16')):
            return f'http://{ip}:8783/s23/'
    return 'http://192.168.1.3:8783/s23/'


def main():
    parser = argparse.ArgumentParser(description='Ativar o monitor do S23+ por USB, sem alterar outros aparelhos.')
    parser.add_argument('--adb', type=Path, required=True)
    parser.add_argument('--open-browser', action='store_true')
    args = parser.parse_args()
    if not args.adb.is_file():
        raise ActivationError('ADB não encontrado. Confira a pasta tools/platform-tools do projeto S23.')
    if not SOURCE.is_file():
        raise ActivationError('Arquivo do agente não encontrado no projeto S23.')
    adb = select_device(Adb(args.adb))
    print('Galaxy S23+ identificado. Abrindo Termux e retomando os serviços…', flush=True)
    launched = adb.run(['shell', 'am', 'start', '--user', '0', '-n', 'com.termux/.app.TermuxActivity'])
    if 'Error:' in launched.stdout + launched.stderr:
        raise ActivationError('Não foi possível abrir o Termux. Desbloqueie o aparelho e tente novamente.')
    install_agent(adb)
    verify_over_usb(adb)
    url = panel_url(adb)
    print('SUCESSO: painel e sensores do S23 confirmados por USB.')
    print('Pode desconectar o cabo e desligar o PC. A coleta continua no celular.')
    print('Após reiniciar o Android, desbloqueie o celular e execute este atalho por USB novamente.')
    print('Painel:', url)
    if args.open_browser:
        webbrowser.open(url)


if __name__ == '__main__':
    try:
        main()
    except (ActivationError, OSError, subprocess.SubprocessError) as error:
        print('Não foi possível concluir:', error)
        sys.exit(1)
