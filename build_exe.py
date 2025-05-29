#!/usr/bin/env python3
"""
Build-Skript für Detektiv Pikachu Discord Bot
Erstellt Windows EXE-Dateien mit PyInstaller
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path
import io

def clean_build_dirs():
    """Bereinigt alte Build-Verzeichnisse"""
    dirs_to_clean = ['dist', 'build', '__pycache__']
    
    for dir_name in dirs_to_clean:
        dir_path = Path(dir_name)
        if dir_path.exists():
            shutil.rmtree(dir_path)
            print(f"[CLEAN] {dir_name}/ geloescht")
    
    # Spec-Dateien löschen
    spec_files = ['launcher.spec']
    for spec_file in spec_files:
        spec_path = Path(spec_file)
        if spec_path.exists():
            spec_path.unlink()
            print(f"[CLEAN] {spec_file} geloescht")

def create_spec_files():
    """Erstellt PyInstaller .spec Datei für den Launcher"""
    
    # Launcher Spec (startet beide Bots)
    launcher_spec = """
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['launcher.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('cogs', 'cogs'),
        ('config', 'config'),
        ('core', 'core'),
        ('utils', 'utils'),
        ('bot_status.py', '.'),
        ('main.py', '.'),
        ('helper_bot.py', '.'),
        ('.env.example', '.'),
        ('README.md', '.'),
        ('LICENSE', '.'),
    ],
    hiddenimports=[
        'discord',
        'discord.ext.commands',
        'asyncio',
        'pathlib',
        'logging',
        'json',
        'os',
        'time',
        'datetime',
        'aiohttp',
        'threading',
        'subprocess',
        'multiprocessing',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='DetektivPikachu-Launcher',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='detective_pikachu_bot_icon.ico' if os.path.exists('detective_pikachu_bot_icon.ico') else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='DetektivPikachu-Launcher',
)
"""

    with open('launcher.spec', 'w', encoding='utf-8') as f:
        f.write(launcher_spec)
    
    print("[SPEC] Launcher.spec Datei erstellt")

def build_executables():
    """Erstellt die Launcher-EXE-Datei mit PyInstaller"""
    
    print("[BUILD] Starte EXE-Build-Prozess...")
    
    # Nur Launcher bauen (All-in-One EXE)
    print("[BUILD] Baue Detektiv Pikachu Launcher (All-in-One)...")
    result = subprocess.run([
        sys.executable, '-m', 'PyInstaller',
        '--clean',
        'launcher.spec'
    ], capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"[ERROR] Fehler beim Bauen des Launchers: {result.stderr}")
        return False
    
    print("[SUCCESS] Launcher-EXE erfolgreich erstellt!")
    return True

def create_release_package():
    """Erstellt ein minimales Release-Paket"""
    
    release_dir = Path('release')
    if release_dir.exists():
        shutil.rmtree(release_dir)
    
    release_dir.mkdir()
    
    # Haupt-Launcher kopieren
    launcher_exe_dir = Path('dist/DetektivPikachu-Launcher')
    if launcher_exe_dir.exists():
        # Kopiere die EXE direkt ins Release-Verzeichnis
        shutil.copy(launcher_exe_dir / 'DetektivPikachu-Launcher.exe', release_dir / 'DetektivPikachu.exe')
        
        # Kopiere notwendige DLLs/Dependencies
        for file in launcher_exe_dir.glob('*'):
            if file.is_file() and file.name != 'DetektivPikachu-Launcher.exe':
                shutil.copy(file, release_dir / file.name)
        
        # Kopiere _internal Verzeichnis falls vorhanden
        internal_dir = launcher_exe_dir / '_internal'
        if internal_dir.exists():
            shutil.copytree(internal_dir, release_dir / '_internal')
    
    # Konfigurationsverzeichnis erstellen
    config_dir = release_dir / 'config'
    data_dir = release_dir / 'data'
    
    config_dir.mkdir()
    data_dir.mkdir()
    (data_dir / 'json').mkdir()
    (data_dir / 'logs').mkdir()
    (data_dir / 'gif').mkdir()
    
    # Nur notwendige Dateien kopieren
    if Path('.env.example').exists():
        shutil.copy('.env.example', config_dir / '.env.example')
    shutil.copy('README.md', release_dir / 'README.md')
    shutil.copy('LICENSE', release_dir / 'LICENSE')
    
    # Einfaches Start-Skript erstellen
    create_simple_start_script(release_dir)
    
    print(f"[PACKAGE] Minimales Release-Paket erstellt in: {release_dir}")
    return release_dir

def create_simple_start_script(release_dir):
    """Erstellt ein einfaches Start-Skript"""
    
    start_script = '''@echo off
title Detektiv Pikachu - Discord Bot
echo ===================================
echo     Detektiv Pikachu Discord Bot
echo ===================================
echo.

REM Prüfe, ob .env-Datei existiert
if not exist "config\\.env" (
    echo WARNUNG: .env-Datei nicht gefunden!
    echo.
    echo Bitte folge diesen Schritten:
    echo 1. Kopiere config\\.env.example nach config\\.env
    echo 2. Öffne config\\.env mit einem Texteditor
    echo 3. Fülle deine Discord Bot-Tokens ein
    echo 4. Starte dieses Skript erneut
    echo.
    echo Möchtest du config\\.env.example jetzt öffnen? (J/N)
    set /p choice=
    if /i "%choice%"=="j" (
        start notepad config\\.env.example
    )
    echo.
    pause
    exit /b 1
)

echo Starte Detektiv Pikachu Bot-System...
echo (Haupt-Bot + Helper-Bot werden beide gestartet)
echo.
DetektivPikachu.exe
echo.
echo Bot-System wurde beendet.
pause
'''

    with open(release_dir / 'Detektiv_Pikachu_starten.bat', 'w', encoding='utf-8') as f:
        f.write(start_script)
    
    print("[SCRIPT] Einfaches Start-Skript erstellt")

def main():
    """Hauptfunktion für den Build-Prozess"""
    
    # Sicherstelle UTF-8 Ausgabe für Windows
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    
    print("[BUILD] Detektiv Pikachu EXE Build Tool")
    print("=" * 40)
    
    # 1. Bereinigung
    clean_build_dirs()
    
    # 2. Spec-Dateien erstellen
    create_spec_files()
    
    # 3. EXE-Dateien bauen
    if not build_executables():
        print("[ERROR] Build fehlgeschlagen!")
        return 1
    
    # 4. Release-Paket erstellen
    release_dir = create_release_package()
    
    print("\n[SUCCESS] Build erfolgreich abgeschlossen!")
    print(f"[INFO] Release-Paket: {release_dir}")
    print("\n[NEXT] Naechste Schritte:")
    print("1. Kopiere config/.env.example nach config/.env")
    print("2. Fuelle deine Bot-Tokens in config/.env ein")
    print("3. Starte mit Detektiv_Pikachu_starten.bat (empfohlen)")
    
    return 0

if __name__ == '__main__':
    sys.exit(main()) 