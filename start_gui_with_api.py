#!/usr/bin/env python3
"""
Detektiv Pikachu Bot GUI + API Starter
Startet sowohl die GUI als auch die API automatisch
"""

import sys
import os
from pathlib import Path
import threading
import asyncio
from core.bot_core import StatusBot
from config.constants import BotConstants

def start_main_bot():
    bot = StatusBot()
    asyncio.run(bot.start(BotConstants.PRIMARY_BOT_TOKEN))

def main():
    print("🔍 Detektiv Pikachu Bot - GUI + API Starter")
    print("=" * 50)
    try:
        # Importiere und starte die GUI (die automatisch die API mitstartet)
        from gui.main_window import MainWindow

        print("🚀 Starte GUI mit integrierter API...")
        print("📡 API wird automatisch auf Port 7000 gestartet")
        print("🌐 API-Endpunkte:")
        print("   • http://localhost:7000/api/status")
        print("   • http://localhost:7000/api/status/summary")
        print("   • http://localhost:7000/api/status/channels")
        print("   • http://localhost:7000/api/health")
        print("")

        # Starte GUI
        gui = MainWindow()
        gui.run()

    except KeyboardInterrupt:
        print("\n👋 Anwendung durch Benutzer beendet")
    except ImportError as e:
        print(f"❌ Import-Fehler: {e}")
        print("💡 Stelle sicher, dass alle Dependencies installiert sind:")
        print("   pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Fehler beim Starten: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main() 