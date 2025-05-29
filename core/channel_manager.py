import discord
import logging
import re
import time
import random
import json
import os
from typing import Set, Dict, Optional, List
from bot_status import BotStatus
import asyncio

logger = logging.getLogger('StatusBot')
logger.setLevel(logging.DEBUG)  # Debug-Level für detailliertere Logs

class ChannelManager:
    def __init__(self, bot):
        self.bot = bot
        self.excluded_channels: Set[str] = set()
        self.channel_owners = {}  # Neues Dictionary für Channel-Owner
        
        # Rate-Limit-Tracking
        self._last_channel_name_ratelimit = 0

    async def update_channel_name(self, channel: discord.TextChannel, status: BotStatus):
        """Update channel name with status emoji"""
        try:
            current_name = channel.name
            status_emoji = self.bot.patterns.get_status_emoji(status)
            base_name = self.bot.patterns.remove_status_emoji(current_name)
            new_name = f"{status_emoji}︱{base_name}"
            
            if current_name != new_name:
                logger.info(f"Changing channel name from '{current_name}' to '{new_name}'")
                
                # Speichere die gewünschte Änderung in der JSON
                channel_states_file = self.bot.data_manager.data_dir / "json" / "channel_states.json"
                channel_states_file.parent.mkdir(parents=True, exist_ok=True)
                
                # Lade aktuelle Channel-States
                channel_states = {}
                if channel_states_file.exists():
                    try:
                        with open(channel_states_file, 'r', encoding='utf-8') as f:
                            content = f.read().strip()
                            if content:
                                channel_states = json.loads(content)
                    except:
                        pass
                
                # Aktualisiere den Channel-State
                channel_states[str(channel.id)] = {
                    "current_name": current_name,
                    "desired_name": new_name,
                    "guild_id": str(channel.guild.id),
                    "last_update": time.time(),
                    "last_attempt": 0,  # Wird vor dem Versuch aktualisiert
                    "completed": False
                }
                
                # Speichere die aktualisierten States
                with open(channel_states_file, 'w', encoding='utf-8') as f:
                    json.dump(channel_states, f, indent=2)
                
                try:
                    # Aktualisiere last_attempt vor dem Versuch
                    channel_states[str(channel.id)]["last_attempt"] = time.time()
                    with open(channel_states_file, 'w', encoding='utf-8') as f:
                        json.dump(channel_states, f, indent=2)
                    
                    # Versuche die Änderung
                    await channel.edit(name=new_name)
                    logger.info(f"Channel name updated to: {new_name}")
                    
                    # Markiere als abgeschlossen
                    channel_states[str(channel.id)]["completed"] = True
                    with open(channel_states_file, 'w', encoding='utf-8') as f:
                        json.dump(channel_states, f, indent=2)
                    
                except discord.HTTPException as e:
                    if hasattr(e, 'status') and e.status == 429:
                        retry_after = getattr(e, 'retry_after', 60)
                        logger.warning(f"Rate-Limit erreicht beim Ändern des Channel-Namens. "
                                     f"Retry after: {retry_after}s. HelperBot wird die Änderung übernehmen.")
                    else:
                        logger.error(f"HTTP-Fehler beim Channel-Update: {e}", exc_info=True)
                        
                except Exception as e:
                    logger.error(f"Unerwarteter Fehler beim Channel-Update: {e}", exc_info=True)
                    
        except Exception as e:
            logger.error(f"Allgemeiner Fehler in update_channel_name: {e}", exc_info=True)

    def is_excluded(self, channel_id: str) -> bool:
        """Check if a channel is excluded from status checks"""
        return channel_id in self.excluded_channels

    def exclude_channel(self, channel_id: str) -> bool:
        """Add a channel to the excluded list"""
        if channel_id not in self.excluded_channels:
            self.excluded_channels.add(channel_id)
            self._save_excluded_channels()
            logger.info(f"Channel {channel_id} added to excluded channels")
            return True
        return False

    def include_channel(self, channel_id: str) -> bool:
        """Remove a channel from the excluded list"""
        if channel_id in self.excluded_channels:
            self.excluded_channels.remove(channel_id)
            self._save_excluded_channels()
            logger.info(f"Channel {channel_id} removed from excluded channels")
            return True
        return False

    def get_excluded_channels(self) -> Set[str]:
        """Gibt die Liste der ausgeschlossenen Kanäle zurück"""
        return self.excluded_channels

    def _save_excluded_channels(self):
        """Save the excluded channels list to file"""
        try:
            self.bot.data_manager.save_json(list(self.excluded_channels), "excluded_channels.json")
        except Exception as e:
            logger.error(f"Error saving excluded channels: {e}")

    def add_channel_pair(self, guild_id: str, log_channel_id: str, update_channel_id: str, owner_id: Optional[int] = None):
        """Add a new log channel and update channel pair with optional owner"""
        if guild_id not in self.bot.guild_channels:
            self.bot.guild_channels[guild_id] = {}
        
        self.bot.guild_channels[guild_id][log_channel_id] = update_channel_id
        
        # Speichere den Owner wenn angegeben
        if owner_id:
            if guild_id not in self.channel_owners:
                self.channel_owners[guild_id] = {}
            self.channel_owners[guild_id][log_channel_id] = owner_id
        
        self._save_channel_pairs()
        self._save_channel_owners()
        logger.info(f"Added channel pair: Log {log_channel_id} -> Update {update_channel_id} (Owner: {owner_id})")

    def remove_channel_pair(self, guild_id: str, log_channel_id: str) -> Optional[str]:
        """Remove a channel pair and return the update channel ID if it existed"""
        update_channel_id = None
        if guild_id in self.bot.guild_channels and log_channel_id in self.bot.guild_channels[guild_id]:
            update_channel_id = self.bot.guild_channels[guild_id].pop(log_channel_id)
            
            # Entferne auch den Owner-Eintrag wenn vorhanden
            if guild_id in self.channel_owners and log_channel_id in self.channel_owners[guild_id]:
                del self.channel_owners[guild_id][log_channel_id]
                if not self.channel_owners[guild_id]:
                    del self.channel_owners[guild_id]
                self._save_channel_owners()
            
            if not self.bot.guild_channels[guild_id]:
                del self.bot.guild_channels[guild_id]
            self._save_channel_pairs()
            logger.info(f"Removed channel pair: Log {log_channel_id} -> Update {update_channel_id}")
        return update_channel_id

    def _save_channel_pairs(self):
        """Save the channel pairs to file"""
        try:
            self.bot.data_manager.save_json(self.bot.guild_channels, "guild_channels.json")
        except Exception as e:
            logger.error(f"Error saving guild channels: {e}")

    def _save_channel_owners(self):
        """Save the channel owners to file"""
        try:
            self.bot.data_manager.save_json(self.channel_owners, "channel_owners.json")
        except Exception as e:
            logger.error(f"Error saving channel owners: {e}")

    def get_channel_pairs(self, guild_id: str) -> List[Dict[str, str]]:
        """Get all channel pairs for a guild"""
        if guild_id in self.bot.guild_channels:
            pairs = []
            for log_id, update_id in self.bot.guild_channels[guild_id].items():
                pairs.append({
                    'log_channel': log_id,
                    'update_channel': update_id
                })
            return pairs
        return []

    def get_update_channel(self, guild_id: str, log_channel_id: str) -> Optional[str]:
        """Get the update channel ID for a given log channel"""
        return self.bot.guild_channels.get(guild_id, {}).get(log_channel_id)

    def get_log_channel(self, guild_id: str, update_channel_id: str) -> Optional[str]:
        """Get the log channel ID for a given update channel"""
        if guild_id in self.bot.guild_channels:
            for log_id, update_id in self.bot.guild_channels[guild_id].items():
                if update_id == update_channel_id:
                    return log_id
        return None

    def get_channel_owner(self, guild_id: str, log_channel_id: str) -> Optional[int]:
        """Get the owner ID for a given channel pair"""
        return self.channel_owners.get(guild_id, {}).get(log_channel_id)

    def load_data(self):
        """Load channel related data"""
        try:
            excluded_data = self.bot.data_manager.load_json("excluded_channels.json")
            self.excluded_channels = set(excluded_data if isinstance(excluded_data, list) else [])
            
            self.channel_owners = self.bot.data_manager.load_json("channel_owners.json")
            
            # Debug-Ausgabe für geladene Daten
            logger.info(f"Excluded Channels: {len(self.excluded_channels)} Kanäle ausgeschlossen")
            owners_count = sum(len(guild_owners) for guild_owners in self.channel_owners.values()) if self.channel_owners else 0
            logger.info(f"Channel Owners: {len(self.channel_owners)} Guilds mit insgesamt {owners_count} konfigurierten Ownern")
            
            # Prüfe, ob die Daten korrekt geladen wurden
            if not self.excluded_channels:
                logger.warning("Keine ausgeschlossenen Kanäle geladen oder leere Liste")
            if not self.channel_owners:
                logger.warning("Keine Channel-Owner geladen oder leeres Dictionary")
                
            logger.info(f"Channel-Daten erfolgreich geladen")
            
        except Exception as e:
            logger.error(f"Error loading channel data: {e}", exc_info=True)
            self.excluded_channels = set()
            self.channel_owners = {}

    async def setup_update_channel(self, channel: discord.TextChannel, status: BotStatus):
        """Initial setup of an update channel"""
        try:
            await self.update_channel_name(channel, status)
            await self.bot.message_manager.purge_bot_messages(channel)
            logger.info(f"Successfully set up update channel {channel.name}")
            return True
        except discord.errors.RateLimited as e:
            # Bei Rate-Limit: Delegieren an Helfer-Bot für Channel-Name und trotzdem fortfahren
            logger.warning(f"Rate-Limit erreicht beim Setup des Update-Channels. Nur Nachrichten werden bereinigt.")
            await self.bot.message_manager.purge_bot_messages(channel)
            logger.info(f"Update channel {channel.name} partially set up (messages purged)")
            return True
        except Exception as e:
            logger.error(f"Error setting up update channel {channel.name}: {e}")
            return False
        
    async def cleanup_invalid_channels(self):
            """Entfernt Einträge für nicht mehr existierende Channels"""
            try:
                channels_to_remove = []
                
                # Warte bis der Bot bereit ist
                await self.bot.wait_until_ready()
                
                # Durchsuche alle Guild-Channel-Paare
                for guild_id, channels in list(self.bot.guild_channels.items()):
                    guild = self.bot.get_guild(int(guild_id))
                    
                    # Debug-Logging für Guild-Check
                    if guild:
                        logger.info(f"Guild {guild_id} ({guild.name}) gefunden")
                    else:
                        logger.warning(f"Guild {guild_id} nicht gefunden - Bot möglicherweise noch nicht bereit")
                        continue  # Überspringen statt zu löschen
                    
                    # Prüfe jeden Channel in der Guild
                    for log_id, update_id in channels.items():
                        log_channel = guild.get_channel(int(log_id))
                        update_channel = guild.get_channel(int(update_id))
                        
                        # Debug-Logging für Channel-Check
                        logger.info(f"Prüfe Channels - Log: {log_id} ({log_channel.name if log_channel else 'nicht gefunden'}), "
                                f"Update: {update_id} ({update_channel.name if update_channel else 'nicht gefunden'})")
                        
                        if not log_channel or not update_channel:
                            channels_to_remove.append((guild_id, log_id))
                            logger.warning(f"Ungültige Channels gefunden - Log: {log_id}, Update: {update_id}")

                # Bestätigungslog vor dem Entfernen
                if channels_to_remove:
                    logger.warning(f"Folgende Channels werden entfernt: {channels_to_remove}")
                
                # Entferne die ungültigen Channels
                removed_count = 0
                for guild_id, log_id in channels_to_remove:
                    if guild_id in self.bot.guild_channels and log_id in self.bot.guild_channels[guild_id]:
                        update_id = self.bot.guild_channels[guild_id].pop(log_id)
                        
                        # Entferne Guild wenn keine Channels mehr übrig
                        if not self.bot.guild_channels[guild_id]:
                            del self.bot.guild_channels[guild_id]
                        
                        # Entferne Channel aus anderen Konfigurationen
                        if log_id in self.bot.status_manager.last_known_status:
                            del self.bot.status_manager.last_known_status[log_id]
                        
                        if log_id in self.excluded_channels:
                            self.excluded_channels.remove(log_id)
                        
                        # Entferne Owner-Informationen
                        if guild_id in self.channel_owners and log_id in self.channel_owners[guild_id]:
                            del self.channel_owners[guild_id][log_id]
                            if not self.channel_owners[guild_id]:
                                del self.channel_owners[guild_id]
                        
                        removed_count += 1
                        logger.info(f"Channel-Paar entfernt - Guild: {guild_id}, Log: {log_id}, Update: {update_id}")

                # Speichere die aktualisierten Daten
                if removed_count > 0:
                    self._save_channel_pairs()
                    self._save_excluded_channels()
                    self.bot.data_manager.save_json(self.bot.status_manager.last_known_status, "last_known_status.json")
                    self._save_channel_owners()
                    logger.info(f"Cleanup abgeschlossen: {removed_count} ungültige Channel-Paare entfernt")
                else:
                    logger.info("Cleanup abgeschlossen: Keine ungültigen Channels gefunden")

            except Exception as e:
                logger.error(f"Fehler beim Cleanup der Channels: {e}", exc_info=True)

    async def delegate_to_helper(self, task_type: str, task_data: Dict) -> str:
        """Delegiert eine Aufgabe an den Helfer-Bot"""
        try:
            # Generiere eine eindeutige Task-ID
            task_id = f"{task_type}_{int(time.time())}_{random.randint(1000, 9999)}"
            logger.debug(f"Generierte Task-ID: {task_id}")
            
            # Aufgabenobjekt erstellen
            task = {
                "id": task_id,
                "type": task_type,
                "timestamp": time.time(),
                "completed": False,
                **task_data
            }
            logger.debug(f"Erstelltes Task-Objekt: {task}")
            
            # Speicherpfad für Helfer-Aufgaben
            helper_tasks_file = self.bot.data_manager.data_dir / "json" / "helper_tasks.json"
            logger.debug(f"Task-Datei-Pfad: {helper_tasks_file}")
            
            # Stelle sicher, dass das Verzeichnis existiert
            helper_tasks_file.parent.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Verzeichnis existiert: {helper_tasks_file.parent.exists()}")
            
            # Initialisiere tasks als leere Liste
            tasks = []
            
            # Versuche vorhandene Tasks zu laden
            if helper_tasks_file.exists():
                file_size = helper_tasks_file.stat().st_size
                logger.debug(f"Vorhandene Task-Datei gefunden, Größe: {file_size} Bytes")
                
                if file_size > 0:
                    try:
                        with open(helper_tasks_file, 'r', encoding='utf-8') as f:
                            content = f.read().strip()
                            logger.debug(f"Gelesener Inhalt: {content}")
                            
                            if content:
                                loaded_tasks = json.loads(content)
                                if isinstance(loaded_tasks, list):
                                    tasks = loaded_tasks
                                    logger.debug(f"Erfolgreich {len(tasks)} bestehende Tasks geladen")
                                else:
                                    logger.warning("Geladene Tasks sind keine Liste")
                    except json.JSONDecodeError as e:
                        logger.error(f"JSON-Fehler beim Laden der Tasks: {e}")
                        # Erstelle Backup der fehlerhaften Datei
                        backup_path = helper_tasks_file.with_suffix('.json.bak')
                        helper_tasks_file.rename(backup_path)
                        logger.warning(f"Fehlerhafte Datei gesichert als: {backup_path}")
                    except Exception as e:
                        logger.error(f"Unerwarteter Fehler beim Laden der Tasks: {e}")
            else:
                logger.debug("Keine bestehende Task-Datei gefunden, erstelle neue")
            
            # Füge neue Aufgabe hinzu
            tasks.append(task)
            logger.debug(f"Task-Liste nach Hinzufügen: {tasks}")
            
            # Speichere die Tasks
            try:
                # Konvertiere zu JSON
                json_str = json.dumps(tasks, indent=2, ensure_ascii=False)
                logger.debug(f"Generierter JSON-String: {json_str}")
                
                # Schreibe in temporäre Datei
                temp_file = helper_tasks_file.with_suffix('.tmp')
                with open(temp_file, 'w', encoding='utf-8') as f:
                    f.write(json_str)
                    f.flush()  # Erzwinge Schreiben auf Festplatte
                    os.fsync(f.fileno())  # Stelle sicher, dass Daten geschrieben wurden
                
                logger.debug(f"Temporäre Datei geschrieben, Größe: {temp_file.stat().st_size} Bytes")
                
                # Ersetze die alte Datei
                temp_file.replace(helper_tasks_file)
                logger.debug(f"Temporäre Datei in finale Datei umbenannt")
                
                # Überprüfe das Ergebnis
                if helper_tasks_file.exists():
                    final_size = helper_tasks_file.stat().st_size
                    logger.debug(f"Finale Datei existiert, Größe: {final_size} Bytes")
                    
                    # Verifiziere den geschriebenen Inhalt
                    with open(helper_tasks_file, 'r', encoding='utf-8') as f:
                        written_content = f.read()
                        if written_content == json_str:
                            logger.info(f"Task {task_id} erfolgreich gespeichert")
                            return task_id
                        else:
                            logger.error("Geschriebener Inhalt stimmt nicht mit Original überein")
                            return ""
                else:
                    logger.error("Finale Datei existiert nicht nach dem Schreiben")
                    return ""
                    
            except Exception as e:
                logger.error(f"Fehler beim Speichern der Tasks: {e}", exc_info=True)
                if temp_file.exists():
                    temp_file.unlink()
                return ""
                
        except Exception as e:
            logger.error(f"Allgemeiner Fehler beim Delegieren: {e}", exc_info=True)
            return ""