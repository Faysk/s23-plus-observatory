"""Metric definitions shared by collection, history and the UI."""
DEFINITIONS = {
    'cpu': ('CPU global', '%', 'cpu.usagePercent', 'Desempenho', 'Delta /proc/stat; janela indicada no diagnóstico'),
    'frequency': ('Frequência máxima observada', 'MHz', 'cpu.frequencyMHz', 'Desempenho', 'cpufreq/scaling_cur_freq; não é frequência máxima do modelo'),
    'load': ('Carga de 1 minuto', '', 'cpu.loadAverage.0', 'Desempenho', '/proc/loadavg; tarefas executáveis ou em espera de I/O'),
    'memory': ('RAM utilizada', '%', 'memory.usedPercent', 'Memória', '(MemTotal − MemAvailable) / MemTotal'),
    'memoryUsed': ('RAM utilizada', 'MiB', 'memory.usedMB', 'Memória', '/proc/meminfo; MB binários (MiB)'),
    'memoryAvailable': ('RAM disponível', 'MiB', 'memory.availableMB', 'Memória', '/proc/meminfo: MemAvailable; MiB'),
    'cached': ('Cache do sistema', 'MiB', 'memory.cachedMB', 'Memória', '/proc/meminfo: Cached; MiB; não somar à RAM usada'),
    'swap': ('Swap utilizada', 'MiB', 'memory.swapUsedMB', 'Memória', 'SwapTotal − SwapFree; MiB; não equivale à RAM física'),
    'battery': ('Nível da bateria', '%', 'battery.levelPercent', 'Energia', 'Serviço Android / Termux:API / sysfs'),
    'temp': ('Temperatura da bateria', '°C', 'battery.temperatureC', 'Energia', 'Sensor da bateria; não é temperatura da CPU'),
    'voltage': ('Tensão da bateria', 'mV', 'battery.voltageMV', 'Energia', 'Serviço Android dumpsys battery; mV'),
    'rx': ('Recebimento', 'Mb/s', 'network.rxMbps', 'Rede', 'Delta dos bytes da interface selecionada; não é speedtest'),
    'tx': ('Envio', 'Mb/s', 'network.txMbps', 'Rede', 'Delta dos bytes da interface selecionada; não é tráfego total da LAN'),
    'signal': ('Sinal Wi-Fi', 'dBm', 'network.signalDbm', 'Rede', 'Android cmd wifi status; potência de sinal recebida'),
    'linkRx': ('Link Wi-Fi RX', 'Mb/s', 'network.rxLinkMbps', 'Rede', 'Taxa de link informada pelo Android; não é consumo'),
    'linkTx': ('Link Wi-Fi TX', 'Mb/s', 'network.txLinkMbps', 'Rede', 'Taxa de link informada pelo Android; não é consumo'),
    'storage': ('Volume ocupado', '%', 'storage.0.usedPercent', 'Armazenamento', 'Filesystem acessível pelo Termux; GB decimais'),
    'storageFree': ('Espaço disponível', 'GB', 'storage.0.availableGB', 'Armazenamento', 'Disponível ao usuário no volume do Termux; decimal'),
    'processCpu': ('CPU do coletor', '%', 'monitor.cpuPercent', 'Coletor', 'Tempo de CPU do processo / tempo decorrido; 100% = um núcleo'),
    'processMemory': ('Memória do coletor', 'MiB', 'monitor.rssMB', 'Coletor', '/proc/self/status: VmRSS; MiB'),
    'collection': ('Tempo de coleta', 'ms', 'monitor.collectionMs', 'Coletor', 'Duração da coleta antes de persistir no SQLite'),
}
for i in range(8):
    DEFINITIONS[f'core{i}'] = (f'CPU · núcleo {i}', '%', f'cpu.coresPercent.{i}', 'Núcleos', 'Delta /proc/stat do núcleo; ausente permanece nulo')


def value_at(snapshot, path):
    value = snapshot
    try:
        for key in path.split('.'):
            value = value[int(key)] if isinstance(value, list) else value[key]
        return value
    except (KeyError, IndexError, TypeError, ValueError):
        return None


def catalog(snapshot=None):
    return {key: dict(label=v[0], unit=v[1], path=v[2], group=v[3], source=v[4],
                      value=value_at(snapshot, v[2]) if snapshot else None)
            for key, v in DEFINITIONS.items()}
