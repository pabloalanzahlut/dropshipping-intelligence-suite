"""
Módulo de Robustez de Entorno — Instalador Automático de FFmpeg
=================================================================
Verifica disponibilidad de FFmpeg en el SO; si no está presente en
Windows, descarga un binario estático ligero desde el mirror oficial
gyan.dev, lo descomprime en `bin/ffmpeg/` dentro del proyecto y
ofrece una función para inyectar dicha ruta dinámicamente en el PATH
al arrancar la aplicación principal.

Uso rápido:
    from app.utils.install_ffmpeg import ensure_ffmpeg
    ensure_ffmpeg()  # descarga si es necesario e inyecta en PATH
"""

import os
import sys
import zipfile
import shutil
import subprocess
import tempfile
import urllib.request
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

# Carpeta relativa donde se alojará el binario dentro del proyecto
BIN_FFMPEG_DIR: Path = Path("bin") / "ffmpeg"

# URL del mirror oficial gyan.dev — distribución "essentials" que contiene
# únicamente ffmpeg.exe y ffprobe.exe, sin documentación ni extras.
FFMPEG_DOWNLOAD_URL: str = (
    "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
)

# Nombre esperado del ejecutable según la plataforma
FFMPEG_EXE: str = "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg"
# ---------------------------------------------------------------------------
# Funciones públicas
# ---------------------------------------------------------------------------

def is_ffmpeg_available() -> bool:
    """
    Retorna True si ffmpeg está accesible en el PATH del sistema operativo.
    Ejecuta ``ffmpeg -version`` con salida suprimida.
    """
    try:
        subprocess.run(
            [FFMPEG_EXE, "-version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False


def download_and_extract_ffmpeg(target_dir: Optional[Path] = None) -> Path:
    """
    Descarga la distribución *essentials* de FFmpeg desde el mirror oficial
    gyan.dev, la descomprime y copia ``ffmpeg.exe`` dentro de *target_dir*.

    Args:
        target_dir: Ruta donde se depositará el binario.
                     Por defecto ``<cwd>/bin/ffmpeg/``.

    Returns:
        Ruta absoluta del directorio que contiene ``ffmpeg.exe``.
    """
    if target_dir is None:
        target_dir = Path.cwd() / BIN_FFMPEG_DIR

    target_dir = Path(target_dir).resolve()
    target_dir.mkdir(parents=True, exist_ok=True)

    print(f"[FFMPEG] Descargando binario estático desde mirror oficial…")
    print(f"  URL: {FFMPEG_DOWNLOAD_URL}")

    # Descarga del ZIP a un archivo temporal
    tmp_path: Optional[str] = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
            tmp_path = tmp.name
        urllib.request.urlretrieve(FFMPEG_DOWNLOAD_URL, tmp_path)
    except Exception:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise

    # Extracción del binario
    print("[FFMPEG] Extrayendo binario…")
    exe_target = target_dir / FFMPEG_EXE

    try:
        with zipfile.ZipFile(tmp_path, "r") as zf:
            candidates = [m for m in zf.namelist() if m.endswith(FFMPEG_EXE)]
            if not candidates:
                raise RuntimeError(
                    f"No se encontró '{FFMPEG_EXE}' dentro del archivo descargado."
                )
            source_path = candidates[0]
            with zf.open(source_path) as src, open(exe_target, "wb") as dst:
                shutil.copyfileobj(src, dst)

        exe_target.chmod(0o755)

        if not exe_target.exists():
            raise RuntimeError(
                f"[FFMPEG] Error crítico: no se pudo crear {exe_target}"
            )
        print(f"[FFMPEG] ✅ Binario instalado en: {exe_target}")

    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)

    return target_dir


def inject_ffmpeg_path(bin_dir: Optional[Path] = None) -> bool:
    """
    Agrega la carpeta que contiene ``ffmpeg.exe`` al inicio de la variable
    de entorno ``PATH`` para máxima prioridad de resolución.

    Args:
        bin_dir: Ruta del directorio con el binario.
                  Por defecto ``<cwd>/bin/ffmpeg/``.

    Returns:
        True si la inyección fue exitosa; False si el binario no existe.
    """
    if bin_dir is None:
        bin_dir = Path.cwd() / BIN_FFMPEG_DIR
    bin_dir = Path(bin_dir).resolve()

    exe_path = bin_dir / FFMPEG_EXE
    if not exe_path.exists():
        print(f"[FFMPEG] ⚠️  No se encontró {FFMPEG_EXE} en {bin_dir}. Omitiendo.")
        return False

    path_str = str(bin_dir)
    current_path = os.environ.get("PATH", "")

    if path_str not in current_path:
        os.environ["PATH"] = path_str + os.pathsep + current_path
        print(f"[FFMPEG] ✅ Ruta inyectada en PATH: {path_str}")
    else:
        print(f"[FFMPEG] ℹ️  La ruta ya está presente en el PATH.")

    return True


def ensure_ffmpeg() -> bool:
    """
    Orquestador principal de instalación.

    Flujo:
        1. Verificar si ffmpeg ya está disponible.
        2. Si no, y estamos en Windows, descargar el binario estático.
        3. Extraer en ``bin/ffmpeg/``.
        4. Inyectar la ruta en ``os.environ['PATH']``.
        5. Verificación post-instalación.

    Returns:
        True si ffmpeg quedó funcional al finalizar; False en otro caso.
    """
    if is_ffmpeg_available():
        print("[FFMPEG] ✅ FFmpeg ya está disponible en el sistema.")
        return True

    print("[FFMPEG] ⚠️  FFmpeg no encontrado en el sistema.")

    if sys.platform != "win32":
        print("[FFMPEG] ❌ Descarga automática solo soportada en Windows.")
        print("   Instala FFmpeg manualmente: sudo apt install ffmpeg / brew install ffmpeg")
        return False

    try:
        bin_dir = download_and_extract_ffmpeg()
        inject_ffmpeg_path(bin_dir)

        if is_ffmpeg_available():
            print("[FFMPEG] ✅ Instalación y verificación completadas con éxito.")
            return True

        print("[FFMPEG] ⚠️  Instalación finalizada pero ffmpeg no responde.")
        return False

    except Exception as exc:
        print(f"[FFMPEG] ❌ Error durante la instalación: {exc}")
        return False


# ---------------------------------------------------------------------------
# Entry point de prueba
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    success = ensure_ffmpeg()
    sys.exit(0 if success else 1)