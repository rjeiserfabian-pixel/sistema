$ErrorActionPreference = "Stop"

$python = Join-Path $PSScriptRoot "env\Scripts\python.exe"
$collectStatic = ($env:RUN_COLLECTSTATIC -eq "1")

if (-not (Test-Path $python)) {
    Write-Host "No se encontro el entorno virtual en env\Scripts\python.exe" -ForegroundColor Red
    exit 1
}

if ($collectStatic) {
    Write-Host "Recolectando archivos estaticos..." -ForegroundColor Cyan
    & $python manage.py collectstatic --noinput
} else {
    Write-Host "Omitiendo collectstatic. WhiteNoise servira desde static/." -ForegroundColor Cyan
}

Write-Host "Iniciando servidor con Waitress en http://0.0.0.0:8000" -ForegroundColor Green
Write-Host "En otra terminal ejecuta: ngrok http 8000" -ForegroundColor Yellow
& $python -m waitress --listen=0.0.0.0:8000 --threads=8 --connection-limit=200 --channel-timeout=120 raiz.wsgi:application
