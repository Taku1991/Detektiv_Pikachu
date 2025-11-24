#!/usr/bin/env python3
"""
Main GUI Window
Hauptfenster mit Tab-Navigation und Bot-Management
"""

import tkinter as tk
import customtkinter as ctk
import threading
import time
import queue
import json
import asyncio
from pathlib import Path
from datetime import datetime
import logging
import sys
import os
from typing import Optional, Dict, Any

# Importiere Bot-Module
try:
    from main import StatusBot, BotTokenBalancer, setup_logging as setup_main_logging
    from helper_bot import HelperBot, setup_logging as setup_helper_logging
    from config.constants import BotConstants
    from core.log_manager import setup_bot_logging
    
    # Importiere API-Server
    try:
        from api_server import app as api_app
        API_AVAILABLE = True
        print("✅ API-Server erfolgreich importiert")
    except ImportError as e:
        print(f"⚠️ API-Server nicht verfügbar - läuft ohne API: {e}")
        API_AVAILABLE = False
        
except ImportError as e:
    print(f"Import-Fehler: {e}")
    sys.exit(1)

# Importiere GUI-Module
from .base import BaseGUIComponent
from .dashboard import Dashboard
from .bot_control import BotControl
from .channel_manager import ChannelManager
from .logs_viewer import LogsViewer
from .settings import Settings
from .setup_wizard import SetupWizard

# Setze das Aussehen für CustomTkinter
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class GUILogHandler(logging.Handler):
    """Verbesserter Log Handler für die GUI mit Bot-Erkennung"""
    
    def __init__(self, log_queue, main_window=None):
        super().__init__()
        self.log_queue = log_queue
        self.main_window = main_window
        self.setLevel(logging.DEBUG)  # Erlaube alle Log-Level
        
        # Formatter für bessere Lesbarkeit
        formatter = logging.Formatter(
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )
        self.setFormatter(formatter)
        
    def emit(self, record):
        """Sendet Log-Eintrag an die GUI"""
        try:
            # Formatiere Log-Nachricht
            formatted_message = self.format(record)
            
            # Erstelle Log-Eintrag für GUI
            log_entry = {
                'timestamp': datetime.fromtimestamp(record.created),
                'level': record.levelname,
                'logger': record.name,
                'message': record.getMessage(),
                'formatted_message': formatted_message,
                'module': getattr(record, 'module', 'unknown'),
                'funcName': getattr(record, 'funcName', 'unknown'),
                'lineno': getattr(record, 'lineno', 0),
                'thread': threading.current_thread().name,
                'process': getattr(record, 'process', 0)
            }
            
            # Füge zur Queue hinzu (non-blocking)
            try:
                self.log_queue.put_nowait(log_entry)
            except queue.Full:
                # Queue ist voll, entferne älteste Einträge
                try:
                    self.log_queue.get_nowait()
                    self.log_queue.put_nowait(log_entry)
                except queue.Empty:
                    pass
                    
        except Exception as e:
            # Fallback-Ausgabe wenn GUI-Logging fehlschlägt
            print(f"[GUI-LOG-ERROR] {e}: {record.getMessage()}")

class BotLoggerManager:
    """Verwaltet Logger für alle Bot-Komponenten"""
    
    def __init__(self, main_window):
        self.main_window = main_window
        self.gui_handler = GUILogHandler(main_window.log_queue, main_window)
        self.setup_loggers()
    
    def setup_loggers(self):
        """Konfiguriert alle Logger für die GUI"""
        # Root Logger konfigurieren
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)
        
        # Entferne bestehende Handler um Duplikate zu vermeiden
        for handler in root_logger.handlers[:]:
            if isinstance(handler, GUILogHandler):
                root_logger.removeHandler(handler)
        
        # Füge GUI-Handler hinzu
        root_logger.addHandler(self.gui_handler)
        
        # Spezifische Logger für Bot-Komponenten
        bot_loggers = [
            'main',           # Main Bot
            'StatusBot',      # Status Bot
            'discord',        # Discord.py
            'discord.client', # Discord Client
            'discord.gateway',# Discord Gateway
            'HelperBot',      # Helper Bot
            'helper_bot',     # Helper Bot Module
            'werkzeug',       # Flask/API
            'flask',          # Flask
            'api_server',     # API Server
            'gui',            # GUI
            'tkinter',        # Tkinter
            'customtkinter',  # CustomTkinter
            'config',         # Konfiguration
            'core',           # Core Module
            'bot_status',     # Bot Status
            'token_balancer', # Token Balancer
        ]
        
        for logger_name in bot_loggers:
            logger = logging.getLogger(logger_name)
            logger.setLevel(logging.DEBUG)
            
            # Entferne bestehende Handler
            for handler in logger.handlers[:]:
                if isinstance(handler, GUILogHandler):
                    logger.removeHandler(handler)
            
            # Füge GUI-Handler hinzu
            logger.addHandler(self.gui_handler)
            
            # Verhindere Duplikate durch Propagation
            logger.propagate = False
            
        # Spezielle Konfiguration für Discord.py
        discord_logger = logging.getLogger('discord')
        discord_logger.setLevel(logging.INFO)  # Reduziere Discord-Spam
        
        # Werkzeug (Flask) Logger reduzieren
        werkzeug_logger = logging.getLogger('werkzeug')
        werkzeug_logger.setLevel(logging.WARNING)
        
        print("[GUI-LOGGING] Logger-Setup abgeschlossen")
    
    def add_bot_logger(self, bot_instance, logger_name):
        """Fügt einen Logger für eine Bot-Instanz hinzu"""
        try:
            # Erstelle Logger für Bot-Instanz
            bot_logger = logging.getLogger(logger_name)
            bot_logger.setLevel(logging.DEBUG)
            
            # Entferne bestehende Handler
            for handler in bot_logger.handlers[:]:
                if isinstance(handler, GUILogHandler):
                    bot_logger.removeHandler(handler)
            
            # Füge GUI-Handler hinzu
            bot_logger.addHandler(self.gui_handler)
            bot_logger.propagate = False
            
            # Setze Logger in Bot-Instanz
            if hasattr(bot_instance, 'logger'):
                bot_instance.logger = bot_logger
            
            print(f"[GUI-LOGGING] Bot-Logger hinzugefügt: {logger_name}")
            
        except Exception as e:
            print(f"[GUI-LOGGING] Fehler beim Hinzufügen des Bot-Loggers {logger_name}: {e}")
    
    def log_bot_event(self, bot_type, event_type, message):
        """Loggt ein Bot-Event direkt"""
        try:
            logger_name = f"{bot_type.lower()}_bot"
            logger = logging.getLogger(logger_name)
            
            if event_type == 'start':
                logger.info(f"🚀 {bot_type} Bot wird gestartet: {message}")
            elif event_type == 'stop':
                logger.info(f"🛑 {bot_type} Bot wird gestoppt: {message}")
            elif event_type == 'ready':
                logger.info(f"✅ {bot_type} Bot ist bereit: {message}")
            elif event_type == 'error':
                logger.error(f"❌ {bot_type} Bot Fehler: {message}")
            elif event_type == 'warning':
                logger.warning(f"⚠️ {bot_type} Bot Warnung: {message}")
            else:
                logger.info(f"📝 {bot_type} Bot: {message}")
                
        except Exception as e:
            print(f"[GUI-LOGGING] Fehler beim Loggen von Bot-Event: {e}")

class APIServerManager:
    """Verwaltet den API-Server in einem separaten Thread"""
    
    def __init__(self):
        self.api_thread = None
        self.api_running = False
        self.api_port = 7000
        
    def start_api_server(self):
        """Startet den API-Server in einem separaten Thread"""
        if not API_AVAILABLE:
            print("⚠️ API-Server nicht verfügbar")
            return False
            
        if self.api_running:
            print("⚠️ API-Server läuft bereits")
            return True
            
        try:
            def run_api():
                try:
                    # Flask im nicht-debug Modus laufen lassen (für Threading)
                    print("🔍 Detektiv Pikachu Bot - API-Server in GUI")
                    print("=" * 50)
                    print(f"🚀 API-Server startet auf 0.0.0.0:{self.api_port}")
                    print(f"🌐 Zugriff von extern: http://10.0.10.7:{self.api_port}/api/status/quick")
                    print(f"📡 Localhost: http://localhost:{self.api_port}/api/status/quick")
                    print("=" * 50)
                    
                    # Starte Flask-App
                    api_app.run(host='0.0.0.0', port=self.api_port, debug=False, use_reloader=False, threaded=True)
                except Exception as e:
                    print(f"❌ API-Server Fehler: {e}")
                    import traceback
                    traceback.print_exc()
                    self.api_running = False
            
            self.api_thread = threading.Thread(target=run_api, daemon=True)
            self.api_thread.start()
            self.api_running = True
            
            # Kurz warten, damit der Thread startet
            import time
            time.sleep(1)
            
            print(f"✅ API-Server Thread gestartet auf Port {self.api_port}")
            print(f"🔗 Test-URL: http://10.0.10.7:{self.api_port}/api/health")
            return True
            
        except Exception as e:
            print(f"❌ Fehler beim Starten des API-Servers: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def stop_api_server(self):
        """Stoppt den API-Server"""
        self.api_running = False
        print("🛑 API-Server gestoppt")
    
    def is_running(self):
        """Prüft ob der API-Server läuft"""
        return self.api_running and self.api_thread and self.api_thread.is_alive()

class BotStatusManager:
    """Verwaltet den Status der Bots"""
    
    def __init__(self):
        self._lock = threading.Lock()
        self.main_bot_status = {
            'online': False,
            'latency': 0.0,
            'guilds': 0,
            'users': 0,
            'uptime': 0,
            'last_update': None
        }
        
        self.helper_bot_status = {
            'online': False,
            'latency': 0.0,
            'guilds': 0,
            'users': 0,
            'uptime': 0,
            'last_update': None
        }
        
        self.token_balancer_status = {
            'using_primary': True,
            'primary_blocked_until': 0,
            'status_text': 'Primärer Bot aktiv'
        }
    
    def update_main_bot_status(self, **kwargs):
        """Thread-sichere Aktualisierung des Main Bot Status"""
        with self._lock:
            self.main_bot_status.update(kwargs)
            self.main_bot_status['last_update'] = datetime.now()
    
    def update_helper_bot_status(self, **kwargs):
        """Thread-sichere Aktualisierung des Helper Bot Status"""
        with self._lock:
            self.helper_bot_status.update(kwargs)
            self.helper_bot_status['last_update'] = datetime.now()
    
    def update_balancer_status(self, **kwargs):
        """Thread-sichere Aktualisierung des Balancer Status"""
        with self._lock:
            self.token_balancer_status.update(kwargs)
    
    def get_main_bot_status(self):
        """Thread-sichere Rückgabe des Main Bot Status"""
        with self._lock:
            return self.main_bot_status.copy()
    
    def get_helper_bot_status(self):
        """Thread-sichere Rückgabe des Helper Bot Status"""
        with self._lock:
            return self.helper_bot_status.copy()
    
    def get_balancer_status(self):
        """Thread-sichere Rückgabe des Balancer Status"""
        with self._lock:
            return self.token_balancer_status.copy()

class MainWindow:
    """Haupt-GUI-Klasse für den Bot"""
    
    def __init__(self):
        # GUI Setup
        self.root = ctk.CTk()
        self.setup_window()
        
        # Status Manager mit Thread-Sicherheit
        self.status_manager = BotStatusManager()
        
        # API Server Manager
        self.api_manager = APIServerManager()
        
        # Bot-Instanzen
        self.main_bot: Optional[StatusBot] = None
        self.helper_bot: Optional[HelperBot] = None
        self.token_balancer: Optional[BotTokenBalancer] = None
        
        # Threading und Kommunikation
        self.log_queue = queue.Queue(maxsize=10000)  # Größere Queue für mehr Logs
        self.bot_threads = {}
        self.running = True
        
        # GUI Update Control
        self._update_in_progress = False
        self._last_update = 0
        self.update_interval = 1000  # ms
        
        # Verbessertes Logger Setup
        self.setup_improved_logging()
        
        # GUI Komponenten erstellen
        self.create_widgets()
        self.create_tabs()
        
        # API-Server starten
        self.start_api_server()
        
        # Periodische Updates starten
        self.start_periodic_updates()
        
        # First-Run-Setup überprüfen
        self.root.after(500, self.check_first_run_setup)
        
        # Auto-Start Bots (nach Setup-Check)
        self.root.after(1000, self.auto_start_bots)
    
    def setup_window(self):
        """Konfiguriert das Hauptfenster"""
        self.root.title("🔍 Detektiv Pikachu Bot Control Center")
        self.root.geometry("1200x800")
        
        # Icon Setup
        self.setup_window_icon()
        
        # Schließen-Event
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
    def setup_window_icon(self):
        """Setzt das Fenster-Icon"""
        try:
            icon_paths = [
                Path("detective_pikachu_bot_icon.ico"),
                Path(sys.executable).parent / "detective_pikachu_bot_icon.ico",
                Path(getattr(sys, '_MEIPASS', '.')) / "detective_pikachu_bot_icon.ico"
            ]
            
            for icon_path in icon_paths:
                if icon_path.exists():
                    try:
                        self.root.iconbitmap(str(icon_path.absolute()))
                        print(f"[GUI] Custom Icon geladen: {icon_path.absolute()}")
                        return
                    except Exception as e:
                        print(f"[GUI] Fehler beim Laden des Icons: {e}")
                        continue
            
            print("[GUI] WARNUNG: Icon-Datei nicht gefunden, verwende Standard-Icon")
        except Exception as e:
            print(f"[GUI] Fehler beim Icon-Setup: {e}")
    
    def setup_improved_logging(self):
        """Erweiterte Logging-Konfiguration"""
        # Bot-Logger-Manager erstellen
        self.bot_logger_manager = BotLoggerManager(self)
        
        print("[GUI] Verbessertes Logging-Setup abgeschlossen")
        
    def create_widgets(self):
        """Erstellt die Haupt-Widget-Struktur"""
        # Header
        self.header_frame = ctk.CTkFrame(self.root)
        self.header_frame.pack(fill="x", padx=10, pady=(10, 5))
        
        self.title_label = ctk.CTkLabel(
            self.header_frame, 
            text="🔍 Detektiv Pikachu Bot Control Center",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        self.title_label.pack(pady=10)
        
        # Status Bar
        self.status_frame = ctk.CTkFrame(self.root)
        self.status_frame.pack(fill="x", padx=10, pady=5)
        
    def create_tabs(self):
        """Erstellt alle Tabs"""
        # Hauptbereich mit Tabs
        self.tab_view = ctk.CTkTabview(self.root)
        self.tab_view.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Tab-Komponenten erstellen
        self.dashboard = Dashboard(self.tab_view.add("📊 Dashboard"), self)
        self.bot_control = BotControl(self.tab_view.add("🤖 Bots"), self)
        self.channel_manager = ChannelManager(self.tab_view.add("📋 Channels"), self)
        self.logs_viewer = LogsViewer(self.tab_view.add("📝 Logs"), self)
        self.settings = Settings(self.tab_view.add("⚙️ Settings"), self)
        
    def start_periodic_updates(self):
        """Startet die periodischen Updates"""
        if not self.running:
            return
        
        try:
            self.update_gui()
        except Exception as e:
            print(f"[ERROR] Periodic Update Error: {e}")
        
        # Nächstes Update planen
        self.root.after(self.update_interval, self.start_periodic_updates)
        
    def update_gui(self):
        """Verbesserte GUI-Aktualisierung mit Fehlerbehandlung"""
        try:
            # Verhindere überlappende Updates
            if self._update_in_progress:
                return
            
            current_time = time.time() * 1000
            if current_time - self._last_update < self.update_interval:
                return
            
            self._update_in_progress = True
            self._last_update = current_time
            
            # Process log queue
            self.process_log_queue()
            
            # Update bot status (Thread-sicher)
            self.update_bot_status_safe()
            
            # Update token balancer status
            self.update_balancer_status_safe()
            
            # Update components (mit Fehlerbehandlung)
            self.update_components_safe()
            
        except Exception as e:
            print(f"[ERROR] GUI Update Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self._update_in_progress = False
    
    def update_bot_status_safe(self):
        """Thread-sichere Bot-Status-Aktualisierung"""
        try:
            # Main Bot Status
            if self.main_bot and self.is_bot_ready(self.main_bot):
                try:
                    user_count = sum(guild.member_count for guild in self.main_bot.guilds if guild.member_count)
                    
                    self.status_manager.update_main_bot_status(
                        online=True,
                        latency=getattr(self.main_bot, 'latency', 0.0),
                        guilds=len(self.main_bot.guilds) if hasattr(self.main_bot, 'guilds') else 0,
                        users=user_count
                    )
                except Exception as e:
                    print(f"[DEBUG] Main Bot Status Error: {e}")
                    self.status_manager.update_main_bot_status(online=False, latency=0.0, guilds=0, users=0)
            else:
                self.status_manager.update_main_bot_status(online=False, latency=0.0, guilds=0, users=0)
            
            # Helper Bot Status
            if self.helper_bot and self.is_bot_ready(self.helper_bot):
                try:
                    user_count = sum(guild.member_count for guild in self.helper_bot.guilds if guild.member_count)
                    
                    self.status_manager.update_helper_bot_status(
                        online=True,
                        latency=getattr(self.helper_bot, 'latency', 0.0),
                        guilds=len(self.helper_bot.guilds) if hasattr(self.helper_bot, 'guilds') else 0,
                        users=user_count
                    )
                except Exception as e:
                    print(f"[DEBUG] Helper Bot Status Error: {e}")
                    self.status_manager.update_helper_bot_status(online=False, latency=0.0, guilds=0, users=0)
            else:
                self.status_manager.update_helper_bot_status(online=False, latency=0.0, guilds=0, users=0)
                
        except Exception as e:
            print(f"[ERROR] Bot Status Update Error: {e}")
    
    def is_bot_ready(self, bot):
        """Sichere Überprüfung ob Bot bereit ist"""
        try:
            return (hasattr(bot, 'is_ready') and bot.is_ready() and 
                    hasattr(bot, 'is_closed') and not bot.is_closed() and
                    hasattr(bot, 'guilds'))
        except Exception:
            return False
    
    def update_balancer_status_safe(self):
        """Thread-sichere Balancer-Status-Aktualisierung"""
        try:
            if self.token_balancer:
                status_text = "Primärer Bot aktiv"
                try:
                    if hasattr(self.token_balancer, 'get_status_text'):
                        status_text = self.token_balancer.get_status_text()
                    elif hasattr(self.token_balancer, 'is_using_primary'):
                        is_primary = self.token_balancer.is_using_primary()
                        status_text = "Primärer Bot aktiv" if is_primary else "Sekundärer Bot aktiv"
                except Exception as e:
                    print(f"[DEBUG] Balancer Status Error: {e}")
                
                self.status_manager.update_balancer_status(
                    using_primary=getattr(self.token_balancer, 'is_using_primary', lambda: True)(),
                    primary_blocked_until=getattr(self.token_balancer, 'primary_blocked_until', 0),
                    status_text=status_text
                )
        except Exception as e:
            print(f"[ERROR] Balancer Status Update Error: {e}")
    
    def update_components_safe(self):
        """Sichere Komponenten-Aktualisierung"""
        components_to_update = [
            ('dashboard', 'update_status'),
            ('bot_control', 'update_status'),
            ('channel_manager', 'update_bot_status')
        ]
        
        for component_name, method_name in components_to_update:
            try:
                if hasattr(self, component_name):
                    component = getattr(self, component_name)
                    if hasattr(component, method_name):
                        update_method = getattr(component, method_name)
                        update_method()
            except Exception as e:
                print(f"[DEBUG] Component Update Error ({component_name}.{method_name}): {e}")
    
    def process_log_queue(self):
        """Verbesserte Log-Queue-Verarbeitung"""
        try:
            processed = 0
            max_process = 50  # Begrenze Anzahl pro Update-Zyklus
            
            while not self.log_queue.empty() and processed < max_process:
                try:
                    log_entry = self.log_queue.get_nowait()
                    
                    # Sende an Logs Viewer
                    if hasattr(self, 'logs_viewer'):
                        self.logs_viewer.add_log_entry(log_entry)
                    
                    processed += 1
                except queue.Empty:
                    break
                except Exception as e:
                    print(f"[DEBUG] Log Entry Processing Error: {e}")
                    break
                    
        except Exception as e:
            print(f"[ERROR] Log Processing Error: {e}")
    
    def show_status_message(self, message: str, msg_type: str = "info"):
        """Verbesserte Status-Nachrichten mit besserer Thread-Sicherheit"""
        try:
            # Stelle sicher, dass wir im Main Thread sind
            if threading.current_thread() != threading.main_thread():
                self.root.after(0, lambda: self.show_status_message(message, msg_type))
                return
            
            # Entferne alte Status-Nachrichten
            for widget in self.status_frame.winfo_children():
                if hasattr(widget, '_status_message'):
                    widget.destroy()
            
            # Farbe basierend auf Typ
            color_map = {
                "success": "green",
                "error": "red", 
                "warning": "orange",
                "info": "blue"
            }
            
            color = color_map.get(msg_type, "blue")
            
            # Erstelle Status-Label
            status_label = ctk.CTkLabel(self.status_frame, text=f"✓ {message}", text_color=color)
            status_label._status_message = True
            status_label.pack(side="right", padx=10, pady=5)
            
            # Entferne nach 3 Sekunden
            self.root.after(3000, lambda: self.remove_status_label(status_label))
            
        except Exception as e:
            print(f"[ERROR] Status Message Error: {e}")
    
    def remove_status_label(self, label):
        """Sichere Entfernung von Status-Labels"""
        try:
            if label.winfo_exists():
                label.destroy()
        except Exception:
            pass  # Label bereits entfernt
    
    def on_closing(self):
        """Verbesserte Cleanup beim Schließen"""
        print("🔄 GUI wird geschlossen...")
        self.running = False
        
        # Stoppe Updates
        try:
            self.root.after_cancel("all")  # Stoppe alle geplanten Updates
        except Exception:
            pass
        
        # Stoppe API-Server
        try:
            self.stop_api_server()
        except Exception as e:
            print(f"Fehler beim Stoppen des API-Servers: {e}")
        
        # Stoppe Bots sanft
        try:
            self.stop_all_bots()
        except Exception as e:
            print(f"Fehler beim Stoppen der Bots: {e}")
        
        # Warte auf Bot-Threads
        try:
            for thread_name, thread in self.bot_threads.items():
                if thread and thread.is_alive():
                    print(f"⏳ Warte auf {thread_name}...")
                    thread.join(timeout=3)  # Reduzierte Wartezeit
                    if thread.is_alive():
                        print(f"⚠️ {thread_name} Thread antwortet nicht - forciere Beendigung")
        except Exception as e:
            print(f"Fehler beim Warten auf Bot-Threads: {e}")
        
        print("✅ GUI geschlossen")
        self.root.destroy()
    
    def start_api_server(self):
        """Startet den API-Server"""
        try:
            success = self.api_manager.start_api_server()
            if success:
                self.show_status_message("✅ API-Server gestartet auf Port 7000", "success")
            else:
                self.show_status_message("⚠️ API-Server konnte nicht gestartet werden", "warning")
        except Exception as e:
            print(f"Fehler beim Starten des API-Servers: {e}")
            self.show_status_message("❌ API-Server Fehler", "error")
    
    def stop_api_server(self):
        """Stoppt den API-Server"""
        try:
            self.api_manager.stop_api_server()
            self.show_status_message("🛑 API-Server gestoppt", "warning")
        except Exception as e:
            print(f"Fehler beim Stoppen des API-Servers: {e}")
    
    def load_settings(self):
        """Lädt die GUI-Einstellungen"""
        try:
            settings_path = Path('gui_settings.json')
            if settings_path.exists():
                with open(settings_path, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                
                # Apply loaded settings
                if 'appearance_mode' in settings:
                    ctk.set_appearance_mode(settings['appearance_mode'])
                
        except Exception as e:
            print(f"Settings loading error: {e}")
    
    def run(self):
        """Startet die GUI"""
        # Load settings
        self.load_settings()
        
        # Start GUI
        self.root.mainloop()
    
    def check_first_run_setup(self):
        """Überprüft, ob ein First-Run-Setup nötig ist"""
        try:
            env_file = Path('.env')
            
            if not env_file.exists() or env_file.stat().st_size == 0:
                self.show_first_run_setup()
            else:
                try:
                    from config.constants import BotConstants
                    if (not hasattr(BotConstants, 'PRIMARY_BOT_TOKEN') or 
                        not BotConstants.PRIMARY_BOT_TOKEN or 
                        BotConstants.PRIMARY_BOT_TOKEN == "your_primary_bot_token_here"):
                        self.show_first_run_setup()
                except:
                    self.show_first_run_setup()
        except Exception as e:
            print(f"First-Run-Check Fehler: {e}")
    
    def show_first_run_setup(self):
        """Zeigt den First-Run-Setup-Dialog"""
        setup_wizard = SetupWizard(self.root, self)
        setup_wizard.show()
    
    def auto_start_bots(self):
        """Startet die Bots automatisch nach dem Setup-Check"""
        try:
            # Prüfe ob Bot-Tokens konfiguriert sind
            from config.constants import BotConstants
            
            if (hasattr(BotConstants, 'PRIMARY_BOT_TOKEN') and 
                BotConstants.PRIMARY_BOT_TOKEN and 
                BotConstants.PRIMARY_BOT_TOKEN != "your_primary_bot_token_here"):
                
                print("🚀 Starte Bots automatisch...")
                self.bot_logger_manager.log_bot_event("System", "start", "Auto-Start aktiviert")
                self.show_status_message("Starte Bots automatisch...", "info")
                
                # Kleine Verzögerung zwischen den Starts
                self.start_main_bot()
                self.root.after(3000, self.start_helper_bot)  # Helper Bot 3 Sekunden später
                
            else:
                print("⚠️ Bot-Tokens nicht konfiguriert - Auto-Start übersprungen")
                self.bot_logger_manager.log_bot_event("System", "warning", "Bot-Tokens nicht konfiguriert")
                self.show_status_message("Bot-Tokens nicht konfiguriert", "warning")
                
        except Exception as e:
            error_msg = f"Auto-Start Fehler: {e}"
            print(error_msg)
            self.bot_logger_manager.log_bot_event("System", "error", error_msg)
            self.show_status_message(error_msg, "error")
    
    # Bot Control Methods mit verbessertem Logging
    def start_main_bot(self):
        """Startet den Main Bot mit verbessertem Logging"""
        if self.main_bot and hasattr(self.main_bot, 'is_closed') and not self.main_bot.is_closed():
            self.show_status_message("Main Bot läuft bereits", "warning")
            return
            
        try:
            # Logge Start-Event
            self.bot_logger_manager.log_bot_event("Main", "start", "Main Bot wird initialisiert")
            
            self.show_status_message("Main Bot wird gestartet...", "info")
            
            # Initialisiere Token Balancer
            self.token_balancer = BotTokenBalancer(
                BotConstants.PRIMARY_BOT_TOKEN,
                BotConstants.SECONDARY_BOT_TOKEN,
                BotConstants.RATE_LIMIT_COOL_DOWN,
                BotConstants.MAX_RETRIES
            )
            
            # Starte Main Bot in separatem Thread
            def run_main_bot():
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                    # Logge Thread-Start
                    self.bot_logger_manager.log_bot_event("Main", "start", "Main Bot Thread gestartet")
                    
                    # Erstelle Bot-Instanz
                    self.main_bot = StatusBot()
                    self.main_bot.token_balancer = self.token_balancer
                    self.token_balancer.bot = self.main_bot
                    
                    # Füge Logger für Main Bot hinzu
                    self.bot_logger_manager.add_bot_logger(self.main_bot, "StatusBot")
                    
                    # Starte Bot
                    current_token = self.token_balancer.get_current_token()
                    
                    self.bot_logger_manager.log_bot_event("Main", "start", f"Verbinde mit Discord...")
                    self.main_bot.run(current_token, reconnect=True)
                    
                except Exception as e:
                    error_msg = f"Main Bot Fehler: {e}"
                    print(error_msg)
                    self.bot_logger_manager.log_bot_event("Main", "error", error_msg)
                    self.show_status_message(f"Main Bot Fehler: {e}", "error")
            
            self.bot_threads['main_bot'] = threading.Thread(target=run_main_bot, daemon=True)
            self.bot_threads['main_bot'].start()
            
            self.show_status_message("Main Bot gestartet", "success")
            
        except Exception as e:
            error_msg = f"Main Bot Start-Fehler: {e}"
            self.bot_logger_manager.log_bot_event("Main", "error", error_msg)
            self.show_status_message(error_msg, "error")
    
    def stop_main_bot(self):
        """Stoppt den Main Bot mit verbessertem Logging"""
        try:
            if self.main_bot and hasattr(self.main_bot, 'close'):
                self.bot_logger_manager.log_bot_event("Main", "stop", "Main Bot wird gestoppt")
                self.show_status_message("Main Bot wird gestoppt...", "warning")
                
                # Stoppe Bot asynchron
                def close_bot():
                    try:
                        if hasattr(self.main_bot, 'loop') and self.main_bot.loop and not self.main_bot.loop.is_closed():
                            future = asyncio.run_coroutine_threadsafe(self.main_bot.close(), self.main_bot.loop)
                            future.result(timeout=10)
                        else:
                            # Fallback für closed loop
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            loop.run_until_complete(self.main_bot.close())
                            loop.close()
                        
                        self.bot_logger_manager.log_bot_event("Main", "stop", "Main Bot erfolgreich gestoppt")
                        
                    except Exception as e:
                        error_msg = f"Main Bot Stop-Fehler: {e}"
                        print(error_msg)
                        self.bot_logger_manager.log_bot_event("Main", "error", error_msg)
                
                threading.Thread(target=close_bot, daemon=True).start()
                self.main_bot = None
                
                self.show_status_message("Main Bot gestoppt", "success")
            else:
                self.show_status_message("Main Bot läuft nicht", "warning")
                
        except Exception as e:
            error_msg = f"Main Bot Stop-Fehler: {e}"
            self.bot_logger_manager.log_bot_event("Main", "error", error_msg)
            self.show_status_message(error_msg, "error")
    
    def restart_main_bot(self):
        """Startet den Main Bot neu"""
        self.bot_logger_manager.log_bot_event("Main", "start", "Main Bot wird neugestartet")
        self.show_status_message("Main Bot wird neugestartet...", "info")
        self.stop_main_bot()
        # Kurze Pause vor dem Neustart
        self.root.after(2000, self.start_main_bot)
    
    def start_helper_bot(self):
        """Startet den Helper Bot mit verbessertem Logging"""
        if self.helper_bot and hasattr(self.helper_bot, 'is_closed') and not self.helper_bot.is_closed():
            self.show_status_message("Helper Bot läuft bereits", "warning")
            return
            
        try:
            # Logge Start-Event
            self.bot_logger_manager.log_bot_event("Helper", "start", "Helper Bot wird initialisiert")
            
            self.show_status_message("Helper Bot wird gestartet...", "info")
            
            # Starte Helper Bot in separatem Thread
            def run_helper_bot():
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                    # Logge Thread-Start
                    self.bot_logger_manager.log_bot_event("Helper", "start", "Helper Bot Thread gestartet")
                    
                    # Erstelle Bot-Instanz
                    self.helper_bot = HelperBot()
                    
                    # Füge Logger für Helper Bot hinzu
                    self.bot_logger_manager.add_bot_logger(self.helper_bot, "HelperBot")
                    
                    # Starte Bot
                    from config.config_loader import load_config
                    _, token, _ = load_config()
                    
                    self.bot_logger_manager.log_bot_event("Helper", "start", f"Verbinde mit Discord...")
                    self.helper_bot.run(token)
                    
                except Exception as e:
                    error_msg = f"Helper Bot Fehler: {e}"
                    print(error_msg)
                    self.bot_logger_manager.log_bot_event("Helper", "error", error_msg)
                    self.show_status_message(f"Helper Bot Fehler: {e}", "error")
            
            self.bot_threads['helper_bot'] = threading.Thread(target=run_helper_bot, daemon=True)
            self.bot_threads['helper_bot'].start()
            
            self.show_status_message("Helper Bot gestartet", "success")
            
        except Exception as e:
            error_msg = f"Helper Bot Start-Fehler: {e}"
            self.bot_logger_manager.log_bot_event("Helper", "error", error_msg)
            self.show_status_message(error_msg, "error")
    
    def stop_helper_bot(self):
        """Stoppt den Helper Bot mit verbessertem Logging"""
        try:
            if self.helper_bot and hasattr(self.helper_bot, 'close'):
                self.bot_logger_manager.log_bot_event("Helper", "stop", "Helper Bot wird gestoppt")
                self.show_status_message("Helper Bot wird gestoppt...", "warning")
                
                # Stoppe Bot asynchron
                def close_bot():
                    try:
                        if hasattr(self.helper_bot, 'loop') and self.helper_bot.loop and not self.helper_bot.loop.is_closed():
                            future = asyncio.run_coroutine_threadsafe(self.helper_bot.close(), self.helper_bot.loop)
                            future.result(timeout=10)
                        else:
                            # Fallback für closed loop
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            loop.run_until_complete(self.helper_bot.close())
                            loop.close()
                        
                        self.bot_logger_manager.log_bot_event("Helper", "stop", "Helper Bot erfolgreich gestoppt")
                        
                    except Exception as e:
                        error_msg = f"Helper Bot Stop-Fehler: {e}"
                        print(error_msg)
                        self.bot_logger_manager.log_bot_event("Helper", "error", error_msg)
                
                threading.Thread(target=close_bot, daemon=True).start()
                self.helper_bot = None
                
                self.show_status_message("Helper Bot gestoppt", "success")
            else:
                self.show_status_message("Helper Bot läuft nicht", "warning")
                
        except Exception as e:
            error_msg = f"Helper Bot Stop-Fehler: {e}"
            self.bot_logger_manager.log_bot_event("Helper", "error", error_msg)
            self.show_status_message(error_msg, "error")
    
    def restart_helper_bot(self):
        """Startet den Helper Bot neu"""
        self.bot_logger_manager.log_bot_event("Helper", "start", "Helper Bot wird neugestartet")
        self.show_status_message("Helper Bot wird neugestartet...", "info")
        self.stop_helper_bot()
        # Kurze Pause vor dem Neustart
        self.root.after(2000, self.start_helper_bot)
    
    def start_all_bots(self):
        """Startet alle Bots"""
        self.start_main_bot()
        self.start_helper_bot()
        self.show_status_message("Alle Bots werden gestartet", "success")
    
    def stop_all_bots(self):
        """Stoppt alle Bots"""
        self.stop_main_bot()
        self.stop_helper_bot()
        self.show_status_message("Alle Bots werden gestoppt", "warning")
    
    def restart_all_bots(self):
        """Startet alle Bots neu"""
        self.restart_main_bot()
        self.restart_helper_bot()
        self.show_status_message("Alle Bots werden neugestartet", "info")
    
    # GUI Action Logging
    async def log_gui_action(self, action_type: str, details: str, guild_id: str = None, channel_id: str = None):
        """Loggt GUI-Aktionen im History-Channel"""
        try:
            if not self.main_bot or not hasattr(self.main_bot, 'history_channel_id'):
                return
                
            if not self.main_bot.history_channel_id:
                return
                
            history_channel = self.main_bot.get_channel(self.main_bot.history_channel_id)
            if not history_channel:
                return
            
            # Importiere discord hier um Circular Imports zu vermeiden
            import discord
            
            # Farbe basierend auf Aktion
            color_map = {
                "channel_pair_added": 0x00ff00,
                "channel_pair_removed": 0xff0000,
                "role_added": 0x0066ff,
                "role_removed": 0xff6600,
                "channel_excluded": 0x666666,
                "channel_included": 0x00ff66,
                "manual_status_change": 0xffff00,
                "config_changed": 0xff00ff
            }
            
            color = color_map.get(action_type, 0x333333)
            
            # Erstelle Embed
            embed = discord.Embed(
                title="🖥️ GUI Management Action",
                description=details,
                color=color,
                timestamp=discord.utils.utcnow()
            )
            
            embed.add_field(name="Action Type", value=action_type.replace("_", " ").title(), inline=True)
            embed.add_field(name="Source", value="Control Panel GUI", inline=True)
            
            if guild_id:
                guild = self.main_bot.get_guild(int(guild_id))
                guild_name = guild.name if guild else f"Guild {guild_id}"
                embed.add_field(name="Guild", value=guild_name, inline=True)
            
            if channel_id:
                # Verwende Channel Manager für Namen-Auflösung
                if hasattr(self, 'channel_manager'):
                    channel_name = self.channel_manager.resolve_channel_name(channel_id)
                    embed.add_field(name="Channel", value=channel_name, inline=True)
            
            embed.set_footer(text="Automated by Detektiv Pikachu Bot Management GUI")
            
            await history_channel.send(embed=embed)
            
        except Exception as e:
            print(f"Fehler beim Loggen der GUI-Aktion: {e}")
    
    def log_gui_action_threaded(self, action_type: str, details: str, guild_id: str = None, channel_id: str = None):
        """Thread-sichere Version der GUI-Action-Logging"""
        def log_action():
            try:
                if hasattr(self.main_bot, 'loop') and self.main_bot.loop and not self.main_bot.loop.is_closed():
                    future = asyncio.run_coroutine_threadsafe(
                        self.log_gui_action(action_type, details, guild_id, channel_id),
                        self.main_bot.loop
                    )
                    future.result(timeout=15)
                else:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(self.log_gui_action(action_type, details, guild_id, channel_id))
                    loop.close()
            except Exception as e:
                print(f"Fehler beim Thread-Logging: {e}")
        
        threading.Thread(target=log_action, daemon=True).start()

def main():
    """Hauptfunktion"""
    try:
        gui = MainWindow()
        gui.run()
    except KeyboardInterrupt:
        print("GUI durch Benutzer beendet")
    except Exception as e:
        print(f"GUI Fehler: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()