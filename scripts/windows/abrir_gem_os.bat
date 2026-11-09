@echo off
rem Doble clic: abre GEM OS (escritorio). El programa arranca solo su servidor web y todas las
rem automatizaciones; el boton "Abrir panel web" de la barra superior abre la web.
rem Usa Python (no el .exe), asi que no le afecta el bloqueo de Windows a los ejecutables sin firmar.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0iniciar_escritorio.ps1"
if errorlevel 1 (
  echo.
  echo No se pudo abrir GEM OS. Revisa logs\elite\escritorio.err
  pause
)
