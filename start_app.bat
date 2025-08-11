@echo off
REM Dhan AI Trader - Application Startup Script for Windows
REM Starts both backend (FastAPI) and frontend (React) services automatically.

setlocal enabledelayedexpansion

REM Configuration
set BACKEND_PORT=8000
set FRONTEND_PORT=3001
set PROJECT_ROOT=%~dp0

REM Colors (limited support in Windows CMD)
set RED=[91m
set GREEN=[92m
set YELLOW=[93m
set BLUE=[94m
set CYAN=[96m
set BOLD=[1m
set NC=[0m

echo.
echo %CYAN%%BOLD%
echo ╔══════════════════════════════════════════════════════════════╗
echo ║                    🚀 DHAN AI TRADER 🚀                     ║
echo ║              Enhanced AI Chat ^& Dynamic OI Analysis          ║
echo ╚══════════════════════════════════════════════════════════════╝
echo %NC%

echo %CYAN%🔍 Checking dependencies...%NC%

REM Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo %RED%❌ Python not found%NC%
    pause
    exit /b 1
) else (
    for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
    echo %GREEN%✅ Python !PYTHON_VERSION!%NC%
)

REM Check Node.js
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo %RED%❌ Node.js not found%NC%
    pause
    exit /b 1
) else (
    for /f %%i in ('node --version') do set NODE_VERSION=%%i
    echo %GREEN%✅ Node.js !NODE_VERSION!%NC%
)

REM Check npm
npm --version >nul 2>&1
if %errorlevel% neq 0 (
    echo %RED%❌ npm not found%NC%
    pause
    exit /b 1
) else (
    for /f %%i in ('npm --version') do set NPM_VERSION=%%i
    echo %GREEN%✅ npm !NPM_VERSION!%NC%
)

echo.
echo %CYAN%📦 Installing dependencies...%NC%

REM Install Python dependencies
echo %BLUE%Installing Python dependencies...%NC%
cd /d "%PROJECT_ROOT%"
python -m pip install -r requirements.txt
python -m pip install scikit-learn scipy pandas numpy

REM Install Node.js dependencies
echo %BLUE%Installing Node.js dependencies...%NC%
cd /d "%PROJECT_ROOT%\frontend"
npm install

echo %GREEN%✅ Dependencies installed%NC%
echo.

REM Create logs directory
if not exist "%PROJECT_ROOT%\logs" mkdir "%PROJECT_ROOT%\logs"

echo %BLUE%🚀 Starting backend server...%NC%

REM Start backend
cd /d "%PROJECT_ROOT%\src"
set PYTHONPATH=%PROJECT_ROOT%\src
start "Dhan AI Trader Backend" /min cmd /c "python -m dhan_trader.api.server > ..\logs\backend.log 2>&1"

REM Wait for backend to start
timeout /t 5 /nobreak >nul

REM Check if backend is running (simple check)
netstat -an | find ":%BACKEND_PORT%" >nul
if %errorlevel% equ 0 (
    echo %GREEN%✅ Backend started on http://localhost:%BACKEND_PORT%%NC%
) else (
    echo %YELLOW%⚠️  Backend may still be starting...%NC%
)

echo %BLUE%🚀 Starting frontend server...%NC%

REM Start frontend
cd /d "%PROJECT_ROOT%\frontend"
set REACT_APP_API_URL=http://localhost:%BACKEND_PORT%
set PORT=%FRONTEND_PORT%
start "Dhan AI Trader Frontend" /min cmd /c "npm start > ..\logs\frontend.log 2>&1"

REM Wait for frontend to start
timeout /t 10 /nobreak >nul

echo %GREEN%✅ Frontend starting on http://localhost:%FRONTEND_PORT%%NC%

echo.
echo %CYAN%🌐 Opening browser...%NC%

REM Wait a bit more for services to be ready
timeout /t 3 /nobreak >nul

REM Open browser
start http://localhost:%FRONTEND_PORT%
timeout /t 2 /nobreak >nul
start http://localhost:%BACKEND_PORT%/docs

echo.
echo %GREEN%%BOLD%🎉 Dhan AI Trader is now running!%NC%
echo.
echo %CYAN%📍 Access URLs:%NC%
echo   • Frontend App:       http://localhost:%FRONTEND_PORT%
echo   • Backend API:        http://localhost:%BACKEND_PORT%
echo   • API Documentation:  http://localhost:%BACKEND_PORT%/docs
echo.
echo %CYAN%🎯 Key Features Available:%NC%
echo   • Enhanced AI Chat with Dynamic OI Analysis
echo   • Real-time Options Chain Data
echo   • Machine Learning Pattern Recognition
echo   • Statistical Anomaly Detection
echo   • Natural Language Trading Queries
echo.
echo %CYAN%💬 Try these AI chat queries:%NC%
echo   • "Provide comprehensive dynamic OI analysis"
echo   • "Analyze current OI patterns using machine learning"
echo   • "What's the market sentiment based on OI data?"
echo.
echo %YELLOW%⚠️  Both services are running in separate windows.%NC%
echo %YELLOW%   Close those windows to stop the services.%NC%
echo.
echo %GREEN%✅ Setup complete! Check the opened browser windows.%NC%
echo.
pause
