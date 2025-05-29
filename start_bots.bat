@echo off
title Detektiv Pikachu Bot Starter

echo ===================================
echo Detektiv Pikachu Bot - Startskript
echo ===================================
echo.

REM Prüfe, ob Python installiert ist
python --version > NUL 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo FEHLER: Python ist nicht installiert oder nicht im PATH.
    echo Bitte installieren Sie Python 3.8 oder höher.
    pause
    exit /b 1
)

REM Prüfe, ob venv existiert, falls nicht, erstelle es
if not exist venv (
    echo Virtuelle Umgebung nicht gefunden. Erstelle neue venv...
    python -m venv venv
    if %ERRORLEVEL% NEQ 0 (
        echo FEHLER: Konnte virtuelle Umgebung nicht erstellen.
        pause
        exit /b 1
    )
    echo Virtuelle Umgebung erfolgreich erstellt.
) else (
    echo Bestehende virtuelle Umgebung gefunden.
)

REM Aktiviere venv
echo Aktiviere virtuelle Umgebung...
call venv\Scripts\activate.bat

REM Installiere/Aktualisiere Abhängigkeiten
echo Installiere/Aktualisiere Abhängigkeiten...
pip install -r requirements.txt
if %ERRORLEVEL% NEQ 0 (
    echo FEHLER: Konnte Abhängigkeiten nicht installieren.
    pause
    exit /b 1
)

echo.
echo ===================================
echo Installation erfolgreich abgeschlossen
echo ===================================
echo.

REM Starte Bots in separaten Fenstern
echo Starte Bots...
start "Detektiv Pikachu - Haupt-Bot" cmd /c "venv\Scripts\python.exe main.py"
start "Detektiv Pikachu - Helper-Bot" cmd /c "venv\Scripts\python.exe helper_bot.py"

echo.
echo Beide Bots wurden gestartet. Du kannst dieses Fenster jetzt schließen.
echo.
pause 