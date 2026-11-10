@echo off
rem Inicia el Robot de Gestion en segundo plano (sin ventana CMD persistente)
cd /d "%~dp0"
start "" "C:\Users\guill\AppData\Local\Programs\Python\Python314\pythonw.exe" "lanzador_escritorio.py"
