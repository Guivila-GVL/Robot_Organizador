import os
import sys
import time
import socket
import subprocess
import webbrowser

WORKSPACE_DIR = r"D:\OneDrive\04_Desarrollo_proyectos\2026_Proyecto_RobotOrganizador"
PYTHON_EXE = r"C:\Users\guill\AppData\Local\Programs\Python\Python314\python.exe"
if not os.path.exists(PYTHON_EXE):
    PYTHON_EXE = sys.executable

PORT = 8002
URL = f"http://localhost:{PORT}"


def is_port_open(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.5):
            return True
    except OSError:
        return False


def start_detached_wmi():
    cmd_line = f'"{PYTHON_EXE}" -m uvicorn app.main:app --host 127.0.0.1 --port {PORT}'
    ps_cmd = (
        f"$si = New-CimInstance -ClassName Win32_ProcessStartup -ClientOnly; "
        f"$si.ShowWindow = 0; "
        f"Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{{ "
        f"CommandLine = '{cmd_line}'; CurrentDirectory = '{WORKSPACE_DIR}'; ProcessStartupInformation = $si }}"
    )
    subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True)


def main():
    if not is_port_open(PORT):
        start_detached_wmi()
        for _ in range(40):
            if is_port_open(PORT):
                break
            time.sleep(0.25)

    try:
        os.startfile(URL)
    except Exception:
        webbrowser.open(URL)


if __name__ == "__main__":
    main()
