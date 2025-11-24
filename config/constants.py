from pathlib import Path
import os
import sys
from dotenv import load_dotenv

# Robuste Pfad-Erkennung für PyInstaller und normale Python-Ausführung
def get_base_dir_and_env_path():
    """Bestimmt BASE_DIR und env_path für verschiedene Ausführungsarten"""
    potential_paths = []
    
    # 1. Neben der .exe (für PyInstaller)
    if getattr(sys, 'frozen', False):
        exe_dir = Path(sys.executable).parent
        potential_paths.append(exe_dir)
        print(f"[CONSTANTS] PyInstaller erkannt - .exe Verzeichnis: {exe_dir}")
    
    # 2. Aktuelles Working Directory
    potential_paths.append(Path.cwd())
    
    # 3. Verzeichnis der Python-Datei (für normale Ausführung)
    potential_paths.append(Path(__file__).parent.parent)
    
    # Suche .env in allen möglichen Verzeichnissen
    for base_dir in potential_paths:
        env_path = base_dir / '.env'
        print(f"[CONSTANTS] Suche .env in: {env_path}")
        if env_path.exists():
            print(f"[CONSTANTS] ✅ .env gefunden: {env_path}")
            return base_dir, env_path
    
    # Keine .env-Datei gefunden - verwende erstes Verzeichnis
    print(f"[CONSTANTS] ❌ .env nicht gefunden. Verwende: {potential_paths[0]}")
    return potential_paths[0], potential_paths[0] / '.env'

BASE_DIR, env_path = get_base_dir_and_env_path()

# Versuche .env zu laden, falls sie existiert (graceful handling)
if env_path.exists():
    load_dotenv(env_path)
    print(f"[CONSTANTS] ✅ .env geladen: {env_path}")
else:
    print(f"[CONSTANTS] ⚠️ .env nicht gefunden: {env_path}")
# Keine Warnung hier ausgeben - das macht der Launcher

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
