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
    # Verwende den neuen AdvancedLogManager
    return setup_bot_logging('HelperBot', logging.INFO)

# Initialisiere Logger
logger = setup_logging()

class HelperBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.guild_messages = True
        
        super().__init__(intents=intents)
        
        # Dateipfade für die Kommunikation mit dem Hauptbot
        self.data_dir = BotConstants.DATA_DIR
        self.tasks_file = self.data_dir / 'json' / 'helper_tasks.json'
        self.results_file = self.data_dir / 'json' / 'helper_results.json'
        
        logger.debug(f"Tasks-Datei-Pfad: {self.tasks_file}")
        logger.debug(f"Results-Datei-Pfad: {self.results_file}")
        
        # Task-Queue und Status
        self.tasks = []
        self.is_processing = False
        self.last_check = 0
        self.check_interval = 1.0  # Sekunden
        
        # Cache für Kanäle und Rollen
        self.channel_cache = {}
        self.role_cache = {}
        
    async def on_ready(self):
        """Wenn der Bot bereit ist"""
        logger.info(f"HelperBot gestartet als: {self.user.name} ({self.user.id})")
        
        # Starte Task-Check-Schleife
        self.bg_task = self.loop.create_task(self.check_tasks_loop())
        
    async def check_tasks_loop(self):
        """Prüft regelmäßig auf neue Aufgaben und verarbeitet diese"""
        await self.wait_until_ready()
        logger.info("Task-Prüfschleife gestartet")
        last_info_log = 0
        
        while not self.is_closed():
            try:
                # Prüfe channel_states.json
                states_file = Path(self.data_dir) / "json" / "channel_states.json"
                
                if states_file.exists():
                    try:
                        with open(states_file, 'r', encoding='utf-8') as f:
                            channel_states = json.loads(f.read())
                            
                        current_time = time.time()
                        changes_made = False
                        
                        # Verarbeite jeden Channel-State
                        for channel_id, state in channel_states.items():
                            # Überspringe bereits abgeschlossene Änderungen
                            if state.get('completed', False):
                                continue
                                
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
                                            logger.info(f"Versuche Channel-Update für {channel_id}: "
                                                      f"'{current_name}' -> '{desired_name}'")
                                            
                                            try:
                                                await channel.edit(name=desired_name)
                                                logger.info(f"Channel {channel_id} erfolgreich auf "
                                                          f"'{desired_name}' aktualisiert")
                                                state['completed'] = True
                                                changes_made = True
                                                
                                            except discord.HTTPException as e:
                                                if e.status == 429:  # Rate limit
                                                    retry_after = e.retry_after
                                                    logger.warning(f"Rate limit erreicht, warte "
                                                                 f"{retry_after} Sekunden")
                                                    state['last_attempt'] = current_time
                                                    changes_made = True
                                                    await asyncio.sleep(retry_after)
                                                else:
                                                    logger.error(f"HTTP-Fehler beim Channel-Update: {e}")
                                                    state['completed'] = True  # Markiere als abgeschlossen bei Fehler
                                                    changes_made = True
                                        else:
                                            # Name ist bereits korrekt
                                            state['completed'] = True
                                            changes_made = True
                                            
                                except Exception as e:
                                    logger.error(f"Fehler bei der Verarbeitung von Channel {channel_id}: {e}")
                                    state['completed'] = True  # Markiere als abgeschlossen bei Fehler
                                    changes_made = True
                        
                        # Speichere Änderungen zurück
                        if changes_made:
                            with open(states_file, 'w', encoding='utf-8') as f:
                                json.dump(channel_states, f, indent=2)
                                
                    except json.JSONDecodeError as e:
                        logger.error(f"Ungültiges JSON in channel_states.json: {e}")
                    except Exception as e:
                        logger.error(f"Fehler beim Verarbeiten der Channel-States: {e}")
                
                # Log nur alle 5 Minuten wenn keine Aktivität
                current_time = time.time()
                if current_time - last_info_log > 300:
                    logger.info("Helper-Bot aktiv - Überwache Channel-States")
                    last_info_log = current_time
                    
            except Exception as e:
                logger.error(f"Unerwarteter Fehler in der Task-Schleife: {e}", exc_info=True)
                
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