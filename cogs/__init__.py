import logging
import os
import importlib
import asyncio
import sys
from pathlib import Path
from discord.ext import commands

logger = logging.getLogger('StatusBot')

def find_cogs_directory():
    """
    Findet das Cogs-Verzeichnis mit robuster Pfad-Auflösung
    """
    # Verschiedene mögliche Pfade ausprobieren
    possible_paths = []
    
    # 1. Relativ zur aktuellen Datei
    current_file_dir = Path(__file__).parent
    possible_paths.append(current_file_dir)
    
    # 2. PyInstaller _MEIPASS Pfad (Priorität!)
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        # Temporärer PyInstaller Pfad
        meipass_cogs = Path(sys._MEIPASS) / "cogs"
        possible_paths.insert(0, meipass_cogs)  # Höchste Priorität
        
        # Auch direkt in _MEIPASS schauen
        meipass_root = Path(sys._MEIPASS)
        possible_paths.insert(1, meipass_root / "cogs")
        
        logger.info(f"🔧 PyInstaller-Modus erkannt - _MEIPASS: {sys._MEIPASS}")
    
    # 3. EXE-Verzeichnis (bei PyInstaller)
    if getattr(sys, 'frozen', False):
        exe_dir = Path(sys.executable).parent
        possible_paths.append(exe_dir / "cogs")
        possible_paths.append(exe_dir)  # Falls cogs direkt im EXE-Verzeichnis
    
    # 4. Aktuelles Arbeitsverzeichnis
    cwd = Path.cwd()
    possible_paths.append(cwd / "cogs")
    
    # 5. Script-Verzeichnis
    if __file__:
        script_dir = Path(__file__).parent.parent
        possible_paths.append(script_dir / "cogs")
    
    # 6. Hauptverzeichnis basierend auf main.py
    try:
        import main
        main_dir = Path(main.__file__).parent
        possible_paths.append(main_dir / "cogs")
    except:
        pass
    
    logger.info("🔍 Suche Cogs-Verzeichnis in folgenden Pfaden:")
    for i, path in enumerate(possible_paths, 1):
        abs_path = path.resolve()
        exists = path.exists()
        is_pyinstaller = "/_MEI" in str(abs_path) or "_MEIPASS" in str(abs_path)
        logger.info(f"  {i}. {abs_path} {'✅' if exists else '❌'} {'🔧(PyInstaller)' if is_pyinstaller else ''}")
        
        if exists and path.is_dir():
            # Prüfe ob es die erwarteten Unterverzeichnisse gibt
            subdirs = ['admin', 'channel', 'system']
            found_subdirs = []
            for subdir in subdirs:
                subdir_path = path / subdir
                if subdir_path.exists() and subdir_path.is_dir():
                    found_subdirs.append(subdir)
            
            logger.info(f"     Gefundene Unterverzeichnisse: {found_subdirs}")
            
            if len(found_subdirs) >= 2:  # Mindestens 2 von 3 Verzeichnissen
                logger.info(f"✅ Verwende Cogs-Verzeichnis: {abs_path}")
                return path
    
    # PyInstaller Fallback: Versuche direkt über importlib
    if getattr(sys, 'frozen', False):
        logger.warning("🔧 PyInstaller-Fallback: Verwende aktuelle Datei-Position")
        return Path(__file__).parent
    
    # Allgemeiner Fallback
    logger.warning("⚠️ Kein geeignetes Cogs-Verzeichnis gefunden - verwende aktuelles Arbeitsverzeichnis")
    fallback_path = cwd / "cogs"
    return fallback_path

async def setup_cogs(bot):
    """
    Lädt alle Cogs aus den Unterverzeichnissen des cogs-Ordners
    """
    logger.info("Lade Cogs...")
    
    # Finde das richtige Cogs-Verzeichnis
    cogs_base_dir = find_cogs_directory()
    logger.info(f"📁 Basis Cogs-Verzeichnis: {cogs_base_dir.resolve()}")
    
    # Verzeichnisse, die Cogs enthalten
    cog_dirs = ['admin', 'channel', 'system']
    
    # Sammle alle Cogs zum parallelen Laden
    cog_tasks = []
    expected_cogs = []
    
    # Lade Cogs aus allen Verzeichnissen
    for cog_dir in cog_dirs:
        cog_path = cogs_base_dir / cog_dir
        
        logger.debug(f"🔍 Prüfe Cog-Verzeichnis: {cog_path.resolve()}")
        
        if not cog_path.exists():
            logger.warning(f"❌ Cog-Verzeichnis {cog_dir} nicht gefunden: {cog_path.resolve()}")
            
            # Versuche alternatives Verzeichnis zu finden
            alternative_paths = [
                Path.cwd() / "cogs" / cog_dir,
                Path(__file__).parent.parent / "cogs" / cog_dir,
            ]
            
            for alt_path in alternative_paths:
                if alt_path.exists():
                    logger.info(f"✅ Alternative gefunden: {alt_path.resolve()}")
                    cog_path = alt_path
                    break
            else:
                continue
            
        logger.debug(f"📂 Durchsuche Cog-Verzeichnis: {cog_path.resolve()}")
        
        # Alle Python-Dateien im Verzeichnis finden
        try:
            cog_files = [f for f in cog_path.glob("*.py") if f.is_file() and f.name != "__init__.py"]
            logger.debug(f"🐍 Gefundene Python-Dateien in {cog_dir}: {[f.name for f in cog_files]}")
        except Exception as e:
            logger.error(f"Fehler beim Durchsuchen von {cog_path}: {e}")
            continue
        
        for cog_file in cog_files:
            cog_name = cog_file.stem
            module_path = f"cogs.{cog_dir}.{cog_name}"
            expected_cogs.append(module_path)
            
            logger.debug(f"📋 Cog vorbereitet: {module_path} ({cog_file.resolve()})")
            
            # Erstelle Task für paralleles Laden
            cog_tasks.append(load_cog(bot, module_path))
    
    logger.info(f"📦 Versuche {len(expected_cogs)} Cogs zu laden: {expected_cogs}")
    
    # Lade alle Cogs parallel
    if cog_tasks:
        results = await asyncio.gather(*cog_tasks, return_exceptions=True)
        
        # Auswertung der Ergebnisse
        loaded_cogs = []
        failed_cogs = []
        
        for i, result in enumerate(results):
            cog_name = expected_cogs[i]
            if isinstance(result, Exception):
                logger.error(f"❌ Fehler beim Laden von Cog {cog_name}: {result}")
                failed_cogs.append(cog_name)
            else:
                logger.debug(f"✅ Cog erfolgreich geladen: {cog_name}")
                loaded_cogs.append(cog_name)
        
        # Zusammenfassung
        logger.info(f"✅ Erfolgreich {len(loaded_cogs)} von {len(expected_cogs)} Cogs geladen")
        if loaded_cogs:
            logger.info(f"📋 Geladene Cogs: {', '.join(loaded_cogs)}")
        if failed_cogs:
            logger.warning(f"⚠️ Fehlgeschlagene Cogs: {', '.join(failed_cogs)}")
            
        # Prüfe ob kritische Cogs geladen wurden
        critical_cogs = ['cogs.system.help_commands', 'cogs.admin.admin_commands']
        critical_loaded = [cog for cog in critical_cogs if cog in loaded_cogs]
        critical_failed = [cog for cog in critical_cogs if cog in failed_cogs]
        
        if critical_failed:
            logger.error(f"⚠️ Kritische Cogs konnten nicht geladen werden: {critical_failed}")
        if critical_loaded:
            logger.info(f"✅ Kritische Cogs erfolgreich geladen: {critical_loaded}")
            
        # Prüfe verfügbare Commands nach dem Laden
        available_commands = [cmd.name for cmd in bot.tree.get_commands()]
        logger.info(f"🎮 Verfügbare Slash-Commands nach Cog-Loading: {available_commands}")
        
        # Auch wenn einige Cogs fehlschlagen, setze fort wenn mindestens ein Cog geladen wurde
        if len(loaded_cogs) > 0:
            return True
        else:
            logger.error("❌ Keine Cogs konnten geladen werden!")
            return False
    else:
        logger.warning("⚠️ Keine Cogs zum Laden gefunden!")
        logger.info("💡 Tipp: Überprüfe die Verzeichnisstruktur und stelle sicher, dass die Cog-Dateien existieren")
        return False

async def load_cog(bot, module_path):
    """
    Lädt ein einzelnes Cog mit verbesserter Fehlerbehandlung für PyInstaller
    """
    try:
        # PyInstaller-spezifische Behandlung
        if getattr(sys, 'frozen', False):
            logger.debug(f"🔧 PyInstaller-Modus: Lade Cog {module_path}")
            
            # Versuche direkten Import für PyInstaller
            try:
                # Spezielle Import-Behandlung für gefrorene Anwendungen
                parts = module_path.split('.')
                if len(parts) >= 3:  # cogs.admin.admin_commands
                    cog_dir = parts[1]  # admin
                    cog_file = parts[2]  # admin_commands
                    
                    # Direkte Imports versuchen
                    if cog_dir == 'admin' and cog_file == 'admin_commands':
                        from cogs.admin.admin_commands import AdminCommands
                        await bot.add_cog(AdminCommands(bot))
                        logger.debug(f"✅ Direct import successful: {module_path}")
                        return module_path
                    elif cog_dir == 'channel' and cog_file == 'channel_commands':
                        from cogs.channel.channel_commands import ChannelCommands
                        await bot.add_cog(ChannelCommands(bot))
                        logger.debug(f"✅ Direct import successful: {module_path}")
                        return module_path
                    elif cog_dir == 'system' and cog_file == 'help_commands':
                        from cogs.system.help_commands import HelpCommands
                        await bot.add_cog(HelpCommands(bot))
                        logger.debug(f"✅ Direct import successful: {module_path}")
                        return module_path
                        
            except ImportError as direct_import_error:
                logger.debug(f"🔧 Direct import failed: {direct_import_error}, trying standard method")
        
        # Standard-Import versuchen (funktioniert meist auch in PyInstaller)
        try:
            import importlib
            module = importlib.import_module(module_path)
            logger.debug(f"📦 Modul {module_path} erfolgreich importiert")
        except ImportError as e:
            logger.error(f"❌ Import-Fehler für {module_path}: {e}")
            logger.debug(f"🔍 Überprüfe ob das Modul im Python-Pfad verfügbar ist")
            
            # Bei PyInstaller zusätzliche Info
            if getattr(sys, 'frozen', False):
                logger.debug(f"🔧 PyInstaller sys.path: {sys.path[:3]}...")  # Nur erste 3 Einträge
                
            raise
        
        # Lade die Extension
        await bot.load_extension(module_path)
        logger.debug(f"✅ Extension {module_path} erfolgreich geladen")
        return module_path
        
    except commands.ExtensionAlreadyLoaded:
        logger.warning(f"⚠️ Extension {module_path} war bereits geladen")
        return module_path
        
    except commands.ExtensionNotFound as e:
        logger.error(f"❌ Extension {module_path} nicht gefunden: {e}")
        
        # PyInstaller-spezifische Hinweise
        if getattr(sys, 'frozen', False):
            logger.error(f"🔧 PyInstaller-Hinweis: Möglicherweise wurde {module_path} nicht in die .exe eingebunden")
            logger.error(f"💡 Prüfe die .spec Datei und füge die Cogs-Verzeichnisse zu 'datas' hinzu")
            
        raise
        
    except commands.NoEntryPointError as e:
        logger.error(f"❌ Kein setup() Entry Point in {module_path}: {e}")
        logger.debug(f"💡 Stelle sicher, dass {module_path} eine async def setup(bot) Funktion hat")
        raise
        
    except commands.ExtensionFailed as e:
        logger.error(f"❌ Extension {module_path} Setup fehlgeschlagen: {e}")
        logger.error(f"🔍 Original Error: {e.original}")
        
        # Bei PyInstaller zusätzliche Diagnose
        if getattr(sys, 'frozen', False):
            logger.error(f"🔧 PyInstaller-Diagnose: Extension Setup in gefrorener Anwendung fehlgeschlagen")
            
        raise
        
    except Exception as e:
        logger.error(f"❌ Unerwarteter Fehler beim Laden von {module_path}: {e}")
        
        # PyInstaller-spezifische Diagnose
        if getattr(sys, 'frozen', False):
            logger.error(f"🔧 PyInstaller-Kontext: Frozen={getattr(sys, 'frozen', False)}")
            logger.error(f"🔧 _MEIPASS: {getattr(sys, '_MEIPASS', 'Nicht verfügbar')}")
            
        import traceback
        logger.error(traceback.format_exc())
        raise 