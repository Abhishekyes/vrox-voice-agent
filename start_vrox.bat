@echo off
:: ============================================================================
:: Vrox one-click launcher (Windows)
::
:: Double-click this file. It will (only the first time, skipped on later
:: runs): check for Python/Ollama, create a virtual environment, install
:: dependencies, pull the local AI model, then start Vrox in fully
:: hands-free mode — after this window opens, just start talking. No
:: further clicking needed.
:: ============================================================================
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo.
echo  ==========================================
echo    Starting Vrox - your voice companion
echo  ==========================================
echo.

:: --- 1. Check Python ---
where python >nul 2>nul
if errorlevel 1 (
    echo [Vrox] Python not found. Attempting to install it via winget...
    winget install -e --id Python.Python.3.11 --silent --accept-package-agreements --accept-source-agreements
    if errorlevel 1 (
        echo.
        echo [Vrox] Could not auto-install Python. Please install Python 3.10+
        echo        from https://python.org, tick "Add to PATH", then re-run this file.
        pause
        exit /b 1
    )
)

:: --- 2. Check Ollama (the free local AI brain) ---
where ollama >nul 2>nul
if errorlevel 1 (
    echo [Vrox] Ollama not found. Attempting to install it via winget...
    winget install -e --id Ollama.Ollama --silent --accept-package-agreements --accept-source-agreements
    if errorlevel 1 (
        echo.
        echo [Vrox] Could not auto-install Ollama. Please install it manually
        echo        from https://ollama.com, then re-run this file.
        pause
        exit /b 1
    )
)

:: --- 3. Create the virtual environment (once) ---
if not exist ".venv" (
    echo [Vrox] Setting up Python environment for the first time...
    python -m venv .venv
)
call ".venv\Scripts\activate.bat"

:: --- 4. Install dependencies (once, tracked by a marker file) ---
if not exist ".venv\.deps_installed" (
    echo [Vrox] Installing dependencies, this happens only once...
    python -m pip install --upgrade pip >nul
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [Vrox] Dependency install failed - check the messages above.
        pause
        exit /b 1
    )
    echo done > ".venv\.deps_installed"
)

:: --- 5. Create .env from the example, once ---
if not exist ".env" (
    copy ".env.example" ".env" >nul
)

:: --- 6. Make sure the Ollama background service is running ---
tasklist /FI "IMAGENAME eq ollama.exe" 2>nul | find /I "ollama.exe" >nul
if errorlevel 1 (
    echo [Vrox] Starting the local AI service in the background...
    start "" /min ollama serve
    timeout /t 3 /nobreak >nul
)

:: --- 7. Pull the local LLM model (once — a few GB, only the first time) ---
ollama list | findstr /I "qwen2.5:7b-instruct" >nul
if errorlevel 1 (
    echo [Vrox] Downloading Vrox's local AI brain the first time - this can
    echo        take a few minutes depending on your internet speed...
    ollama pull qwen2.5:7b-instruct
)

:: --- 8. Launch Vrox - fully hands-free, no more clicking needed ---
echo.
echo [Vrox] All set! Starting up...
echo.
python vrox_cli.py

pause
