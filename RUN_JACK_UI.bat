@echo off
chcp 65001 >nul
cls

echo ╔═══════════════════════════════════════════════════════════════╗
echo ║   💎 GEM OS v3.0 - Jack-Style UI/UX Premium                  ║
echo ╚═══════════════════════════════════════════════════════════════╝
echo.
echo 🎨 Lanzador de Interfaz Rediseñada
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.
echo Selecciona una opción:
echo.
echo   [1] 🚀 Ejecutar aplicación completa (GEM OS v3.0)
echo   [2] 🎨 Demo de componentes Jack-Style
echo   [3] 📚 Ver documentación
echo   [4] ❌ Salir
echo.
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
set /p choice="👉 Ingresa tu opción (1-4): "

if "%choice%"=="1" goto run_app
if "%choice%"=="2" goto run_demo
if "%choice%"=="3" goto show_docs
if "%choice%"=="4" goto exit_script

echo ❌ Opción inválida
pause
exit /b 1

:run_app
cls
echo ╔═══════════════════════════════════════════════════════════════╗
echo ║   🚀 Iniciando GEM OS v3.0                                    ║
echo ╚═══════════════════════════════════════════════════════════════╝
echo.
echo ✓ Cargando módulos...
echo ✓ Aplicando estilos Jack-Style...
echo ✓ Inicializando componentes premium...
echo.
python test_jack_ui.py
goto end

:run_demo
cls
echo ╔═══════════════════════════════════════════════════════════════╗
echo ║   🎨 Demo de Componentes Premium                              ║
echo ╚═══════════════════════════════════════════════════════════════╝
echo.
echo ✓ Cargando componentes...
echo   - ModernButton
echo   - GlassCard
echo   - ModernEntry
echo   - Sidebar
echo.
python demo_jack_components.py
goto end

:show_docs
cls
echo ╔═══════════════════════════════════════════════════════════════╗
echo ║   📚 Documentación del Rediseño                               ║
echo ╚═══════════════════════════════════════════════════════════════╝
echo.
echo Archivos de documentación disponibles:
echo.
echo   📄 JACK_STYLE_REDESIGN.md
echo      → Filosofía de diseño y arquitectura
echo.
echo   📄 UI_V3_JACK_STYLE.md
echo      → Guía de uso completa con ejemplos
echo.
echo   📄 REDESIGN_SUMMARY.md
echo      → Resumen ejecutivo de cambios
echo.
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.
set /p open_doc="¿Abrir documentación en el navegador? (s/n): "
if /i "%open_doc%"=="s" (
    start UI_V3_JACK_STYLE.md
)
pause
goto menu

:exit_script
echo.
echo 👋 ¡Hasta pronto!
timeout /t 2 >nul
exit /b 0

:end
echo.
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.
pause
exit /b 0

:menu
cls
goto :eof
