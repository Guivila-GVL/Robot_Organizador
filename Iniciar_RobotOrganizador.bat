@echo off
title Robot Organizador 2026 - Centro de Mando
color 0D
echo ========================================================
echo   ROBOT ORGANIZADOR 2026
echo   Control de Tareas Multi-Proyecto & Telegram
echo ========================================================
echo.
cd /d "%~dp0"

echo [1/2] Abriendo navegador en http://localhost:8002...
start "" http://localhost:8002

echo [2/2] Iniciando servidor local en http://127.0.0.1:8002...
python -m uvicorn app.main:app --host 127.0.0.1 --port 8002 --reload

pause
