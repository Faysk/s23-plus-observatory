param(
  [string]$WorkspaceRoot = (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent)
)
$ErrorActionPreference = 'Stop'
$WorkspaceRoot = (Resolve-Path -LiteralPath $WorkspaceRoot).Path
$Activator = Join-Path $WorkspaceRoot 's23-plus-observatory\tools\activate.py'
$AdbPath = Join-Path $WorkspaceRoot 'tools\platform-tools\adb.exe'
if (!(Test-Path -LiteralPath $Activator) -or !(Test-Path -LiteralPath $AdbPath)) {
  throw 'Selecione a pasta S23 contendo o projeto e tools\platform-tools\adb.exe.'
}
$CommandPath = Join-Path $WorkspaceRoot 'Ativar-monitor-S23.cmd'
$CommandText = @'
@echo off
chcp 65001 >nul
set "PYTHONUTF8=1"
title Ativar monitor S23
cd /d "%~dp0"
python "%~dp0s23-plus-observatory\tools\activate.py" --adb "%~dp0tools\platform-tools\adb.exe" --open-browser
set "S23_RESULT=%ERRORLEVEL%"
echo.
pause
exit /b %S23_RESULT%
'@
if (Test-Path -LiteralPath $CommandPath) {
  $ExistingText = [IO.File]::ReadAllText($CommandPath)
  if (!$ExistingText.Contains('s23-plus-observatory\tools\activate.py')) {
    throw 'Já existe um arquivo diferente com o nome Ativar-monitor-S23.cmd. Nenhum arquivo foi substituído.'
  }
}
[IO.File]::WriteAllText($CommandPath, ($CommandText -replace "`r?`n", "`r`n") + "`r`n", [Text.UTF8Encoding]::new($false))
$DesktopPath = [Environment]::GetFolderPath('DesktopDirectory')
$ShortcutPath = Join-Path $DesktopPath 'Ativar monitor S23.lnk'
$ShortcutShell = New-Object -ComObject WScript.Shell
$Shortcut = $ShortcutShell.CreateShortcut($ShortcutPath)
if ((Test-Path -LiteralPath $ShortcutPath) -and !$Shortcut.Arguments.Contains($CommandPath)) {
  throw 'Já existe um atalho diferente com esse nome. Nenhum atalho foi substituído.'
}
$Shortcut.TargetPath = $env:ComSpec
$Shortcut.Arguments = '/c ""' + $CommandPath + '""'
$Shortcut.WorkingDirectory = $WorkspaceRoot
$Shortcut.IconLocation = "$env:SystemRoot\System32\shell32.dll,17"
$Shortcut.Description = 'Após reiniciar o S23+, desbloqueie, conecte USB e ative o monitor. Não altera o S7.'
$Shortcut.WindowStyle = 1
$Shortcut.Save()
Write-Output "Atalho criado: $ShortcutPath"
Write-Output "Comando: $($Shortcut.TargetPath) $($Shortcut.Arguments)"
