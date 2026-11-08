# GEM OS — Programar sincronización diaria de Skool
# Ejecutar como Administrador UNA SOLA VEZ

$rutaApp     = "H:\dropshipping_intelligence_suite"
$rutaPython  = (Get-Command python).Source
$rutaScript  = "$rutaApp\ai_workspace\scripts\skool_scraper.py"
$nombreTarea = "GEM_OS_Skool_Sync"

# Acción: ejecutar el scraper cada día a las 09:00
$action  = New-ScheduledTaskAction `
    -Execute $rutaPython `
    -Argument "`"$rutaScript`"" `
    -WorkingDirectory $rutaApp

$trigger = New-ScheduledTaskTrigger -Daily -At "09:00"

$settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Hours 1) `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 10)

Register-ScheduledTask `
    -TaskName   $nombreTarea `
    -Action     $action `
    -Trigger    $trigger `
    -Settings   $settings `
    -RunLevel   Highest `
    -Force

Write-Host "✅ Tarea '$nombreTarea' programada para las 09:00 diariamente."
Write-Host "   Puedes verla en: Programador de tareas → $nombreTarea"
