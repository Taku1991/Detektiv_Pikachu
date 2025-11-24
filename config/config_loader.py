import os
import sys
from pathlib import Path
from typing import Tuple
import logging
from dotenv import load_dotenv

logger = logging.getLogger('ConfigLoader')

def get_env_path() -> Path:
    """
    Bestimmt den korrekten Pfad zur .env-Datei.
    Berücksichtigt PyInstaller-Builds und normale Python-Ausführung.
    """
    # Mögliche Pfade für die .env-Datei
    potential_paths = []
    
    # 1. Neben der .exe (für PyInstaller)
    if getattr(sys, 'frozen', False):
        exe_dir = Path(sys.executable).parent
        potential_paths.append(exe_dir / '.env')
        print(f"[CONFIG] PyInstaller erkannt - .exe Verzeichnis: {exe_dir}")
    
    # 2. Aktuelles Working Directory
    potential_paths.append(Path.cwd() / '.env')
    
    # 3. Verzeichnis der Python-Datei (für normale Ausführung)
    potential_paths.append(Path(__file__).parent.parent / '.env')
    
    # Suche in allen möglichen Pfaden
    for path in potential_paths:
        print(f"[CONFIG] Suche .env in: {path}")
        if path.exists():
            print(f"[CONFIG] ✅ .env gefunden: {path}")
            return path
    
    # Keine .env-Datei gefunden
    print(f"[CONFIG] ❌ .env nicht gefunden. Suchpfade waren:")
    for path in potential_paths:
        print(f"[CONFIG]   - {path}")
    
    # Verwende den ersten Pfad als Fallback für Fehlermeldung
    return potential_paths[0]

def load_config() -> Tuple[str, str, str]:
    """
    Lädt die Konfiguration aus der .env-Datei.
    
    Returns:
        Tuple[str, str, str]: (primary_token, helper_token, command_prefix)
    """
    try:
        # Bestimme den korrekten Pfad zur .env-Datei
        env_path = get_env_path()
        
        if not env_path.exists():
            raise FileNotFoundError(
                f".env Datei nicht gefunden: {env_path}\n"
                f"💡 Verwende das Setup-Tool: python setup_bot.py"
            )
            
        load_dotenv(env_path)
        
        # Lade die Tokens aus den Umgebungsvariablen
        primary_token = os.getenv('PRIMARY_BOT_TOKEN')
        helper_token = os.getenv('SECONDARY_BOT_TOKEN')
        command_prefix = os.getenv('COMMAND_PREFIX', '!')  # Default: !
        
        # Überprüfe, ob die Tokens vorhanden sind
        if not primary_token:
            raise ValueError(
                "PRIMARY_BOT_TOKEN fehlt in der .env Datei\n"
                "💡 Verwende das Setup-Tool: python setup_bot.py"
            )
            
        if not helper_token:
            raise ValueError(
                "SECONDARY_BOT_TOKEN fehlt in der .env Datei\n"
                "💡 Verwende das Setup-Tool: python setup_bot.py"
            )
            
        logger.info("✅ Konfiguration erfolgreich geladen")
        logger.info(f"📁 .env Pfad: {env_path}")
        logger.info(f"🔑 Primärer Token: {primary_token[:20]}...")
        logger.info(f"🔑 Sekundärer Token: {helper_token[:20]}...")
        logger.info(f"⚙️  Befehlspräfix: {command_prefix}")
        
        return primary_token, helper_token, command_prefix
        
    except Exception as e:
        logger.error(f"❌ Fehler beim Laden der Konfiguration: {e}")
        raise 

def validate_config() -> bool:
    """
    Validiert die Konfiguration ohne sie zu laden
    
    Returns:
        bool: True wenn Konfiguration gültig ist
    """
    try:
        load_config()
        return True
    except Exception:
        return False 