from pathlib import Path
import os
from dotenv import load_dotenv

# .env-Datei laden
load_dotenv()

class BotConstants:
    # Zeitliche Konstanten
    INACTIVITY_THRESHOLD = 600  # 10 Minuten in Sekunden
    ACTIVITY_CHECK_THRESHOLD = 120  # 2 Minuten in Sekunden
    
    # Verzeichnisse und Pfade
    BASE_DIR = Path(__file__).parent.parent  # Wurzelverzeichnis des Projekts
    DATA_DIR = BASE_DIR / 'data'
    LOG_DIR = BASE_DIR / 'logs'
    GIF_DIR = DATA_DIR / 'gif'
    
    # Retry-Einstellungen
    MAX_RETRIES = 3
    RETRY_DELAY = 1  # Sekunden zwischen Retry-Versuchen
    
    # Bot-Konfiguration
    ADMIN_USER_ID = 306103492056055808  # Ihre Admin-ID hier
    MAINTENANCE_EMOJI = "🟦"
    
    # Bot-Tokens aus .env-Datei
    PRIMARY_BOT_TOKEN = os.getenv('PRIMARY_BOT_TOKEN')
    SECONDARY_BOT_TOKEN = os.getenv('SECONDARY_BOT_TOKEN')
    
    # Rate-Limit-Einstellungen
    RATE_LIMIT_COOL_DOWN = int(os.getenv('RATE_LIMIT_COOL_DOWN', '60'))
    
    # Log-Einstellungen
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    MAX_LOG_DAYS = 7  # Maximales Alter der Log-Dateien in Tagen
