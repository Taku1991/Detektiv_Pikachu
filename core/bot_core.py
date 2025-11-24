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
logger.setLevel(logging.DEBUG)

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
        
        # Command sync tracking
        self.commands_synced = False
        
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
        cogs_loaded = False
        try:
            logger.info("Loading cogs...")
            from cogs import setup_cogs
            await setup_cogs(self)
            logger.info("All cogs loaded successfully")
            cogs_loaded = True
        except Exception as e:
            logger.error(f"Error loading cogs: {e}", exc_info=True)
            logger.warning("Continuing setup despite cog loading errors...")
            # NICHT mehr return hier - setze fort!
        
        # Dann lade Daten und starte Tasks
        try:
            self.load_data()
            logger.info("Bot data loaded successfully")
        except Exception as e:
            logger.error(f"Error loading bot data: {e}", exc_info=True)
        
        # Prüfe ob last_known_status.json existiert und Daten enthält
        status_file = self.data_manager.data_dir / "json" / "last_known_status.json"
        should_initialize = False
        
        if not status_file.exists():
            logger.info("last_known_status.json existiert nicht - Status-Initialisierung erforderlich")
            should_initialize = True
        elif status_file.stat().st_size == 0:
            logger.info("last_known_status.json ist leer - Status-Initialisierung erforderlich")
            should_initialize = True
        elif not self.status_manager.last_known_status:
            logger.info("last_known_status ist leer nach dem Laden - Status-Initialisierung erforderlich")
            should_initialize = True
        else:
            logger.info(f"last_known_status.json erfolgreich geladen mit {len(self.status_manager.last_known_status)} Kanälen - keine Initialisierung erforderlich")
        
        # Asynchrone Initialisierung der Statusdaten, nur falls notwendig
        try:
            if should_initialize:
                await self.status_manager.initialize_status_from_channels()
            else:
                logger.info("Status-Initialisierung übersprungen - verwende existierende Daten")
        except Exception as e:
            logger.error(f"Error during status initialization: {e}", exc_info=True)
            
        # Stelle sicher, dass alle Manager-Daten geladen sind
        try:
            logger.info("Lade Manager-Daten...")
            self.status_manager.load_data()
            self.channel_manager.load_data()
            self.channel_locker.load_data()
            logger.info("Manager-Daten geladen")
        except Exception as e:
            logger.error(f"Error loading manager data: {e}", exc_info=True)
        
        # Starte Tasks - initialisiere Manager falls nötig
        try:
            logger.info("Starte Status Manager Tasks...")
            self.status_manager.start_tasks()
            logger.info("Status Manager Tasks gestartet")
        except Exception as e:
            logger.error(f"Error starting status manager tasks: {e}", exc_info=True)
        
        # Initialisiere Channel-Namen für API/GUI
        try:
            logger.info("Initialisiere Channel-Namen...")
            await self.initialize_channel_names()
            logger.info("Channel-Namen-Initialisierung abgeschlossen")
        except Exception as e:
            logger.error(f"Error initializing channel names: {e}", exc_info=True)
        
        # Warte auf Bot-Ready - aber stoppe die Ausführung NICHT bei Timeout
        bot_ready = False
        try:
            logger.info("Waiting for bot to be fully ready...")
            # Warte maximal 30 Sekunden
            await asyncio.wait_for(self.wait_until_ready(), timeout=30.0)
            logger.info("Bot is ready!")
            bot_ready = True
            
        except asyncio.TimeoutError:
            logger.warning("Bot ready timeout after 30 seconds - continuing with command sync anyway")
        except Exception as e:
            logger.error(f"Unexpected error while waiting for bot to be ready: {e}", exc_info=True)
            logger.warning("Continuing with command sync despite ready error...")
        
        # Synchronisiere die Slash-Commands - IMMER versuchen!
        await self.sync_commands_with_retry()
        
        logger.info("Setup hook completed")

    async def sync_commands_with_retry(self, max_retries=3):
        """Synchronisiert Commands mit Retry-Logik"""
        for attempt in range(max_retries):
            try:
                logger.info(f"Starting command sync (attempt {attempt + 1}/{max_retries})...")
                commands = [cmd.name for cmd in self.tree.get_commands()]
                logger.info(f"Found commands to sync: {commands}")
                
                if not commands:
                    logger.warning("No commands found to sync! Check if cogs were loaded properly.")
                    # Versuche Cogs nochmal zu laden falls leer
                    if attempt == 0:
                        try:
                            logger.info("Attempting to reload cogs...")
                            from cogs import setup_cogs
                            await setup_cogs(self)
                            commands = [cmd.name for cmd in self.tree.get_commands()]
                            logger.info(f"Commands after cog reload: {commands}")
                        except Exception as e:
                            logger.error(f"Failed to reload cogs: {e}")
                
                # Sync mit Timeout
                synced = await asyncio.wait_for(self.tree.sync(), timeout=15.0)
                synced_names = [cmd.name for cmd in synced]
                logger.info(f"✅ Successfully synced {len(synced)} command(s): {synced_names}")
                
                if len(synced) == 0:
                    logger.warning("⚠️ Command sync returned 0 commands - this might indicate an issue")
                else:
                    self.commands_synced = True  # Markiere als erfolgreich synchronisiert
                
                return True  # Erfolg
                
            except asyncio.TimeoutError:
                logger.warning(f"Command sync timeout after 15 seconds (attempt {attempt + 1})")
                if attempt < max_retries - 1:
                    logger.info("Retrying command sync in 5 seconds...")
                    await asyncio.sleep(5)
                    
            except Exception as e:
                logger.error(f"Error syncing application commands (attempt {attempt + 1}): {e}", exc_info=True)
                if attempt < max_retries - 1:
                    logger.info("Retrying command sync in 3 seconds...")
                    await asyncio.sleep(3)
        
        logger.error("❌ Failed to sync commands after all retries!")
        return False

    async def on_ready(self):
        """Called when the bot has successfully connected to Discord - Konsolidierte Version"""
        try:
            # Set bot presence
            await self.change_presence(
                activity=discord.Activity(
                    type=discord.ActivityType.watching,
                    name="Bot-Status"
                ),
                status=discord.Status.online
            )

            logger.info(f"Logged in as {self.user.name} ({self.user.id})")
            logger.info(f"Connected to {len(self.guilds)} guilds")

            # Log all connected guilds
            connected_guilds = []
            for guild in self.guilds:
                connected_guilds.append(f"{guild.name} (ID: {guild.id})")
                logger.info(f"Connected to guild: {guild.name} ({guild.id})")

            if not connected_guilds:
                logger.warning("Bot is not connected to any guilds!")
            else:
                logger.info("Connected to guilds:\n" + "\n".join(connected_guilds))

            # Stelle sicher, dass Status-Manager-Tasks laufen
            if not self.status_manager.check_inactivity_task.is_running():
                logger.info("Status-Manager-Task nicht aktiv - starte explizit...")
                self.status_manager.start_tasks()

            # Fallback Command-Sync falls setup_hook fehlgeschlagen ist
            if not self.commands_synced:
                logger.warning("🔄 Commands wurden noch nicht synchronisiert - versuche Fallback-Sync in on_ready")

                # Warte kurz, damit der Bot vollständig ready ist
                await asyncio.sleep(2)

                # Prüfe ob Cogs geladen sind
                available_commands = [cmd.name for cmd in self.tree.get_commands()]
                if not available_commands:
                    logger.warning("Keine Commands verfügbar - versuche Cogs nachzuladen...")
                    try:
                        from cogs import setup_cogs
                        await setup_cogs(self)
                        available_commands = [cmd.name for cmd in self.tree.get_commands()]
                        logger.info(f"Commands nach Cog-Nachladen: {available_commands}")
                    except Exception as e:
                        logger.error(f"Fehler beim Nachladen der Cogs in on_ready: {e}")

                # Versuche Command-Sync
                try:
                    success = await self.sync_commands_with_retry(max_retries=2)
                    if success:
                        logger.info("✅ Fallback Command-Sync in on_ready erfolgreich!")
                    else:
                        logger.error("❌ Auch Fallback Command-Sync fehlgeschlagen!")
                except Exception as e:
                    logger.error(f"Fehler beim Fallback Command-Sync: {e}")
            else:
                logger.info("✅ Commands bereits synchronisiert - kein Fallback-Sync nötig")

        except Exception as e:
            logger.error(f"Error in on_ready: {e}", exc_info=True)

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
        try:
            # Verarbeite Commands
            await self.process_commands(message)

            # Verarbeite Status-Updates - wichtig für Channel-Namen-Updates
            await self.status_manager.process_message(message)

            logger.debug(f"Nachricht verarbeitet: {message.content}")
            
        except Exception as e:
            logger.error(f"Fehler in on_message: {e}", exc_info=True)

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
                
                # Informiere Token Balancer über Rate Limit
                if hasattr(self, 'token_balancer') and self.token_balancer:
                    alternate_token = self.token_balancer.handle_rate_limit(e.retry_after)
                    if alternate_token:
                        logger.info("Token Balancer wechselt aufgrund von Rate Limit")
                
                # Erstelle Task für Helper-Bot
                return await self._create_helper_task("update_channel_name", {
                    "channel_id": str(channel.id),
                    "guild_id": str(channel.guild.id),
                    "new_name": new_name
                })
                
            except discord.HTTPException as e:
                # Prüfe auf Rate Limit (Status 429)
                if e.status == 429:
                    retry_after = getattr(e, 'retry_after', 60)
                    logger.warning(f"HTTP Rate-Limit (429) erreicht beim Umbenennen von Channel {channel.id}. Retry after: {retry_after}s")
                    
                    # Informiere Token Balancer über Rate Limit
                    if hasattr(self, 'token_balancer') and self.token_balancer:
                        alternate_token = self.token_balancer.handle_rate_limit(retry_after)
                        if alternate_token:
                            logger.info("Token Balancer wechselt aufgrund von HTTP Rate Limit")
                    
                    # Erstelle Task für Helper-Bot
                    return await self._create_helper_task("update_channel_name", {
                        "channel_id": str(channel.id),
                        "guild_id": str(channel.guild.id),
                        "new_name": new_name
                    })
                else:
                    logger.error(f"HTTP-Fehler beim Umbenennen von Channel {channel.id}: {e}")
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
                
                # Informiere Token Balancer über Rate Limit
                if hasattr(self, 'token_balancer') and self.token_balancer:
                    alternate_token = self.token_balancer.handle_rate_limit(e.retry_after)
                    if alternate_token:
                        logger.info("Token Balancer wechselt aufgrund von Rate Limit")
                
                # Erstelle Task für Helper-Bot
                return await self._create_helper_task("update_channel_lock", {
                    "channel_id": str(channel.id),
                    "guild_id": str(channel.guild.id),
                    "locked": locked
                })
                
            except discord.HTTPException as e:
                # Prüfe auf Rate Limit (Status 429)
                if e.status == 429:
                    retry_after = getattr(e, 'retry_after', 60)
                    logger.warning(f"HTTP Rate-Limit (429) erreicht beim {'Sperren' if locked else 'Entsperren'} von Channel {channel.id}. Retry after: {retry_after}s")
                    
                    # Informiere Token Balancer über Rate Limit
                    if hasattr(self, 'token_balancer') and self.token_balancer:
                        alternate_token = self.token_balancer.handle_rate_limit(retry_after)
                        if alternate_token:
                            logger.info("Token Balancer wechselt aufgrund von HTTP Rate Limit")
                    
                    # Erstelle Task für Helper-Bot
                    return await self._create_helper_task("update_channel_lock", {
                        "channel_id": str(channel.id),
                        "guild_id": str(channel.guild.id),
                        "locked": locked
                    })
                else:
                    logger.error(f"HTTP-Fehler beim {'Sperren' if locked else 'Entsperren'} von Channel {channel.id}: {e}")
                    return False
                    
            except Exception as e:
                logger.error(f"Fehler beim {'Sperren' if locked else 'Entsperren'} von Channel {channel.id}: {e}")
                return False
                
        except Exception as e:
            logger.error(f"Allgemeiner Fehler in update_channel_lock: {e}")
            return False

    async def _create_helper_task(self, task_type: str, task_data: dict) -> bool:
        """
        Hilfsmethode zum Erstellen von Helper-Bot-Tasks
        """
        try:
            # Stelle sicher, dass das Verzeichnis existiert
            self.tasks_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Erweitere Task-Daten
            full_task_data = {
                **task_data,
                "type": task_type,
                "id": f"{int(time.time())}_{random.randint(1000, 9999)}",
                "timestamp": time.time(),
                "completed": False
            }
            
            # Lade bestehende Tasks
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
            
            tasks.append(full_task_data)
            
            with open(self.tasks_file, 'w', encoding='utf-8') as f:
                json.dump(tasks, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Task für Helper-Bot erstellt: {task_type} - {full_task_data['id']}")
            return True
            
        except Exception as e:
            logger.error(f"Fehler beim Speichern der Helper-Task: {e}")
            return False

    async def initialize_channel_names(self):
        """Sammelt alle Channel-Namen beim Bot-Start für die API"""
        try:
            print("🔍 Sammle Channel-Namen für API...")
            
            # Lade existierende guild_channels.json
            guild_channels_path = 'data/json/guild_channels.json'
            if not os.path.exists(guild_channels_path):
                print("❌ guild_channels.json nicht gefunden")
                return
            
            # Lade mit UTF-8 Encoding
            with open(guild_channels_path, 'r', encoding='utf-8') as f:
                guild_channels = json.load(f)
            
            # Neue Struktur mit Namen erstellen
            guild_channels_with_names = {}
            
            for guild_id, categories in guild_channels.items():
                guild_channels_with_names[guild_id] = {}
                
                # Hole Guild-Objekt
                guild = self.get_guild(int(guild_id))
                if not guild:
                    print(f"❌ Guild {guild_id} nicht gefunden")
                    continue
                    
                print(f"📋 Verarbeite Guild: {guild.name}")
                
                for category_id, channel_list in categories.items():
                    guild_channels_with_names[guild_id][category_id] = {}
                    
                    # Hole Category-Objekt für Namen
                    category = guild.get_channel(int(category_id))
                    category_name = category.name if category else f"Category {category_id}"
                    
                    for channel_id in channel_list:
                        # Hole Channel-Objekt
                        channel = guild.get_channel(int(channel_id))
                        if channel:
                            # Erstelle sauberen Channel-Namen (ohne Emoji-Prefix)
                            clean_name = channel.name
                            
                            # Entferne bekannte Emoji-Prefixes
                            prefixes = ['⚡ᴾ│', '✅ᴾ│', '❌ᴾ│', '🔧ᴾ│', '⚡│', '✅│', '❌│', '🔧│']
                            for prefix in prefixes:
                                if clean_name.startswith(prefix):
                                    clean_name = clean_name[len(prefix):]
                                    break
                            
                            guild_channels_with_names[guild_id][category_id][str(channel_id)] = {
                                'name': clean_name,
                                'full_name': channel.name,
                                'category': category_name,
                                'type': str(channel.type),
                                'position': channel.position
                            }
                            
                            print(f"  ✅ {clean_name} ({channel_id})")
                        else:
                            print(f"  ❌ Channel {channel_id} nicht gefunden")
                            # Fallback-Eintrag
                            guild_channels_with_names[guild_id][category_id][str(channel_id)] = {
                                'name': f'Channel {channel_id}',
                                'full_name': f'Channel {channel_id}',
                                'category': category_name,
                                'type': 'text',
                                'position': 0
                            }
            
            # Speichere mit UTF-8 Encoding
            output_path = 'data/json/guild_channels_with_names.json'
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(guild_channels_with_names, f, ensure_ascii=False, indent=2)
            
            print(f"✅ Channel-Namen erfolgreich gespeichert in {output_path}")
            
        except Exception as e:
            print(f"❌ Fehler beim Sammeln der Channel-Namen: {e}")
            import traceback
            traceback.print_exc()
    
    def get_status_emoji_by_name(self, status_name: str) -> str:
        """Hilfsfunktion um Status-Emoji anhand des Namens zu bekommen"""
        from bot_status import BotStatus
        status_map = {
            BotStatus.ONLINE.value: "🟢",
            BotStatus.OFFLINE.value: "🔴", 
            BotStatus.PROBLEM.value: "🟡",
            BotStatus.MAINTENANCE.value: "🟦"
        }
        return status_map.get(status_name, "⚪")