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

def clean_build_dirs():
    """Bereinigt alte Build-Verzeichnisse"""
    dirs_to_clean = ['build', 'dist', '__pycache__']
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            print(f"✓ {dir_name} bereinigt")

def create_spec_files():
    """Erstellt PyInstaller .spec Dateien für bessere Kontrolle"""
    
    # Haupt-Bot Spec
    main_spec = """
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('cogs', 'cogs'),
        ('config', 'config'),
        ('core', 'core'),
        ('utils', 'utils'),
        ('bot_status.py', '.'),
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
    name='DetektivPikachu-MainBot',
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
    icon='assets/pikachu.ico' if os.path.exists('assets/pikachu.ico') else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='DetektivPikachu-MainBot',
)
"""

    # Helper-Bot Spec
    helper_spec = """
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['helper_bot.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('config', 'config'),
        ('core', 'core'),
        ('utils', 'utils'),
        ('bot_status.py', '.'),
        ('.env.example', '.'),
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
    name='DetektivPikachu-HelperBot',
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
    icon='assets/pikachu.ico' if os.path.exists('assets/pikachu.ico') else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='DetektivPikachu-HelperBot',
)
"""

    with open('main_bot.spec', 'w', encoding='utf-8') as f:
        f.write(main_spec)
    
    with open('helper_bot.spec', 'w', encoding='utf-8') as f:
        f.write(helper_spec)
    
    print("✓ .spec Dateien erstellt")

def build_executables():
    """Erstellt die EXE-Dateien mit PyInstaller"""
    
    print("🚀 Starte EXE-Build-Prozess...")
    
    # Haupt-Bot bauen
    print("📦 Baue Haupt-Bot...")
    result = subprocess.run([
        sys.executable, '-m', 'PyInstaller',
        '--clean',
        'main_bot.spec'
    ], capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"❌ Fehler beim Bauen des Haupt-Bots: {result.stderr}")
        return False
    
    # Helper-Bot bauen
    print("📦 Baue Helper-Bot...")
    result = subprocess.run([
        sys.executable, '-m', 'PyInstaller',
        '--clean', 
        'helper_bot.spec'
    ], capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"❌ Fehler beim Bauen des Helper-Bots: {result.stderr}")
        return False
    
    print("✅ EXE-Dateien erfolgreich erstellt!")
    return True

def create_release_package():
    """Erstellt ein Release-Paket mit allen notwendigen Dateien"""
    
    release_dir = Path('release')
    if release_dir.exists():
        shutil.rmtree(release_dir)
    
    release_dir.mkdir()
    
    # EXE-Dateien kopieren
    main_exe_dir = Path('dist/DetektivPikachu-MainBot')
    helper_exe_dir = Path('dist/DetektivPikachu-HelperBot')
    
    if main_exe_dir.exists():
        shutil.copytree(main_exe_dir, release_dir / 'MainBot')
    
    if helper_exe_dir.exists():
        shutil.copytree(helper_exe_dir, release_dir / 'HelperBot')
    
    # Externe Konfigurationsverzeichnisse erstellen
    config_dir = release_dir / 'config'
    data_dir = release_dir / 'data'
    
    config_dir.mkdir()
    data_dir.mkdir()
    (data_dir / 'json').mkdir()
    (data_dir / 'logs').mkdir()
    (data_dir / 'gif').mkdir()
    
    # Beispiel-Konfigurationsdateien kopieren
    shutil.copy('.env.example', config_dir / '.env.example')
    shutil.copy('README.md', release_dir / 'README.md')
    shutil.copy('LICENSE', release_dir / 'LICENSE')
    
    # Start-Skripts erstellen
    create_start_scripts(release_dir)
    
    print(f"📦 Release-Paket erstellt in: {release_dir}")
    return release_dir

def create_start_scripts(release_dir):
    """Erstellt Start-Skripts für die EXE-Dateien"""
    
    start_main_script = '''@echo off
title Detektiv Pikachu - Haupt-Bot
echo ===================================
echo Detektiv Pikachu - Haupt-Bot
echo ===================================
echo.

REM Prüfe, ob .env-Datei existiert
if not exist "config\\.env" (
    echo FEHLER: .env-Datei nicht gefunden!
    echo Bitte kopiere config\\.env.example nach config\\.env
    echo und fülle deine Bot-Tokens ein.
    echo.
    pause
    exit /b 1
)

echo Starte Haupt-Bot...
MainBot\\DetektivPikachu-MainBot.exe
echo.
echo Bot wurde beendet.
pause
'''

    start_helper_script = '''@echo off
title Detektiv Pikachu - Helper-Bot
echo ===================================
echo Detektiv Pikachu - Helper-Bot
echo ===================================
echo.

REM Prüfe, ob .env-Datei existiert
if not exist "config\\.env" (
    echo FEHLER: .env-Datei nicht gefunden!
    echo Bitte kopiere config\\.env.example nach config\\.env
    echo und fülle deine Bot-Tokens ein.
    echo.
    pause
    exit /b 1
)

echo Starte Helper-Bot...
HelperBot\\DetektivPikachu-HelperBot.exe
echo.
echo Bot wurde beendet.
pause
'''

    start_both_script = '''@echo off
title Detektiv Pikachu - Bot Starter
echo ===================================
echo Detektiv Pikachu - Beide Bots starten
echo ===================================
echo.

REM Prüfe, ob .env-Datei existiert
if not exist "config\\.env" (
    echo FEHLER: .env-Datei nicht gefunden!
    echo Bitte kopiere config\\.env.example nach config\\.env
    echo und fülle deine Bot-Tokens ein.
    echo.
    pause
    exit /b 1
)

echo Starte beide Bots...
start "Detektiv Pikachu - Haupt-Bot" cmd /c "MainBot\\DetektivPikachu-MainBot.exe"
start "Detektiv Pikachu - Helper-Bot" cmd /c "HelperBot\\DetektivPikachu-HelperBot.exe"

echo.
echo Beide Bots wurden gestartet.
echo Du kannst dieses Fenster jetzt schließen.
echo.
pause
'''

    with open(release_dir / 'start_main_bot.bat', 'w', encoding='utf-8') as f:
        f.write(start_main_script)
    
    with open(release_dir / 'start_helper_bot.bat', 'w', encoding='utf-8') as f:
        f.write(start_helper_script)
    
    with open(release_dir / 'start_both_bots.bat', 'w', encoding='utf-8') as f:
        f.write(start_both_script)
    
    print("✓ Start-Skripts erstellt")

def main():
    """Hauptfunktion für den Build-Prozess"""
    
    print("🔨 Detektiv Pikachu EXE Build Tool")
    print("=" * 40)
    
    # 1. Bereinigung
    clean_build_dirs()
    
    # 2. Spec-Dateien erstellen
    create_spec_files()
    
    # 3. EXE-Dateien bauen
    if not build_executables():
        print("❌ Build fehlgeschlagen!")
        return 1
    
    # 4. Release-Paket erstellen
    release_dir = create_release_package()
    
    print("\n🎉 Build erfolgreich abgeschlossen!")
    print(f"📁 Release-Paket: {release_dir}")
    print("\n📋 Nächste Schritte:")
    print("1. Kopiere config/.env.example nach config/.env")
    print("2. Fülle deine Bot-Tokens in config/.env ein")
    print("3. Starte die Bots mit start_both_bots.bat")
    
    return 0

if __name__ == '__main__':
    sys.exit(main()) 