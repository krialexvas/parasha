@echo off
REM Telegram News Bot Startup Script for Windows
REM Place this file in the news_bot directory and run it

cd /d "%~dp0"

echo ========================================
echo   Telegram News Bot - Starting...
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python from https://python.org
    pause
    exit /b 1
)

REM Check if dependencies are installed
echo Checking dependencies...
python -c "import telethon" >nul 2>&1
if errorlevel 1 (
    echo Installing dependencies...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo ERROR: Failed to install dependencies
        pause
        exit /b 1
    )
)

REM Check configuration
echo.
echo Checking configuration...
python -c "from config import TELEGRAM_BOT_TOKEN; print('Config OK')" >nul 2>&1
if errorlevel 1 (
    echo WARNING: Configuration may need attention
    echo Please edit config.py with your API keys
)

REM Start the bot
echo.
echo Starting bot...
echo Press Ctrl+C to stop
echo.

python bot.py

pause
