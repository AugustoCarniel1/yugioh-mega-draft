@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo Ambiente virtual nao encontrado. Execute start_local.bat uma vez primeiro.
  pause
  exit /b 1
)

echo.
echo Sincronizando cartas e impressoes no banco local...
echo Isso pode levar alguns minutos na primeira vez. E seguro executar novamente para retomar.
echo.
.venv\Scripts\python.exe scripts\sync_card_catalog.py
set "SYNC_EXIT=%ERRORLEVEL%"
echo.
if not "%SYNC_EXIT%"=="0" (
  echo A sincronizacao terminou com pendencias. Execute este arquivo novamente para tentar os sets que falharam.
) else (
  echo Base de cartas sincronizada com sucesso.
)
pause
exit /b %SYNC_EXIT%
