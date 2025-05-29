import os
from pathlib import Path
from typing import Tuple
import logging
from dotenv import load_dotenv

logger = logging.getLogger('ConfigLoader')

def load_config() -> Tuple[str, str, str]:
    """
    Lädt die Konfiguration aus der .env-Datei.
    
    Returns:
        Tuple[str, str, str]: (primary_token, helper_token, command_prefix)
    """
    try:
        # Lade .env Datei
        env_path = Path(__file__).parent.parent / '.env'
        if not env_path.exists():
            raise FileNotFoundError(f".env Datei nicht gefunden: {env_path}")
            
        load_dotenv(env_path)
        
        # Lade die Tokens aus den Umgebungsvariablen
        primary_token = os.getenv('PRIMARY_BOT_TOKEN')
        helper_token = os.getenv('SECONDARY_BOT_TOKEN')
        command_prefix = os.getenv('COMMAND_PREFIX', '!')  # Default: !
        
        # Überprüfe, ob die Tokens vorhanden sind
        if not primary_token:
            raise ValueError("PRIMARY_BOT_TOKEN fehlt in der .env Datei")
            
        if not helper_token:
            raise ValueError("SECONDARY_BOT_TOKEN fehlt in der .env Datei")
            
        return primary_token, helper_token, command_prefix
        
    except Exception as e:
        logger.error(f"Fehler beim Laden der Konfiguration: {e}")
        raise 