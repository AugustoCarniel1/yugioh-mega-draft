param(
    [switch]$ForceInstall
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$venvPath = Join-Path $projectRoot ".venv"
$pythonExe = Join-Path $venvPath "Scripts\python.exe"
$backendCmd = "Set-Location '$projectRoot'; & '$pythonExe' -m uvicorn app.backend.main:app --reload"
$frontendCmd = "Set-Location '$projectRoot'; & '$pythonExe' -m streamlit run app/frontend/streamlit_app.py"

function Get-SystemPython {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        return @("py", "-3")
    }
    if (Get-Command python -ErrorAction SilentlyContinue) {
        return @("python")
    }
    throw "Python 3 nao encontrado. Instale Python 3.11+ antes de continuar."
}

function Invoke-Python {
    param(
        [string[]]$CommandParts
    )

    if ($CommandParts.Length -le 1) {
        & $CommandParts[0]
        return
    }
    & $CommandParts[0] $CommandParts[1..($CommandParts.Length - 1)]
}

Write-Host ""
Write-Host "Yu-Gi-Oh! Mega Draft - inicializacao local" -ForegroundColor Cyan
Write-Host ""

if (-not (Test-Path $venvPath)) {
    Write-Host "Criando ambiente virtual..." -ForegroundColor Yellow
    $systemPython = Get-SystemPython
    Invoke-Python ($systemPython + @("-m", "venv", $venvPath))
}

if (-not (Test-Path $pythonExe)) {
    throw "Nao encontrei o Python da virtualenv em $pythonExe"
}

Write-Host "Atualizando pip..." -ForegroundColor Yellow
& $pythonExe -m pip install --upgrade pip | Out-Host

if ($ForceInstall -or -not (Test-Path (Join-Path $venvPath ".deps_installed"))) {
    Write-Host "Instalando dependencias..." -ForegroundColor Yellow
    & $pythonExe -m pip install -r (Join-Path $projectRoot "requirements.txt") | Out-Host
    New-Item -ItemType File -Path (Join-Path $venvPath ".deps_installed") -Force | Out-Null
} else {
    Write-Host "Dependencias ja preparadas. Use -ForceInstall para reinstalar." -ForegroundColor DarkGray
}

Write-Host "Inicializando banco..." -ForegroundColor Yellow
& $pythonExe (Join-Path $projectRoot "scripts\init_db.py") | Out-Host

Write-Host "Abrindo backend em http://127.0.0.1:8000" -ForegroundColor Green
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    $backendCmd
)

Write-Host "Abrindo frontend em http://localhost:8501" -ForegroundColor Green
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    $frontendCmd
)

Write-Host ""
Write-Host "Tudo certo. Aguarde alguns segundos e abra http://localhost:8501" -ForegroundColor Cyan
