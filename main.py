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
import os

if getattr(sys, 'frozen', False):
    base_dir = Path(sys.executable).parent
else:
    base_dir = Path(__file__).parent

logs_dir = base_dir / "logs"
logs_dir.mkdir(exist_ok=True)
print("Logs-Verzeichnis:", logs_dir)

def setup_logging():
    """Konfiguriert das erweiterte Logging-System"""
    # Verwende den neuen AdvancedLogManager
    return setup_bot_logging('StatusBot', logging.DEBUG)

# Setup Logging HIER - NICHT im if __name__ == "__main__":
print("Aktuelles Arbeitsverzeichnis:", os.getcwd())
print("Existiert logs?:", os.path.exists("logs"))
os.makedirs("logs", exist_ok=True)
logger = setup_logging()

# Test-Logs schreiben
logger.debug("Logger-Setup abgeschlossen")
logger.info("StatusBot Logger initialisiert")

class BotTokenBalancer:
    def __init__(self, primary_token, secondary_token, cooldown_time=60, max_retries=3):
        self.primary_token = primary_token
        self.secondary_token = secondary_token
        self.cooldown_time = cooldown_time  # Zeit in Sekunden
        self.max_retries = max_retries
        self.using_primary = True
        self.primary_blocked_until = 0
        self.retry_count = 0
        self.current_session_token = None  # Token-Lock: Welches Token nutzt die aktuelle Bot-Session
        self.logger = logging.getLogger('StatusBot')
        self.bot = None  # Wird später vom Bot gesetzt für History-Logging
        
        # Status-Speicherung
        self.status_file = BotConstants.DATA_DIR / 'json' / 'token_balancer_status.json'
        
        # Statistiken für Monitoring
        self.stats = {
            'total_switches': 0,
            'rate_limit_switches': 0,
            'connection_error_switches': 0,
            'gradual_return_switches': 0,
            'primary_uptime': 0,
            'secondary_uptime': 0,
            'last_reset': time.time(),
            'switches_last_hour': [],
            'daily_stats': {}
        }
        
        self.load_status()
        
    def load_status(self):
        """Lädt den gespeicherten Status des Balancers mit File-Locking"""
        try:
            if self.status_file.exists():
                import json
                from filelock import FileLock, Timeout

                lock_path = self.status_file.with_suffix('.lock')
                try:
                    with FileLock(lock_path, timeout=10):
                        with open(self.status_file, 'r', encoding='utf-8') as f:
                            status = json.load(f)
                            self.using_primary = status.get('using_primary', True)
                            self.primary_blocked_until = status.get('primary_blocked_until', 0)

                            # Lade Statistiken falls vorhanden
                            if 'stats' in status:
                                self.stats.update(status['stats'])

                            # Nur beachten, wenn die Blockierung noch nicht abgelaufen ist
                            current_time = time.time()
                            if current_time >= self.primary_blocked_until:
                                self.using_primary = True

                            self.logger.info(f"Balancer Status geladen: Primärer Bot {'aktiv' if self.using_primary else 'blockiert bis ' + datetime.fromtimestamp(self.primary_blocked_until).strftime('%H:%M:%S')}")
                except Timeout:
                    self.logger.error(f"Timeout beim Laden des Balancer-Status - andere Instanz blockiert Datei")
        except Exception as e:
            self.logger.warning(f"Fehler beim Laden des Balancer-Status: {e}")
            
    def save_status(self):
        """Speichert den aktuellen Status des Balancers mit File-Locking"""
        try:
            import json
            from filelock import FileLock, Timeout

            # Stelle sicher, dass das Verzeichnis existiert
            self.status_file.parent.mkdir(parents=True, exist_ok=True)

            lock_path = self.status_file.with_suffix('.lock')
            try:
                with FileLock(lock_path, timeout=10):
                    with open(self.status_file, 'w', encoding='utf-8') as f:
                        status = {
                            'using_primary': self.using_primary,
                            'primary_blocked_until': self.primary_blocked_until,
                            'last_updated': time.time(),
                            'stats': self.stats
                        }
                        json.dump(status, f, indent=2)
            except Timeout:
                self.logger.error(f"Timeout beim Speichern des Balancer-Status - andere Instanz blockiert Datei")
        except Exception as e:
            self.logger.warning(f"Fehler beim Speichern des Balancer-Status: {e}")
        
    def get_current_token(self):
        """
        Gibt das Token für den Bot-Start zurück.
        WICHTIG: Dieses Token wird für die gesamte Bot-Session verwendet!
        Token-Wechsel passieren nur durch Bot-Neustart.
        """
        current_time = time.time()

        # Prüfe zuerst, ob der gespeicherte Status noch gültig ist
        self._validate_stored_status()

        # Wenn bereits eine Session läuft, gib das gelockte Token zurück
        if self.current_session_token:
            self.logger.debug(f"Session-Token ist gelockt: {'Primär' if self.current_session_token == self.primary_token else 'Sekundär'}")
            return self.current_session_token

        # Neuer Bot-Start: Entscheide welches Token verwendet wird
        # Wenn der primäre Bot blockiert ist, verwende sekundären Bot
        if current_time < self.primary_blocked_until:
            remaining = int(self.primary_blocked_until - current_time)
            self.logger.info(f"Primärer Bot ist blockiert für weitere {remaining}s - verwende sekundären Bot")
            token = self.secondary_token
            self.using_primary = False
        else:
            # Cooldown ist vorbei oder primärer Bot war nie blockiert
            if not self.using_primary:
                self.logger.info("✅ Cooldown abgelaufen - zurück zum primären Bot")
            token = self.primary_token
            self.using_primary = True
            self.primary_blocked_until = 0

        # Locke das Token für diese Session
        self.current_session_token = token
        self.save_status()

        token_name = "Primärer Bot" if token == self.primary_token else "Sekundärer Bot"
        self.logger.info(f"🔒 Token gelockt für diese Session: {token_name}")

        return token
    
    def _validate_stored_status(self):
        """Validiert den gespeicherten Status gegen die aktuelle Zeit"""
        try:
            current_time = time.time()

            # Wenn der primäre Bot blockiert sein sollte, aber die Zeit abgelaufen ist
            if self.primary_blocked_until > 0 and current_time >= self.primary_blocked_until:
                if not self.using_primary:
                    self.logger.info("🔄 Blockierzeit abgelaufen - Status auf primären Bot korrigiert")
                    self.using_primary = True
                    self.primary_blocked_until = 0
                    self.save_status()

            # Wenn der Status inkonsistent ist (primärer Bot aktiv aber blockiert)
            if self.using_primary and self.primary_blocked_until > current_time:
                self.logger.warning("⚠️ Inkonsistenter Status erkannt - primärer Bot ist blockiert aber aktiv")
                self.using_primary = False
                self.save_status()

        except Exception as e:
            self.logger.error(f"Fehler bei der Status-Validierung: {e}")
    
    def force_token_switch(self, use_primary: bool, duration: int = 0, reason: str = "Manueller Wechsel"):
        """
        Erzwingt einen Token-Wechsel (für Notfälle und Tests).
        WICHTIG: Bot muss neu gestartet werden, damit der Wechsel wirksam wird!
        """
        try:
            old_status = self.get_status_text()

            if use_primary:
                self.using_primary = True
                self.primary_blocked_until = 0
                self.logger.info(f"🔧 Erzwinge primären Bot: {reason}")
            else:
                self.using_primary = False
                if duration > 0:
                    self.primary_blocked_until = time.time() + duration
                    self.logger.info(f"🔧 Erzwinge sekundären Bot für {duration}s: {reason}")
                else:
                    self.primary_blocked_until = time.time() + self.cooldown_time
                    self.logger.info(f"🔧 Erzwinge sekundären Bot: {reason}")

            self.retry_count = 0
            self.current_session_token = None  # Unlock für nächste Session
            self.save_status()

            # Log den manuellen Wechsel
            if self.bot:
                def log_switch():
                    try:
                        import asyncio
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        loop.run_until_complete(self.log_token_switch(
                            "unknown",
                            self.primary_token if self.using_primary else self.secondary_token,
                            f"Manueller Wechsel: {reason} (Bot-Neustart erforderlich!)"
                        ))
                        loop.close()
                    except Exception as e:
                        self.logger.error(f"Fehler beim History-Log: {e}")

                import threading
                threading.Thread(target=log_switch, daemon=True).start()

            new_status = self.get_status_text()
            self.logger.warning(f"⚠️ Token-Wechsel vorbereitet: '{old_status}' -> '{new_status}' - BOT MUSS NEU STARTEN!")

            return True

        except Exception as e:
            self.logger.error(f"Fehler beim erzwungenen Token-Wechsel: {e}")
            return False
    
    def get_real_discord_status(self):
        """Prüft den echten Discord API Status (falls Bot verfügbar)"""
        try:
            if not self.bot:
                return None
                
            # Prüfe Bot-Status
            status_info = {
                'is_ready': self.bot.is_ready() if hasattr(self.bot, 'is_ready') else False,
                'is_closed': self.bot.is_closed() if hasattr(self.bot, 'is_closed') else True,
                'latency': self.bot.latency if hasattr(self.bot, 'latency') else -1,
                'guild_count': len(self.bot.guilds) if hasattr(self.bot, 'guilds') else 0,
                'user_name': str(self.bot.user) if hasattr(self.bot, 'user') and self.bot.user else "Unknown"
            }
            
            # Log den echten Status
            self.logger.debug(f"🔍 Discord API Status: Ready={status_info['is_ready']}, "
                            f"Closed={status_info['is_closed']}, Latency={status_info['latency']:.2f}ms, "
                            f"Guilds={status_info['guild_count']}, User={status_info['user_name']}")
            
            return status_info
            
        except Exception as e:
            self.logger.error(f"Fehler beim Prüfen des Discord API Status: {e}")
            return None
    
    def handle_rate_limit(self, retry_after=None):
        """
        Markiert primären Bot als blockiert wegen Rate Limit.
        Bot muss neu starten, um zum sekundären Token zu wechseln.
        """
        if retry_after is None:
            retry_after = self.cooldown_time

        if self.using_primary:
            # Setze Zeitpunkt, wann der primäre Bot wieder verwendet werden kann
            self.primary_blocked_until = time.time() + retry_after
            self.using_primary = False
            self.current_session_token = None  # Unlock für Bot-Neustart

            # Update Statistiken
            self.update_stats('rate_limit')

            self.logger.warning(f"⚠️ Rate Limit auf primärem Bot! Blockiert für {retry_after}s")
            self.logger.info("🔄 Bot wird neu starten mit sekundärem Token...")

            # Log Token-Wechsel
            if self.bot:
                def log_switch():
                    try:
                        import asyncio
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        loop.run_until_complete(self.log_token_switch(
                            self.primary_token,
                            self.secondary_token,
                            f"Rate Limit erreicht (Blockiert für {retry_after}s)"
                        ))
                        loop.close()
                    except Exception as e:
                        self.logger.error(f"Fehler beim History-Log: {e}")

                import threading
                threading.Thread(target=log_switch, daemon=True).start()

            self.save_status()
            return self.secondary_token

        # Wenn bereits der sekundäre Bot verwendet wird
        self.logger.warning("⚠️ Rate Limit auf sekundärem Bot - beide Bots sind blockiert!")
        return None
    
    def handle_connection_error(self):
        """
        Behandelt Verbindungsfehler durch Erhöhen des Retry-Zählers.
        Bei zu vielen Fehlern wird Bot-Neustart mit anderem Token initiiert.
        """
        self.retry_count += 1
        if self.retry_count >= self.max_retries:
            # Bei zu vielen Fehlern zum anderen Bot wechseln
            self.retry_count = 0
            self.current_session_token = None  # Unlock für Bot-Neustart

            if self.using_primary:
                self.logger.warning(f"❌ {self.max_retries} Verbindungsfehler mit primärem Bot - wechsle zu sekundär")
                return self.handle_rate_limit(self.cooldown_time / 2)  # Kürzere Blockierzeit bei Verbindungsfehlern
            else:
                self.logger.warning(f"❌ {self.max_retries} Verbindungsfehler mit sekundärem Bot - wechsle zu primär")

                # Update Statistiken
                self.update_stats('connection_error')

                # Log Token-Wechsel bei Connection-Error
                if self.bot:
                    def log_switch():
                        try:
                            import asyncio
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            loop.run_until_complete(self.log_token_switch(
                                self.secondary_token,
                                self.primary_token,
                                f"Verbindungsfehler - {self.max_retries} Versuche fehlgeschlagen"
                            ))
                            loop.close()
                        except Exception as e:
                            self.logger.error(f"Fehler beim History-Log: {e}")

                    import threading
                    threading.Thread(target=log_switch, daemon=True).start()

                self.using_primary = True
                self.primary_blocked_until = 0
                self.save_status()
                return self.primary_token

        self.logger.warning(f"⚠️ Verbindungsfehler {self.retry_count}/{self.max_retries} - Retry...")
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
    
    async def log_token_switch(self, from_token, to_token, reason):
        """Loggt Token-Wechsel im History Channel"""
        try:
            if not self.bot or not hasattr(self.bot, 'history_channel_id') or not self.bot.history_channel_id:
                return
                
            history_channel = self.bot.get_channel(self.bot.history_channel_id)
            if not history_channel:
                self.logger.warning("History Channel nicht gefunden für Token-Wechsel-Log")
                return
            
            import discord
            from datetime import datetime
            
            # Bestimme Token-Namen für bessere Lesbarkeit
            from_name = "Primärer Bot" if from_token == self.primary_token else "Sekundärer Bot"
            to_name = "Primärer Bot" if to_token == self.primary_token else "Sekundärer Bot"
            
            # Farbe basierend auf Wechsel-Richtung
            color = 0x00ff00 if to_token == self.primary_token else 0xff9900  # Grün für zurück zu Primary, Orange für zu Secondary
            
            embed = discord.Embed(
                title="⚖️ Token Balancer - Wechsel",
                description=f"Bot-Token wurde automatisch gewechselt",
                color=color,
                timestamp=discord.utils.utcnow()
            )
            
            embed.add_field(name="Von", value=from_name, inline=True)
            embed.add_field(name="Zu", value=to_name, inline=True)
            embed.add_field(name="Grund", value=reason, inline=True)
            
            if not self.using_primary:
                remaining = max(0, self.primary_blocked_until - time.time())
                embed.add_field(name="Blockiert für", value=f"{int(remaining)} Sekunden", inline=True)
            
            embed.add_field(name="Retry Count", value=f"{self.retry_count}/{self.max_retries}", inline=True)
            embed.add_field(name="Source", value="Token Balancer", inline=True)
            
            await history_channel.send(embed=embed)
            self.logger.info(f"Token-Wechsel im History Channel geloggt: {from_name} -> {to_name}")
            
        except Exception as e:
            self.logger.error(f"Fehler beim Loggen des Token-Wechsels: {e}", exc_info=True)
    
    def update_stats(self, switch_type):
        """Aktualisiert die Statistiken für Token-Wechsel"""
        try:
            current_time = time.time()
            
            # Gesamtzähler
            self.stats['total_switches'] += 1
            
            # Nach Typ
            if switch_type == 'rate_limit':
                self.stats['rate_limit_switches'] += 1
            elif switch_type == 'connection_error':
                self.stats['connection_error_switches'] += 1
            elif switch_type == 'gradual_return':
                self.stats['gradual_return_switches'] += 1
            
            # Stündliche Statistiken (für Rate-Limit-Monitoring)
            self.stats['switches_last_hour'].append(current_time)
            # Entferne Einträge älter als 1 Stunde
            hour_ago = current_time - 3600
            self.stats['switches_last_hour'] = [t for t in self.stats['switches_last_hour'] if t > hour_ago]
            
            # Tagesstatistiken
            from datetime import datetime
            today = datetime.fromtimestamp(current_time).strftime('%Y-%m-%d')
            if today not in self.stats['daily_stats']:
                self.stats['daily_stats'][today] = {'switches': 0, 'rate_limits': 0}
            
            self.stats['daily_stats'][today]['switches'] += 1
            if switch_type == 'rate_limit':
                self.stats['daily_stats'][today]['rate_limits'] += 1
            
            # Behalte nur letzte 30 Tage
            if len(self.stats['daily_stats']) > 30:
                oldest_date = min(self.stats['daily_stats'].keys())
                del self.stats['daily_stats'][oldest_date]
            
            self.save_status()
            
            # Warnung bei zu vielen Wechseln
            switches_last_hour = len(self.stats['switches_last_hour'])
            if switches_last_hour >= 10:
                self.logger.warning(f"⚠️ ACHTUNG: {switches_last_hour} Token-Wechsel in der letzten Stunde! Möglicherweise 2. Helper Bot nötig.")
                if self.bot:
                    self._log_performance_warning(switches_last_hour)
            
        except Exception as e:
            self.logger.error(f"Fehler beim Aktualisieren der Statistiken: {e}")
    
    def _log_performance_warning(self, switches_last_hour):
        """Loggt Performance-Warnung im History Channel"""
        try:
            def log_warning():
                try:
                    import asyncio
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(self._send_performance_warning(switches_last_hour))
                    loop.close()
                except Exception as e:
                    self.logger.error(f"Fehler beim Performance-Warning-Log: {e}")
            
            import threading
            threading.Thread(target=log_warning, daemon=True).start()
        except Exception as e:
            self.logger.error(f"Fehler beim Erstellen des Performance-Warning-Threads: {e}")
    
    async def _send_performance_warning(self, switches_last_hour):
        """Sendet Performance-Warnung an History Channel"""
        try:
            if not self.bot or not self.bot.history_channel_id:
                return
                
            history_channel = self.bot.get_channel(self.bot.history_channel_id)
            if not history_channel:
                return
            
            import discord
            
            embed = discord.Embed(
                title="⚠️ Token Balancer - Performance Warnung",
                description=f"**{switches_last_hour} Token-Wechsel in der letzten Stunde!**",
                color=0xff0000,  # Rot für Warnung
                timestamp=discord.utils.utcnow()
            )
            
            embed.add_field(name="Status", value="Hohe API-Belastung erkannt", inline=True)
            embed.add_field(name="Empfehlung", value="🤖 2. Helper Bot in Betracht ziehen", inline=True)
            embed.add_field(name="Rate Limits", value=f"{self.stats['rate_limit_switches']} gesamt", inline=True)
            
            # Berechne durchschnittliche Wechsel pro Tag
            if self.stats['daily_stats']:
                avg_switches = sum(day['switches'] for day in self.stats['daily_stats'].values()) / len(self.stats['daily_stats'])
                embed.add_field(name="Ø Wechsel/Tag", value=f"{avg_switches:.1f}", inline=True)
            
            embed.add_field(name="Aktion erforderlich", value="🔍 System-Performance überprüfen", inline=False)
            
            await history_channel.send(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Fehler beim Senden der Performance-Warnung: {e}")
    
    def get_performance_stats(self):
        """Gibt Performance-Statistiken zurück"""
        try:
            current_time = time.time()
            uptime_hours = (current_time - self.stats['last_reset']) / 3600
            
            switches_last_hour = len(self.stats['switches_last_hour'])
            rate_limit_ratio = (self.stats['rate_limit_switches'] / max(1, self.stats['total_switches'])) * 100
            
            return {
                'total_switches': self.stats['total_switches'],
                'switches_last_hour': switches_last_hour,
                'rate_limit_ratio': rate_limit_ratio,
                'uptime_hours': uptime_hours,
                'needs_second_helper': switches_last_hour >= 10 or rate_limit_ratio >= 30
            }
        except Exception as e:
            self.logger.error(f"Fehler beim Abrufen der Performance-Statistiken: {e}")
            return None
    
    async def send_daily_summary(self):
        """Sendet eine tägliche Zusammenfassung der Token Balancer Performance"""
        try:
            if not self.bot or not self.bot.history_channel_id:
                return
                
            history_channel = self.bot.get_channel(self.bot.history_channel_id)
            if not history_channel:
                return
            
            import discord
            from datetime import datetime, timedelta
            
            today = datetime.now().strftime('%Y-%m-%d')
            yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
            
            today_stats = self.stats['daily_stats'].get(today, {'switches': 0, 'rate_limits': 0})
            yesterday_stats = self.stats['daily_stats'].get(yesterday, {'switches': 0, 'rate_limits': 0})
            
            # Nur senden wenn es Aktivität gab
            if today_stats['switches'] == 0 and yesterday_stats['switches'] == 0:
                return
            
            embed = discord.Embed(
                title="📊 Token Balancer - Tägliche Zusammenfassung",
                description=f"Performance-Bericht für {today}",
                color=0x3498db,
                timestamp=discord.utils.utcnow()
            )
            
            embed.add_field(name="Wechsel heute", value=f"{today_stats['switches']}", inline=True)
            embed.add_field(name="Rate Limits heute", value=f"{today_stats['rate_limits']}", inline=True)
            embed.add_field(name="Gesamt Wechsel", value=f"{self.stats['total_switches']}", inline=True)
            
            # Vergleich zu gestern
            switch_change = today_stats['switches'] - yesterday_stats['switches']
            if switch_change > 0:
                trend = f"📈 +{switch_change} vs. gestern"
                if switch_change > 5:
                    embed.color = 0xe67e22  # Orange bei starkem Anstieg
            elif switch_change < 0:
                trend = f"📉 {switch_change} vs. gestern"
            else:
                trend = "➡️ Gleich wie gestern"
            
            embed.add_field(name="Trend", value=trend, inline=True)
            
            # Warnung bei kritischen Werten
            if today_stats['switches'] > 20:
                embed.add_field(
                    name="⚠️ Achtung", 
                    value="Hohe Anzahl an Token-Wechseln!\n🤖 2. Helper Bot empfohlen", 
                    inline=False
                )
                embed.color = 0xe74c3c  # Rot bei kritischen Werten
            
            # Rate Limit Prozentsatz
            if today_stats['switches'] > 0:
                rate_limit_percent = (today_stats['rate_limits'] / today_stats['switches']) * 100
                embed.add_field(name="Rate Limit %", value=f"{rate_limit_percent:.1f}%", inline=True)
            
            # Durchschnitt letzte 7 Tage
            recent_days = sorted(self.stats['daily_stats'].keys())[-7:]
            if len(recent_days) >= 3:
                avg_switches = sum(self.stats['daily_stats'][day]['switches'] for day in recent_days) / len(recent_days)
                embed.add_field(name="Ø letzte 7 Tage", value=f"{avg_switches:.1f}", inline=True)
            
            await history_channel.send(embed=embed)
            self.logger.info("Tägliche Token Balancer Zusammenfassung gesendet")
            
        except Exception as e:
            self.logger.error(f"Fehler beim Senden der täglichen Zusammenfassung: {e}")

if __name__ == "__main__":
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
    
    logger.info("TEST: MainBot-Logger wurde initialisiert!")

    # Schreibe direkt in die Datei, um Rechte/Verzeichnis zu testen
    with open(logs_dir / "mainbot.log", "a", encoding="utf-8") as f:
        f.write("TEST: Direkter Dateizugriff funktioniert!\n")

    for handler in logger.handlers:
        logger.info(f"Logger-Handler aktiv: {handler} (Typ: {type(handler)})")
    
    while True:  # Endlosschleife für automatische Wiederverbindungsversuche
        try:
            # Reset Session-Token für neuen Start
            token_balancer.current_session_token = None

            # Erstelle Bot-Instanz
            init_start = time.time()
            logger.debug("Creating StatusBot instance")
            bot = StatusBot()

            # Füge den Token-Balancer zum Bot hinzu, damit er über Befehle zugänglich ist
            bot.token_balancer = token_balancer
            # Füge Bot-Referenz zum Token Balancer für History-Logging hinzu
            token_balancer.bot = bot
            logger.info(f"Token Balancer successfully attached to bot: {token_balancer.get_status_text()}")

            # Cogs werden jetzt in setup_hook() geladen - nicht hier!
            init_time = time.time() - init_start
            logger.info(f"Bot instance created successfully (took {init_time:.2f}s)")

            # Starte den Bot mit dem aktuellen Token
            logger.info(f"Bot initialized, attempting to run ({token_balancer.get_status_text()})")
            total_init_time = time.time() - start_time
            logger.info(f"=== Gesamte Initialisierung: {total_init_time:.2f}s ===")

            current_token = token_balancer.get_current_token()
            token_name = "Primärer Bot" if current_token == token_balancer.primary_token else "Sekundärer Bot"
            logger.info(f"🚀 Starte Bot mit: {token_name}")

            bot.run(current_token, reconnect=True)

            # Wenn bot.run() normal beendet wird (was ungewöhnlich ist)
            logger.warning("⚠️ Bot beendet sich normal - Neustart in 5 Sekunden...")
            time.sleep(5)
            
        except discord.RateLimited as e:
            # Bei Rate Limit, versuche mit dem sekundären Bot
            logger.warning(f"🚨 Rate Limit erreicht! Retry nach: {e.retry_after}s")
            alternate_token = token_balancer.handle_rate_limit(e.retry_after)

            if alternate_token:
                logger.info("✅ Wechsel zu anderem Bot - Neustart in 1s...")
                time.sleep(1)
                # Die Schleife wird den Bot mit dem neuen Token neu starten
            else:
                logger.critical("❌ BEIDE Bots sind Rate-Limited! Warte vor Retry...")
                time.sleep(min(e.retry_after, 60))  # Warte maximal 60 Sekunden

        except discord.LoginFailure:
            logger.critical("❌ Login fehlgeschlagen! Token überprüfen!")
            alternate_token = token_balancer.handle_connection_error()
            if alternate_token:
                logger.info("🔄 Versuche alternativen Token - Neustart in 2s...")
                time.sleep(2)
            else:
                # Beide Tokens funktionieren nicht, längere Pause
                logger.critical("❌ BEIDE Token ungültig! Warte 30s vor Retry...")
                time.sleep(30)

        except (discord.ConnectionClosed, discord.GatewayNotFound, discord.HTTPException) as e:
            logger.error(f"❌ Verbindungsfehler: {e}")
            alternate_token = token_balancer.handle_connection_error()

            if alternate_token:
                logger.info("🔄 Wechsel zu anderem Bot - Neustart in 2s...")
                time.sleep(2)
            else:
                # Keine Token-Änderung, nur kurze Pause vor dem Neuversuch
                wait_time = min(5 * token_balancer.retry_count, 30)
                logger.warning(f"⏳ Verbindungsfehler - Retry in {wait_time}s...")
                time.sleep(wait_time)

        except KeyboardInterrupt:
            logger.info("⚠️ Bot wird durch Benutzer beendet (Ctrl+C)...")
            break  # Beende die while-Schleife

        except Exception as e:
            logger.exception(f"❌ Unerwarteter Fehler: {e}")
            # Bei unbekannten Fehlern längere Pause und kein automatischer Token-Wechsel
            logger.critical("⏳ Warte 60s vor Neustart wegen unerwartetem Fehler...")
            time.sleep(60)

        finally:
            # Cleanup: Bot ordentlich schließen falls noch offen
            try:
                if 'bot' in locals() and not bot.is_closed():
                    logger.info("🧹 Schließe Bot-Verbindung...")
                    asyncio.run(bot.close())
            except Exception as cleanup_error:
                logger.debug(f"Fehler beim Bot-Cleanup (ignorierbar): {cleanup_error}")

    logger.info("👋 Bot wurde vollständig beendet")
