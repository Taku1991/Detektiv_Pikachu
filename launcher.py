#!/usr/bin/env python3
"""
Detektiv Pikachu Bot Launcher
Startet sowohl den Haupt-Bot als auch den Helper-Bot gleichzeitig
"""

import asyncio
import logging
import sys
import threading
import time
from pathlib import Path
from datetime import datetime

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
            # Token Balancer erstellen
            self.token_balancer = BotTokenBalancer(
                BotConstants.PRIMARY_BOT_TOKEN,
                BotConstants.SECONDARY_BOT_TOKEN,
                BotConstants.RATE_LIMIT_COOL_DOWN,
                BotConstants.MAX_RETRIES
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
            await self.helper_bot.start(BotConstants.SECONDARY_BOT_TOKEN)
            
        except Exception as e:
            self.helper_logger.error(f"Helper-Bot Fehler: {e}", exc_info=True)
            raise

    async def run_bots(self):
        """Startet beide Bots gleichzeitig"""
        try:
            print("[LAUNCHER] Starte beide Bots...")
            
            # Erstelle Tasks für beide Bots
            main_task = asyncio.create_task(self.start_main_bot())
            helper_task = asyncio.create_task(self.start_helper_bot())
            
            # Warte auf beide Tasks
            done, pending = await asyncio.wait(
                [main_task, helper_task],
                return_when=asyncio.FIRST_EXCEPTION
            )
            
            # Überprüfe auf Fehler
            for task in done:
                if task.exception():
                    print(f"[ERROR] Bot-Task fehlgeschlagen: {task.exception()}")
                    
                    # Stoppe die anderen Tasks
                    for pending_task in pending:
                        pending_task.cancel()
                        try:
                            await pending_task
                        except asyncio.CancelledError:
                            pass
                    
                    raise task.exception()
            
        except Exception as e:
            print(f"[ERROR] Bot-Ausführung fehlgeschlagen: {e}")
            raise

    def run(self):
        """Hauptfunktion zum Starten der Bots"""
        try:
            print("=" * 50)
            print("[LAUNCHER] Detektiv Pikachu Bot Launcher")
            print(f"[LAUNCHER] Gestartet um: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("=" * 50)
            
            # Setup
            self.setup_logging()
            self.create_bots()
            
            # Starte beide Bots
            asyncio.run(self.run_bots())
            
        except KeyboardInterrupt:
            print("\n[LAUNCHER] Shutdown durch Benutzer...")
        except Exception as e:
            print(f"[ERROR] Launcher-Fehler: {e}")
            return 1
        finally:
            print("[LAUNCHER] Shutdown abgeschlossen.")
            
        return 0

def main():
    """Haupteinstiegspunkt"""
    launcher = BotLauncher()
    return launcher.run()

if __name__ == '__main__':
    sys.exit(main()) 