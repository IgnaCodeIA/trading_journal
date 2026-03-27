"""
launcher.py — Lanzador de Trading Journal Pro como app de escritorio macOS.
Arranca Streamlit en un puerto libre y abre una ventana nativa con pywebview.
"""

import os
import sys
import socket
import subprocess
import time
import threading

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def wait_for_server(port: int, timeout: int = 40) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection(("localhost", port), timeout=1):
                return True
        except OSError:
            time.sleep(0.4)
    return False


def find_streamlit() -> str:
    candidates = [
        os.path.join(PROJECT_DIR, ".venv", "bin", "streamlit"),
        os.path.join(os.path.dirname(sys.executable), "streamlit"),
        "streamlit",
    ]
    for c in candidates:
        if os.path.isfile(c) and os.access(c, os.X_OK):
            return c
    return "streamlit"


def main():
    try:
        import webview
    except ImportError:
        print("[Trading Journal] pywebview no encontrado. Instalando…")
        pip = os.path.join(PROJECT_DIR, ".venv", "bin", "pip")
        if not os.path.isfile(pip):
            pip = os.path.join(os.path.dirname(sys.executable), "pip")
        subprocess.check_call([pip, "install", "pywebview", "--quiet"])
        import webview

    port = find_free_port()
    streamlit_bin = find_streamlit()
    app_script = os.path.join(PROJECT_DIR, "app.py")

    env = os.environ.copy()
    env["PYTHONPATH"] = PROJECT_DIR

    proc = subprocess.Popen(
        [
            streamlit_bin, "run", app_script,
            "--server.port", str(port),
            "--server.headless", "true",
            "--server.enableCORS", "false",
            "--server.enableXsrfProtection", "false",
            "--browser.gatherUsageStats", "false",
        ],
        cwd=PROJECT_DIR,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    def _shutdown():
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()

    if not wait_for_server(port, timeout=45):
        _shutdown()
        sys.exit(1)

    window = webview.create_window(
        title="Trading Journal Pro",
        url=f"http://localhost:{port}",
        width=1440,
        height=920,
        min_size=(900, 650),
        background_color="#0d1117",
    )

    window.events.closed += _shutdown

    webview.start(debug=False)

    _shutdown()


if __name__ == "__main__":
    main()
