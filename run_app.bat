@echo off
title Smart Academic ERP - Master Launcher
echo ==============================================================
echo   Launching Smart Academic ERP (Backend + Web + Mobile)
echo ==============================================================
echo.

:: 1. Start FastAPI Backend Server
echo [1/3] Starting Backend Server (Port 8000)...
start "FastAPI Backend (Port 8000)" cmd /k "call venv\Scripts\activate.bat && set PYTHONPATH=backend && python backend/manage.py runserver --port 8000"

timeout /t 2 /nobreak >nul

:: 2. Start React Web Dashboard
echo [2/3] Starting Web Admin Dashboard (Port 3000)...
start "React Web Dashboard (Port 3000)" cmd /k "cd web-dashboard && npm run dev -- --port 3000"

timeout /t 2 /nobreak >nul

:: 3. Start Expo Mobile App
echo [3/3] Starting Expo Mobile App (Port 8081)...
start "Expo Mobile App (Port 8081)" cmd /k "cd mobile-app && npx expo start"

echo.
echo ==============================================================
echo   ALL SERVERS LAUNCHED SUCCESSFULLY!
echo ==============================================================
echo   - Backend API Docs : http://localhost:8000/api/docs
echo   - Web Admin Portal : http://localhost:3000
echo   - Mobile App Dev   : http://localhost:8081
echo ==============================================================
echo.
pause