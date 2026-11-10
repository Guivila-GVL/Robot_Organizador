import os
import sys
import time
import socket
import subprocess
import webbrowser

WORKSPACE_DIR = r"D:\OneDrive\04_Desarrollo_proyectos\2026_Proyecto_RobotOrganizador"
RUNNER_SCRIPT = os.path.join(WORKSPACE_DIR, "run_uvicorn_hidden.py")
ESIOS_SCRIPTS_DIR = r"D:\OneDrive\04_Desarrollo_proyectos\2026_Proyecto_Energia_Graficos\02_Scripts_Python"
ESIOS_SCRIPT = os.path.join(ESIOS_SCRIPTS_DIR, "00_DASHBOARD_ACTUALIZADOR.py")

PYTHONW_EXE = r"C:\Users\guill\AppData\Local\Programs\Python\Python314\pythonw.exe"
if not os.path.exists(PYTHONW_EXE):
    _py_dir = os.path.dirname(sys.executable) if sys.executable else ""
    _cand = os.path.join(_py_dir, "pythonw.exe")
    PYTHONW_EXE = _cand if os.path.exists(_cand) else sys.executable

PORT = 8002
URL = f"http://localhost:{PORT}"

# Flags para subprocesos totalmente ocultos en Windows:
# DETACHED_PROCESS (0x00000008) | CREATE_NEW_PROCESS_GROUP (0x00000200) | CREATE_NO_WINDOW (0x08000000)
HIDDEN_FLAGS = 0x00000008 | 0x00000200 | 0x08000000


def is_port_open(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.4):
            return True
    except OSError:
        return False


def start_hidden_process(args_list: list, cwd: str) -> None:
    subprocess.Popen(
        args_list,
        cwd=cwd,
        creationflags=HIDDEN_FLAGS,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        close_fds=True
    )


def main():
    # 1. Asegurar que el Robot de Gestión (:8002) esté corriendo en modo oculto (pythonw.exe)
    if not is_port_open(PORT):
        start_hidden_process(
            [PYTHONW_EXE, RUNNER_SCRIPT, "--app", "app.main:app", "--host", "127.0.0.1", "--port", str(PORT)],
            WORKSPACE_DIR
        )
        for _ in range(40):
            if is_port_open(PORT):
                break
            time.sleep(0.25)

    # 2. Asegurar que el servicio de Energía ESIOS (:8050) esté activo en segundo plano (sin abrir pestaña ni ventana CMD)
    if not is_port_open(8050) and os.path.exists(ESIOS_SCRIPT):
        start_hidden_process(
            [PYTHONW_EXE, ESIOS_SCRIPT, "--no-browser"],
            ESIOS_SCRIPTS_DIR
        )

    # 3. Abrir interfaz web del Robot Organizador
    try:
        os.startfile(URL)
    except Exception:
        webbrowser.open(URL)


if __name__ == "__main__":
    main()
