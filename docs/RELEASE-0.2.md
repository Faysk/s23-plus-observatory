# S23 Observatory v0.2 — 01/11/2026

Publicado em http://192.168.1.3:8783/s23/ no próprio SM-S916B / Android 17.

## Entrega

29 métricas numéricas com origem, estado, pesquisa e agrupamento; oito núcleos,
frequências, carga média, RAM/cache/slab/swap, energia e tensão, qualidade de Wi-Fi,
contadores da interface, tráfego e consumo do coletor. Leituras ausentes ficam nulas.

Gráficos SVG com teclado/cursor, eixos adequados para celular, ajuste à janela
real de amostras, médias/extremos/contagem e quebras nas lacunas detectadas.
Estatísticas usam as observações originais. CSV é explicitamente agregado;
JSON exporta a amostra atual. Snapshots completos são guardados a partir desta versão.
Retenção existente de 90 dias mantida. Pausar afeta somente a visualização.

Workspace recíproco com Router, S7, Vault, S23 e Acer. No S7/Router/Vault foi alterado
somente o frontend compartilhado finish.js; nenhum reinício do coletor.
No Acer, apenas feedback.js/feedback.css receberam o seletor de navegação.
Links são navegação; o S23 não consulta a telemetria dos outros equipamentos.

## Validação

- 17 testes Python aprovados, incluindo extrema, archive, cursor e reabertura SQLite.
- Teste Node dos gráficos: vazio, lacunas, faixa percentual, domínio e picos.
- Sintaxe dos JavaScript alterados validada.
- API real confirmou as 29 métricas disponíveis e os oito núcleos do S23.
- Comparação do SQLite com backup consistente: todos os 785 registros anteriores
  continuaram idênticos. PRAGMA quick_check retornou ok.
- Navegador: visão geral, CPU/núcleos, busca no catálogo, inspeção de gráfico por
  teclado, exportação CSV e pausa/retomada verificados.
- Layout móvel em viewport com 375 px úteis: documento sem transbordamento horizontal;
  SVG com geometria própria de 400 unidades para melhorar a leitura dos eixos.
- Links e projeto ativo conferidos no S7, Router e Vault; Acer conferido pelo serviço
  local através de túnel SSH autenticado. A URL pública mantém Cloudflare Access.

## Recuperação e limites

Backup consistente e código anterior no S23:
~/.local/state/s23-observatory/backups/ui-v02/.
Não restaurar o banco antigo sobre as observações novas para reverter a interface.
A reversão de código pode ignorar a nova tabela snapshots sem apagar seu conteúdo.

O agente iniciado via ADB continua após desconectar o USB, mas requer reinício por ADB
após reboot do Android. Nenhuma promessa de inicialização autônoma é feita.
Temperatura da CPU, corrente/potência e autonomia continuam não homologadas.
A reserva DHCP do S23 permanece associada ao perfil Wi-Fi Hades_WiFi7.
