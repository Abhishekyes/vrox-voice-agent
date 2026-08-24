#!/usr/bin/env bash
# ==============================================================================
# Vrox one-click launcher (macOS / Linux)
#
# Run this file (double-click if your file manager runs .sh scripts, or
# `./start_vrox.sh` in a terminal). It will, only the first time: check for
# Python/Ollama, create a virtual environment, install dependencies, pull
# the local AI model, then start Vrox in fully hands-free mode — after
# this opens, just start talking. No further clicking needed.
# ==============================================================================
set -e
cd "$(dirname "$0")"

echo ""
echo " =========================================="
echo "   Starting Vrox - your voice companion"
echo " =========================================="
echo ""

# --- 1. Check Python ---
if ! command -v python3 >/dev/null 2>&1; then
    echo "[Vrox] Python 3 not found."
    if command -v brew >/dev/null 2>&1; then
        echo "[Vrox] Installing Python via Homebrew..."
        brew install python
    else
        echo "[Vrox] Please install Python 3.10+ from https://python.org and re-run this script."
        exit 1
    fi
fi

# --- 2. Check Ollama ---
if ! command -v ollama >/dev/null 2>&1; then
    echo "[Vrox] Ollama not found."
    if command -v brew >/dev/null 2>&1; then
        echo "[Vrox] Installing Ollama via Homebrew..."
        brew install ollama
    else
        echo "[Vrox] Please install Ollama from https://ollama.com and re-run this script."
        exit 1
    fi
fi

# --- 3. Create the virtual environment (once) ---
if [ ! -d ".venv" ]; then
    echo "[Vrox] Setting up Python environment for the first time..."
    python3 -m venv .venv
fi
source .venv/bin/activate

# --- 4. Install dependencies (once, tracked by a marker file) ---
if [ ! -f ".venv/.deps_installed" ]; then
    echo "[Vrox] Installing dependencies, this happens only once..."
    pip install --upgrade pip >/dev/null
    pip install -r requirements.txt
    touch .venv/.deps_installed
fi

# --- 5. Create .env from the example, once ---
if [ ! -f ".env" ]; then
    cp .env.example .env
fi

# --- 6. Make sure the Ollama background service is running ---
if ! pgrep -x "ollama" >/dev/null 2>&1; then
    echo "[Vrox] Starting the local AI service in the background..."
    ollama serve >/dev/null 2>&1 &
    sleep 3
fi

# --- 7. Pull the local LLM model (once — a few GB, only the first time) ---
if ! ollama list | grep -qi "qwen2.5:7b-instruct"; then
    echo "[Vrox] Downloading Vrox's local AI brain the first time - this can"
    echo "       take a few minutes depending on your internet speed..."
    ollama pull qwen2.5:7b-instruct
fi

# --- 8. Launch Vrox - fully hands-free, no more clicking needed ---
echo ""
echo "[Vrox] All set! Starting up..."
echo ""
python3 vrox_cli.py
