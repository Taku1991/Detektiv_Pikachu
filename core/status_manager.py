import discord
from discord.ext import tasks
import logging
import time
import asyncio
from typing import Dict, Optional
from datetime import datetime
from bot_status import BotStatus
from config.constants import BotConstants

logger = logging.getLogger('StatusBot')
logger.setLevel(logging.DEBUG)

class StatusManager:
    def __init__(self, bot):
        self.bot = bot
        self.last_known_status: Dict[str, str] = {}
        self.last_message_times: Dict[str, float] = {}
        self.continuous_activity: Dict[str, float] = {}
        self.last_status_update: Dict[str, Dict[str, float]] = {}
        self.check_inactivity_task = tasks.loop(seconds=10)(self.check_inactivity)
        self.check_inactivity_task.before_loop(self.before_check_inactivity)

    def initialize_tasks(self):
        """Initialize inactivity check task"""
        self.check_inactivity_task = tasks.loop(seconds=10)(self.check_inactivity)
        self.check_inactivity_task.before_loop(self.before_check_inactivity)

    def start_tasks(self):
        """Start the tasks if they're not already running"""
        try:
            if not self.check_inactivity_task.is_running():
                self.check_inactivity_task.start()
                logger.info("Started inactivity check task")
            else:
                logger.info("Inactivity check task is already running")
        except Exception as e:
            logger.error(f"Error starting tasks: {e}", exc_info=True)

    def update_last_message_time(self, channel_id: str):
        """Aktualisiert die letzte Nachrichtenzeit für einen Channel"""
        current_time = time.time()
        previous_time = self.last_message_times.get(channel_id, 0)
        time_since_last = current_time - previous_time if previous_time > 0 else 0
        
        self.last_message_times[channel_id] = current_time
        
        # Nur ausführliches Logging, wenn vorherige Zeit existiert und signifikante Zeit vergangen ist
        if previous_time > 0 and time_since_last > 10:
            logger.info(f"Letzte Nachrichtenzeit aktualisiert für Channel {channel_id}: Nach {time_since_last:.1f}s Inaktivität")
        else:
            logger.debug(f"Letzte Nachrichtenzeit aktualisiert für Channel {channel_id}: {current_time}")

    async def initialize_status_from_channels(self):
        """
        Initialisiert last_known_status.json automatisch:
        Für jeden Log-Channel wird asynchron geprüft, ob in den letzten 2 Minuten eine Nachricht vorhanden ist.
        Falls ja: online, sonst: offline.
        Respektiert existierende Status-Einträge und fügt nur fehlende hinzu!
        """
        logger.info("Initialisiere Status für alle Log-Channels anhand der letzten Nachrichten (asynchron)...")
        
        import datetime
        now = datetime.datetime.utcnow().timestamp()
        channels_processed = 0
        channels_added = 0
        channels_kept = 0
        
        for guild_id, channels in self.bot.guild_channels.items():
            for log_channel_id in channels.keys():
                channels_processed += 1
                log_channel_str = str(log_channel_id)
                
                # Prüfe ob bereits ein Status existiert
                if log_channel_str in self.last_known_status:
                    existing_status = self.last_known_status[log_channel_str]
                    logger.debug(f"Channel {log_channel_id}: Bestehender Status beibehalten: {existing_status}")
                    channels_kept += 1
                    continue
                
                # Nur für neue Channels Status ermitteln
                channel = self.bot.get_channel(int(log_channel_id))
                status = "offline"
                
                if channel:
                    try:
                        last_message = None
                        async for msg in channel.history(limit=1):
                            last_message = msg
                            break
                        if last_message:
                            age = now - last_message.created_at.replace(tzinfo=None).timestamp()
                            logger.debug(f"Channel {log_channel_id}: Letzte Nachricht: {last_message.content if hasattr(last_message, 'content') else str(last_message)}")
                            logger.debug(f"Channel {log_channel_id}: Zeit seit letzter Nachricht: {age:.1f}s")
                            logger.debug(f"Channel {log_channel_id}: Nachricht erstellt am: {last_message.created_at} (UTC)")
                            if age < 120:  # 2 Minuten
                                status = "online"
                        else:
                            logger.debug(f"Channel {log_channel_id}: Keine Nachrichten gefunden.")
                    except Exception as e:
                        logger.warning(f"Fehler beim Prüfen von Channel {log_channel_id}: {e}")
                else:
                    logger.debug(f"Channel {log_channel_id}: Channel-Objekt nicht gefunden.")
                
                self.last_known_status[log_channel_str] = status
                logger.info(f"Neuer Channel {log_channel_id}: Initial-Status gesetzt auf {status}")
                channels_added += 1
        
        # Speichere nur wenn Änderungen vorgenommen wurden
        if channels_added > 0:
            self.bot.data_manager.save_json(self.last_known_status, "last_known_status.json")
            logger.info(f"Status-Initialisierung abgeschlossen: {channels_processed} Channels verarbeitet, {channels_added} hinzugefügt, {channels_kept} beibehalten")
        else:
            logger.info(f"Status-Initialisierung abgeschlossen: Alle {channels_processed} Channels hatten bereits einen Status")

    def load_data(self):
        """Load status related data"""
        raw_status = self.bot.data_manager.load_json("last_known_status.json")
        # Stelle sicher, dass alle Keys Strings sind
        self.last_known_status = {str(k): v for k, v in raw_status.items()}
        # Initialisierung erfolgt jetzt asynchron im Setup-Hook
        logger.info(f"Status-Daten geladen: {len(self.last_known_status)} Kanäle mit bekanntem Status")
        # Debug: Zeige alle Keys und deren Typen
        for k in self.last_known_status.keys():
            logger.info(f"last_known_status Key: {k} (Typ: {type(k)})")
        # Logge den kompletten Inhalt
        logger.info(f"Geladene last_known_status: {self.last_known_status}")
        
        # Detaillierte Debug-Informationen
        online_count = sum(1 for status in self.last_known_status.values() if status == BotStatus.ONLINE.value)
        offline_count = sum(1 for status in self.last_known_status.values() if status == BotStatus.OFFLINE.value)
        problem_count = sum(1 for status in self.last_known_status.values() if status == BotStatus.PROBLEM.value)
        maintenance_count = sum(1 for status in self.last_known_status.values() if status == BotStatus.MAINTENANCE.value)
        
        logger.info(f"Status-Verteilung: Online: {online_count}, Offline: {offline_count}, Problem: {problem_count}, Wartung: {maintenance_count}")
        
        # Initialize last message times for online channels
        current_time = time.time()
        online_channels_initialized = 0
        
        for channel_id, status in self.last_known_status.items():
            if status == BotStatus.ONLINE.value:
                self.last_message_times[channel_id] = current_time
                online_channels_initialized += 1
                
                # Um sicherzustellen, dass kontinuierliche Aktivität nicht verloren geht
                if channel_id not in self.continuous_activity:
                    self.continuous_activity[channel_id] = current_time
        
        logger.info(f"Letzte Nachrichtenzeiten für {online_channels_initialized} Online-Kanäle initialisiert")
        logger.info(f"Activity-Tracking für {len(self.continuous_activity)} Kanäle initialisiert")

    async def before_check_inactivity(self):
        await self.bot.wait_until_ready()

    async def check_inactivity(self):
        """Verbesserte Inaktivitätsprüfung mit korrektem Activity-Reset"""
        if not self.bot.is_ready():
            return

        try:
            current_time = time.time()
            channels_to_check = []
            
            for guild_id, channels in self.bot.guild_channels.items():
                for log_channel_id in channels.keys():
                    channels_to_check.append((guild_id, log_channel_id))
            
            logger.debug(f"Inaktivitätsprüfung für {len(channels_to_check)} Kanäle")
            
            for guild_id, log_channel_id in channels_to_check:
                try:
                    if log_channel_id in self.bot.channel_manager.excluded_channels:
                        continue

                    channel_status = self.last_known_status.get(log_channel_id)
                    if not channel_status or channel_status == BotStatus.OFFLINE.value:
                        continue

                    last_message_time = self.last_message_times.get(log_channel_id)
                    
                    # Bei Problem-Status: Prüfe auf neue Aktivität
                    if channel_status == BotStatus.PROBLEM.value:
                        if last_message_time:
                            activity_duration = current_time - last_message_time
                            logger.debug(f"Problem-Status Activity Check - Channel {log_channel_id}: "
                                       f"Aktivität seit {activity_duration:.1f}s")
                            
                            # Nur wenn kontinuierlich aktiv für die Schwellzeit
                            if activity_duration < BotConstants.ACTIVITY_CHECK_THRESHOLD:
                                if log_channel_id not in self.continuous_activity:
                                    self.continuous_activity[log_channel_id] = current_time
                                    logger.info(f"Starte neues Activity-Tracking für {log_channel_id} (letzte Aktivität vor {activity_duration:.1f}s)")
                            else:
                                # Reset wenn Inaktivität zu lang
                                if log_channel_id in self.continuous_activity:
                                    del self.continuous_activity[log_channel_id]
                                    logger.info(f"Activity-Tracking zurückgesetzt wegen Inaktivität: {log_channel_id} (inaktiv seit {activity_duration:.1f}s)")
                            
                            # Prüfe ob lang genug kontinuierlich aktiv
                            if log_channel_id in self.continuous_activity:
                                continuous_duration = current_time - self.continuous_activity[log_channel_id]
                                if continuous_duration >= BotConstants.ACTIVITY_CHECK_THRESHOLD:
                                    logger.info(f"Channel {log_channel_id}: Online nach {continuous_duration:.1f}s "
                                              f"kontinuierlicher Aktivität")
                                    await self.update_status(
                                        log_channel_id,
                                        BotStatus.ONLINE,
                                        f"Kontinuierliche Aktivität für {int(continuous_duration)} Sekunden"
                                    )
                    
                    # Bei Online-Status: Prüfe auf Inaktivität
                    elif channel_status == BotStatus.ONLINE.value and last_message_time:
                        inactive_duration = current_time - last_message_time
                        logger.debug(f"Online-Status Inaktivitäts-Check - Channel {log_channel_id}: "
                                   f"Inaktiv seit {inactive_duration:.1f}s (Schwelle: {BotConstants.INACTIVITY_THRESHOLD}s)")
                        
                        if inactive_duration >= BotConstants.INACTIVITY_THRESHOLD:
                            logger.info(f"Channel {log_channel_id}: Problem (Inaktiv seit {inactive_duration:.1f}s)")
                            await self.update_status(
                                log_channel_id,
                                BotStatus.PROBLEM,
                                f"Inaktiv seit {int(inactive_duration)} Sekunden"
                            )

                except Exception as e:
                    logger.error(f"Fehler bei Prüfung von Channel {log_channel_id}: {e}", exc_info=True)

            # Memory-Cleanup: Bereinige alte Einträge aus Dictionaries (verhindert Memory-Leaks)
            self._cleanup_old_activity_data(current_time)

        except Exception as e:
            logger.error(f"Fehler bei Inaktivitätsprüfung: {e}", exc_info=True)

    def _cleanup_old_activity_data(self, current_time: float):
        """
        Bereinigt alte Einträge aus Activity-Dictionaries um Memory-Leaks zu verhindern.
        Wird automatisch bei jeder Inaktivitätsprüfung aufgerufen.
        """
        try:
            # Schwellwerte für Cleanup
            MAX_DICT_SIZE = 1000  # Maximale Anzahl Einträge bevor Cleanup
            ENTRY_MAX_AGE = 3600  # 1 Stunde - danach werden Einträge gelöscht

            # Cleanup für continuous_activity
            if len(self.continuous_activity) > MAX_DICT_SIZE:
                original_size = len(self.continuous_activity)
                self.continuous_activity = {
                    k: v for k, v in self.continuous_activity.items()
                    if current_time - v < ENTRY_MAX_AGE
                }
                cleaned_count = original_size - len(self.continuous_activity)
                if cleaned_count > 0:
                    logger.info(f"Memory-Cleanup: {cleaned_count} alte continuous_activity Einträge entfernt (Alter > {ENTRY_MAX_AGE}s)")

            # Cleanup für last_message_times
            if len(self.last_message_times) > MAX_DICT_SIZE:
                original_size = len(self.last_message_times)
                self.last_message_times = {
                    k: v for k, v in self.last_message_times.items()
                    if current_time - v < ENTRY_MAX_AGE * 2  # Längere Retention für message times
                }
                cleaned_count = original_size - len(self.last_message_times)
                if cleaned_count > 0:
                    logger.info(f"Memory-Cleanup: {cleaned_count} alte last_message_times Einträge entfernt (Alter > {ENTRY_MAX_AGE * 2}s)")

            # Cleanup für last_status_update (verschachtelte Dict-Struktur)
            if len(self.last_status_update) > MAX_DICT_SIZE:
                original_size = sum(len(status_dict) for status_dict in self.last_status_update.values())
                channels_to_remove = []

                for channel_id, status_dict in self.last_status_update.items():
                    # Entferne alte Status-Einträge
                    status_dict_cleaned = {
                        status: timestamp for status, timestamp in status_dict.items()
                        if current_time - timestamp < ENTRY_MAX_AGE
                    }

                    if status_dict_cleaned:
                        self.last_status_update[channel_id] = status_dict_cleaned
                    else:
                        channels_to_remove.append(channel_id)

                # Entferne komplett leere Channel-Einträge
                for channel_id in channels_to_remove:
                    del self.last_status_update[channel_id]

                new_size = sum(len(status_dict) for status_dict in self.last_status_update.values())
                cleaned_count = original_size - new_size
                if cleaned_count > 0:
                    logger.info(f"Memory-Cleanup: {cleaned_count} alte last_status_update Einträge entfernt, {len(channels_to_remove)} leere Channels entfernt")

        except Exception as e:
            logger.error(f"Fehler beim Memory-Cleanup: {e}", exc_info=True)

    async def process_message(self, message: discord.Message):
        """Verbesserte Nachrichtenverarbeitung mit Debug-Logging"""
        try:
            channel_id = str(message.channel.id)
            guild_id = str(message.guild.id) if message.guild else None

            if not guild_id or guild_id not in self.bot.guild_channels:
                return

            # Prüfe ob dies ein Log-Channel ist
            is_log_channel = channel_id in self.bot.guild_channels[guild_id]

            if is_log_channel:
                # Debug: Zeige die Nachricht
                logger.debug(f"Log-Channel Nachricht empfangen: {message.content}")
                # Debug: Zeige Channel-ID und alle Keys
                logger.info(f"Zugriff auf last_known_status mit Channel-ID: {channel_id} (Typ: {type(channel_id)})")
                logger.info(f"Alle Keys in last_known_status: {list(self.last_known_status.keys())}")
                
                # Aktualisiere letzte Nachrichtenzeit
                self.update_last_message_time(channel_id)
                
                # Hole aktuellen Status und prüfe auf Muster
                current_status = self.last_known_status.get(channel_id)
                new_status = self.bot.patterns.check_patterns(message.content)
                
                # Debug: Status-Info
                logger.info(f"Channel {channel_id} - Aktueller Status: {current_status}, "
                            f"Erkannter Status: {new_status.value if new_status else 'None'}")
                
                if new_status:
                    # Bei Online-Muster: immer continuous_activity aktualisieren
                    if new_status == BotStatus.ONLINE:
                        current_time = time.time()
                        logger.info(f"Online-Aktivität für Channel {channel_id} erkannt: {message.content}")
                        
                        # Activity-Tracking starten/aktualisieren
                        if channel_id not in self.continuous_activity:
                            self.continuous_activity[channel_id] = current_time
                            logger.info(f"Starte neues Activity-Tracking für {channel_id}")
                        else:
                            # Existierende Activity aktualisieren
                            continuous_duration = current_time - self.continuous_activity[channel_id]
                            logger.info(f"Channel {channel_id}: Kontinuierliche Aktivität seit {continuous_duration:.1f}s")
                    
                    # Prüfe Cooldown nur wenn es eine echte Statusänderung ist
                    if current_status != new_status.value:
                        current_time = time.time()
                        last_update_time = self.last_status_update.get(channel_id, {}).get(new_status.value, 0)
                        
                        # Debug: Cooldown-Info
                        time_since_last = current_time - last_update_time
                        logger.info(f"Zeit seit letztem Update: {time_since_last:.1f}s")
                        
                        if time_since_last >= 30:  # Cooldown von 30 Sekunden
                            # Aktualisiere Cooldown und Status
                            if channel_id not in self.last_status_update:
                                self.last_status_update[channel_id] = {}
                            self.last_status_update[channel_id][new_status.value] = current_time
                            
                            logger.info(f"Führe Status-Update durch: {current_status} -> {new_status.value}")
                            await self.update_status(
                                channel_id,
                                new_status,
                                f"Statusänderung erkannt in: {message.content}"
                            )
                        else:
                            logger.info(f"Status-Update ignoriert (Cooldown aktiv: {30 - time_since_last:.1f}s verbleibend)")
                    else:
                        if new_status == BotStatus.ONLINE and current_status == BotStatus.ONLINE.value:
                            logger.info(f"Online-Status unverändert: {current_status} - Aktivität wird weiterhin überwacht")
                        else:
                            logger.info(f"Status unverändert: {current_status}")

        except Exception as e:
            logger.error(f"Fehler bei Nachrichtenverarbeitung: {e}", exc_info=True)

    async def update_status(self, log_channel_id: str, new_status: BotStatus, reason: str):
        """Status-Update mit verbessertem Activity-Reset und Multi-Channel-Support"""
        logger.info(f"Status-Update für Channel {log_channel_id}: {new_status.value}")
        logger.info(f"Grund: {reason}")
        
        try:
            guild_id = next((guild_id for guild_id, channels in self.bot.guild_channels.items() 
                         if log_channel_id in channels), None)
            
            if not guild_id:
                logger.error(f"Keine Guild gefunden für Channel {log_channel_id}")
                return

            # Hole alle Update-Channels für diesen Log-Channel
            update_channel_ids = self.bot.channel_manager.get_update_channels(guild_id, log_channel_id)
            if not update_channel_ids:
                logger.error(f"Keine Update-Channels gefunden für Log-Channel {log_channel_id}")
                return
            
            logger.info(f"Update an {len(update_channel_ids)} Update-Channels: {update_channel_ids}")
            
            current_status = self.last_known_status.get(log_channel_id)
            logger.debug(f"Status-Änderung: {current_status} -> {new_status.value}")

            # Wenn der neue Status PROBLEM ist, setze Activity-Tracking zurück
            if new_status == BotStatus.PROBLEM:
                if log_channel_id in self.continuous_activity:
                    del self.continuous_activity[log_channel_id]
                if log_channel_id in self.last_message_times:
                    del self.last_message_times[log_channel_id]
                logger.debug(f"Activity-Tracking zurückgesetzt für Channel {log_channel_id}")
            
            # Statusänderung für alle Update-Channels durchführen
            successful_updates = 0
            for update_channel_id in update_channel_ids:
                try:
                    update_channel = self.bot.get_channel(int(update_channel_id))
                    if not update_channel:
                        logger.error(f"Update-Channel {update_channel_id} nicht gefunden")
                        continue
                    
                    # Alte Nachrichten löschen
                    try:
                        await self.bot.message_manager.purge_bot_messages(update_channel)
                    except Exception as e:
                        logger.error(f"Fehler beim Löschen alter Nachrichten in {update_channel_id}: {e}")

                    # Neue Nachricht senden
                    embed, gif_name = await self.bot.message_manager.create_status_embed(
                        new_status,
                        log_channel_id,
                        guild_id
                    )
                    
                    gif_path = BotConstants.GIF_DIR / gif_name
                    new_message = await self.bot.message_manager.send_with_retry(update_channel, embed, str(gif_path))
                    
                    if not new_message:
                        logger.error(f"Fehler beim Senden der Status-Nachricht in {update_channel_id}")
                        continue

                    # Channel-Name und Lock aktualisieren
                    await self.bot.channel_manager.update_channel_name(update_channel, new_status)
                    await self.bot.channel_locker.update_channel_lock(update_channel, new_status)
                    
                    successful_updates += 1
                    logger.info(f"Status-Update erfolgreich für Update-Channel {update_channel_id}")
                    
                except Exception as e:
                    logger.error(f"Fehler beim Update von Channel {update_channel_id}: {e}", exc_info=True)
            
            if successful_updates > 0:
                # Status speichern (nur wenn mindestens ein Update erfolgreich war)
                self.last_known_status[log_channel_id] = new_status.value
                self.bot.data_manager.save_json(self.last_known_status, "last_known_status.json")
                
                # History-Log
                await self._log_status_change(new_status, log_channel_id, reason, guild_id, successful_updates, len(update_channel_ids))
                
                logger.info(f"Status-Update erfolgreich durchgeführt für {successful_updates}/{len(update_channel_ids)} Channels")
            else:
                logger.error("Kein Status-Update konnte erfolgreich durchgeführt werden")
                
        except Exception as e:
            logger.error(f"Fehler bei Status-Update-Vorbereitung: {e}", exc_info=True)

    async def _log_status_change(self, status: BotStatus, log_channel_id: str, reason: str, guild_id: str, successful_updates: int = None, total_channels: int = None):
        """Log status change to history channel with multi-channel support"""
        try:
            history_channel = self.bot.get_channel(self.bot.history_channel_id)
            if not history_channel:
                logger.error("History channel not found")
                return

            update_channel_ids = self.bot.channel_manager.get_update_channels(guild_id, log_channel_id)
            
            # Update-Channels als String formatieren
            if len(update_channel_ids) == 1:
                channel_info = f"Update-Channel: <#{update_channel_ids[0]}>"
            else:
                channel_mentions = [f"<#{uid}>" for uid in update_channel_ids]
                channel_info = f"Update-Channels ({len(update_channel_ids)}): {', '.join(channel_mentions)}"
            
            embed = discord.Embed(
                title="Status Change Log",
                description=channel_info,
                color=self.bot.config.status_colors[status],
                timestamp=discord.utils.utcnow()
            )
            embed.add_field(name="New Status", value=status.value, inline=True)
            embed.add_field(name="Reason", value=reason, inline=True)
            
            # Wenn Multi-Channel Updates, zeige Success-Rate
            if successful_updates is not None and total_channels is not None and total_channels > 1:
                embed.add_field(name="Update Success", value=f"{successful_updates}/{total_channels} Channels", inline=True)
            
            # Füge Bot-Owner Information ohne Mention hinzu
            owner_id = self.bot.channel_manager.get_channel_owner(guild_id, log_channel_id)
            if owner_id:
                user = self.bot.get_user(owner_id)
                owner_name = user.name if user else f"User (ID: {owner_id})"
                embed.add_field(name="Bot Owner", value=owner_name, inline=True)
                
            await history_channel.send(embed=embed)

        except Exception as e:
            logger.error(f"Error logging status change: {e}", exc_info=True)