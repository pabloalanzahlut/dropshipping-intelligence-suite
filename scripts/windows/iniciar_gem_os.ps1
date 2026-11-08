<#
.SYNOPSIS
  Arranca el servidor web de GEM OS en segundo plano (sin ventana de consola).

.DESCRIPTION
  - Si el servidor ya está escuchando en el puerto, no hace nada (se puede lanzar las veces que haga falta).
  - Escucha solo en 127.0.0.1 (este PC). Para verlo desde otro equipo hay que pedirlo: $env:GEM_OS_HOST.
  - Con el servidor en marcha trabajan solos: sincronización de transcripciones, ingesta a la KB,
    alertas, resumen diario (08:00), copia de seguridad (03:30) y mantenimiento semanal (domingo 04:00).

.PARAMETER Abrir
  Abre el panel en el navegador cuando el servidor responde.
#>
param(
    [switch]$Abrir,
    [int]$Puerto = 47821
)

$ErrorActionPreference = 'Stop'
$raiz = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$url  = "http://127.0.0.1:$Puerto/"

function Servidor-Activo {
    try { return ((Invoke-WebRequest -Uri ($url + 'api/status') -UseBasicParsing -TimeoutSec 3).StatusCode -eq 200) }
    catch { return $false }
}

if (Servidor-Activo) {
    Write-Host "GEM OS ya está en marcha: $url"
    if ($Abrir) { Start-Process $url }
    exit 0
}

# pythonw.exe = Python sin consola; si no existe se usa python.exe oculto
$python = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $python) { Write-Error 'No encuentro Python en el PATH. Instálalo o ajusta el PATH.'; exit 1 }
$pythonw = Join-Path (Split-Path $python) 'pythonw.exe'
$exe = if (Test-Path $pythonw) { $pythonw } else { $python }

$logs = Join-Path $raiz 'logs\elite'
New-Item -ItemType Directory -Force -Path $logs | Out-Null
$salida = Join-Path $logs 'arranque.log'

$argumentos = @('-m', 'uvicorn', 'app.services.dashboard_server:app',
                '--host', '127.0.0.1', '--port', "$Puerto")
Start-Process -FilePath $exe -ArgumentList $argumentos -WorkingDirectory $raiz -WindowStyle Hidden `
              -RedirectStandardOutput $salida -RedirectStandardError ($salida + '.err')

# Espera hasta 40 s a que responda
$listo = $false
for ($i = 0; $i -lt 20; $i++) {
    Start-Sleep -Seconds 2
    if (Servidor-Activo) { $listo = $true; break }
}
if ($listo) {
    Write-Host "GEM OS en marcha: $url"
    if ($Abrir) { Start-Process $url }
    exit 0
}
Write-Error "El servidor no respondió en 40 s. Revisa $salida y $salida.err"
exit 1
