import os
import sys
import time
import socket
import subprocess
import webbrowser

PYTHON_EXE = r"C:\Users\guill\AppData\Local\Programs\Python\Python314\python.exe"
if not os.path.exists(PYTHON_EXE):
    PYTHON_EXE = sys.executable

ROBOT_DIR = r"D:\OneDrive\04_Desarrollo_proyectos\2026_Proyecto_RobotOrganizador"
ESIOS_SCRIPTS_DIR = r"D:\OneDrive\04_Desarrollo_proyectos\2026_Proyecto_Energia_Graficos\02_Scripts_Python"
ESIOS_SCRIPT = os.path.join(ESIOS_SCRIPTS_DIR, "00_DASHBOARD_ACTUALIZADOR.py")


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


def start_detached_process(cmd_line: str, cwd: str) -> None:
    ps_cmd = (
        f"$si = New-CimInstance -ClassName Win32_ProcessStartup -ClientOnly; "
        f"$si.ShowWindow = 0; "
        f"Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{{ "
        f"CommandLine = '{cmd_line}'; CurrentDirectory = '{cwd}'; ProcessStartupInformation = $si }}"
    )
    subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True)


def main():
    is_boot = "--boot" in sys.argv
    if is_boot:
        # Breve pausa tras iniciar sesión para que Docker/red/OneDrive terminen de estabilizarse
        time.sleep(5)

    # 1. Arrancar Actualizador Maestro ESIOS (:8050) si no está en marcha
    esios_started_now = False
    if not is_port_open(8050) and os.path.exists(ESIOS_SCRIPT):
        # Si viene de arranque de PC, esperamos hasta 15s por si Postgres/Docker está subiendo
        if is_boot:
            wait_for_port(5432, timeout_s=15.0)
        cmd_esios = f'"{PYTHON_EXE}" "{ESIOS_SCRIPT}" --autostart'
        start_detached_process(cmd_esios, ESIOS_SCRIPTS_DIR)
        wait_for_port(8050, timeout_s=10.0)
        esios_started_now = True

    # 2. Arrancar Robot de Gestión de Proyectos (:8002) si no está en marcha
    if not is_port_open(8002):
        cmd_robot = f'"{PYTHON_EXE}" -m uvicorn app.main:app --host 127.0.0.1 --port 8002'
        start_detached_process(cmd_robot, ROBOT_DIR)
        wait_for_port(8002, timeout_s=10.0)

    # 3. Abrir Robot Organizador en el navegador (ESIOS ya abre su pestaña al arrancar si no estaba abierto)
    try:
        os.startfile("http://localhost:8002")
        if not esios_started_now and "--open-all" in sys.argv:
            os.startfile("http://127.0.0.1:8050")
    except Exception:
        webbrowser.open("http://localhost:8002")


if __name__ == "__main__":
    main()

