<#
.SYNOPSIS
  Hace que GEM OS arranque solo al iniciar sesión en Windows (tarea programada del usuario).

.DESCRIPTION
  Crea la tarea «GEM OS · servidor» que ejecuta iniciar_gem_os.ps1 oculto al iniciar sesión.
  No necesita permisos de administrador (es una tarea del usuario actual) y se reinicia sola
  hasta 3 veces si el servidor se cae.

.PARAMETER SoloMostrar
  No instala nada: muestra qué se registraría.

.PARAMETER Quitar
  Elimina la tarea.

.PARAMETER Exe
  Ruta de GEM_OS_Suite.exe. Si se indica, al iniciar sesión se abre el programa (minimizado, con su
  servidor web y todas las automatizaciones) en lugar de lanzar el servidor con Python.

.PARAMETER Escritorio
  Al iniciar sesión abre el escritorio desde Python (minimizado, con su servidor web y todas las
  automatizaciones). Es la opción recomendada si Windows bloquea el .exe (Smart App Control).

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts\windows\instalar_autoarranque.ps1 -Escritorio
  powershell -ExecutionPolicy Bypass -File scripts\windows\instalar_autoarranque.ps1
  powershell -ExecutionPolicy Bypass -File scripts\windows\instalar_autoarranque.ps1 -Exe "C:\GEM_OS_Suite\GEM_OS_Suite.exe"
  powershell -ExecutionPolicy Bypass -File scripts\windows\instalar_autoarranque.ps1 -Quitar
#>
param(
    [switch]$SoloMostrar,
    [switch]$Quitar,
    [string]$Exe = '',
    [switch]$Escritorio
)

$ErrorActionPreference = 'Stop'
$nombre  = 'GEM OS · servidor'
$script  = (Resolve-Path (Join-Path $PSScriptRoot 'iniciar_gem_os.ps1')).Path
$usuario = "$env:USERDOMAIN\$env:USERNAME"

if ($Quitar) {
    if (Get-ScheduledTask -TaskName $nombre -ErrorAction SilentlyContinue) {
        Unregister-ScheduledTask -TaskName $nombre -Confirm:$false
        Write-Host "Tarea «$nombre» eliminada."
    } else {
        Write-Host "No existe la tarea «$nombre»."
    }
    exit 0
}

if ($Escritorio) {
    # Escritorio desde Python (sin el .exe): lo abre minimizado y arranca su propio servidor web
    $raiz = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
    $python = (Get-Command python -ErrorAction Stop).Source
    $pythonw = Join-Path (Split-Path $python) 'pythonw.exe'
    if (-not (Test-Path $pythonw)) { $pythonw = $python }
    $accion = New-ScheduledTaskAction -Execute $pythonw -Argument '-m app.main --minimizado' -WorkingDirectory $raiz
    $queEjecuta = "`"$pythonw`" -m app.main --minimizado  (en $raiz)"
} elseif ($Exe) {
    if (-not (Test-Path $Exe -PathType Leaf)) { Write-Error "No existe el programa: $Exe"; exit 1 }
    $Exe = (Resolve-Path $Exe).Path
    $accion = New-ScheduledTaskAction -Execute $Exe -Argument '--minimizado' -WorkingDirectory (Split-Path $Exe)
    $queEjecuta = "`"$Exe`" --minimizado"
} else {
    $accion = New-ScheduledTaskAction -Execute 'powershell.exe' `
        -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$script`""
    $queEjecuta = "powershell.exe -File `"$script`" (oculto)"
}
$disparador = New-ScheduledTaskTrigger -AtLogOn -User $usuario
# Vigilante: cada 5 min vuelve a lanzar la tarea; con IgnoreNew no duplica si ya está corriendo,
# así que solo actúa cuando el proceso ha muerto.
$disparador.Repetition = (New-ScheduledTaskTrigger -Once -At (Get-Date) `
    -RepetitionInterval (New-TimeSpan -Minutes 5)).Repetition
$ajustes = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit ([TimeSpan]::Zero) -MultipleInstances IgnoreNew
$principal = New-ScheduledTaskPrincipal -UserId $usuario -LogonType Interactive -RunLevel Limited

if ($SoloMostrar) {
    Write-Host "Se registraría la tarea «$nombre»:"
    Write-Host "  Usuario:     $usuario (sin administrador)"
    Write-Host "  Al iniciar sesión ejecuta: $queEjecuta"
    Write-Host "  Reintentos:  3, cada minuto, si se cae; vigilante cada 5 min si el proceso muere"
    exit 0
}

Register-ScheduledTask -TaskName $nombre -Action $accion -Trigger $disparador -Settings $ajustes `
    -Principal $principal -Description 'Arranca el servidor web de GEM OS al iniciar sesión.' -Force | Out-Null
Write-Host "Listo: GEM OS arrancará solo cuando inicies sesión. Para quitarlo: -Quitar"
