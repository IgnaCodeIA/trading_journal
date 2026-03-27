#!/usr/bin/env python3
"""
build_windows.py — Empaqueta Trading Journal Pro como acceso directo de Windows
y, opcionalmente, como ejecutable .exe con PyInstaller.

Uso (desde PowerShell o CMD, con el venv activo o sin él):
    python build_windows.py              # acceso directo en carpeta del proyecto
    python build_windows.py --desktop    # acceso directo en Escritorio
    python build_windows.py --exe        # genera TradingJournalPro.exe con PyInstaller
    python build_windows.py --desktop --exe
"""

import argparse
import os
import shutil
import subprocess
import sys

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
APP_NAME    = "Trading Journal Pro"


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _venv_python() -> str:
    p = os.path.join(PROJECT_DIR, ".venv", "Scripts", "python.exe")
    return p if os.path.isfile(p) else sys.executable


def _venv_pip() -> str:
    p = os.path.join(PROJECT_DIR, ".venv", "Scripts", "pip.exe")
    return p if os.path.isfile(p) else os.path.join(os.path.dirname(_venv_python()), "pip.exe")


def _run(cmd: list, **kwargs):
    print("  $", " ".join(cmd))
    subprocess.check_call(cmd, **kwargs)


def _desktop_path() -> str:
    import ctypes
    buf = ctypes.create_unicode_buffer(260)
    ctypes.windll.shell32.SHGetFolderPathW(None, 0x0000, None, 0, buf)  # CSIDL_DESKTOP
    return buf.value if buf.value else os.path.expanduser("~/Desktop")


def _ensure_icon() -> str:
    """
    Devuelve la ruta a assets/icon.ico lista para usar.
    Si ya existe icon.ico lo devuelve directamente.
    Si existe business.ico lo copia como icon.ico.
    Devuelve "" si no hay ningún icono disponible.
    """
    assets_dir   = os.path.join(PROJECT_DIR, "assets")
    icon_ico     = os.path.join(assets_dir, "icon.ico")
    business_ico = os.path.join(assets_dir, "business.ico")

    if os.path.isfile(icon_ico):
        print("  Icono encontrado: assets/icon.ico")
        return icon_ico

    if os.path.isfile(business_ico):
        print("  Usando assets/business.ico como icono…")
        shutil.copy2(business_ico, icon_ico)
        print("  ✅ Copiado como assets/icon.ico")
        return icon_ico

    print("  ⚠️  No se encontró assets/business.ico ni assets/icon.ico — sin icono personalizado.")
    return ""


# ─── Steps ────────────────────────────────────────────────────────────────────

def step_install_pywebview():
    print("\n[1] Instalando pywebview en el entorno virtual…")
    _run([_venv_pip(), "install", "pywebview", "--quiet"])


def step_create_bat(dest_dir: str) -> str:
    """Crea un .bat que activa el venv y lanza el launcher sin ventana de consola."""
    print(f"\n[2] Creando lanzador .bat en {dest_dir}…")

    python_bin  = _venv_python()
    launcher_py = os.path.join(PROJECT_DIR, "launcher.py")

    pythonw = python_bin.replace("python.exe", "pythonw.exe")
    if not os.path.isfile(pythonw):
        pythonw = python_bin   # fallback: con consola visible

    bat_content = f"""@echo off
set PYTHONPATH={PROJECT_DIR}
set PYTHONDONTWRITEBYTECODE=1
start "" "{pythonw}" "{launcher_py}"
"""
    bat_path = os.path.join(dest_dir, f"{APP_NAME}.bat")
    with open(bat_path, "w", encoding="utf-8") as f:
        f.write(bat_content)
    print(f"  Creado: {bat_path}")
    return bat_path


def step_create_shortcut(bat_path: str, dest_dir: str, icon_path: str) -> str:
    """Crea un acceso directo .lnk apuntando al .bat usando PowerShell."""
    print(f"\n[3] Creando acceso directo .lnk en {dest_dir}…")

    lnk_path = os.path.join(dest_dir, f"{APP_NAME}.lnk")

    ps_script = (
        f'$ws = New-Object -ComObject WScript.Shell; '
        f'$s = $ws.CreateShortcut("{lnk_path}"); '
        f'$s.TargetPath = "{bat_path}"; '
        f'$s.WorkingDirectory = "{PROJECT_DIR}"; '
        f'$s.WindowStyle = 7; '
        f'$s.Description = "{APP_NAME}"; '
        f'$s.Save()'
    )

    if icon_path:
        ps_script = ps_script.replace(
            "$s.Save()",
            f'$s.IconLocation = "{icon_path}"; $s.Save()',
        )

    try:
        subprocess.check_call(
            ["powershell", "-NoProfile", "-Command", ps_script],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        print(f"  Creado: {lnk_path}")
    except Exception as e:
        print(f"  Aviso: no se pudo crear el .lnk con PowerShell ({e}).")
        print(f"  Puedes crear el acceso directo manualmente apuntando a: {bat_path}")
        lnk_path = bat_path

    return lnk_path


def step_build_exe(icon_path: str) -> str:
    """Usa PyInstaller para crear un .exe standalone del launcher."""
    print("\n[4] Construyendo .exe con PyInstaller…")

    try:
        _run([_venv_pip(), "install", "pyinstaller", "--quiet"])
    except Exception as e:
        print(f"  Error instalando PyInstaller: {e}")
        return ""

    launcher_py = os.path.join(PROJECT_DIR, "launcher.py")
    dist_dir    = os.path.join(PROJECT_DIR, "dist")
    icon_arg    = [f"--icon={icon_path}"] if icon_path else []

    python_bin   = _venv_python()
    pyinstaller  = os.path.join(os.path.dirname(python_bin), "pyinstaller.exe")
    if not os.path.isfile(pyinstaller):
        pyinstaller = "pyinstaller"

    try:
        _run([
            pyinstaller,
            "--onefile",
            "--windowed",
            "--name", APP_NAME,
            "--distpath", dist_dir,
            "--workpath", os.path.join(PROJECT_DIR, "build"),
            "--specpath", os.path.join(PROJECT_DIR, "build"),
            f"--add-data={PROJECT_DIR};.",
            *icon_arg,
            launcher_py,
        ])
        exe_path = os.path.join(dist_dir, f"{APP_NAME}.exe")
        print(f"  Ejecutable: {exe_path}")
        return exe_path
    except Exception as e:
        print(f"  Error en PyInstaller: {e}")
        return ""


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    if sys.platform != "win32":
        print("AVISO: build_windows.py está diseñado para ejecutarse en Windows.")
        print("En macOS/Linux usa build_macos.py en su lugar.")
        print("Continuando de todas formas para generar los archivos de texto…\n")

    parser = argparse.ArgumentParser(
        description=f"Construye '{APP_NAME}' como app de escritorio Windows"
    )
    parser.add_argument("--desktop", action="store_true",
                        help="Coloca el acceso directo en el Escritorio de Windows")
    parser.add_argument("--exe",     action="store_true",
                        help="Genera un .exe con PyInstaller (requiere más tiempo)")
    parser.add_argument("--dest",    default=None, metavar="DIR",
                        help="Directorio de destino (por defecto: carpeta del proyecto)")
    args = parser.parse_args()

    if args.desktop and sys.platform == "win32":
        dest = _desktop_path()
    elif args.dest:
        dest = os.path.abspath(args.dest)
    else:
        dest = PROJECT_DIR

    print("=" * 60)
    print(f"  Build: {APP_NAME}")
    print(f"  Destino acceso directo: {dest}")
    print(f"  Crear .exe: {'sí' if args.exe else 'no'}")
    print("=" * 60)

    step_install_pywebview()

    # Resuelve el icono una sola vez y lo reutiliza en todos los pasos
    icon_path = _ensure_icon()

    bat_path = step_create_bat(dest)

    shortcut_path = bat_path
    if sys.platform == "win32":
        shortcut_path = step_create_shortcut(bat_path, dest, icon_path)

    exe_path = ""
    if args.exe:
        exe_path = step_build_exe(icon_path)

    print("\n" + "=" * 60)
    print("  ✅  Build completado:")
    if sys.platform == "win32":
        print(f"      Acceso directo : {shortcut_path}")
    print(f"      Lanzador .bat   : {bat_path}")
    if exe_path:
        print(f"      Ejecutable .exe : {exe_path}")
    print()
    print("  Para abrir la app haz doble clic en el acceso directo,")
    print("  o ejecuta directamente el .bat.")
    print()
    if not args.desktop:
        print("  Para instalar en el Escritorio vuelve a ejecutar con --desktop:")
        print("      python build_windows.py --desktop")
    print("=" * 60)


if __name__ == "__main__":
    main()