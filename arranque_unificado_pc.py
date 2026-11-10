import os
import sys
import time
import socket
import subprocess
import webbrowser

PYTHONW_EXE = r"C:\Users\guill\AppData\Local\Programs\Python\Python314\pythonw.exe"
if not os.path.exists(PYTHONW_EXE):
    _py_dir = os.path.dirname(sys.executable) if sys.executable else ""
    _cand = os.path.join(_py_dir, "pythonw.exe")
    PYTHONW_EXE = _cand if os.path.exists(_cand) else sys.executable

ROBOT_DIR = r"D:\OneDrive\04_Desarrollo_proyectos\2026_Proyecto_RobotOrganizador"
RUNNER_SCRIPT = os.path.join(ROBOT_DIR, "run_uvicorn_hidden.py")
ESIOS_SCRIPTS_DIR = r"D:\OneDrive\04_Desarrollo_proyectos\2026_Proyecto_Energia_Graficos\02_Scripts_Python"
ESIOS_SCRIPT = os.path.join(ESIOS_SCRIPTS_DIR, "00_DASHBOARD_ACTUALIZADOR.py")

# DETACHED_PROCESS (0x00000008) | CREATE_NEW_PROCESS_GROUP (0x00000200) | CREATE_NO_WINDOW (0x08000000)
HIDDEN_FLAGS = 0x00000008 | 0x00000200 | 0x08000000


def is_port_open(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.5):
            return True
    except OSError:
        return False


def wait_for_port(port: int, timeout_s: float = 12.0) -> bool:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if is_port_open(port):
            return True
        time.sleep(0.3)
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
    is_boot = "--boot" in sys.argv
    if is_boot:
        # Breve pausa tras iniciar sesión para que Docker/red/OneDrive terminen de estabilizarse
        time.sleep(5)

    # 1. Arrancar Actualizador Maestro ESIOS (:8050) en segundo plano oculto (sin ventana CMD ni pestaña extra)
    if not is_port_open(8050) and os.path.exists(ESIOS_SCRIPT):
        if is_boot:
            wait_for_port(5432, timeout_s=15.0)
        start_hidden_process(
            [PYTHONW_EXE, ESIOS_SCRIPT, "--autostart", "--no-browser"],
            ESIOS_SCRIPTS_DIR
        )
        wait_for_port(8050, timeout_s=10.0)

    # 2. Arrancar Robot de Gestión de Proyectos (:8002) en segundo plano oculto (pythonw.exe)
    if not is_port_open(8002):
        start_hidden_process(
            [PYTHONW_EXE, RUNNER_SCRIPT, "--app", "app.main:app", "--host", "127.0.0.1", "--port", "8002"],
            ROBOT_DIR
        )
        wait_for_port(8002, timeout_s=10.0)

    # 3. Abrir únicamente el Robot Organizador en el navegador (desde ahí se ve Consola CMD & Tareas)
    try:
        os.startfile("http://localhost:8002")
        if "--open-all" in sys.argv:
            os.startfile("http://127.0.0.1:8050")
    except Exception:
        webbrowser.open("http://localhost:8002")


if __name__ == "__main__":
    main()
