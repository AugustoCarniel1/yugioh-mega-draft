@echo off
setlocal
cd /d "%~dp0"
powershell -ExecutionPolicy Bypass -File ".\scripts\start_local.ps1"
if errorlevel 1 (
  echo.
  echo Falha ao iniciar o projeto.
  pause
)
