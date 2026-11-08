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

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts\windows\instalar_autoarranque.ps1
  powershell -ExecutionPolicy Bypass -File scripts\windows\instalar_autoarranque.ps1 -Quitar
#>
param(
    [switch]$SoloMostrar,
    [switch]$Quitar
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

$accion = New-ScheduledTaskAction -Execute 'powershell.exe' `
    -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$script`""
$disparador = New-ScheduledTaskTrigger -AtLogOn -User $usuario
$ajustes = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit ([TimeSpan]::Zero)
$principal = New-ScheduledTaskPrincipal -UserId $usuario -LogonType Interactive -RunLevel Limited

if ($SoloMostrar) {
    Write-Host "Se registraría la tarea «$nombre»:"
    Write-Host "  Usuario:     $usuario (sin administrador)"
    Write-Host "  Al iniciar sesión ejecuta: powershell.exe -File `"$script`" (oculto)"
    Write-Host "  Reintentos:  3, cada minuto, si el servidor se cae"
    exit 0
}

Register-ScheduledTask -TaskName $nombre -Action $accion -Trigger $disparador -Settings $ajustes `
    -Principal $principal -Description 'Arranca el servidor web de GEM OS al iniciar sesión.' -Force | Out-Null
Write-Host "Listo: GEM OS arrancará solo cuando inicies sesión. Para quitarlo: -Quitar"
