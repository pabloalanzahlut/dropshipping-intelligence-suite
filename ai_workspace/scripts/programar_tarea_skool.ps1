# GEM OS — Automatización completa Skool (ejecutar como Administrador)
# Programa DOS tareas en Windows Task Scheduler:
#   1. Sync diario a las 09:00
#   2. Reporte semanal los lunes a las 08:00

$rutaApp    = "H:\dropshipping_intelligence_suite"
$rutaPython = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $rutaPython) {
    Write-Error "Python no encontrado en PATH. Instálalo primero."
    exit 1
}

$rutaScript = "$rutaApp\ai_workspace\scripts\auto_pipeline_skool.py"

# ── Tarea 1: Sync diario ──────────────────────────────────────────────────────
$action1  = New-ScheduledTaskAction `
    -Execute  $rutaPython `
    -Argument "`"$rutaScript`"" `
    -WorkingDirectory $rutaApp

$trigger1 = New-ScheduledTaskTrigger -Daily -At "09:00"

$settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit  (New-TimeSpan -Hours 1) `
    -RestartCount        3 `
    -RestartInterval     (New-TimeSpan -Minutes 10) `
    -StartWhenAvailable  $true

Register-ScheduledTask `
    -TaskName   "GEM_OS_Skool_Sync_Diario" `
    -Action     $action1 `
    -Trigger    $trigger1 `
    -Settings   $settings `
    -RunLevel   Highest `
    -Force | Out-Null

Write-Host "✅ Sync diario: todos los días a las 09:00"

# ── Tarea 2: Reporte semanal ──────────────────────────────────────────────────
$action2  = New-ScheduledTaskAction `
    -Execute  $rutaPython `
    -Argument "`"$rutaScript`" --solo-reporte" `
    -WorkingDirectory $rutaApp

# Lunes a las 08:00
$trigger2 = New-ScheduledTaskTrigger -Weekly -WeeksInterval 1 -DaysOfWeek Monday -At "08:00"

Register-ScheduledTask `
    -TaskName   "GEM_OS_Skool_Reporte_Semanal" `
    -Action     $action2 `
    -Trigger    $trigger2 `
    -Settings   $settings `
    -RunLevel   Highest `
    -Force | Out-Null

Write-Host "✅ Reporte semanal: lunes a las 08:00"

# ── Resumen ───────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "════════════════════════════════════════"
Write-Host "  GEM OS — Skool automatizado"
Write-Host "════════════════════════════════════════"
Write-Host "  📡 Sync:    diario 09:00"
Write-Host "  📊 Reporte: lunes  08:00"
Write-Host ""
Write-Host "Para ejecutar ahora sin esperar:"
Write-Host "  python `"$rutaScript`""
Write-Host ""
Write-Host "Para ver las tareas:"
Write-Host "  Get-ScheduledTask | Where-Object {`$_.TaskName -like 'GEM_OS*'}"
