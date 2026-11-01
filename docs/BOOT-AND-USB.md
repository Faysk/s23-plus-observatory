# Boot e atalho do S23 — 01/11/2026

## Uso normal

Na Área de Trabalho do PC, use **Ativar monitor S23** depois de reiniciar o Android:

1. Desbloqueie o S23+ uma vez após o reboot.
2. Conecte o USB e aceite a autorização de depuração deste PC, se solicitada.
3. Execute o atalho e aguarde a confirmação do painel e dos sensores.
4. Depois da confirmação, pode desconectar o cabo e desligar o PC.

O comando do atalho instalado é:

```text
C:\Windows\System32\cmd.exe /c ""E:\Projects\S23\Ativar-monitor-S23.cmd""
```

O ativador procura exatamente um `SM-S916B` por USB. O S7 pode permanecer conectado;
outros modelos, dispositivos sem autorização e transportes ADB de rede são ignorados.
Ele verifica o SHA-256 do agente, confirma seu processo, abre o Termux, consulta a API
por encaminhamento USB temporário e remove esse encaminhamento ao terminar.
Só anuncia sucesso após CPU, bateria, rede e oito núcleos terem uma amostra válida.
Em um início frio, duas amostras podem levar cerca de um minuto.

## Configuração instalada no celular

- Termux:Boot **0.8.1 (1000), F-Droid**, instalado e aberto uma vez.
- Assinatura do complemento comparada à do Termux instalado, com correspondência.
- `~/.termux/boot/start-s23-observatory` chama `scripts/resume.sh`.
- `~/.local/state/s23-observatory/boot-mode` guarda o modo fixo `lan`.
- `~/.local/state/s23-observatory/keep-awake` habilita o wake lock do Termux.
- O bloco delimitado em `~/.bashrc` também retoma os serviços em terminais interativos;
  comandos SSH não interativos não disparam esse bloco.
- Termux e Termux:Boot estão na lista de exceções de otimização de bateria do Android.

O `resume.sh` inicia o SSH se necessário e retoma o painel. O início usa lock e
verificação de PID/cwd/comando para não duplicar processos, mesmo com duas chamadas.
Os arquivos de configuração contêm valores fixos, nunca comandos fornecidos externamente.

Manter a coleta com a tela apagada aumenta o consumo de bateria. O wake lock não
inicia o agente ADB depois de reboot: ele precisa novamente do atalho pelo PC.
O comportamento de boot depende do primeiro desbloqueio e das restrições do Android.
Um reboot físico completo não foi realizado nesta configuração; não se afirma aceite
de reinicialização somente a partir da instalação do complemento.

## Reproduzir e verificar

O complemento deve ter a **mesma assinatura/origem** do Termux. No S23 observado,
o Termux é assinado pelo F-Droid; o APK do GitHub é incompatível. Não desinstalar o
Termux para trocar a origem, pois isso colocaria seus dados em risco.

Fonte oficial: https://f-droid.org/en/packages/com.termux.boot/ . APK utilizado:
`https://f-droid.org/repo/com.termux.boot_1000.apk`.
SHA-256 do APK: `6f7cf9b94f539d3efd4af3544ff819947b49395275d8cfa7e5f80de14f3d9cf8`.

No Termux, depois de instalar/abrir o complemento compatível:

```bash
cd ~/s23-plus-observatory
bash scripts/setup-boot.sh --lan --keep-awake
bash scripts/resume.sh
bash scripts/status.sh
```

Os padrões de `setup-boot.sh` continuam loopback e sem wake lock. As opções acima
registram a escolha LAN/monitoramento contínuo autorizada para este S23.

No PC, para recriar o wrapper e o atalho no diretório de trabalho usado pelo dono:

```powershell
pwsh -NoProfile -File E:\Projects\S23\s23-plus-observatory\tools\create-shortcut.ps1 -WorkspaceRoot E:\Projects\S23
```

Teste sem abrir navegador:

```powershell
python E:\Projects\S23\s23-plus-observatory\tools\activate.py --adb E:\Projects\S23\tools\platform-tools\adb.exe
```

## Desativação e retorno

Remova somente `~/.termux/boot/start-s23-observatory` para retirar nosso boot.
Remova o bloco entre `BEGIN/END S23 OBSERVATORY RESUME` da `.bashrc` para retirar
a retomada ao abrir o terminal, preservando o restante do arquivo.
Apague o arquivo `keep-awake` e use `termux-wake-unlock` se nenhum outro uso do
Termux precisar manter o aparelho acordado. A opção de bateria pode ser restaurada
nas configurações Android de Termux/Termux:Boot.
Nada disso exige apagar o banco, desinstalar o Termux ou alterar o S7.

Verificação desta sessão: complemento instalado/lançado, exceções de bateria e wake
lock confirmados; dois inícios simultâneos e retomada interativa sem duplicação;
ativador testado com S7 e S23 conectados; 22 testes Python aprovados.
