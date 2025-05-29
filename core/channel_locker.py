import discord
import logging
from typing import Dict, List, Optional, Set
from bot_status import BotStatus
import time

logger = logging.getLogger('StatusBot')

class ChannelLocker:
    def __init__(self, bot):
        self.bot = bot
        self.locked_channels = {}  # Speichert die ursprünglichen Berechtigungen
        self.managed_roles = {}  # Dict[str, List[int]] - Channel ID -> Liste von Rollen-IDs
        self._last_channel_lock_ratelimit = 0

    async def set_managed_roles(self, channel_id: str, role_ids: List[int]):
        """Setzt die zu verwaltenden Rollen für einen Channel"""
        self.managed_roles[channel_id] = role_ids
        logger.info(f"Updated managed roles for channel {channel_id}: {role_ids}")

    async def get_managed_roles(self, channel_id: str) -> List[int]:
        """Holt die Liste der verwalteten Rollen-IDs für einen Channel"""
        return self.managed_roles.get(channel_id, [])

    async def remove_managed_role(self, channel_id: str, role_id: int):
        """Entfernt eine Rolle aus der Verwaltung"""
        if channel_id in self.managed_roles and role_id in self.managed_roles[channel_id]:
            self.managed_roles[channel_id].remove(role_id)
            logger.info(f"Removed role {role_id} from managed roles for channel {channel_id}")

    async def add_managed_role(self, channel_id: str, role_id: int):
        """Fügt eine Rolle zur Verwaltung hinzu"""
        if channel_id not in self.managed_roles:
            self.managed_roles[channel_id] = []
        if role_id not in self.managed_roles[channel_id]:
            self.managed_roles[channel_id].append(role_id)
            logger.info(f"Added role {role_id} to managed roles for channel {channel_id}")

    async def update_channel_lock(self, channel: discord.TextChannel, status: BotStatus):
        """Aktualisiert den Lock-Status eines Channels basierend auf dem Bot-Status"""
        try:
            # Prüfe auf vorherige Rate-Limits
            last_ratelimit_time = getattr(self, '_last_channel_lock_ratelimit', 0)
            if time.time() - last_ratelimit_time < 600:  # 10 Minuten
                logger.warning(f"Vorbeugend delegiere Lock-Aufgabe an Helper-Bot wegen vorherigem Rate-Limit")
                
                # Managed Rollen abrufen
                channel_id = str(channel.id)
                role_ids = await self.get_managed_roles(channel_id)
                
                # Task-Daten erstellen
                task_data = {
                    "channel_id": channel_id,
                    "status": status.value,
                    "guild_id": str(channel.guild.id),
                    "role_ids": role_ids
                }
                
                # Aufgabe an Helfer-Bot delegieren
                task_id = self.bot.channel_manager.delegate_to_helper("update_channel_lock", task_data)
                logger.info(f"Channel-Lock-Aufgabe {task_id} an Helfer-Bot delegiert")
                return
            
            try:
                if status in [BotStatus.OFFLINE, BotStatus.PROBLEM, BotStatus.MAINTENANCE]:
                    await self._lock_channel(channel)
                elif status == BotStatus.ONLINE:
                    await self._unlock_channel(channel)
            except discord.HTTPException as e:
                if e.status == 429:  # Rate limit Status Code
                    # Speichere Zeit des letzten Rate-Limits
                    self._last_channel_lock_ratelimit = time.time()
                    
                    logger.warning(f"Rate-Limit erreicht beim Ändern der Channel-Berechtigungen. Retry after: {getattr(e, 'retry_after', 'unbekannt')}s. Delegiere an Helfer-Bot.")
                    
                    # Managed Rollen abrufen
                    channel_id = str(channel.id)
                    role_ids = await self.get_managed_roles(channel_id)
                    
                    # Task-Daten erstellen
                    task_data = {
                        "channel_id": channel_id,
                        "status": status.value,
                        "guild_id": str(channel.guild.id),
                        "role_ids": role_ids
                    }
                    
                    # Aufgabe an Helfer-Bot delegieren
                    task_id = self.bot.channel_manager.delegate_to_helper("update_channel_lock", task_data)
                    logger.info(f"Channel-Lock-Aufgabe {task_id} an Helfer-Bot delegiert")
                else:
                    raise  # Andere Fehler weiterreichen
            
        except discord.errors.RateLimited as e:
            # Bei Rate-Limit: Delegieren an Helfer-Bot
            logger.warning(f"Rate-Limit erreicht beim Ändern der Channel-Berechtigungen. Retry after: {e.retry_after}s. Delegiere an Helfer-Bot.")
            
            # Managed Rollen abrufen
            channel_id = str(channel.id)
            role_ids = await self.get_managed_roles(channel_id)
            
            # Task-Daten erstellen
            task_data = {
                "channel_id": channel_id,
                "status": status.value,
                "guild_id": str(channel.guild.id),
                "role_ids": role_ids
            }
            
            # Aufgabe an Helfer-Bot delegieren
            task_id = self.bot.channel_manager.delegate_to_helper("update_channel_lock", task_data)
            logger.info(f"Channel-Lock-Aufgabe {task_id} an Helfer-Bot delegiert")
        except Exception as e:
            logger.error(f"Error updating channel lock status: {e}", exc_info=True)

    async def _lock_channel(self, channel: discord.TextChannel):
        """Sperrt spezifische Berechtigungen eines Channels mit Erhalt der anderen Berechtigungen"""
        try:
            channel_id = str(channel.id)
            role_ids = await self.get_managed_roles(channel_id)
            
            if not role_ids:
                logger.warning(f"Keine Rollen konfiguriert für Channel {channel.id}")
                return

            for role_id in role_ids:
                role = channel.guild.get_role(role_id)
                if role:
                    # Bot-Rolle Position prüfen
                    bot_member = channel.guild.me
                    if bot_member and role >= bot_member.top_role:
                        logger.warning(f"Bot-Rolle hat nicht genügend Rechte für Rolle {role.name}")
                        continue

                    # Hole existierende Berechtigungen
                    existing_overwrite = channel.overwrites_for(role)
                    
                    # Aktualisiere nur die spezifischen Berechtigungen
                    existing_overwrite.send_messages = False
                    existing_overwrite.add_reactions = False
                    existing_overwrite.send_messages_in_threads = False
                    existing_overwrite.create_public_threads = False
                    existing_overwrite.create_private_threads = False

                    await channel.set_permissions(role, overwrite=existing_overwrite)
                    logger.info(f"Rolle {role.name} ({role_id}) für Channel {channel.name} gesperrt")
                else:
                    logger.warning(f"Rolle {role_id} nicht gefunden in Guild {channel.guild.id}")

        except Exception as e:
            logger.error(f"Fehler beim Sperren des Channels {channel.name}: {e}")

    async def _unlock_channel(self, channel: discord.TextChannel):
        """Entsperrt spezifische Berechtigungen eines Channels mit Erhalt der anderen Berechtigungen"""
        try:
            channel_id = str(channel.id)
            role_ids = await self.get_managed_roles(channel_id)
            
            if not role_ids:
                return

            for role_id in role_ids:
                role = channel.guild.get_role(role_id)
                if role:
                    # Bot-Rolle Position prüfen
                    bot_member = channel.guild.me
                    if bot_member and role >= bot_member.top_role:
                        logger.warning(f"Bot-Rolle hat nicht genügend Rechte für Rolle {role.name}")
                        continue

                    # Hole existierende Berechtigungen
                    existing_overwrite = channel.overwrites_for(role)
                    
                    # Aktualisiere nur die spezifischen Berechtigungen
                    existing_overwrite.send_messages = True
                    existing_overwrite.add_reactions = True
                    existing_overwrite.view_channel = True
                    existing_overwrite.read_message_history = True
                    existing_overwrite.attach_files = True

                    await channel.set_permissions(role, overwrite=existing_overwrite)
                    logger.info(f"Rolle {role.name} ({role_id}) für Channel {channel.name} entsperrt")
                else:
                    logger.warning(f"Rolle {role_id} nicht gefunden in Guild {channel.guild.id}")

        except Exception as e:
            logger.error(f"Fehler beim Entsperren des Channels {channel.name}: {e}")

    def save_data(self):
        """Speichert die Konfiguration der verwalteten Rollen"""
        try:
            data = {
                'managed_roles': self.managed_roles,
            }
            self.bot.data_manager.save_json(data, "channel_locker.json")
            logger.info("Channel locker data saved successfully")
        except Exception as e:
            logger.error(f"Error saving channel locker data: {e}", exc_info=True)

    def load_data(self):
        """Lädt die Konfiguration der verwalteten Rollen"""
        try:
            data = self.bot.data_manager.load_json("channel_locker.json")
            self.managed_roles = data.get('managed_roles', {})
            
            # Detaillierte Debug-Informationen
            channel_count = len(self.managed_roles)
            role_count = sum(len(roles) for roles in self.managed_roles.values())
            logger.info(f"Channel Locker: {channel_count} Kanäle mit insgesamt {role_count} verwalteten Rollen geladen")
            
            logger.info("Channel locker data loaded successfully")
        except Exception as e:
            logger.error(f"Error loading channel locker data: {e}", exc_info=True)