import discord
from discord import app_commands
from discord.ext import commands
from typing import Dict, Set, Optional
import logging
import time
import asyncio
import os
from datetime import datetime
from pathlib import Path
import json
import random

# Interne Module (aus dem core Ordner)
from .status_manager import StatusManager
from .message_manager import MessageManager
from .channel_manager import ChannelManager
from .channel_config import ChannelConfig
from .channel_locker import ChannelLocker

# Externe Module (aus dem Hauptverzeichnis und anderen Ordnern)
from bot_status import BotStatus
from .data_manager import DataManager
from config.constants import BotConstants
from utils.status_patterns import StatusPatterns

logger = logging.getLogger('StatusBot')

class StatusBot(commands.Bot):
    def __init__(self):
        logger.info("Initializing StatusBot")
        intents = discord.Intents.default()
        intents.members = True
        intents.guild_messages = True
        intents.message_content = True
        intents.reactions = True
        intents.presences = True
        
        super().__init__(command_prefix="!", intents=intents)
        
        # Basis-Komponenten sofort initialisieren
        logger.info("Initializing essential components")
        self.data_manager = DataManager(BotConstants.DATA_DIR)
        self.config = ChannelConfig()
        self.patterns = StatusPatterns()
        
        # Manager werden lazy initialisiert
        self._status_manager = None
        self._message_manager = None
        self._channel_manager = None
        self._channel_locker = None
        
        # State tracking (basics only)
        self.guild_channels: Dict[str, Dict[str, str]] = {}
        self.history_channel_id: Optional[int] = None
        
        # Tasks file path
        self.tasks_file = Path(BotConstants.DATA_DIR) / "json" / "helper_tasks.json"
        
        # Füge den Error Handler für Slash-Commands hinzu
        @self.tree.error
        async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
            try:
                if isinstance(error, app_commands.MissingPermissions):
                    await interaction.response.send_message(
                        "❌ Du hast nicht die erforderlichen Berechtigungen für diesen Befehl.",
                        ephemeral=True
                    )
                elif isinstance(error, app_commands.CommandNotFound):
                    await interaction.response.send_message(
                        "❌ Unbekannter Befehl. Nutze `/help` für eine Liste aller verfügbaren Befehle.",
                        ephemeral=True
                    )
                else:
                    logger.error(f"Command error: {error}", exc_info=True)
                    if interaction.response.is_done():
                        await interaction.followup.send(
                            "❌ Ein unerwarteter Fehler ist aufgetreten. Bitte überprüfe die Logs.",
                            ephemeral=True
                        )
                    else:
                        await interaction.response.send_message(
                            "❌ Ein unerwarteter Fehler ist aufgetreten. Bitte überprüfe die Logs.",
                            ephemeral=True
                        )
            except discord.errors.NotFound:
                pass
        
        # Initiale Datenladung in setup_hook() verschoben
        logger.info("StatusBot initialization complete")
    
    # Lazy Properties für Manager
    @property
    def status_manager(self):
        if self._status_manager is None:
            logger.info("Initializing StatusManager")
            self._status_manager = StatusManager(self)
        return self._status_manager
    
    @property  
    def message_manager(self):
        if self._message_manager is None:
            logger.info("Initializing MessageManager")
            self._message_manager = MessageManager(self)
        return self._message_manager
    
    @property
    def channel_manager(self):
        if self._channel_manager is None:
            logger.info("Initializing ChannelManager")
            self._channel_manager = ChannelManager(self)
        return self._channel_manager
    
    @property
    def channel_locker(self):
        if self._channel_locker is None:
            logger.info("Initializing ChannelLocker")
            self._channel_locker = ChannelLocker(self)
        return self._channel_locker

    def load_data(self):
            """Load initial data"""
            # Lade Channel-Konfigurationen
            self.guild_channels = self.data_manager.load_json("guild_channels.json")
            logger.info(f"Geladene Guild-Channels: {len(self.guild_channels)} Guilds mit insgesamt {sum(len(channels) for channels in self.guild_channels.values())} Kanälen")
            
            # Lade History Channel
            history_data = self.data_manager.load_json("history_channel.json")
            self.history_channel_id = history_data.get("history_channel")
            logger.info(f"History Channel ID geladen: {self.history_channel_id}")
            
            # Lade Manager-Daten nur wenn Manager bereits initialisiert
            if self._status_manager is not None:
                self.status_manager.load_data()
            if self._channel_manager is not None:
                self.channel_manager.load_data()
            if self._channel_locker is not None:
                self.channel_locker.load_data()

    async def on_connect(self):
        """Called when the bot connects to Discord"""
        logger.info("Bot connected to Discord")
        try:
            app_info = await self.application_info()
            logger.info(f"Connected as: {app_info.name}")
        except Exception as e:
            logger.error(f"Error getting application info: {e}")

    async def on_ready(self):
        """Called when the bot has successfully connected to Discord"""
        try:
            await self.change_presence(
                activity=discord.Activity(
                    type=discord.ActivityType.watching,
                    name="Bot-Status"
                ),
                status=discord.Status.online
            )
            logger.info(f"Logged in as {self.user.name} ({self.user.id})")
            logger.info(f"Connected to {len(self.guilds)} guilds")
            
            connected_guilds = []
            for guild in self.guilds:
                connected_guilds.append(f"{guild.name} (ID: {guild.id})")
            
            if connected_guilds:
                logger.info("Connected to guilds:\n" + "\n".join(connected_guilds))
            else:
                logger.warning("Bot is not connected to any guilds!")
                
        except Exception as e:
            logger.error(f"Error in on_ready: {e}", exc_info=True)

    async def on_disconnect(self):
        """Called when the bot disconnects from Discord"""
        logger.warning("Bot disconnected from Discord")
        # Versuche neu zu verbinden
        try:
            if not self.is_closed():
                logger.info("Attempting to reconnect...")
        except Exception as e:
            logger.error(f"Error during reconnect attempt: {e}")

    async def setup_hook(self):
        """Initialize bot data and start tasks"""
        logger.info("Setup hook started...")
        
        # Lade Cogs zuerst (vor anderen Tasks)
        try:
            logger.info("Loading cogs...")
            from cogs import setup_cogs
            await setup_cogs(self)
            logger.info("All cogs loaded successfully")
        except Exception as e:
            logger.error(f"Error loading cogs: {e}", exc_info=True)
            return
        
        # Dann lade Daten und starte Tasks
        self.load_data()
        
        # Starte Tasks nur wenn Manager bereits initialisiert
        if self._status_manager is not None:
            self.status_manager.start_tasks()
        
        try:
            logger.info("Waiting for bot to be fully ready...")
            # Warte maximal 30 Sekunden
            await asyncio.wait_for(self.wait_until_ready(), timeout=30.0)
            logger.info("Bot is ready!")
            
        except asyncio.TimeoutError:
            logger.warning("Bot ready timeout after 30 seconds - continuing anyway")
        except Exception as e:
            logger.error(f"Unexpected error while waiting for bot to be ready: {e}")
            return
        
        # Synchronisiere die Slash-Commands
        try:
            logger.info("Starting command sync...")
            commands = [cmd.name for cmd in self.tree.get_commands()]
            logger.info(f"Found commands to sync: {commands}")
            
            # Sync mit Timeout
            synced = await asyncio.wait_for(self.tree.sync(), timeout=15.0)
            synced_names = [cmd.name for cmd in synced]
            logger.info(f"Successfully synced {len(synced)} command(s): {synced_names}")
            
        except asyncio.TimeoutError:
            logger.warning("Command sync timeout after 15 seconds")
        except Exception as e:
            logger.error(f"Error syncing application commands: {e}", exc_info=True)
            
        logger.info("Setup hook completed")

    async def on_ready(self):
        """Called when the bot has successfully connected to Discord"""
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="Bot-Status"
            ),
            status=discord.Status.online
        )
        logger.info(f"Logged in as {self.user.name} ({self.user.id})")
        logger.info(f"Connected to {len(self.guilds)} guilds")
        for guild in self.guilds:
            logger.info(f"Connected to guild: {guild.name} ({guild.id})")

    async def on_connect(self):
        """Called when the bot connects to Discord"""
        logger.info("Bot connected to Discord")

    async def on_disconnect(self):
        """Called when the bot disconnects from Discord"""
        logger.warning("Bot disconnected from Discord")

    async def on_resumed(self):
        """Called when the bot resumes a session"""
        logger.info("Bot session resumed")

    async def on_message(self, message: discord.Message):
            """Handle incoming messages"""
            # Verarbeite Commands
            await self.process_commands(message)

            # Verarbeite Status-Updates
            await self.status_manager.process_message(message)

            logger.debug(f"Nachricht verarbeitet: {message.content}")

    async def update_channel_name(self, channel: discord.TextChannel, new_name: str, reason: str = None) -> bool:
        """
        Aktualisiert den Namen eines Kanals mit Rate-Limit-Behandlung
        """
        try:
            # Versuche zuerst die direkte Änderung
            try:
                await channel.edit(name=new_name, reason=reason)
                logger.info(f"Channel {channel.id} erfolgreich umbenannt zu '{new_name}'")
                return True
            except discord.RateLimited as e:
                logger.warning(f"Rate-Limit erreicht beim Umbenennen von Channel {channel.id}. Retry after: {e.retry_after}s")
                
                # Stelle sicher, dass das Verzeichnis existiert
                self.tasks_file.parent.mkdir(parents=True, exist_ok=True)
                
                # Erstelle Task für Helper-Bot
                task_data = {
                    "channel_id": str(channel.id),
                    "guild_id": str(channel.guild.id),
                    "new_name": new_name,
                    "type": "update_channel_name",
                    "id": f"{int(time.time())}_{random.randint(1000, 9999)}",
                    "timestamp": time.time(),
                    "completed": False
                }
                
                # Speichere die Task
                try:
                    tasks = []
                    if self.tasks_file.exists():
                        try:
                            with open(self.tasks_file, 'r', encoding='utf-8') as f:
                                content = f.read().strip()
                                if content:
                                    tasks = json.loads(content)
                        except json.JSONDecodeError as e:
                            logger.error(f"Fehler beim Lesen der Tasks-Datei: {e}")
                            # Erstelle Backup der fehlerhaften Datei
                            backup_file = self.tasks_file.with_suffix('.json.bak')
                            self.tasks_file.rename(backup_file)
                    
                    tasks.append(task_data)
                    
                    with open(self.tasks_file, 'w', encoding='utf-8') as f:
                        json.dump(tasks, f, indent=2, ensure_ascii=False)
                    
                    logger.info(f"Task für Helper-Bot erstellt: Channel {channel.id} -> '{new_name}'")
                    return True
                    
                except Exception as e:
                    logger.error(f"Fehler beim Speichern der Helper-Task: {e}")
                    return False
                    
            except Exception as e:
                logger.error(f"Fehler beim Umbenennen von Channel {channel.id}: {e}")
                return False
                
        except Exception as e:
            logger.error(f"Allgemeiner Fehler in update_channel_name: {e}")
            return False
            
    async def update_channel_lock(self, channel: discord.TextChannel, locked: bool, reason: str = None) -> bool:
        """
        Aktualisiert den Lock-Status eines Kanals mit Rate-Limit-Behandlung
        """
        try:
            # Versuche zuerst die direkte Änderung
            try:
                overwrite = channel.overwrites_for(channel.guild.default_role)
                
                if locked:
                    overwrite.send_messages = False
                    overwrite.add_reactions = False
                    overwrite.send_messages_in_threads = False
                    overwrite.create_public_threads = False
                    overwrite.create_private_threads = False
                else:
                    if overwrite.send_messages is False:
                        overwrite.send_messages = None
                    if overwrite.add_reactions is False:
                        overwrite.add_reactions = None
                    if overwrite.send_messages_in_threads is False:
                        overwrite.send_messages_in_threads = None
                    if overwrite.create_public_threads is False:
                        overwrite.create_public_threads = None
                    if overwrite.create_private_threads is False:
                        overwrite.create_private_threads = None
                
                await channel.set_permissions(channel.guild.default_role, overwrite=overwrite, reason=reason)
                logger.info(f"Channel {channel.id} erfolgreich {'gesperrt' if locked else 'entsperrt'}")
                return True
                
            except discord.RateLimited as e:
                logger.warning(f"Rate-Limit erreicht beim {'Sperren' if locked else 'Entsperren'} von Channel {channel.id}. Retry after: {e.retry_after}s")
                
                # Erstelle Task für Helper-Bot
                task_data = {
                    "channel_id": str(channel.id),
                    "guild_id": str(channel.guild.id),
                    "locked": locked,
                    "type": "lock_channel",
                    "id": f"{int(time.time())}_{random.randint(1000, 9999)}",
                    "timestamp": time.time(),
                    "completed": False
                }
                
                # Speichere die Task
                try:
                    tasks = []
                    if self.tasks_file.exists():
                        try:
                            with open(self.tasks_file, 'r', encoding='utf-8') as f:
                                content = f.read().strip()
                                if content:
                                    tasks = json.loads(content)
                        except Exception as e:
                            logger.error(f"Fehler beim Lesen der Tasks: {e}")
                    
                    tasks.append(task_data)
                    
                    with open(self.tasks_file, 'w', encoding='utf-8') as f:
                        json.dump(tasks, f, indent=2, ensure_ascii=False)
                    
                    logger.info(f"Task für Helper-Bot erstellt: Channel {channel.id} -> {'Sperren' if locked else 'Entsperren'}")
                    return True
                    
                except Exception as e:
                    logger.error(f"Fehler beim Speichern der Helper-Task: {e}")
                    return False
                    
            except Exception as e:
                logger.error(f"Fehler beim {'Sperren' if locked else 'Entsperren'} von Channel {channel.id}: {e}")
                return False
                
        except Exception as e:
            logger.error(f"Allgemeiner Fehler in update_channel_lock: {e}")
            return False