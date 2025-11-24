#!/usr/bin/env python3
"""
Fixed GUI + API Builder für Detektiv Pikachu Bot
Verbesserte Version mit PyInstaller-Fallbacks und besserer Fehlerbehandlung
"""

import os
import sys
import subprocess
import shutil
import importlib.util
from pathlib import Path

def print_header():
    """Druckt den Header"""
    print("🔧 Fixed GUI + API Builder")
    print("=" * 50)

def check_pyinstaller():
    """Verbesserte PyInstaller-Erkennung"""
    print("🔍 Suche PyInstaller...")
    
    # Methode 1: Direkter Import
    try:
        import PyInstaller
        print(f"✅ PyInstaller gefunden (Import): {PyInstaller.__version__}")
        return True, "python -m PyInstaller"
    except ImportError:
        pass
    
    # Methode 2: Als Python-Modul
    try:
        result = subprocess.run([sys.executable, "-m", "PyInstaller", "--version"], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            version = result.stdout.strip()
            print(f"✅ PyInstaller gefunden (Modul): {version}")
            return True, f"{sys.executable} -m PyInstaller"
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
        pass
    
    # Methode 3: Direkter Command
    try:
        result = subprocess.run(["pyinstaller", "--version"], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            version = result.stdout.strip()
            print(f"✅ PyInstaller gefunden (Command): {version}")
            return True, "pyinstaller"
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
        pass
    
    # Methode 4: pip list Check
    try:
        result = subprocess.run([sys.executable, "-m", "pip", "list"], 
                              capture_output=True, text=True, timeout=15)
        if result.returncode == 0 and "pyinstaller" in result.stdout.lower():
            print("⚠️ PyInstaller in pip list gefunden, aber nicht ausführbar")
            
            # Versuche Installation zu reparieren
            print("🔧 Versuche PyInstaller-Installation zu reparieren...")
            repair_result = subprocess.run([sys.executable, "-m", "pip", "install", "--force-reinstall", "pyinstaller"], 
                                         capture_output=True, text=True, timeout=60)
            if repair_result.returncode == 0:
                print("✅ PyInstaller-Reparatur erfolgreich")
                return True, f"{sys.executable} -m PyInstaller"
            else:
                print(f"❌ PyInstaller-Reparatur fehlgeschlagen: {repair_result.stderr}")
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
        pass
    
    print("❌ PyInstaller nicht gefunden oder nicht ausführbar")
    return False, None

def validate_cogs():
    """Validiert die Cogs-Struktur"""
    print("🔍 Validiere Cogs-Struktur...")
    
    required_files = [
        ("cogs/admin/admin_commands.py", "AdminCommands"),
        ("cogs/channel/channel_commands.py", "ChannelCommands"),
        ("cogs/system/help_commands.py", "HelpCommands"),
        ("cogs/__init__.py", "setup_cogs")
    ]
    
    for file_path, class_name in required_files:
        if not Path(file_path).exists():
            print(f"❌ Datei fehlt: {file_path}")
            return False
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                if class_name not in content:
                    print(f"❌ {class_name} nicht in {file_path} gefunden")
                    return False
            print(f"✅ {file_path} - {class_name} gefunden")
        except Exception as e:
            print(f"❌ Fehler beim Lesen von {file_path}: {e}")
            return False
    
    print("✅ Alle Cogs-Dateien validiert")
    return True

def test_imports():
    """Testet Cogs-Imports"""
    print("🧪 Teste Cogs-Imports...")
    
    test_modules = [
        "cogs.admin.admin_commands",
        "cogs.channel.channel_commands", 
        "cogs.system.help_commands"
    ]
    
    for module_name in test_modules:
        try:
            spec = importlib.util.find_spec(module_name)
            if spec is None:
                print(f"❌ Modul nicht gefunden: {module_name}")
                return False
            print(f"✅ Import erfolgreich: {module_name}")
        except Exception as e:
            print(f"❌ Import-Fehler {module_name}: {e}")
            return False
    
    print("✅ Alle Cogs-Imports erfolgreich")
    return True





def install_pyinstaller():
    """Installiert PyInstaller falls nicht vorhanden"""
    print("📦 Versuche PyInstaller zu installieren...")
    
    try:
        result = subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller", "pyinstaller-hooks-contrib"], 
                              capture_output=True, text=True, timeout=120)
        
        if result.returncode == 0:
            print("✅ PyInstaller erfolgreich installiert")
            return True
        else:
            print(f"❌ PyInstaller-Installation fehlgeschlagen: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Fehler bei PyInstaller-Installation: {e}")
        return False

def cleanup_build():
    """Bereinigt alte Build-Artefakte"""
    print("🧹 Bereinige alte Build-Artefakte...")
    
    cleanup_paths = [
        "build",
        "dist", 
        "__pycache__",
        "*.pyc"
    ]
    
    for path in cleanup_paths:
        try:
            if Path(path).exists():
                if Path(path).is_dir():
                    shutil.rmtree(path)
                    print(f"🗑️ Verzeichnis entfernt: {path}")
                else:
                    Path(path).unlink()
                    print(f"🗑️ Datei entfernt: {path}")
        except Exception as e:
            print(f"⚠️ Konnte {path} nicht entfernen: {e}")

def main():
    """Hauptfunktion"""
    print_header()
    
    # Schritt 1: Validiere Cogs
    if not validate_cogs():
        print("\n❌ Fixed Build fehlgeschlagen - Cogs-Validierung")
        return False
    
    # Schritt 2: Teste Imports
    if not test_imports():
        print("\n❌ Fixed Build fehlgeschlagen - Import-Test")
        return False
    
    # Schritt 3: Prüfe .spec Dateien
    spec_files = {
        "Directory": "gui_with_api_fixed.spec",
        "Portable": "gui_with_api_fixed_onefile.spec"
    }
    
    available_specs = {}
    for build_type, spec_file in spec_files.items():
        if Path(spec_file).exists():
            print(f"✅ {build_type} .spec Datei gefunden: {spec_file}")
            available_specs[build_type] = spec_file
        else:
            print(f"❌ {build_type} .spec Datei fehlt: {spec_file}")
    
    if not available_specs:
        print("\n❌ Fixed Build fehlgeschlagen - Keine .spec Dateien gefunden")
        return False
    
    # Schritt 4: Prüfe PyInstaller
    pyinstaller_available, pyinstaller_cmd = check_pyinstaller()
    
    if not pyinstaller_available:
        print("🔧 Versuche PyInstaller zu installieren...")
        if install_pyinstaller():
            # Nochmal prüfen nach Installation
            pyinstaller_available, pyinstaller_cmd = check_pyinstaller()
            if not pyinstaller_available:
                print("\n❌ Fixed Build fehlgeschlagen - PyInstaller Problem")
                print("\n💡 Mögliche Lösungen:")
                print("• pip install pyinstaller pyinstaller-hooks-contrib")
                print("• python -m pip install --upgrade pyinstaller")
                print("• Neustart der Konsole nach Installation")
                return False
        else:
            print("\n❌ Fixed Build fehlgeschlagen - PyInstaller Installation")
            return False
    
    # Schritt 5: Bereinige alte Builds
    cleanup_build()
    
    # Schritt 6: Baue alle verfügbaren Versionen
    successful_builds = 0
    total_builds = len(available_specs)
    
    print(f"\n🔨 Starte Builds für {total_builds} Versionen...\n")
    
    for build_type, spec_file in available_specs.items():
        print(f"🚀 Baue {build_type} Version...")
        print(f"📄 Spec-Datei: {spec_file}")
        
        if run_pyinstaller_with_spec(pyinstaller_cmd, spec_file):
            successful_builds += 1
            
            # Ermittle Output-Pfad basierend auf Spec-Typ
            if build_type == "Directory":
                exe_path = Path("dist/DetektivPikachu-GUI-API-Fixed/DetektivPikachu-GUI-API-Fixed.exe")
                description = "Directory-Build (mit _internal Ordner)"
            else:  # Portable
                exe_path = Path("dist/DetektivPikachu-GUI-API-Fixed-Portable.exe")
                description = "Portable Single-File (ohne _internal)"
            
            if exe_path.exists():
                size_mb = exe_path.stat().st_size / (1024 * 1024)
                print(f"✅ {build_type} erfolgreich erstellt!")
                print(f"📁 Pfad: {exe_path}")
                print(f"📊 Größe: {size_mb:.1f} MB")
                print(f"📝 Typ: {description}")
            else:
                print(f"⚠️ {build_type} Build erfolgreich, aber .exe nicht gefunden")
        else:
            print(f"❌ {build_type} Build fehlgeschlagen")
        
        print("-" * 50)
    
    # Zusammenfassung
    print(f"\n📋 Build-Zusammenfassung:")
    print(f"✅ Erfolgreiche Builds: {successful_builds}/{total_builds}")
    
    if successful_builds > 0:
        print(f"\n🎉 Fixed Build erfolgreich abgeschlossen!")
        
        print(f"\n📁 Verfügbare Versionen:")
        
        # Directory Version
        dir_exe = Path("dist/DetektivPikachu-GUI-API-Fixed/DetektivPikachu-GUI-API-Fixed.exe")
        if dir_exe.exists():
            size_mb = dir_exe.stat().st_size / (1024 * 1024)
            print(f"🗂️ Directory: {dir_exe} ({size_mb:.1f} MB)")
            print("   └─ Benötigt _internal Ordner")
        
        # Portable Version  
        portable_exe = Path("dist/DetektivPikachu-GUI-API-Fixed-Portable.exe")
        if portable_exe.exists():
            size_mb = portable_exe.stat().st_size / (1024 * 1024)
            print(f"📦 Portable: {portable_exe} ({size_mb:.1f} MB)")
            print("   └─ Einzelne .exe Datei")
        
        print(f"\n💡 Empfehlung:")
        print(f"• Für einfache Verteilung: Verwende die Portable Version")
        print(f"• Für schnelleren Start: Verwende die Directory Version")
        print(f"\n🚀 Beide Versionen haben funktionierende Slash Commands!")
        
        return True
    else:
        print(f"\n❌ Fixed Build fehlgeschlagen")
        print(f"\n💡 Mögliche Lösungen:")
        print("• Prüfe ob alle Cogs-Dateien existieren")
        print("• Stelle sicher, dass Dependencies installiert sind")
        print("• Verwende den normalen Bot ohne .exe als Test")
        print("• Prüfe die PyInstaller-Logs für Details")
        return False

def run_pyinstaller_with_spec(pyinstaller_cmd, spec_file):
    """Führt PyInstaller mit einer spezifischen .spec Datei aus"""
    print(f"🔨 Starte PyInstaller Build für {spec_file}...")
    
    # Basis-Command
    if pyinstaller_cmd.startswith("python"):
        # Python-Modul Aufruf
        cmd_parts = pyinstaller_cmd.split() + [spec_file, "--noconfirm", "--clean"]
    else:
        # Direkter Command
        cmd_parts = [pyinstaller_cmd, spec_file, "--noconfirm", "--clean"]
    
    print(f"📝 PyInstaller Command: {' '.join(cmd_parts)}")
    
    try:
        # Führe PyInstaller aus
        result = subprocess.run(cmd_parts, 
                              capture_output=False, 
                              text=True,
                              timeout=600)  # 10 Minuten Timeout
        
        if result.returncode == 0:
            print("✅ PyInstaller Build erfolgreich!")
            return True
        else:
            print(f"❌ PyInstaller Build fehlgeschlagen (Exit Code: {result.returncode})")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ PyInstaller Build Timeout (> 10 Minuten)")
        return False
    except subprocess.CalledProcessError as e:
        print(f"❌ PyInstaller Build-Fehler: {e}")
        return False
    except Exception as e:
        print(f"❌ Unerwarteter Fehler beim PyInstaller Build: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 