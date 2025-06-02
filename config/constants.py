from pathlib import Path
import os
from dotenv import load_dotenv

# Lade .env-Datei aus dem Hauptverzeichnis (nicht aus config/)
BASE_DIR = Path(__file__).parent.parent  # Wurzelverzeichnis des Projekts
env_path = BASE_DIR / '.env'

# Versuche .env zu laden, falls sie existiert
if env_path.exists():
    load_dotenv(env_path)
else:
    print(f"⚠️  WARNUNG: .env Datei nicht gefunden: {env_path}")
    print("💡 Erstelle eine .env Datei im Hauptverzeichnis mit deinen Bot-Tokens")

class BotConstants:
    # Verzeichnisse und Pfade
    BASE_DIR = BASE_DIR
    DATA_DIR = BASE_DIR / 'data'
    LOG_DIR = BASE_DIR / 'logs'
    GIF_DIR = DATA_DIR / 'gif'
    
    # Bot-Tokens aus .env-Datei
    PRIMARY_BOT_TOKEN = os.getenv('PRIMARY_BOT_TOKEN')
    SECONDARY_BOT_TOKEN = os.getenv('SECONDARY_BOT_TOKEN')
    
    # Bot-Einstellungen
    COMMAND_PREFIX = os.getenv('COMMAND_PREFIX', '!')
    ADMIN_USER_ID = int(os.getenv('ADMIN_USER_ID', '0'))  # 0 = nicht konfiguriert
    MAINTENANCE_EMOJI = "🟦"
    
    # Rate-Limit-Einstellungen
    RATE_LIMIT_COOL_DOWN = int(os.getenv('RATE_LIMIT_COOL_DOWN', '60'))
    MAX_RETRIES = int(os.getenv('MAX_RETRIES', '3'))
    RETRY_DELAY = int(os.getenv('RETRY_DELAY', '1'))
    
    # Zeitliche Konstanten
    INACTIVITY_THRESHOLD = int(os.getenv('INACTIVITY_THRESHOLD', '600'))  # 10 Minuten
    ACTIVITY_CHECK_THRESHOLD = int(os.getenv('ACTIVITY_CHECK_THRESHOLD', '120'))  # 2 Minuten
    
    # Log-Einstellungen
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
    MAX_LOG_SIZE_MB = int(os.getenv('MAX_LOG_SIZE_MB', '50'))
    MAX_LOG_DAYS = int(os.getenv('MAX_LOG_DAYS', '7'))
    
    @classmethod
    def validate_tokens(cls):
        """Überprüft, ob die erforderlichen Tokens und Einstellungen vorhanden sind"""
        missing = []
        if not cls.PRIMARY_BOT_TOKEN:
            missing.append('PRIMARY_BOT_TOKEN')
        if not cls.SECONDARY_BOT_TOKEN:
            missing.append('SECONDARY_BOT_TOKEN')
        if cls.ADMIN_USER_ID == 0:
            missing.append('ADMIN_USER_ID')
        
        if missing:
            return False, missing
        return True, []
    
    @classmethod
    def print_config_status(cls):
        """Zeigt den aktuellen Konfigurationsstatus an"""
        valid, missing = cls.validate_tokens()
        print("\n🔧 Detektiv Pikachu - Konfigurationsstatus:")
        print("=" * 45)
        
        if valid:
            print("✅ Bot-Tokens: Konfiguriert")
            print(f"✅ Primärer Token: {cls.PRIMARY_BOT_TOKEN[:20]}...")
            print(f"✅ Sekundärer Token: {cls.SECONDARY_BOT_TOKEN[:20]}...")
            print(f"✅ Admin User ID: {cls.ADMIN_USER_ID}")
        else:
            print("❌ Bot-Konfiguration: NICHT VOLLSTÄNDIG")
            for item in missing:
                if item == 'ADMIN_USER_ID':
                    print(f"   - {item}: NICHT KONFIGURIERT")
                else:
                    print(f"   - {item}: FEHLT")
        
        print(f"📁 Basis-Verzeichnis: {cls.BASE_DIR}")
        print(f"📄 .env Datei: {'✅ Gefunden' if env_path.exists() else '❌ Nicht gefunden'}")
        print(f"⚙️  Rate-Limit Cooldown: {cls.RATE_LIMIT_COOL_DOWN}s")
        print(f"📊 Log-Level: {cls.LOG_LEVEL}")
        
        if not valid:
            print("\n💡 Um den Bot zu konfigurieren:")
            print("   1. Starte den Bot erneut")
            print("   2. Gib deine Bot-Tokens und Admin-User-ID ein")
            print("   3. Der Bot startet automatisch nach der Eingabe")

# Zeige Konfigurationsstatus beim Import an
if __name__ == "__main__":
    BotConstants.print_config_status()
