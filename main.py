import discord
import logging
import sys
import time
import random
from pathlib import Path
from datetime import datetime
from core.bot_core import StatusBot
from config.constants import BotConstants
from cogs import setup_cogs
import asyncio
from core.log_manager import setup_bot_logging

def setup_logging():
    """Konfiguriert das erweiterte Logging-System"""
    # Verwende den neuen AdvancedLogManager
    return setup_bot_logging('MainBot', logging.INFO)

class BotTokenBalancer:
    def __init__(self, primary_token, secondary_token, cooldown_time=60, max_retries=3):
        self.primary_token = primary_token
        self.secondary_token = secondary_token
        self.cooldown_time = cooldown_time  # Zeit in Sekunden
        self.max_retries = max_retries
        self.using_primary = True
        self.primary_blocked_until = 0
        self.retry_count = 0
        self.gradual_return_chance = 0.0  # Wahrscheinlichkeit für graduelle Rückkehr
        self.logger = logging.getLogger('StatusBot')
        
        # Status-Speicherung
        self.status_file = BotConstants.DATA_DIR / 'json' / 'token_balancer_status.json'
        self.load_status()
        
    def load_status(self):
        """Lädt den gespeicherten Status des Balancers, falls vorhanden"""
        try:
            if self.status_file.exists():
                import json
                with open(self.status_file, 'r') as f:
                    status = json.load(f)
                    self.using_primary = status.get('using_primary', True)
                    self.primary_blocked_until = status.get('primary_blocked_until', 0)
                    
                    # Nur beachten, wenn die Blockierung noch nicht abgelaufen ist
                    current_time = time.time()
                    if current_time >= self.primary_blocked_until:
                        self.using_primary = True
                        
                    self.logger.info(f"Balancer Status geladen: Primärer Bot {'aktiv' if self.using_primary else 'blockiert bis ' + datetime.fromtimestamp(self.primary_blocked_until).strftime('%H:%M:%S')}")
        except Exception as e:
            self.logger.warning(f"Fehler beim Laden des Balancer-Status: {e}")
            
    def save_status(self):
        """Speichert den aktuellen Status des Balancers"""
        try:
            import json
            with open(self.status_file, 'w') as f:
                status = {
                    'using_primary': self.using_primary,
                    'primary_blocked_until': self.primary_blocked_until,
                    'last_updated': time.time()
                }
                json.dump(status, f)
        except Exception as e:
            self.logger.warning(f"Fehler beim Speichern des Balancer-Status: {e}")
        
    def get_current_token(self):
        """Gibt das aktuell zu verwendende Token zurück"""
        current_time = time.time()
        
        # Wenn der primäre Bot blockiert ist, aber die graduelle Rückkehr begonnen hat
        if not self.using_primary and current_time < self.primary_blocked_until and self.gradual_return_chance > 0:
            # Mit zunehmender Wahrscheinlichkeit zum primären Bot zurückkehren
            if random.random() < self.gradual_return_chance:
                self.logger.info(f"Graduelle Rückkehr zum primären Bot (Chance: {self.gradual_return_chance:.1%})")
                return self.primary_token
        
        # Wenn der primäre Bot nicht blockiert ist oder die Cooldown-Zeit abgelaufen ist
        if current_time >= self.primary_blocked_until:
            if not self.using_primary:
                self.logger.info("Cooldown abgelaufen, wechsle zurück zum primären Bot")
                self.using_primary = True
                self.save_status()
            return self.primary_token
        
        # Sonst verwende den sekundären Bot
        return self.secondary_token
    
    def handle_rate_limit(self, retry_after=None):
        """Wechselt zum sekundären Bot, wenn der primäre ein Rate Limit erreicht"""
        if retry_after is None:
            retry_after = self.cooldown_time
            
        if self.using_primary:
            # Setze Zeitpunkt, wann der primäre Bot wieder verwendet werden kann
            self.primary_blocked_until = time.time() + retry_after
            self.using_primary = False
            
            # Starte graduelle Rückkehr nach 2/3 der Wartezeit
            def start_gradual_return():
                time.sleep(retry_after * 2/3)
                self.gradual_return_chance = 0.1  # Starte mit 10% Chance
                
                # Erhöhe die Chance schrittweise
                for _ in range(5):
                    time.sleep(retry_after / 15)  # 5 Schritte im letzten Drittel
                    self.gradual_return_chance += 0.15
                    self.logger.debug(f"Graduelle Rückkehr Chance erhöht auf {self.gradual_return_chance:.1%}")
            
            # Starte den graduellen Rückkehr-Prozess in einem separaten Thread
            import threading
            threading.Thread(target=start_gradual_return, daemon=True).start()
            
            self.save_status()
            return self.secondary_token
        
        # Wenn bereits der sekundäre Bot verwendet wird
        return None
    
    def handle_connection_error(self):
        """Behandelt Verbindungsfehler durch Erhöhen des Retry-Zählers"""
        self.retry_count += 1
        if self.retry_count >= self.max_retries:
            # Bei zu vielen Fehlern zum anderen Bot wechseln
            self.retry_count = 0
            if self.using_primary:
                self.logger.warning(f"Maximale Anzahl an Verbindungsversuchen ({self.max_retries}) mit primärem Bot erreicht. Wechsle zum sekundären Bot.")
                return self.handle_rate_limit(self.cooldown_time / 2)  # Kürzere Blockierzeit bei Verbindungsfehlern
            else:
                self.logger.warning(f"Maximale Anzahl an Verbindungsversuchen ({self.max_retries}) mit sekundärem Bot erreicht. Wechsle zum primären Bot.")
                self.using_primary = True
                self.primary_blocked_until = 0
                self.save_status()
                return self.primary_token
        
        self.logger.warning(f"Verbindungsfehler, Versuch {self.retry_count}/{self.max_retries}. Warte vor nächstem Versuch...")
        return None  # Kein Token-Wechsel, nur Retry-Zähler erhöht
    
    def is_using_primary(self):
        """Gibt zurück, ob der primäre Bot aktuell verwendet wird"""
        return self.using_primary
        
    def get_status_text(self):
        """Gibt einen lesbaren Status des Balancers zurück"""
        if self.using_primary:
            return "Primärer Bot aktiv"
        else:
            remaining = max(0, self.primary_blocked_until - time.time())
            return f"Sekundärer Bot aktiv (Primärer Bot blockiert für weitere {int(remaining)} Sekunden)"

if __name__ == "__main__":
    # Setup Logging
    logger = setup_logging()
    
    # Performance-Tracking
    start_time = time.time()
    logger.info("=== Bot-Start initialisiert ===")
    
    # Initialisiere Token Balancer
    token_balancer = BotTokenBalancer(
        BotConstants.PRIMARY_BOT_TOKEN,
        BotConstants.SECONDARY_BOT_TOKEN,
        BotConstants.RATE_LIMIT_COOL_DOWN,
        BotConstants.MAX_RETRIES
    )
    
    logger.info("Starting bot initialization")
    
    while True:  # Endlosschleife für automatische Wiederverbindungsversuche
        try:
            # Erstelle Bot-Instanz
            init_start = time.time()
            logger.debug("Creating StatusBot instance")  
            bot = StatusBot()
            
            # Füge den Token-Balancer zum Bot hinzu, damit er über Befehle zugänglich ist
            bot.token_balancer = token_balancer
            
            # Cogs werden jetzt in setup_hook() geladen - nicht hier!
            init_time = time.time() - init_start
            logger.info(f"Bot instance created successfully (took {init_time:.2f}s)")
            
            # Starte den Bot mit dem aktuellen Token
            logger.info(f"Bot initialized, attempting to run ({token_balancer.get_status_text()})")
            total_init_time = time.time() - start_time
            logger.info(f"=== Gesamte Initialisierung: {total_init_time:.2f}s ===")
            
            current_token = token_balancer.get_current_token()
            bot.run(current_token, reconnect=True)
            
            # Wenn bot.run() normal beendet wird (was ungewöhnlich ist)
            logger.warning("Bot run ended normally, restarting in 5 seconds...")
            time.sleep(5)
            
        except discord.RateLimited as e:
            # Bei Rate Limit, versuche mit dem sekundären Bot
            logger.warning(f"Rate limit reached. Retry after: {e.retry_after} seconds")
            alternate_token = token_balancer.handle_rate_limit(e.retry_after)
            
            if alternate_token:
                logger.info("Switching to secondary bot token due to rate limit")
                time.sleep(1)  # Kurze Pause vor dem Neustart
                # Die Schleife wird den Bot mit dem neuen Token neu starten
            else:
                logger.critical("Both bots are rate limited. Waiting before retry...")
                time.sleep(min(e.retry_after, 60))  # Warte maximal 60 Sekunden
                
        except discord.LoginFailure:
            logger.critical("Failed to login. Please check if the token is correct.")
            alternate_token = token_balancer.handle_connection_error()
            if alternate_token:
                logger.info("Trying alternate token due to login failure")
                time.sleep(2)  # Kurze Pause vor dem Neustart
            else:
                # Beide Tokens funktionieren nicht, längere Pause
                logger.critical("Both tokens failed to login. Waiting 30 seconds before retry...")
                time.sleep(30)
                
        except (discord.ConnectionClosed, discord.GatewayNotFound, discord.HTTPException) as e:
            logger.error(f"Connection error: {e}")
            alternate_token = token_balancer.handle_connection_error()
            
            if alternate_token:
                logger.info("Switching bot token due to connection error")
                time.sleep(2)
            else:
                # Keine Token-Änderung, nur kurze Pause vor dem Neuversuch
                wait_time = min(5 * token_balancer.retry_count, 30)  # Erhöhe die Wartezeit mit jedem Versuch
                logger.warning(f"Connection error, retrying in {wait_time} seconds...")
                time.sleep(wait_time)
                
        except Exception as e:
            logger.exception(f"An unexpected error occurred: {e}")
            # Bei unbekannten Fehlern längere Pause und kein automatischer Token-Wechsel
            logger.critical("Waiting 60 seconds before restarting due to unexpected error")
            time.sleep(60)
