@echo off
rem Doble clic: arranca GEM OS (si no esta en marcha) y abre el panel en el navegador.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0iniciar_gem_os.ps1" -Abrir
if errorlevel 1 (
  echo.
  echo No se pudo arrancar GEM OS. Revisa logs\elite\arranque.log
  pause
)
