"""Coleta conservadora e sem root para Android/Termux.

Leitura bloqueada/ausente => None (nunca zero inventado).
Não recolhe contactos, localização, número de série, SSID ou apps pessoais.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import shutil
import socket
import subprocess
import time
from pathlib import Path
from typing import Any
from .adb_source import AdbSource
from .catalog import DEFINITIONS, value_at

_METRIC = tuple(DEFINITIONS)


def read_text(path: str) -> str | None:
    try:
        return Path(path).read_text(encoding='utf-8').strip()
    except (OSError, UnicodeError):
        return None


def num(value: Any) -> float | None:
    try:
        if value is None or isinstance(value, bool) or str(value).strip() == '':
            return None
        v = float(value)
        if v != v or not -1e20 < v < 1e20:
            return None
        return v
    except (TypeError, ValueError, OverflowError):
        return None


def cmd(arguments: list[str], timeout: float = 3.0) -> str | None:
    if not shutil.which(arguments[0]):
        return None
    try:
        p = subprocess.run(arguments, capture_output=True, text=True, timeout=timeout, check=False)
        return p.stdout.strip() if p.returncode == 0 and p.stdout.strip() else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def parse_meminfo(source: str | None) -> dict[str, float | None]:
    values: dict[str, float] = {}
    for name, kb in re.findall(r'^([A-Za-z_()]+):\s+(\d+)\s+kB\s*$', source or '', re.M):
        values[name] = int(kb) / 1024
    total = values.get('MemTotal')
    available = values.get('MemAvailable')
    return {
        'totalMB': round(total, 1) if total is not None else None,
        'usedMB': round(max(0, total - available), 1) if total is not None and available is not None else None,
        'availableMB': round(available, 1) if available is not None else None,
        'cachedMB': round(values['Cached'], 1) if 'Cached' in values else None,
        'swapMB': round(values['SwapTotal'], 1) if 'SwapTotal' in values else None,
        'swapFreeMB': round(values['SwapFree'], 1) if 'SwapFree' in values else None,
        'swapUsedMB': round(max(0, values['SwapTotal']-values['SwapFree']), 1) if 'SwapTotal' in values and 'SwapFree' in values else None,
        'buffersMB': round(values['Buffers'], 1) if 'Buffers' in values else None,
        'slabMB': round(values['Slab'], 1) if 'Slab' in values else None,
        'usedPercent': round((total-available)/total*100, 2) if total and available is not None else None,
    }


def parse_proc_stat(source: str | None) -> dict[str, tuple[int, int]]:
    result: dict[str, tuple[int, int]] = {}
    for line in (source or '').splitlines():
        parts = line.split()
        if not parts or not re.fullmatch(r'cpu\d*', parts[0]):
            continue
        try:
            fields = [int(p) for p in parts[1:]]
            if len(fields) < 4 or any(v < 0 or v > 2**63-1 for v in fields):
                continue
            # Linux: user nice system idle iowait irq softirq steal guest guest_nice
            # guest fields are already included in user/nice, so use first 8.
            total = sum(fields[:8]); idle = fields[3] + (fields[4] if len(fields) > 4 else 0)
            result[parts[0]] = (total, idle)
        except ValueError:
            continue
    return result


def cpu_percent(previous: tuple[int, int] | None, current: tuple[int, int] | None) -> float | None:
    if not previous or not current:
        return None
    total = current[0] - previous[0]
    idle = current[1] - previous[1]
    if total <= 0 or idle < 0 or idle > total:
        return None
    return round(max(0, min(100, 100 * (1 - idle / total))), 1)


def parse_netdev(source: str | None) -> dict[str, tuple[int, int]]:
    out: dict[str, tuple[int, int]] = {}
    for line in (source or '').splitlines():
        if ':' not in line:
            continue
        name, raw = line.split(':', 1)
        fields = raw.split()
        try:
            if len(fields) >= 16:
                out[name.strip()] = (int(fields[0]), int(fields[8]))
        except ValueError:
            continue
    return out


def as_percent(v: Any) -> float | None:
    n = num(v)
    return round(n, 1) if n is not None and 0 <= n <= 100 else None


def battery_from_api() -> dict[str, Any] | None:
    raw = cmd(['termux-battery-status'], timeout=3.0)
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        return None
    if not isinstance(data, dict):
        return None
    temp = num(data.get('temperature'))
    if temp is not None and not -30 <= temp <= 100:
        temp = None
    return {
        'levelPercent': as_percent(data.get('percentage')),
        'status': str(data['status'])[:32] if data.get('status') is not None else None,
        'plugged': str(data['plugged'])[:32] if data.get('plugged') is not None else None,
        'temperatureC': round(temp, 1) if temp is not None else None,
        'health': str(data['health'])[:32] if data.get('health') is not None else None,
        'source': 'Termux:API',
    }


def battery_from_sysfs() -> dict[str, Any]:
    prefix = '/sys/class/power_supply/battery/'
    level = as_percent(read_text(prefix + 'capacity'))
    raw = num(read_text(prefix + 'temp'))
    # Linux power_supply/temp costuma estar em décimos de grau. Validar faixa.
    temperature = raw / 10 if raw is not None else None
    if temperature is not None and not -30 <= temperature <= 100:
        temperature = None
    return {
        'levelPercent': level,
        'status': read_text(prefix + 'status'),
        'plugged': None,
        'temperatureC': round(temperature, 1) if temperature is not None else None,
        'health': read_text(prefix + 'health'),
        'source': 'sysfs' if level is not None or temperature is not None else None,
    }


def battery_from_android(raw):
    fields = dict(re.findall(r'^  ([A-Za-z ]+):\s*(\S+)\s*$', raw or '', re.M))
    level, scale = num(fields.get('level')), num(fields.get('scale'))
    temp = num(fields.get('temperature'))
    status = {'1':'UNKNOWN','2':'CHARGING','3':'DISCHARGING','4':'NOT_CHARGING','5':'FULL'}
    health = {'1':'UNKNOWN','2':'GOOD','3':'OVERHEAT','4':'DEAD','5':'OVER_VOLTAGE','6':'FAILURE','7':'COLD'}
    return {'levelPercent': as_percent(level * 100 / scale) if level is not None and scale and scale > 0 else None,
            'status': status.get(fields.get('status')), 'health': health.get(fields.get('health')),
            'temperatureC': round(temp / 10, 1) if temp is not None and -300 <= temp <= 1000 else None,
            'plugged': next((label for key, label in [('AC powered','AC'),('USB powered','USB'),('Wireless powered','WIRELESS')]
                             if fields.get(key) == 'true'), 'UNPLUGGED' if any(k in fields for k in ('AC powered','USB powered','Wireless powered')) else None),
            'voltageMV': num(fields.get('voltage')), 'source': 'Android dumpsys battery (agente ADB)'}


def disk_info(directory: str) -> dict[str, Any]:
    try:
        usage = shutil.disk_usage(directory)
        if usage.total <= 0:
            raise OSError('invalid filesystem')
        return {
            'id': 'termux', 'label': 'Armazenamento do Termux',
            'totalGB': round(usage.total / 1e9, 2),
            'usedGB': round(usage.used / 1e9, 2),
            'availableGB': round(usage.free / 1e9, 2),
            'usedPercent': round(100 * usage.used / usage.total, 1),
        }
    except OSError:
        return {'id': 'termux', 'label': 'Armazenamento do Termux', 'totalGB': None,
                'usedGB': None, 'availableGB': None, 'usedPercent': None}


def getprop(name: str) -> str | None:
    value = cmd(['getprop', name], timeout=1.5)
    return value[:120] if value else None


class Collector:
    def __init__(self, home: str | None = None):
        self.home = home or str(Path.home())
        self._agent = AdbSource()
        self._cpu: dict[str, tuple[int, int]] = {}
        self._net: dict[str, tuple[int, int]] = {}
        self._last_net_at: float | None = None
        self._process_at = time.monotonic()
        self._process_cpu = time.process_time()
        self._identity: dict[str, Any] | None = None

    def collect(self) -> dict[str, Any]:
        began = time.monotonic()
        now = began
        agent = self._agent.read()
        stat = parse_proc_stat(read_text('/proc/stat'))
        cpu = cpu_percent(self._cpu.get('cpu'), stat.get('cpu'))
        cores = [cpu_percent(self._cpu.get(key), value)
                 for key, value in sorted(stat.items()) if key != 'cpu']
        self._cpu = stat
        if cpu is None and agent:
            previous = parse_proc_stat(agent.get('cpu_before'))
            current = parse_proc_stat(agent.get('cpu_after'))
            cpu = cpu_percent(previous.get('cpu'), current.get('cpu'))
            cores = [cpu_percent(previous.get(key), current[key]) for key in sorted(current, key=lambda k: int(k[3:]) if k != 'cpu' else -1) if key != 'cpu']
        mem = parse_meminfo(read_text('/proc/meminfo'))
        battery = battery_from_api() or battery_from_sysfs()
        if battery.get('levelPercent') is None and agent:
            battery = battery_from_android(agent.get('battery'))
        disk = disk_info(self.home)
        nets = parse_netdev(read_text('/proc/net/dev'))
        if not nets and agent:
            nets = parse_netdev(agent.get('network'))
            now = agent['uptime']
        iface = next((p for p in ('wlan0', 'rmnet_data0', 'eth0') if p in nets), None)
        # Nunca usa tráfego loopback como "Wi-Fi".
        if iface is None:
            iface = next((p for p in nets if p != 'lo' and not p.startswith(('veth', 'dummy'))), None)
        rx = tx = None
        if iface in nets and iface in self._net and self._last_net_at is not None:
            elapsed = now - self._last_net_at
            dx = nets[iface][0] - self._net[iface][0]
            dy = nets[iface][1] - self._net[iface][1]
            if elapsed > 0 and dx >= 0 and dy >= 0:
                rx, tx = round(dx * 8 / elapsed / 1e6, 4), round(dy * 8 / elapsed / 1e6, 4)
        self._net, self._last_net_at = nets, now
        if self._identity is None:
            model = getprop('ro.product.model')
            self._identity = {
                'name': model or 'Android (modelo não identificado)',
                'model': model,
                'brand': getprop('ro.product.brand'),
                'os': ('Android ' + value) if (value := getprop('ro.build.version.release')) else None,
                'architecture': getprop('ro.product.cpu.abi'),
            }
        uptime = num((read_text('/proc/uptime') or '').split(' ')[0])
        if uptime is None:
            try:
                uptime = time.clock_gettime(time.CLOCK_BOOTTIME)
            except (AttributeError, OSError):
                pass
        frequencies = [num(read_text(str(path))) for path in sorted(Path('/sys/devices/system/cpu').glob('cpu[0-9]*/cpufreq/scaling_cur_freq'), key=lambda p: int(p.parent.parent.name[3:]))]
        frequencies = [round(v / 1000, 1) if v is not None and 0 < v < 10000000 else None for v in frequencies]
        ssh = None
        try:
            with socket.create_connection(('127.0.0.1', 8022), timeout=0.25):
                ssh = 'running'
        except OSError:
            ssh = 'unreachable'
        elapsed = time.monotonic()-self._process_at
        process_cpu = time.process_time()
        process_usage = round(100*(process_cpu-self._process_cpu)/elapsed, 2) if elapsed > 0 else None
        self._process_at, self._process_cpu = time.monotonic(), process_cpu
        status = read_text('/proc/self/status') or ''
        rss = re.search(r'^VmRSS:\s+(\d+) kB', status, re.M)
        load_raw = read_text('/proc/loadavg') or (agent.get('load') if agent else '') or ''
        load = [num(v) for v in load_raw.split()[:3]]
        wifi = agent.get('wifi', '') if agent else ''
        def wifi_value(label, minimum, maximum):
            match = re.search(re.escape(label) + r':\s*(-?\d+)', wifi)
            value = num(match[1]) if match else None
            return value if value is not None and minimum <= value <= maximum else None
        net_fields = None
        net_raw = read_text('/proc/net/dev') or (agent.get('network') if agent else '') or ''
        for line in net_raw.splitlines():
            if ':' in line and line.split(':',1)[0].strip() == iface:
                fields = line.split(':',1)[1].split()
                if len(fields)>=16 and all(v.isdigit() for v in fields):
                    net_fields = list(map(int, fields))
        timestamp = dt.datetime.now(dt.timezone.utc).isoformat()
        snapshot = {
            'source': 'live', 'timestamp': timestamp, 'device': dict(self._identity, uptimeSec=round(uptime) if uptime is not None else None),
            'cpu': {'usagePercent': cpu, 'coresPercent': cores, 'frequencyMHz': max((v for v in frequencies if v is not None), default=None), 'coresFrequencyMHz': frequencies, 'temperatureC': None, 'loadAverage': load},
            'memory': mem,
            'battery': battery,
            'network': {'interface': iface, 'rxMbps': rx, 'txMbps': tx,
                        'ip': None, 'ssid': None, 'signalDbm': wifi_value('RSSI', -127, 0), 'latencyMs': None,
                        'rxLinkMbps': wifi_value('Rx Link speed', 0, 100000),
                        'txLinkMbps': wifi_value('Tx Link speed', 0, 100000),
                        'frequencyMHz': wifi_value('Frequency', 2000, 8000),
                        'rxBytes': net_fields[0] if net_fields else None,
                        'txBytes': net_fields[8] if net_fields else None,
                        'rxPackets': net_fields[1] if net_fields else None,
                        'txPackets': net_fields[9] if net_fields else None,
                        'rxErrors': net_fields[2] if net_fields else None,
                        'txErrors': net_fields[10] if net_fields else None,
                        'rxDrops': net_fields[3] if net_fields else None,
                        'txDrops': net_fields[11] if net_fields else None},
            'monitor': {'cpuPercent': process_usage, 'rssMB': round(int(rss[1])/1024,2) if rss else None,
                        'collectionMs': round((time.monotonic()-began)*1000,2)} ,
            'storage': [disk],
            'services': [{'id': 'ssh', 'name': 'OpenSSH', 'port': 8022, 'status': ssh}],
            'diagnostics': {'cpuSource': '/proc/stat' if stat else 'Agente Android ADB: /proc/stat' if agent and cpu is not None else None,
                            'agentAgeSeconds': agent['ageSeconds'] if agent else None,
                            'cpuWindowSec': agent['windowSec'] if agent and not stat else None,
                            'networkSource': ('Agente Android ADB: /proc/net/dev' if agent and not read_text('/proc/net/dev') else '/proc/net/dev') if nets else None,
                            'batterySource': battery.get('source'),
                            'notes': 'null = indisponível; CPU necessita de duas amostras; sem root'},
        }
        snapshot['availability'] = {
            'cpu': cpu is not None, 'memory': mem['usedMB'] is not None,
            'battery': battery['levelPercent'] is not None,
            'temperature': battery['temperatureC'] is not None,
            'network': rx is not None, 'storage': disk['usedPercent'] is not None,
        }
        return snapshot


def flatten(snapshot: dict[str, Any]) -> dict[str, float]:
    source = {key: value_at(snapshot, definition[2]) for key, definition in DEFINITIONS.items()}
    mem = snapshot.get('memory', {})
    if source['memory'] is None and mem.get('usedMB') is not None and mem.get('totalMB'):
        source['memory'] = round(mem['usedMB']/mem['totalMB']*100, 2)
    return {key: float(value) for key, value in source.items() if num(value) is not None}
