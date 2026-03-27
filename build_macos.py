#!/usr/bin/env python3
"""
build_macos.py — Empaqueta Trading Journal Pro como app nativa de macOS (.app)

Uso:
    python build_macos.py           # crea la app en esta carpeta del proyecto
    python build_macos.py --desktop # crea la app directamente en ~/Desktop
"""

import argparse
import os
import plistlib
import shutil
import stat
import subprocess
import sys
import tempfile

APP_NAME = "Trading Journal Pro"
APP_BUNDLE = f"{APP_NAME}.app"
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _venv_python() -> str:
    p = os.path.join(PROJECT_DIR, ".venv", "bin", "python")
    return p if os.path.isfile(p) else sys.executable


def _venv_pip() -> str:
    p = os.path.join(PROJECT_DIR, ".venv", "bin", "pip")
    return p if os.path.isfile(p) else os.path.join(os.path.dirname(_venv_python()), "pip")


def _run(cmd: list, **kwargs):
    print("  $", " ".join(cmd))
    subprocess.check_call(cmd, **kwargs)


def _convert_ico_to_icns(ico_path: str, icns_path: str):
    """Convierte un archivo .ico (o cualquier imagen) a .icns usando sips + iconutil."""
    print(f"  Convirtiendo {os.path.basename(ico_path)} → icon.icns…")
    tmp_dir = tempfile.mkdtemp()
    try:
        png      = os.path.join(tmp_dir, "icon.png")
        iconset  = os.path.join(tmp_dir, "icon.iconset")
        os.makedirs(iconset)

        # Paso 1: convertir a PNG
        _run(["sips", "-s", "format", "png", ico_path, "--out", png])

        # Paso 2: generar todos los tamaños requeridos por macOS
        sizes = [16, 32, 128, 256, 512]
        for s in sizes:
            _run(["sips", "-z", str(s), str(s), png,
                  "--out", os.path.join(iconset, f"icon_{s}x{s}.png")])
            _run(["sips", "-z", str(s * 2), str(s * 2), png,
                  "--out", os.path.join(iconset, f"icon_{s}x{s}@2x.png")])

        # Paso 3: empaquetar como .icns
        _run(["iconutil", "-c", "icns", iconset, "-o", icns_path])
        print(f"  ✅ icon.icns generado en assets/")

    finally:
        shutil.rmtree(tmp_dir)


# ─── Steps ────────────────────────────────────────────────────────────────────

def step_install_pywebview():
    print("\n[1/3] Instalando pywebview en el entorno virtual…")
    _run([_venv_pip(), "install", "pywebview", "--quiet"])


def step_create_app_bundle(dest_dir: str) -> str:
    print(f"\n[2/3] Creando bundle '{APP_BUNDLE}'…")

    app_path = os.path.join(dest_dir, APP_BUNDLE)
    if os.path.exists(app_path):
        print(f"  Eliminando bundle anterior en {app_path}")
        shutil.rmtree(app_path)

    contents_dir  = os.path.join(app_path,    "Contents")
    macos_dir     = os.path.join(contents_dir, "MacOS")
    resources_dir = os.path.join(contents_dir, "Resources")
    os.makedirs(macos_dir)
    os.makedirs(resources_dir)

    python_bin  = _venv_python()
    launcher_py = os.path.join(PROJECT_DIR, "launcher.py")

    # --- Shell wrapper ejecutable -------------------------------------------
    shell_script = f"""#!/bin/bash
# Launcher generado por build_macos.py
export PYTHONPATH="{PROJECT_DIR}"
export PYTHONDONTWRITEBYTECODE=1

exec "{python_bin}" "{launcher_py}" "$@"
"""
    exec_path = os.path.join(macos_dir, "trading_journal")
    with open(exec_path, "w", encoding="utf-8") as f:
        f.write(shell_script)
    os.chmod(
        exec_path,
        stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH,
    )

    # --- Info.plist ---------------------------------------------------------
    plist_data = {
        "CFBundleIdentifier":         "com.tradingjournal.pro",
        "CFBundleName":               APP_NAME,
        "CFBundleDisplayName":        APP_NAME,
        "CFBundleExecutable":         "trading_journal",
        "CFBundleVersion":            "2.0.0",
        "CFBundleShortVersionString": "2.0",
        "CFBundlePackageType":        "APPL",
        "CFBundleSignature":          "????",
        "LSMinimumSystemVersion":     "10.14",
        "NSHighResolutionCapable":    True,
        "NSRequiresAquaSystemAppearance": False,  # soporta Dark Mode
        "LSUIElement":                False,
        "CFBundleIconFile":           "AppIcon",
    }
    with open(os.path.join(contents_dir, "Info.plist"), "wb") as f:
        plistlib.dump(plist_data, f)

    # --- Icono: convierte .ico → .icns automáticamente si hace falta --------
    icon_icns = os.path.join(PROJECT_DIR, "assets", "icon.icns")
    icon_ico  = os.path.join(PROJECT_DIR, "assets", "business.ico")

    if not os.path.isfile(icon_icns):
        if os.path.isfile(icon_ico):
            _convert_ico_to_icns(icon_ico, icon_icns)
        else:
            print(f"  ⚠️  No se encontró assets/business.ico ni assets/icon.icns")

    if os.path.isfile(icon_icns):
        shutil.copy2(icon_icns, os.path.join(resources_dir, "AppIcon.icns"))
        print("  Icono copiado al bundle.")
    else:
        print("  (sin icono personalizado)")

    return app_path


def step_verify(app_path: str):
    print("\n[3/3] Verificando bundle…")
    exec_path = os.path.join(app_path, "Contents", "MacOS", "trading_journal")
    assert os.path.isfile(exec_path),    "Ejecutable no encontrado"
    assert os.access(exec_path, os.X_OK), "Ejecutable sin permisos de ejecución"
    plist_path = os.path.join(app_path, "Contents", "Info.plist")
    assert os.path.isfile(plist_path),   "Info.plist no encontrado"
    print("  Bundle válido.")


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Construye Trading Journal Pro como app de macOS"
    )
    parser.add_argument(
        "--desktop",
        action="store_true",
        help="Coloca la app directamente en ~/Desktop",
    )
    parser.add_argument(
        "--dest",
        default=None,
        metavar="DIR",
        help="Directorio de destino (por defecto: carpeta del proyecto)",
    )
    args = parser.parse_args()

    if args.desktop:
        dest = os.path.expanduser("~/Desktop")
    elif args.dest:
        dest = os.path.abspath(args.dest)
    else:
        dest = PROJECT_DIR

    print("=" * 60)
    print(f"  Build: {APP_NAME}")
    print(f"  Destino: {dest}")
    print("=" * 60)

    step_install_pywebview()
    app_path = step_create_app_bundle(dest)
    step_verify(app_path)

    print("\n" + "=" * 60)
    print(f"  ✅  App creada correctamente:")
    print(f"      {app_path}")
    print()
    print("  Para abrir ahora mismo:")
    print(f'      open "{app_path}"')
    print()
    if not args.desktop:
        print("  O ejecútalo con --desktop para moverla al Escritorio:")
        print("      python build_macos.py --desktop")
    print("=" * 60)


if __name__ == "__main__":
    main()