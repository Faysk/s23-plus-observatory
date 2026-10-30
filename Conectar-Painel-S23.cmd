@echo off
setlocal
chcp 65001 >nul
title S23+ Observatory - Tunel SSH
if not defined S23_HOST set /p "S23_HOST=IP do Galaxy S23+: "
if not defined S23_USER set /p "S23_USER=Usuario Termux (whoami): "
if not defined S23_SSH_PORT set "S23_SSH_PORT=8022"
if "%S23_HOST%"=="" goto :missing
if "%S23_USER%"=="" goto :missing
echo.
echo  SSH: %S23_USER%@%S23_HOST%:%S23_SSH_PORT%
echo  Painel: http://127.0.0.1:8783
echo  Mantenha a janela aberta. Ctrl+C encerra o tunel.
echo.
ssh -o ExitOnForwardFailure=yes -p %S23_SSH_PORT% -L 8783:127.0.0.1:8783 -N %S23_USER%@%S23_HOST%
echo.
echo Tunel finalizado.
pause
exit /b
:missing
echo IP e usuario sao obrigatorios.
pause
