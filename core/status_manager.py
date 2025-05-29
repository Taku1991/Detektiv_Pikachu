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

    def load_data(self):
        """Load status related data"""
        self.last_known_status = self.bot.data_manager.load_json("last_known_status.json")
        logger.info(f"Status-Daten geladen: {len(self.last_known_status)} Kanäle mit bekanntem Status")
        
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

        except Exception as e:
            logger.error(f"Fehler bei Inaktivitätsprüfung: {e}", exc_info=True)

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
        """Status-Update mit verbessertem Activity-Reset"""
        logger.info(f"Status-Update für Channel {log_channel_id}: {new_status.value}")
        logger.info(f"Grund: {reason}")
        
        try:
            guild_id = next((guild_id for guild_id, channels in self.bot.guild_channels.items() 
                         if log_channel_id in channels), None)
            
            if not guild_id:
                logger.error(f"Keine Guild gefunden für Channel {log_channel_id}")
                return

            update_channel_id = self.bot.guild_channels[guild_id].get(log_channel_id)
            if not update_channel_id:
                logger.error(f"Kein Update-Channel gefunden für Log-Channel {log_channel_id}")
                return
            
            update_channel = self.bot.get_channel(int(update_channel_id))
            if not update_channel:
                logger.error(f"Update-Channel {update_channel_id} nicht gefunden")
                return
            
            current_status = self.last_known_status.get(log_channel_id)
            logger.debug(f"Status-Änderung: {current_status} -> {new_status.value}")

            # Wenn der neue Status PROBLEM ist, setze Activity-Tracking zurück
            if new_status == BotStatus.PROBLEM:
                if log_channel_id in self.continuous_activity:
                    del self.continuous_activity[log_channel_id]
                if log_channel_id in self.last_message_times:
                    del self.last_message_times[log_channel_id]
                logger.debug(f"Activity-Tracking zurückgesetzt für Channel {log_channel_id}")
            
            # Statusänderung durchführen
            try:
                # Alte Nachrichten löschen
                try:
                    await self.bot.message_manager.purge_bot_messages(update_channel)
                except Exception as e:
                    logger.error(f"Fehler beim Löschen alter Nachrichten: {e}")

                # Neue Nachricht senden
                embed, gif_name = await self.bot.message_manager.create_status_embed(
                    new_status,
                    log_channel_id,
                    guild_id
                )
                
                gif_path = BotConstants.GIF_DIR / gif_name
                new_message = await self.bot.message_manager.send_with_retry(update_channel, embed, str(gif_path))
                
                if not new_message:
                    logger.error("Fehler beim Senden der Status-Nachricht")
                    return

                # Channel-Name und Lock aktualisieren
                await self.bot.channel_manager.update_channel_name(update_channel, new_status)
                await self.bot.channel_locker.update_channel_lock(update_channel, new_status)
                
                # Status speichern
                self.last_known_status[log_channel_id] = new_status.value
                self.bot.data_manager.save_json(self.last_known_status, "last_known_status.json")
                
                # History-Log
                await self._log_status_change(new_status, log_channel_id, reason, guild_id)
                
                logger.info(f"Status-Update erfolgreich durchgeführt")
                
            except Exception as e:
                logger.error(f"Fehler während Status-Update: {e}", exc_info=True)
                
        except Exception as e:
            logger.error(f"Fehler bei Status-Update-Vorbereitung: {e}", exc_info=True)

    async def _log_status_change(self, status: BotStatus, log_channel_id: str, reason: str, guild_id: str):
        """Log status change to history channel"""
        try:
            history_channel = self.bot.get_channel(self.bot.history_channel_id)
            if not history_channel:
                logger.error("History channel not found")
                return

            update_channel_id = self.bot.guild_channels[guild_id][log_channel_id]
            
            embed = discord.Embed(
                title="Status Change Log",
                description=f"Update-Channel: <#{update_channel_id}>",
                color=self.bot.config.status_colors[status],
                timestamp=discord.utils.utcnow()
            )
            embed.add_field(name="New Status", value=status.value, inline=True)
            embed.add_field(name="Reason", value=reason, inline=True)
            
            # Füge Bot-Owner Information ohne Mention hinzu
            owner_id = self.bot.channel_manager.get_channel_owner(guild_id, log_channel_id)
            if owner_id:
                user = self.bot.get_user(owner_id)
                owner_name = user.name if user else f"User (ID: {owner_id})"
                embed.add_field(name="Bot Owner", value=owner_name, inline=True)
                
            await history_channel.send(embed=embed)

        except Exception as e:
            logger.error(f"Error logging status change: {e}", exc_info=True)