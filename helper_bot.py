import discord
import asyncio
import logging
import json
import time
import os
import random
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Set
from bot_status import BotStatus
from config.constants import BotConstants
from core.log_manager import setup_bot_logging

# Konfiguriere Logging
def setup_logging():
    """Konfiguriert das erweiterte Logging-System"""
    try:
        # Verwende den neuen AdvancedLogManager
        logger = setup_bot_logging('HelperBot', logging.INFO)
        
        # Teste das Logging sofort
        logger.info("Helper Bot Logging initialisiert - Test erfolgreich")
        print(f"[HELPER] Logger konfiguriert: {logger.name}")
        print(f"[HELPER] Logger Level: {logger.level}")
        print(f"[HELPER] Logger Handlers: {len(logger.handlers)}")
        for i, handler in enumerate(logger.handlers):
            print(f"[HELPER] Handler {i}: {type(handler).__name__}")
            if hasattr(handler, 'baseFilename'):
                print(f"[HELPER] Log-Datei: {handler.baseFilename}")
        
        return logger
    except Exception as e:
        print(f"[ERROR] Helper Bot Logging Setup fehlgeschlagen: {e}")
        # Fallback auf Standard-Logging
        import logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('logs/helperbot_fallback.log', encoding='utf-8')
            ]
        )
        fallback_logger = logging.getLogger('HelperBot_Fallback')
        fallback_logger.error(f"Fallback auf Standard-Logging: {e}")
        return fallback_logger

# Initialisiere Logger
print("[HELPER] Starte Helper Bot Logging-Setup...")
logger = setup_logging()
print(f"[HELPER] Logging-Setup abgeschlossen. Logger: {logger}")

class HelperBot(discord.Client):
    def __init__(self):
        # Sofortiges Logging beim Start
        print("[HELPER] Helper Bot __init__ gestartet")
        logger.info("=== Helper Bot Initialisierung gestartet ===")
        
        intents = discord.Intents.default()
        intents.members = True
        intents.guild_messages = True
        
        super().__init__(intents=intents)
        
        # Dateipfade für die Kommunikation mit dem Hauptbot
        self.data_dir = BotConstants.DATA_DIR
        self.tasks_file = self.data_dir / 'json' / 'helper_tasks.json'
        self.results_file = self.data_dir / 'json' / 'helper_results.json'
        
        logger.info(f"Tasks-Datei-Pfad: {self.tasks_file}")
        logger.info(f"Results-Datei-Pfad: {self.results_file}")
        print(f"[HELPER] Tasks-Datei: {self.tasks_file}")
        print(f"[HELPER] Results-Datei: {self.results_file}")
        
        # Task-Queue und Status
        self.tasks = []
        self.is_processing = False
        self.last_check = 0
        self.check_interval = 1.0  # Sekunden
        
        # Cache für Kanäle und Rollen
        self.channel_cache = {}
        self.role_cache = {}
        
        # Startup-Timestamp für Debugging
        self.startup_time = time.time()
        logger.info(f"Helper Bot Initialisierung abgeschlossen - Startup Time: {self.startup_time}")
        print(f"[HELPER] Initialisierung abgeschlossen um {datetime.fromtimestamp(self.startup_time)}")
        
    async def on_ready(self):
        """Wenn der Bot bereit ist"""
        ready_time = time.time()
        startup_duration = ready_time - self.startup_time
        
        logger.info(f"🤖 HelperBot gestartet als: {self.user.name} ({self.user.id})")
        logger.info(f"⏱️ Startup-Dauer: {startup_duration:.2f} Sekunden")
        logger.info(f"🏠 Verbunden mit {len(self.guilds)} Servern")
        
        print(f"[HELPER] ✅ Bot bereit: {self.user.name}")
        print(f"[HELPER] ⏱️ Startup-Dauer: {startup_duration:.2f}s")
        print(f"[HELPER] 🏠 Server: {len(self.guilds)}")
        
        for guild in self.guilds:
            logger.info(f"📊 Verbunden mit Server: {guild.name} ({guild.id})")
            print(f"[HELPER] Server: {guild.name}")
        
        # Starte Task-Check-Schleife
        logger.info("🔄 Starte Task-Prüfschleife...")
        print("[HELPER] 🔄 Starte Task-Überwachung...")
        self.bg_task = self.loop.create_task(self.check_tasks_loop())
        
        # Gesundheitscheck-Log
        logger.info("💚 Helper Bot vollständig initialisiert und betriebsbereit")
        print("[HELPER] 💚 Helper Bot ist betriebsbereit!")
        
    async def on_connect(self):
        """Wenn der Bot sich verbindet"""
        logger.info("🔗 Helper Bot verbindet sich mit Discord...")
        print("[HELPER] 🔗 Verbindung zu Discord wird hergestellt...")
        
    async def on_disconnect(self):
        """Wenn der Bot getrennt wird"""
        logger.warning("⚠️ Helper Bot von Discord getrennt")
        print("[HELPER] ⚠️ Verbindung zu Discord getrennt")
        
    async def on_resumed(self):
        """Wenn die Session wiederhergestellt wird"""
        logger.info("🔄 Helper Bot Session wiederhergestellt")
        print("[HELPER] 🔄 Session wiederhergestellt")
        
    async def check_tasks_loop(self):
        """Prüft regelmäßig auf neue Aufgaben und verarbeitet diese"""
        await self.wait_until_ready()
        logger.info("🔄 Task-Prüfschleife gestartet")
        print("[HELPER] 🔄 Task-Überwachung aktiv")
        
        last_info_log = 0
        task_count = 0
        
        while not self.is_closed():
            try:
                current_time = time.time()
                tasks_processed = False
                
                # Prüfe channel_states.json
                states_file = Path(self.data_dir) / "json" / "channel_states.json"
                
                if states_file.exists():
                    try:
                        with open(states_file, 'r', encoding='utf-8') as f:
                            channel_states = json.loads(f.read())
                        
                        # Log nur bei der ersten Überprüfung oder alle 5 Minuten
                        if current_time - last_info_log > 300:
                            logger.info(f"📊 Überprüfe {len(channel_states)} Channel-States")
                            print(f"[HELPER] 📊 {len(channel_states)} Channel-States zu prüfen")
                            
                        changes_made = False
                        pending_tasks = 0
                        
                        # Verarbeite jeden Channel-State
                        for channel_id, state in channel_states.items():
                            # Überspringe bereits abgeschlossene Änderungen
                            if state.get('completed', False):
                                continue
                                
                            pending_tasks += 1
                            
                            # Prüfe ob die Änderung älter als 5 Sekunden ist und noch nicht abgeschlossen
                            if (current_time - state['last_update'] >= 5 and 
                                current_time - state.get('last_attempt', 0) >= 5):
                                
                                try:
                                    channel = self.get_channel(int(channel_id))
                                    if channel:
                                        current_name = channel.name
                                        desired_name = state['desired_name']
                                        
                                        # Prüfe ob die Änderung noch notwendig ist
                                        if current_name != desired_name:
                                            logger.info(f"🔧 Versuche Channel-Update für {channel_id}: "
                                                      f"'{current_name}' -> '{desired_name}'")
                                            print(f"[HELPER] 🔧 Update: {current_name} -> {desired_name}")
                                            
                                            try:
                                                await channel.edit(name=desired_name)
                                                logger.info(f"✅ Channel {channel_id} erfolgreich auf "
                                                          f"'{desired_name}' aktualisiert")
                                                print(f"[HELPER] ✅ Erfolgreich: {desired_name}")
                                                state['completed'] = True
                                                changes_made = True
                                                tasks_processed = True
                                                task_count += 1
                                                
                                            except discord.HTTPException as e:
                                                if e.status == 429:  # Rate limit
                                                    retry_after = getattr(e, 'retry_after', 60)
                                                    logger.warning(f"⏰ Rate limit erreicht, warte "
                                                                 f"{retry_after} Sekunden")
                                                    print(f"[HELPER] ⏰ Rate limit: {retry_after}s warten")
                                                    state['last_attempt'] = current_time
                                                    changes_made = True
                                                    await asyncio.sleep(min(retry_after, 60))
                                                else:
                                                    logger.error(f"❌ HTTP-Fehler beim Channel-Update: {e}")
                                                    print(f"[HELPER] ❌ HTTP-Fehler: {e}")
                                                    state['completed'] = True  # Markiere als abgeschlossen bei Fehler
                                                    changes_made = True
                                        else:
                                            # Name ist bereits korrekt
                                            logger.debug(f"✓ Channel {channel_id} ist bereits '{desired_name}'")
                                            state['completed'] = True
                                            changes_made = True
                                    else:
                                        logger.warning(f"⚠️ Channel {channel_id} nicht gefunden")
                                        state['completed'] = True  # Markiere als abgeschlossen
                                        changes_made = True
                                            
                                except Exception as e:
                                    logger.error(f"❌ Fehler bei der Verarbeitung von Channel {channel_id}: {e}")
                                    print(f"[HELPER] ❌ Channel-Fehler {channel_id}: {e}")
                                    state['completed'] = True  # Markiere als abgeschlossen bei Fehler
                                    changes_made = True
                        
                        # Speichere Änderungen zurück
                        if changes_made:
                            with open(states_file, 'w', encoding='utf-8') as f:
                                json.dump(channel_states, f, indent=2)
                            logger.debug(f"💾 Channel-States gespeichert ({len(channel_states)} Einträge)")
                        
                        # Status-Log alle 5 Minuten oder bei Aktivität
                        if current_time - last_info_log > 300 or tasks_processed:
                            if pending_tasks > 0:
                                logger.info(f"📈 {pending_tasks} ausstehende Tasks, {task_count} gesamt verarbeitet")
                                print(f"[HELPER] 📈 {pending_tasks} ausstehend, {task_count} erledigt")
                            else:
                                logger.info(f"✅ Alle Channel-Updates abgeschlossen ({task_count} gesamt)")
                                print(f"[HELPER] ✅ Alle Updates fertig ({task_count} gesamt)")
                            last_info_log = current_time
                                
                    except json.JSONDecodeError as e:
                        logger.error(f"❌ Ungültiges JSON in channel_states.json: {e}")
                        print(f"[HELPER] ❌ JSON-Fehler: {e}")
                    except Exception as e:
                        logger.error(f"❌ Fehler beim Verarbeiten der Channel-States: {e}")
                        print(f"[HELPER] ❌ States-Fehler: {e}")
                else:
                    # Datei existiert nicht - Log nur alle 5 Minuten
                    if current_time - last_info_log > 300:
                        logger.debug("📂 Keine channel_states.json gefunden")
                        last_info_log = current_time
                
                # Heartbeat-Log alle 5 Minuten wenn keine Aktivität
                if not tasks_processed and current_time - last_info_log > 300:
                    logger.info(f"💚 Helper Bot aktiv - {task_count} Tasks gesamt verarbeitet")
                    print(f"[HELPER] 💚 Aktiv - {task_count} Tasks erledigt")
                    last_info_log = current_time
                    
            except Exception as e:
                logger.error(f"💥 Unerwarteter Fehler in der Task-Schleife: {e}", exc_info=True)
                print(f"[HELPER] 💥 Task-Schleife Fehler: {e}")
                
            await asyncio.sleep(0.1)  # Kurze Pause zwischen den Prüfungen
    
    async def load_tasks(self):
        """Lädt Aufgaben aus der Aufgabendatei"""
        try:
            # Überprüfe, ob die Datei existiert und lesbar ist
            if not self.tasks_file.exists():
                return
                
            # Prüfe die Dateigröße
            file_size = self.tasks_file.stat().st_size
            if file_size == 0:
                return
                
            try:
                with open(self.tasks_file, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if not content:
                        return
                        
                    new_tasks = json.loads(content)
                    
                if new_tasks:
                    logger.info(f"Neue Aufgaben gefunden: {new_tasks}")
                    
                    # Leere die Datei sofort
                    with open(self.tasks_file, 'w', encoding='utf-8') as f:
                        json.dump([], f)
                    
                    # Füge die Aufgaben zur Queue hinzu
                    if isinstance(new_tasks, list):
                        self.tasks.extend(new_tasks)
                        logger.info(f"{len(new_tasks)} neue Aufgaben zur Queue hinzugefügt")
                    else:
                        self.tasks.append(new_tasks)
                        logger.info("Eine neue Aufgabe zur Queue hinzugefügt")
                    
            except json.JSONDecodeError as e:
                logger.error(f"Ungültiges JSON in der Aufgabendatei: {e}")
                # Erstelle Backup der fehlerhaften Datei
                backup_path = self.tasks_file.with_suffix('.json.bak')
                with open(backup_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                logger.warning(f"Backup der fehlerhaften Datei erstellt: {backup_path}")
                # Leere die fehlerhafte Datei
                with open(self.tasks_file, 'w', encoding='utf-8') as f:
                    json.dump([], f)
                    
            except Exception as e:
                logger.error(f"Fehler beim Laden der Aufgaben: {e}", exc_info=True)
                
        except Exception as e:
            logger.error(f"Allgemeiner Fehler beim Laden der Aufgaben: {e}", exc_info=True)
    
    async def process_tasks(self):
        """Verarbeitet die Aufgaben in der Queue"""
        if not self.tasks:
            return
            
        self.is_processing = True
        results = []
        
        try:
            while self.tasks:
                task = self.tasks.pop(0)
                task_type = task.get('type')
                logger.info(f"Verarbeite Task: {task}")
                
                if task_type == 'update_channel_name':
                    result = await self.update_channel_name(task)
                elif task_type == 'lock_channel':
                    result = await self.update_channel_lock(task)
                elif task_type == 'update_channel_lock':
                    result = await self.update_channel_lock(task)
                else:
                    logger.warning(f"Unbekannter Aufgabentyp: {task_type}")
                    result = {"status": "error", "task_id": task.get('id'), "error": "Unbekannter Aufgabentyp"}
                
                logger.info(f"Task-Ergebnis: {result}")
                results.append(result)
                
            # Speichere Ergebnisse
            if results:
                await self.save_results(results)
            
        except Exception as e:
            logger.error(f"Fehler bei der Aufgabenverarbeitung: {e}", exc_info=True)
        finally:
            self.is_processing = False
    
    async def update_channel_name(self, task):
        """Aktualisiert den Kanalnamen"""
        try:
            channel_id = task.get('channel_id')
            guild_id = task.get('guild_id')
            new_name = task.get('new_name')
            
            start_time = time.time()
            logger.info(f"Starte Channel-Name-Update für Channel {channel_id} zu '{new_name}'")
            
            # Obligatorische Parameter prüfen
            if not channel_id:
                return {"status": "error", "task_id": task.get('id'), "error": "Fehlende Channel-ID"}
                
            if not new_name:
                return {"status": "error", "task_id": task.get('id'), "error": "Fehlender neuer Name"}
            
            # Channel abrufen
            channel = self.get_channel(int(channel_id))
            
            # Falls Channel nicht direkt gefunden wurde, versuche über Guild
            if not channel and guild_id:
                try:
                    guild = self.get_guild(int(guild_id))
                    if guild:
                        channel = guild.get_channel(int(channel_id))
                except Exception as e:
                    logger.error(f"Fehler beim Abrufen der Guild {guild_id}: {e}")
            
            if not channel:
                logger.error(f"Channel nicht gefunden: {channel_id}")
                return {"status": "error", "task_id": task.get('id'), "error": f"Channel nicht gefunden: {channel_id}"}
            
            # Vermeide unnötige Updates, wenn der Name bereits identisch ist
            if channel.name == new_name:
                logger.info(f"Channel {channel_id} hat bereits den Namen '{new_name}', keine Änderung nötig")
                return {"status": "success", "task_id": task.get('id'), "message": "Name bereits aktuell"}
            
            # Führe die Namensänderung durch
            try:
                logger.info(f"Ändere Namen von Channel {channel_id} von '{channel.name}' zu '{new_name}'")
                await channel.edit(name=new_name, reason="Status-Update durch Helper-Bot")
                
                # Erfolg protokollieren
                duration = time.time() - start_time
                logger.info(f"Channel-Name erfolgreich aktualisiert in {duration:.2f}s")
                return {
                    "status": "success", 
                    "task_id": task.get('id'),
                    "channel_id": channel_id,
                    "old_name": channel.name,
                    "new_name": new_name,
                    "duration": duration
                }
                
            except discord.Forbidden:
                logger.error(f"Keine Berechtigung zum Ändern des Channel-Namens: {channel_id}")
                return {"status": "error", "task_id": task.get('id'), "error": "Keine Berechtigung"}
                
            except discord.HTTPException as e:
                logger.error(f"HTTP-Fehler beim Ändern des Channel-Namens: {e}")
                return {"status": "error", "task_id": task.get('id'), "error": f"HTTP-Fehler: {str(e)}"}
                
        except Exception as e:
            logger.error(f"Allgemeiner Fehler beim Channel-Name-Update: {e}", exc_info=True)
            return {"status": "error", "task_id": task.get('id'), "error": str(e)}
    
    async def update_channel_lock(self, task):
        """Aktualisiert den Lock-Status eines Kanals"""
        try:
            channel_id = task.get('channel_id')
            guild_id = task.get('guild_id')
            locked = task.get('locked', False)  # Bool-Wert: True = sperren, False = entsperren
            permission_data = task.get('permission_data', None)  # Direkte Berechtigungsdaten
            
            start_time = time.time()
            logger.info(f"Starte Channel-Lock-Update für Channel {channel_id}, Lock: {locked}")
            
            # Obligatorische Parameter prüfen
            if not channel_id:
                return {"status": "error", "task_id": task.get('id'), "error": "Fehlende Channel-ID"}
            
            # Channel abrufen
            channel = self.get_channel(int(channel_id))
            
            # Falls Channel nicht direkt gefunden wurde, versuche über Guild
            if not channel and guild_id:
                try:
                    guild = self.get_guild(int(guild_id))
                    if guild:
                        channel = guild.get_channel(int(channel_id))
                except Exception as e:
                    logger.error(f"Fehler beim Abrufen der Guild {guild_id}: {e}")
            
            if not channel:
                logger.error(f"Channel nicht gefunden: {channel_id}")
                return {"status": "error", "task_id": task.get('id'), "error": f"Channel nicht gefunden: {channel_id}"}
            
            # Berechtigungen aktualisieren
            try:
                if permission_data:
                    # Wenn wir direkte Berechtigungsdaten haben, setze sie genau wie spezifiziert
                    logger.info(f"Aktualisiere Berechtigungen mit bereitgestellten Daten für Channel {channel_id}")
                    
                    # Die Berechtigungsdaten von Discord kommen als Liste von Overwrite-Objekten
                    for overwrite_data in permission_data:
                        # Extrahiere die Daten
                        target_id = int(overwrite_data.get('id'))
                        target_type = overwrite_data.get('type')
                        
                        # Bestimme das Zielobjekt (Rolle oder Member)
                        target = None
                        if target_type == 0:  # Rolle
                            target = channel.guild.get_role(target_id)
                        elif target_type == 1:  # Member
                            target = channel.guild.get_member(target_id)
                        
                        if target:
                            # Konvertiere die Berechtigungsflags
                            allow = discord.Permissions(int(overwrite_data.get('allow', 0)))
                            deny = discord.Permissions(int(overwrite_data.get('deny', 0)))
                            
                            # Erstelle das Overwrite-Objekt
                            overwrite = discord.PermissionOverwrite.from_pair(allow, deny)
                            
                            # Setze die Berechtigungen
                            await channel.set_permissions(target, overwrite=overwrite)
                else:
                    # Ansonsten führe Standard-Lock/Unlock durch
                    logger.info(f"Führe {'Sperrung' if locked else 'Entsperrung'} für Channel {channel_id} durch")
                    
                    # Default-Berechtigungen für @everyone
                    everyone_role = channel.guild.default_role
                    
                    # Existierende Berechtigungen abrufen
                    overwrite = channel.overwrites_for(everyone_role)
                    
                    # Berechtigungen je nach Lock-Status setzen
                    if locked:
                        # Sperren
                        overwrite.send_messages = False
                        overwrite.add_reactions = False
                        overwrite.send_messages_in_threads = False
                        overwrite.create_public_threads = False
                        overwrite.create_private_threads = False
                    else:
                        # Entsperren - nur überschreiben, wenn die Permission gesetzt ist
                        # Sonst belassen wir es bei der Standard-Einstellung
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
                    
                    # Berechtigungen anwenden
                    await channel.set_permissions(everyone_role, overwrite=overwrite)
                
                # Erfolg protokollieren
                duration = time.time() - start_time
                logger.info(f"Channel-Lock erfolgreich aktualisiert in {duration:.2f}s")
                return {
                    "status": "success", 
                    "task_id": task.get('id'),
                    "channel_id": channel_id,
                    "action": "locked" if locked else "unlocked",
                    "duration": duration
                }
                
            except discord.Forbidden:
                logger.error(f"Keine Berechtigung zum Ändern der Channel-Berechtigungen: {channel_id}")
                return {"status": "error", "task_id": task.get('id'), "error": "Keine Berechtigung"}
                
            except discord.HTTPException as e:
                logger.error(f"HTTP-Fehler beim Ändern der Channel-Berechtigungen: {e}")
                return {"status": "error", "task_id": task.get('id'), "error": f"HTTP-Fehler: {str(e)}"}
                
        except Exception as e:
            logger.error(f"Allgemeiner Fehler beim Channel-Lock-Update: {e}", exc_info=True)
            return {"status": "error", "task_id": task.get('id'), "error": str(e)}
    
    async def save_results(self, results):
        """Speichert die Ergebnisse der Aufgabenverarbeitung"""
        try:
            if not results:
                return
                
            # Laden existierender Ergebnisse
            existing_results = []
            if self.results_file.exists():
                try:
                    with open(self.results_file, 'r', encoding='utf-8') as f:
                        existing_results = json.load(f)
                except Exception as e:
                    logger.error(f"Fehler beim Laden der Ergebnisse: {e}")
            
            # Neue Ergebnisse hinzufügen
            existing_results.extend(results)
            
            # Ergebnisse speichern
            with open(self.results_file, 'w', encoding='utf-8') as f:
                json.dump(existing_results, f, indent=2)
                
            logger.info(f"{len(results)} Ergebnisse gespeichert")
            
        except Exception as e:
            logger.error(f"Fehler beim Speichern der Ergebnisse: {e}", exc_info=True)
    
    async def on_message(self, message):
        """Behandelt Discord-Nachrichten"""
        # Ignoriere Nachrichten vom Bot selbst
        if message.author == self.user:
            return
            
        # Einfache Ping-Antwort, um zu prüfen ob der Bot läuft
        if message.content.startswith('!helper'):
            await message.channel.send("HelperBot ist aktiv und prüft auf Aufgaben")

if __name__ == "__main__":
    # Helper Bot starten
    from config.config_loader import load_config
    _, token, _ = load_config()  # Zweites Token ist für den Helper Bot
    
    bot = HelperBot()
    bot.run(token) 