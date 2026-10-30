# Arquitetura e contrato

## Fluxo

```
S23+ / Termux
  /proc/stat, /proc/meminfo, /proc/net/dev, sysfs, Termux:API opcional
        │ leitura a cada 30 s
        ▼
  Python Collector ──▶ SQLite metrics.sqlite3 (90 dias; dados numéricos)
        │                    │
        └──────────┬─────────┘
                   ▼
        HTTP 127.0.0.1:8783 (somente GET)
                   │
              túnel SSH:8022
                   ▼
        Navegador no Windows: http://127.0.0.1:8783
```

## API

- `GET /api/health`: `{ok,lastSample,lastErrorType}`; código 503 se ainda não coletou ou está parado.
- `GET /api/host/snapshot`: `source:"live"`, `timestamp` ISO 8601 UTC, `device`, `cpu`, `memory`, `battery`, `network`, `storage`, `services`, `availability`, `diagnostics`. Dados ausentes aparecem como JSON `null`.
- `GET /api/host/catalog`: métricas e intervalos suportados.
- `GET /api/host/history?metric=cpu&range=24h`: `{metric,range,points:[{time:epochMilliseconds,value:number}]}`.

Métricas (`value` para histórico):

| Métrica | Unidade | Semântica |
| --- | --- | --- |
| cpu | % | Delta de `/proc/stat` entre observações; global, todas CPUs |
| memory | % | `(MemTotal - MemAvailable) / MemTotal ×100` |
| battery | % | Nível da bateria |
| temp | °C | Temperatura da **bateria** |
| rx / tx | Mb/s | Delta de bytes da interface ×8 / segundos /10⁶ |
| storage | % | Espaço usado no filesystem do Termux |

Os horários de bucket do histórico representam o início do intervalo; valores são **médias aritméticas das amostras disponíveis** naquele bucket, não interpolação de lacunas. Sem registro é ausência, não zero. O frontend fragmenta segmentos separados por lacunas longas, mas os limites de perda de amostras precisam ser validados em campo.

## Política de coleta

- Sem root, sem Android ADB, sem sensores privados e sem solicitar novas permissões por padrão.
- Biblioteca padrão Python (SQLite, HTTP server, subprocess).
- Catálogo estático de sensores; disponibilidade informada pela amostra atual.
- `Termux:API` opcional para bateria; `getprop` apenas campos de modelo, versão e arquitetura.
- Sem SSID, IP do telefone, localização, serial, IMEI, processos de outras apps ou ficheiros pessoais.
- Retenção limitada a 90 dias por padrão; backup é responsabilidade do operador.

## Pendências de homologação no S23+

- Verificar modelo real, versão Android, sensores permitidos, uso em Doze/foreground e comportamento de `termux-battery-status`.
- Conferir leitura CPU após 2 amostras; nulidade de `/proc/stat` é válida e esperada em alguns dispositivos.
- Comparar `/proc/meminfo` contra a UI Android, levando em conta diferentes conceitos de memória livre/disponível.
- Validar formato e escala da temperatura sysfs, se utilizada, com Termux:API.
- Medir custo de bateria e suspensão com tela apagada; validar acesso remoto após horas.
- Verificar precisão da taxa RX/TX quando interface muda ou contador reinicia.
- Inspecionar responsividade e acessibilidade no aparelho físico e no PC.
