# Tooltips e feedback visual — 01/11/2026

Todos os gráficos usam o mesmo renderer charts.js: CPU, memória, frequência,
swap, bateria, temperatura, tensão, rede, sinal, link, armazenamento e coletor.

Tooltip flutuante mostra data, valor, mínimo, máximo e quantidade de amostras.
A seleção segue o ponto real mais próximo, sem interpolar telemetria. Cursor e
posição do tooltip usam requestAnimationFrame, com atualização do conteúdo somente
quando muda a amostra. Teclado: setas, Home, End e Escape. Toque seleciona o ponto.

O cartão fica dentro do gráfico e muda de lado nos limites; mantém leitura textual
acessível. Animações respeitam prefers-reduced-motion; páginas ocultas suspendem
animações. Navegação cancela os frames dos gráficos descartados.

Skeletons exibem o estado real de carregamento; atualizações preservam dados
anteriores quando disponíveis. Botão Atualizar indica requisição em andamento.
Entrada de página e abertura de menus têm transições breves, sem repetir a animação
de página a cada amostra. Nenhuma alteração na cadência, retenção ou sensores.

Validação: 17 testes Python, testes Node de geometria/extremos/lacunas e limites do
tooltip, verificação no navegador com dados reais, teclado e tela estreita.
