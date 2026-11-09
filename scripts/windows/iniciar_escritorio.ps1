<#
.SYNOPSIS
  Abre GEM OS (escritorio) desde Python, sin ventana de consola. No usa el .exe: no le afecta el bloqueo
  de Windows a los ejecutables sin firmar (Smart App Control).

.DESCRIPTION
  - El programa arranca por sí mismo el servidor web (o reutiliza el que ya esté en marcha), así que
    alertas, avisos, resumen diario, mantenimiento y sincronización funcionan mientras esté abierto.
  - Si ya está abierto, no abre otro.
  - Los errores de arranque quedan en logs\elite\escritorio.err (pythonw no muestra nada por pantalla).

.PARAMETER Minimizado
  Arranca minimizado (para el inicio de Windows).
#>
param(
    [switch]$Minimizado
)

$ErrorActionPreference = 'Stop'
$raiz = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path

# ¿Ya hay un escritorio abierto? (proceso de Python ejecutando app.main de ESTE proyecto)
$abierto = Get-CimInstance Win32_Process -Filter "Name = 'pythonw.exe' OR Name = 'python.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -match 'app[\\/.]main' -and $_.CommandLine -notmatch 'uvicorn' }
if ($abierto) {
    Write-Host "GEM OS ya está abierto (proceso $($abierto[0].ProcessId))."
    exit 0
}

$python = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $python) { Write-Error 'No encuentro Python en el PATH. Instálalo o ajusta el PATH.'; exit 1 }
$pythonw = Join-Path (Split-Path $python) 'pythonw.exe'
$exe = if (Test-Path $pythonw) { $pythonw } else { $python }

$logs = Join-Path $raiz 'logs\elite'
New-Item -ItemType Directory -Force -Path $logs | Out-Null
$err = Join-Path $logs 'escritorio.err'
$out = Join-Path $logs 'escritorio.out'

$argumentos = @('-m', 'app.main')
if ($Minimizado) { $argumentos += '--minimizado' }

$p = Start-Process -FilePath $exe -ArgumentList $argumentos -WorkingDirectory $raiz -WindowStyle Hidden `
        -RedirectStandardError $err -RedirectStandardOutput $out -PassThru

# Espera a que se vea la ventana (o a que el proceso muera por un error)
$listo = $false
for ($i = 0; $i -lt 40; $i++) {
    Start-Sleep -Milliseconds 500
    $p.Refresh()
    if ($p.HasExited) { break }
    if ($p.MainWindowHandle -ne 0) { $listo = $true; break }
}
if ($listo) { Write-Host 'GEM OS abierto.'; exit 0 }
if ($p.HasExited) {
    Write-Error "GEM OS se cerró al arrancar. Revisa $err"
    exit 1
}
Write-Host 'GEM OS está arrancando (la ventana tarda unos segundos).'
exit 0
