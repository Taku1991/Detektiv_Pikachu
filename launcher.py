#!/usr/bin/env python3
"""
Detektiv Pikachu Bot Launcher
Startet sowohl den Haupt-Bot als auch den Helper-Bot gleichzeitig
"""

import asyncio
import logging
import sys
import os
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# EXE-kompatible Pfad-Ermittlung
if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    # Läuft als PyInstaller EXE
    BASE_DIR = Path(sys.executable).parent
else:
    # Läuft als normale Python-Datei  
    BASE_DIR = Path(__file__).parent

# Importiere die Bot-Module
try:
    from main import StatusBot, BotTokenBalancer, setup_logging as setup_main_logging
    from helper_bot import HelperBot, setup_logging as setup_helper_logging
    from config.constants import BotConstants
    from cogs import setup_cogs
except ImportError as e:
    print(f"[ERROR] Import-Fehler: {e}")
    print("[ERROR] Stelle sicher, dass alle Abhängigkeiten installiert sind.")
    sys.exit(1)

def create_env_file_simple(primary_token, secondary_token, admin_user_id, rate_limit=60):
    """Erstellt eine einfache .env Datei mit den Basis-Einstellungen"""
    env_content = f"""# Detektiv Pikachu Discord Bot - Konfiguration
# Automatisch erstellt beim ersten Start

# Bot-Tokens (erforderlich)
PRIMARY_BOT_TOKEN={primary_token}
SECONDARY_BOT_TOKEN={secondary_token}

# Admin-Einstellungen
ADMIN_USER_ID={admin_user_id}

# Rate-Limit-Einstellungen
RATE_LIMIT_COOL_DOWN={rate_limit}

# Weitere Einstellungen (können später angepasst werden)
COMMAND_PREFIX=!
LOG_LEVEL=INFO
MAX_LOG_SIZE_MB=50
MAX_LOG_DAYS=7
MAX_RETRIES=3
RETRY_DELAY=1
INACTIVITY_THRESHOLD=600
ACTIVITY_CHECK_THRESHOLD=120
"""
    
    env_path = BASE_DIR / '.env'
    with open(env_path, 'w', encoding='utf-8') as f:
        f.write(env_content)
    
    print(f"✅ .env Datei erstellt: {env_path.absolute()}")
    return env_path

def simple_setup():
    """Einfache Token-Abfrage direkt in der Konsole"""
    print("🤖 Detektiv Pikachu Bot - Erste Einrichtung")
    print("=" * 50)
    print()
    print("Der Bot benötigt zwei Discord Bot-Tokens und deine Admin-User-ID.")
    print("Bot-Tokens findest du hier: https://discord.com/developers/applications")
    print("Deine Discord User-ID findest du, indem du dich selbst rechtsklickst → 'ID kopieren'")
    print("(Entwicklermodus muss in Discord aktiviert sein)")
    print()
    
    # Token-Eingabe
    while True:
        primary_token = input("🔑 Hauptbot-Token: ").strip()
        if len(primary_token) < 50:
            print("❌ Token zu kurz! Bitte überprüfe deine Eingabe.")
            continue
        break
    
    while True:
        secondary_token = input("🔑 Helper-Bot-Token: ").strip()
        if len(secondary_token) < 50:
            print("❌ Token zu kurz! Bitte überprüfe deine Eingabe.")
            continue
        if secondary_token == primary_token:
            print("❌ Helper-Token muss sich vom Hauptbot-Token unterscheiden!")
            continue
        break
    
    # Admin User ID
    while True:
        admin_id_input = input("👤 Deine Discord User-ID (Admin): ").strip()
        try:
            admin_user_id = int(admin_id_input)
            if admin_user_id < 100000000000000000:  # Discord IDs sind mindestens 17-18 Stellen
                print("❌ Discord User-ID zu kurz! Sollte 17-19 Stellen haben.")
                continue
            break
        except ValueError:
            print("❌ Ungültige User-ID! Nur Zahlen erlaubt.")
            continue
    
    # Rate-Limit (optional)
    rate_limit_input = input("⚙️  Rate-Limit Cooldown in Sekunden (Standard: 60): ").strip()
    try:
        rate_limit = int(rate_limit_input) if rate_limit_input else 60
    except ValueError:
        rate_limit = 60
    
    print()
    print("📝 Erstelle Konfigurationsdatei...")
    
    try:
        env_path = create_env_file_simple(primary_token, secondary_token, admin_user_id, rate_limit)
        print("✅ Konfiguration erfolgreich erstellt!")
        print()
        
        # Wichtig: .env neu laden und os.environ aktualisieren
        load_dotenv(env_path)
        
        # BotConstants Werte manuell aktualisieren
        os.environ['PRIMARY_BOT_TOKEN'] = primary_token
        os.environ['SECONDARY_BOT_TOKEN'] = secondary_token
        os.environ['ADMIN_USER_ID'] = str(admin_user_id)
        os.environ['RATE_LIMIT_COOL_DOWN'] = str(rate_limit)
        
        return True
    except Exception as e:
        print(f"❌ Fehler beim Erstellen der Konfiguration: {e}")
        return False

class BotLauncher:
    def __init__(self):
        self.main_bot = None
        self.helper_bot = None
        self.main_logger = None
        self.helper_logger = None
        self.token_balancer = None
        
    def setup_logging(self):
        """Konfiguriert das Logging für beide Bots"""
        try:
            self.main_logger = setup_main_logging()
            self.helper_logger = setup_helper_logging()
            print("[LAUNCHER] Logging konfiguriert")
        except Exception as e:
            print(f"[ERROR] Logging-Setup fehlgeschlagen: {e}")
            raise

    def create_bots(self):
        """Erstellt die Bot-Instanzen"""
        try:
            # Token Balancer erstellen - verwende aktuelle Umgebungsvariablen
            primary_token = os.getenv('PRIMARY_BOT_TOKEN')
            secondary_token = os.getenv('SECONDARY_BOT_TOKEN')
            rate_limit = int(os.getenv('RATE_LIMIT_COOL_DOWN', '60'))
            max_retries = int(os.getenv('MAX_RETRIES', '3'))
            
            self.token_balancer = BotTokenBalancer(
                primary_token,
                secondary_token,
                rate_limit,
                max_retries
            )
            
            # Haupt-Bot erstellen
            self.main_bot = StatusBot()
            self.main_bot.token_balancer = self.token_balancer
            
            # Helper-Bot erstellen
            self.helper_bot = HelperBot()
            
            print("[LAUNCHER] Bot-Instanzen erstellt")
            
        except Exception as e:
            print(f"[ERROR] Bot-Erstellung fehlgeschlagen: {e}")
            raise

    async def start_main_bot(self):
        """Startet den Haupt-Bot"""
        try:
            # Lade Cogs für den Haupt-Bot
            await setup_cogs(self.main_bot)
            self.main_logger.info("Starte Haupt-Bot...")
            
            # Haupt-Bot mit Token-Balancing starten
            current_token = self.token_balancer.get_current_token()
            await self.main_bot.start(current_token)
            
        except Exception as e:
            self.main_logger.error(f"Haupt-Bot Fehler: {e}", exc_info=True)
            raise

    async def start_helper_bot(self):
        """Startet den Helper-Bot"""
        try:
            self.helper_logger.info("Starte Helper-Bot...")
            secondary_token = os.getenv('SECONDARY_BOT_TOKEN')
            await self.helper_bot.start(secondary_token)
            
        except Exception as e:
            self.helper_logger.error(f"Helper-Bot Fehler: {e}", exc_info=True)
            raise

    async def run_bots(self):
        """Startet beide Bots gleichzeitig"""
        try:
            # Setup
            self.setup_logging()
            self.create_bots()
            
            print("🚀 Starte Dual-Bot-System...")
            print("   Zum Beenden: Strg+C drücken")
            print("=" * 40)
            print()
            
            # Beide Bots parallel starten
            await asyncio.gather(
                self.start_main_bot(),
                self.start_helper_bot(),
                return_exceptions=True
            )
            
        except Exception as e:
            print(f"[ERROR] Launcher-Fehler: {e}")
            raise

def main():
    """Hauptfunktion"""
    print("🤖 Detektiv Pikachu Bot Launcher")
    print("=" * 35)
    print()
    
    # Prüfe ob .env existiert
    env_path = BASE_DIR / '.env'
    if not env_path.exists():
        print("📄 Keine Konfigurationsdatei gefunden!")
        print()
        
        response = input("Möchtest du jetzt die Bot-Tokens eingeben? (J/N): ").lower()
        if response != 'j':
            print("❌ Bot kann ohne Tokens nicht gestartet werden.")
            print("💡 Erstelle eine .env Datei oder starte das Programm erneut.")
            sys.exit(1)
        
        print()
        if not simple_setup():
            print("❌ Setup fehlgeschlagen!")
            sys.exit(1)
    
    # Lade Konfiguration und prüfe Tokens
    try:
        # Nach Setup: direkte Validierung der Umgebungsvariablen
        primary_token = os.getenv('PRIMARY_BOT_TOKEN')
        secondary_token = os.getenv('SECONDARY_BOT_TOKEN') 
        admin_user_id = os.getenv('ADMIN_USER_ID')
        
        missing = []
        if not primary_token:
            missing.append('PRIMARY_BOT_TOKEN')
        if not secondary_token:
            missing.append('SECONDARY_BOT_TOKEN')
        if not admin_user_id or admin_user_id == '0':
            missing.append('ADMIN_USER_ID')
        
        if missing:
            print("❌ Ungültige Konfiguration!")
            print(f"Fehlende Einstellungen: {', '.join(missing)}")
            print()
            print("💡 Lösung: Lösche die .env Datei und starte erneut für neue Token-Eingabe")
            sys.exit(1)
            
        print("✅ Konfiguration validiert")
        
    except Exception as e:
        print(f"❌ Konfigurationsfehler: {e}")
        print("💡 Lösung: Lösche die .env Datei und starte erneut")
        sys.exit(1)
    
    # Bots starten
    launcher = BotLauncher()
    
    try:
        asyncio.run(launcher.run_bots())
    except KeyboardInterrupt:
        print("\n🛑 Bot-System wird beendet...")
    except Exception as e:
        print(f"\n❌ Unerwarteter Fehler: {e}")
        print("🔍 Überprüfe die Log-Dateien für weitere Details")
        sys.exit(1)
    finally:
        print("👋 Bot-System beendet")

if __name__ == "__main__":
    main() 