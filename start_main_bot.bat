@echo off
title Detektiv Pikachu - Haupt-Bot

echo ===================================
echo Detektiv Pikachu Haupt-Bot Starter
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

REM Starte Haupt-Bot
echo Starte Haupt-Bot...
python main.py

pause 