@echo off
title Detektiv Pikachu - Helper-Bot

echo ===================================
echo Detektiv Pikachu Helper-Bot Starter
echo ===================================
echo.

REM Prüfe, ob venv existiert
if not exist venv (
    echo FEHLER: Virtuelle Umgebung nicht gefunden!
    echo Bitte führe zuerst start_bots.bat aus, um die Umgebung einzurichten.
    pause
    exit /b 1
)

REM Aktiviere venv
echo Aktiviere virtuelle Umgebung...
call venv\Scripts\activate.bat

REM Starte Helper-Bot
echo Starte Helper-Bot...
python helper_bot.py

pause 