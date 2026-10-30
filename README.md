# S23+ Observatory

Observatório **local-first** para um **Samsung Galaxy S23+** com Android/Termux, criado como projeto independente e inspirado no [S7 Edge Observatory](https://github.com/Faysk/s7-edge-observatory). Interface web responsiva em português, backend Python (somente biblioteca padrão) e histórico SQLite com retenção de 90 dias.

> **Status: v0.1, base funcional/testada em Linux.** Os sensores exatos do S23+ ainda precisam de homologação no próprio aparelho. Nenhum número fictício é exibido como telemetria real.

## Recursos

- API `GET /api/host/snapshot`, `GET /api/host/history`, `GET /api/host/catalog` e `GET /api/health`.
- CPU global e por núcleo via `/proc/stat`, **quando o Android permitir**. Primeira amostra não dispõe de delta de CPU.
- Memória via `/proc/meminfo`; `used = total - MemAvailable` (não equivale à soma dos processos).
- Bateria via Termux:API (opcional); fallback por sysfs se acessível. Temperatura exibida é **da bateria**, nunca atribuída à CPU.
- Rede via contadores `/proc/net/dev`, taxas em **Mb/s** calculadas entre duas amostras; não é velocidade contratada, RSSI nem speedtest. Pode ser inacessível em Android moderno.
- Armazenamento via `disk_usage` na pasta Home do Termux; representa o **filesystem/volume acessível**, não uma leitura isolada de dados de outros apps.
- Estado de SSH local na porta 8022; informações básicas de SO/modelo sem serial/IMEI.
- Histórico com 1h/6h/12h/24h/7d/30d/90d; sem interpolação e sem `0` inventado. SQLite registra somente valores validados e não nulos.
- Tema escuro/claro, interface adaptável a desktop/mobile, sem CDN e sem telemetria de terceiros.

## 1. Instalando no S23+

No **PC Windows**, transfira o ZIP para o celular (PowerShell):

```powershell
scp -P 8022 "$HOME\Downloads\s23-plus-observatory.zip" u0_aXXX@192.0.2.10:~/
```

No **Termux do S23+** (pelo SSH que já funciona):

```bash
pkg install unzip -y
unzip -o ~/s23-plus-observatory.zip -d ~/
cd ~/s23-plus-observatory
bash scripts/install.sh
bash scripts/start.sh
```

A aplicação inicia em `http://127.0.0.1:8783` **dentro do celular**. Deixe esse terminal aberto enquanto executa em primeiro plano. Outra opção:

```bash
# Após Ctrl+C, iniciar em segundo plano:
bash scripts/start-background.sh
bash scripts/status.sh
# Para parar:
bash scripts/stop.sh
```

## 2. Abrir no PC sem expor a porta web na rede

Use o arquivo `Conectar-Painel-S23.cmd`, ou o comando:

```powershell
ssh -p 8022 -N -o ExitOnForwardFailure=yes -L 8783:127.0.0.1:8783 u0_aXXX@192.0.2.10
```

**Deixe a janela SSH aberta** e acesse **http://127.0.0.1:8783** no navegador do PC. O link local só é acessível enquanto o SSH tunnel estiver ativo. Não precisa abrir portas no roteador.

## 3. Bateria (opcional, para mais leituras)

Como o Termux foi instalado via **F-Droid**, instale **Termux:API do F-Droid** (não misture APKs de outras origens). Abra o aplicativo, conceda apenas as permissões necessárias e execute no Termux:

```bash
pkg install termux-api -y
termux-battery-status
bash scripts/diagnose.sh
```

O observatório funciona **sem** esse plugin, mas a bateria pode aparecer como indisponível se a leitura sysfs estiver bloqueada. Não coleta GPS, SMS, contactos, fotos, SSID ou número de série. A instalação do app Termux:API expõe outras funcionalidades que este projeto **não chama**.

## 4. Iniciar automaticamente no boot (opcional)

Para um telefone principal, considere o consumo de bateria e as restrições do Android. Instale **Termux:Boot pelo F-Droid**, abra o aplicativo uma vez, e então:

```bash
cd ~/s23-plus-observatory
bash scripts/setup-boot.sh
```

Para desativar: `rm ~/.termux/boot/start-s23-observatory`. A execução após reinício depende das permissões e otimizações de bateria do Android; não é garantida.

## 5. Testes e diagnóstico

```bash
python -m unittest discover -s tests -v
python -m compileall -q observatory run.py
bash scripts/diagnose.sh
```

O sistema não exige root nem bibliotecas Python externas. Algumas leituras podem ficar indisponíveis por restrições do Android/SELinux; **não** tente conceder root só para habilitar sensores.

## Publicação no GitHub

O código deste projeto está publicado em [Faysk/s23-plus-observatory](https://github.com/Faysk/s23-plus-observatory). Para instalar pelo Git no Termux, execute:

```bash
pkg install git -y
git clone https://github.com/Faysk/s23-plus-observatory.git
cd s23-plus-observatory
bash scripts/install.sh
bash scripts/start-background.sh
```

As alterações no S23+ são independentes do S7 Edge. O painel só recebe dados reais depois da instalação no aparelho.

## Limites e segurança

- O HTTP inicia apenas em **loopback** (`127.0.0.1`), sem autenticação web: **túnel SSH é a fronteira de segurança**.
- `--bind 0.0.0.0` exige `--unsafe-lan` e **não é recomendado**: expõe a API sem autenticação na LAN.
- Nenhuma execução remota de comandos via HTTP, downloads, mudanças de configurações, nem sensores fictícios.
- SQLite local em `~/.local/share/s23-observatory/metrics.sqlite3`, não versionado no Git.
- A telemetria em segundo plano e os wakelocks consomem recursos; instale o boot automático somente se quiser manter coleta contínua.
- Consulte `docs/ARCHITECTURE.md` e `docs/SECURITY.md`.

## Licença

MIT — implementação original do projeto S23+. O S7 Edge Observatory serve de referência conceitual e não teve seus arquivos incorporados.

## Próxima etapa: mapear a precisão dos sensores físicos

Depois de instalar, execute no próprio S23+:

```bash
cd ~/s23-plus-observatory
bash scripts/probe-sensors.sh
```

O resultado lista somente capacidades, dados brutos selecionados de CPU/bateria e nomes de zonas térmicas; **não** recolhe localização, SSID, IP, MAC, IMEI ou série. Envie o resultado para decidir com segurança quais sensores adicionais podem ser incorporados. A leitura de CPU/GPU, frequências e térmicos de chipset exige validação específica; não se deve atribuir um `thermal_zone` aleatório à CPU.
