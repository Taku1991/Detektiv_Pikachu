#!/usr/bin/env python3
"""
Erweiterte Logs Viewer Component
Mit verbesserter Filterung für Bot-spezifische Logs und Channel-Nachrichten
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import ttk
import re
from datetime import datetime
from typing import List, Dict, Optional
from .base import BaseGUIComponent

class LogsViewer(BaseGUIComponent):
    """Erweiterte Log-Anzeige-Komponente mit verbesserter Bot-Filterung"""
    
    def __init__(self, parent, main_window):
        super().__init__(parent, main_window)
        self.log_entries = []  # Alle Log-Einträge
        self.filtered_entries = []  # Gefilterte Log-Einträge
        self.max_log_entries = 10000  # Maximum Anzahl Log-Einträge
        self.auto_scroll = True
        
        # Erweiterte Filter-Optionen
        self.noise_patterns = [
            r'Heartbeat acknowledged',
            r'Sending a keepalive',
            r'Received message',
            r'HTTP request',
            r'Websocket.*ping',
            r'Websocket.*pong'
        ]
        
        self.setup_logs_viewer()
        
    def setup_logs_viewer(self):
        """Erstellt die Log-Anzeige mit erweiterten Filteroptionen"""
        # Filter Controls Frame
        self.setup_filter_controls()
        
        # Log Display Frame
        self.setup_log_display()
        
        # Control Buttons Frame
        self.setup_control_buttons()
        
    def setup_filter_controls(self):
        """Erstellt die erweiterten Filter-Kontrollen"""
        filter_frame = ctk.CTkFrame(self.parent)
        filter_frame.pack(fill="x", padx=10, pady=10)
        
        # Titel
        ctk.CTkLabel(filter_frame, text="📝 Erweiterte System-Logs", 
                     font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(10, 5))
        
        # Haupt-Filter-Optionen (Reihe 1)
        controls_frame1 = ctk.CTkFrame(filter_frame)
        controls_frame1.pack(fill="x", padx=10, pady=5)
        
        # Log Level Filter
        ctk.CTkLabel(controls_frame1, text="Level:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.level_filter = ctk.CTkOptionMenu(
            controls_frame1, 
            values=["Alle", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
            command=self.apply_filters
        )
        self.level_filter.set("INFO")
        self.level_filter.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        
        # Bot Filter (erweitert)
        ctk.CTkLabel(controls_frame1, text="Bot:").grid(row=0, column=2, padx=5, pady=5, sticky="w")
        self.bot_filter = ctk.CTkOptionMenu(
            controls_frame1, 
            values=["Alle", "Main Bot", "Helper Bot", "GUI", "API", "Discord", "System"],
            command=self.apply_filters
        )
        self.bot_filter.set("Alle")
        self.bot_filter.grid(row=0, column=3, padx=5, pady=5, sticky="ew")
        
        # Message Source Filter (NEU)
        ctk.CTkLabel(controls_frame1, text="Quelle:").grid(row=0, column=4, padx=5, pady=5, sticky="w")
        self.source_filter = ctk.CTkOptionMenu(
            controls_frame1, 
            values=["Alle", "Bot Internal", "Discord Events", "Channel Messages", "Commands", "API Calls"],
            command=self.apply_filters
        )
        self.source_filter.set("Alle")
        self.source_filter.grid(row=0, column=5, padx=5, pady=5, sticky="ew")
        
        # Erweiterte Filter-Optionen (Reihe 2)
        controls_frame2 = ctk.CTkFrame(filter_frame)
        controls_frame2.pack(fill="x", padx=10, pady=5)
        
        # Relevanz Filter
        ctk.CTkLabel(controls_frame2, text="Relevanz:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.relevance_filter = ctk.CTkOptionMenu(
            controls_frame2, 
            values=["Alle", "Nur Bot-Aktionen", "Nur Fehler", "Nur Status", "Nur Commands", "Nur Discord"],
            command=self.apply_filters
        )
        self.relevance_filter.set("Nur Bot-Aktionen")
        self.relevance_filter.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        
        # Channel Filter (NEU)
        ctk.CTkLabel(controls_frame2, text="Channel:").grid(row=0, column=2, padx=5, pady=5, sticky="w")
        self.channel_filter = ctk.CTkOptionMenu(
            controls_frame2, 
            values=["Alle", "Keine Channel-Logs", "Nur Channel-Logs", "Nur System", "Nur Befehle"],
            command=self.apply_filters
        )
        self.channel_filter.set("Keine Channel-Logs")  # Standard: Channel-Logs ausblenden
        self.channel_filter.grid(row=0, column=3, padx=5, pady=5, sticky="ew")
        
        # Noise Filter (NEU)
        self.noise_filter_var = ctk.BooleanVar(value=True)
        noise_filter_check = ctk.CTkCheckBox(controls_frame2, text="Noise filtern", 
                                           variable=self.noise_filter_var,
                                           command=self.apply_filters)
        noise_filter_check.grid(row=0, column=4, padx=5, pady=5)
        
        # Live Filter (NEU)
        self.live_filter_var = ctk.BooleanVar(value=False)
        live_filter_check = ctk.CTkCheckBox(controls_frame2, text="Nur Live-Events", 
                                          variable=self.live_filter_var,
                                          command=self.apply_filters)
        live_filter_check.grid(row=0, column=5, padx=5, pady=5)
        
        # Such- und Kontroll-Optionen (Reihe 3)
        controls_frame3 = ctk.CTkFrame(filter_frame)
        controls_frame3.pack(fill="x", padx=10, pady=5)
        
        # Suche
        ctk.CTkLabel(controls_frame3, text="Suche:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.search_entry = ctk.CTkEntry(controls_frame3, placeholder_text="Suche in Logs...")
        self.search_entry.grid(row=0, column=1, columnspan=2, padx=5, pady=5, sticky="ew")
        self.search_entry.bind('<KeyRelease>', self.on_search_changed)
        
        # Clear Search Button
        clear_search_btn = ctk.CTkButton(controls_frame3, text="🗑️ Leeren", 
                                        command=self.clear_search, width=80)
        clear_search_btn.grid(row=0, column=3, padx=5, pady=5)
        
        # Auto-Scroll Toggle
        self.auto_scroll_var = ctk.BooleanVar(value=True)
        auto_scroll_check = ctk.CTkCheckBox(controls_frame3, text="Auto-Scroll", 
                                           variable=self.auto_scroll_var,
                                           command=self.toggle_auto_scroll)
        auto_scroll_check.grid(row=0, column=4, padx=5, pady=5)
        
        # Quick Filter Buttons (NEU)
        quick_filter_frame = ctk.CTkFrame(filter_frame)
        quick_filter_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(quick_filter_frame, text="Quick Filter:").pack(side="left", padx=5)
        
        quick_buttons = [
            ("🤖 Nur Bot", self.filter_bot_only),
            ("❌ Nur Fehler", self.filter_errors_only),
            ("📨 Nur Commands", self.filter_commands_only),
            ("🔧 Nur System", self.filter_system_only),
            ("📊 Alle", self.filter_show_all)
        ]
        
        for text, command in quick_buttons:
            btn = ctk.CTkButton(quick_filter_frame, text=text, command=command, width=80)
            btn.pack(side="left", padx=2)
        
        # Configure grid weights
        for frame in [controls_frame1, controls_frame2, controls_frame3]:
            frame.grid_columnconfigure(1, weight=1)
        
    def setup_log_display(self):
        """Erstellt die Log-Anzeige"""
        # Log Display Frame
        display_frame = ctk.CTkFrame(self.parent)
        display_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Erweiterte Info Bar
        self.info_frame = ctk.CTkFrame(display_frame)
        self.info_frame.pack(fill="x", padx=10, pady=5)
        
        self.info_label = ctk.CTkLabel(self.info_frame, text="Log-Einträge: 0 | Gefiltert: 0")
        self.info_label.pack(side="left", padx=10, pady=5)
        
        # Filter Status Label (NEU)
        self.filter_status_label = ctk.CTkLabel(self.info_frame, text="Filter: Standard")
        self.filter_status_label.pack(side="right", padx=10, pady=5)
        
        # Log Text Display
        self.log_display = ctk.CTkTextbox(
            display_frame,
            font=ctk.CTkFont(family="Consolas", size=11),
            wrap="word"
        )
        self.log_display.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Konfiguriere Text-Tags für verschiedene Log-Level
        self.configure_text_tags()
        
    def configure_text_tags(self):
        """Konfiguriert erweiterte Text-Tags für verschiedene Log-Level und Typen"""
        try:
            # Level-Tags
            self.log_display._textbox.tag_configure("DEBUG", foreground="#888888")
            self.log_display._textbox.tag_configure("INFO", foreground="#FFFFFF")
            self.log_display._textbox.tag_configure("WARNING", foreground="#FFA500")
            self.log_display._textbox.tag_configure("ERROR", foreground="#FF6B6B")
            self.log_display._textbox.tag_configure("CRITICAL", foreground="#8B0000")
            
            # Bot-spezifische Tags
            self.log_display._textbox.tag_configure("MAIN_BOT", foreground="#4A90E2")
            self.log_display._textbox.tag_configure("HELPER_BOT", foreground="#7ED321")
            self.log_display._textbox.tag_configure("GUI", foreground="#BD10E0")
            self.log_display._textbox.tag_configure("API", foreground="#F5A623")
            self.log_display._textbox.tag_configure("DISCORD", foreground="#7289DA")
            self.log_display._textbox.tag_configure("SYSTEM", foreground="#95A5A6")
            
            # Message-Type-Tags (NEU)
            self.log_display._textbox.tag_configure("COMMAND", foreground="#E67E22", font=("Consolas", 11, "bold"))
            self.log_display._textbox.tag_configure("CHANNEL_MSG", foreground="#95A5A6", font=("Consolas", 10, "italic"))
            self.log_display._textbox.tag_configure("BOT_ACTION", foreground="#2ECC71", font=("Consolas", 11, "bold"))
            self.log_display._textbox.tag_configure("NOISE", foreground="#7F8C8D", font=("Consolas", 10))
            
        except Exception as e:
            print(f"[DEBUG] Text-Tags-Konfiguration fehlgeschlagen: {e}")
        
    def setup_control_buttons(self):
        """Erstellt die Kontroll-Buttons"""
        controls_frame = ctk.CTkFrame(self.parent)
        controls_frame.pack(fill="x", padx=10, pady=10)
        
        buttons_frame = ctk.CTkFrame(controls_frame)
        buttons_frame.pack(pady=10)
        
        # Clear Logs Button
        clear_btn = ctk.CTkButton(buttons_frame, text="🗑️ Logs leeren", 
                                 command=self.clear_logs, width=120)
        clear_btn.pack(side="left", padx=5)
        
        # Export Logs Button
        export_btn = ctk.CTkButton(buttons_frame, text="📤 Exportieren", 
                                  command=self.export_logs, width=120)
        export_btn.pack(side="left", padx=5)
        
        # Refresh Button
        refresh_btn = ctk.CTkButton(buttons_frame, text="🔄 Aktualisieren", 
                                   command=self.refresh_logs, width=120)
        refresh_btn.pack(side="left", padx=5)
        
        # Scroll to Bottom Button
        scroll_btn = ctk.CTkButton(buttons_frame, text="⬇️ Nach unten", 
                                  command=self.scroll_to_bottom, width=120)
        scroll_btn.pack(side="left", padx=5)
        
    def add_log_entry(self, log_entry):
        """Fügt einen Log-Eintrag hinzu"""
        try:
            # Bereite Log-Eintrag auf
            processed_entry = self.process_log_entry(log_entry)
            
            # Füge zur Liste hinzu
            self.log_entries.append(processed_entry)
            
            # Begrenze die Anzahl der Log-Einträge
            if len(self.log_entries) > self.max_log_entries:
                self.log_entries = self.log_entries[-self.max_log_entries:]
            
            # Wende Filter an
            self.apply_filters()
            
        except Exception as e:
            print(f"[ERROR] Log Entry Add Error: {e}")
    
    def process_log_entry(self, log_entry):
        """Erweiterte Verarbeitung eines Log-Eintrags mit verbesserter Kategorisierung"""
        try:
            # Extrahiere Informationen
            timestamp = log_entry.get('timestamp', datetime.now())
            level = log_entry.get('level', 'INFO')
            logger_name = log_entry.get('logger', 'Unknown')
            message = log_entry.get('message', '')
            
            # Bestimme erweiterte Kategorien
            bot_type = self.determine_bot_type_extended(logger_name, message)
            message_source = self.determine_message_source(logger_name, message)
            message_type = self.determine_message_type(message)
            relevance = self.determine_relevance_extended(level, message, message_type)
            is_noise = self.is_noise_message(message)
            is_channel_log = self.is_channel_log_message(message)
            
            # Formatiere Nachricht
            formatted_message = self.format_message_extended(timestamp, level, logger_name, message, message_type)
            
            return {
                'timestamp': timestamp,
                'level': level,
                'logger': logger_name,
                'message': message,
                'bot_type': bot_type,
                'message_source': message_source,
                'message_type': message_type,
                'relevance': relevance,
                'is_noise': is_noise,
                'is_channel_log': is_channel_log,
                'formatted_message': formatted_message,
                'raw_entry': log_entry
            }
            
        except Exception as e:
            print(f"[ERROR] Log Entry Processing Error: {e}")
            return {
                'timestamp': datetime.now(),
                'level': 'ERROR',
                'logger': 'LogProcessor',
                'message': f'Fehler beim Verarbeiten: {str(e)}',
                'bot_type': 'GUI',
                'message_source': 'Bot Internal',
                'message_type': 'error',
                'relevance': 'error',
                'is_noise': False,
                'is_channel_log': False,
                'formatted_message': f'[ERROR] Fehler beim Verarbeiten: {str(e)}',
                'raw_entry': log_entry
            }
    
    def determine_bot_type_extended(self, logger_name, message):
        """Erweiterte Bot-Typ-Bestimmung"""
        logger_lower = logger_name.lower()
        message_lower = message.lower()
        
        if ('main' in logger_lower or 'status' in logger_lower or 
            'main bot' in message_lower or 'statusbot' in logger_lower):
            return 'Main Bot'
        elif ('helper' in logger_lower or 'helper bot' in message_lower):
            return 'Helper Bot'
        elif ('gui' in logger_lower or 'tkinter' in logger_lower or 'customtkinter' in logger_lower):
            return 'GUI'
        elif ('api' in logger_lower or 'flask' in logger_lower or 'werkzeug' in logger_lower):
            return 'API'
        elif ('discord' in logger_lower or 'websocket' in logger_lower):
            return 'Discord'
        else:
            return 'System'
    
    def determine_message_source(self, logger_name, message):
        """Bestimmt die Quelle der Nachricht"""
        message_lower = message.lower()
        
        if any(term in message_lower for term in ['command', 'slash', '/', 'invoked']):
            return 'Commands'
        elif any(term in message_lower for term in ['channel', 'message received', 'sent message']):
            return 'Channel Messages'
        elif any(term in message_lower for term in ['api', 'request', 'response', 'http']):
            return 'API Calls'
        elif any(term in message_lower for term in ['connected', 'disconnected', 'ready', 'login']):
            return 'Discord Events'
        else:
            return 'Bot Internal'
    
    def determine_message_type(self, message):
        """Bestimmt den Typ der Nachricht"""
        message_lower = message.lower()
        
        if any(term in message_lower for term in ['command', 'slash', '/', 'invoked']):
            return 'command'
        elif any(term in message_lower for term in ['channel', 'message', 'sent', 'received']):
            return 'channel_message'
        elif any(term in message_lower for term in ['started', 'stopped', 'ready', 'connecting']):
            return 'bot_action'
        elif any(term in message_lower for term in ['error', 'exception', 'failed', 'traceback']):
            return 'error'
        elif any(term in message_lower for term in ['warning', 'warnung']):
            return 'warning'
        elif any(term in message_lower for term in ['status', 'online', 'offline']):
            return 'status'
        else:
            return 'general'
    
    def determine_relevance_extended(self, level, message, message_type):
        """Erweiterte Relevanz-Bestimmung"""
        if message_type == 'error':
            return 'error'
        elif message_type == 'command':
            return 'command'
        elif message_type == 'bot_action':
            return 'bot_action'
        elif message_type == 'channel_message':
            return 'channel'
        elif level in ['ERROR', 'CRITICAL']:
            return 'error'
        elif level == 'WARNING':
            return 'warning'
        elif message_type == 'status':
            return 'status'
        else:
            return 'general'
    
    def is_noise_message(self, message):
        """Prüft ob eine Nachricht als Noise eingestuft wird"""
        message_lower = message.lower()
        
        for pattern in self.noise_patterns:
            if re.search(pattern, message_lower):
                return True
        
        # Zusätzliche Noise-Patterns
        noise_terms = [
            'heartbeat', 'keepalive', 'ping', 'pong',
            'received message', 'sending message',
            'http request', 'http response',
            'websocket', 'connection established'
        ]
        
        return any(term in message_lower for term in noise_terms)
    
    def is_channel_log_message(self, message):
        """Prüft ob eine Nachricht aus einem Log-Channel stammt"""
        message_lower = message.lower()
        
        channel_indicators = [
            'channel message', 'received message', 'sent message',
            'message from', 'message to', 'channel log',
            'user message', 'guild message'
        ]
        
        return any(indicator in message_lower for indicator in channel_indicators)
    
    def format_message_extended(self, timestamp, level, logger_name, message, message_type):
        """Erweiterte Nachrichtenformatierung mit Typ-Indikatoren"""
        time_str = timestamp.strftime('%H:%M:%S')
        
        # Typ-Indikatoren
        type_indicators = {
            'command': '⚡',
            'channel_message': '💬',
            'bot_action': '🤖',
            'error': '❌',
            'warning': '⚠️',
            'status': '📊'
        }
        
        indicator = type_indicators.get(message_type, '📝')
        
        return f"[{time_str}] {indicator} {level:8} | {logger_name:20} | {message}"
    
    def apply_filters(self, *args):
        """Erweiterte Filter-Anwendung"""
        try:
            # Hole Filter-Werte
            level_filter = self.level_filter.get()
            bot_filter = self.bot_filter.get()
            source_filter = self.source_filter.get()
            relevance_filter = self.relevance_filter.get()
            channel_filter = self.channel_filter.get()
            search_text = self.search_entry.get().lower()
            filter_noise = self.noise_filter_var.get()
            live_only = self.live_filter_var.get()
            
            # Filtere Log-Einträge
            filtered = []
            
            for entry in self.log_entries:
                # Level-Filter
                if level_filter != "Alle":
                    if not self.matches_level_filter(entry['level'], level_filter):
                        continue
                
                # Bot-Filter
                if bot_filter != "Alle":
                    if entry['bot_type'] != bot_filter:
                        continue
                
                # Source-Filter (NEU)
                if source_filter != "Alle":
                    if entry['message_source'] != source_filter:
                        continue
                
                # Relevanz-Filter (erweitert)
                if relevance_filter != "Alle":
                    if not self.matches_relevance_filter_extended(entry['relevance'], relevance_filter):
                        continue
                
                # Channel-Filter (NEU)
                if not self.matches_channel_filter(entry, channel_filter):
                    continue
                
                # Noise-Filter (NEU)
                if filter_noise and entry['is_noise']:
                    continue
                
                # Live-Filter (NEU)
                if live_only:
                    time_diff = (datetime.now() - entry['timestamp']).total_seconds()
                    if time_diff > 300:  # Nur letzte 5 Minuten
                        continue
                
                # Such-Filter
                if search_text:
                    if not self.matches_search_filter(entry, search_text):
                        continue
                
                filtered.append(entry)
            
            # Aktualisiere gefilterte Einträge
            self.filtered_entries = filtered
            
            # Aktualisiere Display
            self.update_log_display()
            
            # Aktualisiere Filter-Status
            self.update_filter_status()
            
        except Exception as e:
            print(f"[ERROR] Filter Application Error: {e}")
    
    def matches_level_filter(self, entry_level, filter_level):
        """Prüft ob ein Log-Level dem Filter entspricht"""
        level_hierarchy = {
            'DEBUG': 0,
            'INFO': 1,
            'WARNING': 2,
            'ERROR': 3,
            'CRITICAL': 4
        }
        
        entry_level_num = level_hierarchy.get(entry_level, 0)
        filter_level_num = level_hierarchy.get(filter_level, 0)
        
        return entry_level_num >= filter_level_num
    
    def matches_relevance_filter_extended(self, entry_relevance, filter_relevance):
        """Erweiterte Relevanz-Filter-Prüfung"""
        relevance_mapping = {
            "Nur Bot-Aktionen": ['bot_action', 'command'],
            "Nur Fehler": ['error'],
            "Nur Status": ['status'],
            "Nur Commands": ['command'],
            "Nur Discord": ['channel', 'status']
        }
        
        allowed_relevance = relevance_mapping.get(filter_relevance, [])
        return entry_relevance in allowed_relevance
    
    def matches_channel_filter(self, entry, channel_filter):
        """Prüft Channel-Filter"""
        if channel_filter == "Alle":
            return True
        elif channel_filter == "Keine Channel-Logs":
            return not entry['is_channel_log']
        elif channel_filter == "Nur Channel-Logs":
            return entry['is_channel_log']
        elif channel_filter == "Nur System":
            return not entry['is_channel_log'] and entry['message_source'] == 'Bot Internal'
        elif channel_filter == "Nur Befehle":
            return entry['message_type'] == 'command'
        
        return True
    
    def matches_search_filter(self, entry, search_text):
        """Prüft ob ein Log-Eintrag dem Such-Filter entspricht"""
        searchable_text = (
            entry['message'].lower() + " " +
            entry['logger'].lower() + " " +
            entry['bot_type'].lower() + " " +
            entry['message_source'].lower() + " " +
            entry['message_type'].lower()
        )
        
        return search_text in searchable_text
    
    def update_filter_status(self):
        """Aktualisiert den Filter-Status"""
        active_filters = []
        
        if self.level_filter.get() != "Alle":
            active_filters.append(f"Level:{self.level_filter.get()}")
        
        if self.bot_filter.get() != "Alle":
            active_filters.append(f"Bot:{self.bot_filter.get()}")
        
        if self.source_filter.get() != "Alle":
            active_filters.append(f"Quelle:{self.source_filter.get()}")
        
        if self.channel_filter.get() != "Alle":
            active_filters.append(f"Channel:{self.channel_filter.get()}")
        
        if self.noise_filter_var.get():
            active_filters.append("Noise gefiltert")
        
        if self.live_filter_var.get():
            active_filters.append("Live-Modus")
        
        if self.search_entry.get():
            active_filters.append(f"Suche:'{self.search_entry.get()}'")
        
        status_text = "Filter: " + (", ".join(active_filters) if active_filters else "Standard")
        self.filter_status_label.configure(text=status_text[:80] + "..." if len(status_text) > 80 else status_text)
    
    def update_log_display(self):
        """Aktualisiert die Log-Anzeige"""
        try:
            # Lösche aktuellen Inhalt
            self.log_display.delete("1.0", "end")
            
            # Füge gefilterte Einträge hinzu
            for entry in self.filtered_entries[-1000:]:  # Zeige nur letzte 1000 Einträge
                self.insert_log_entry(entry)
            
            # Aktualisiere Info-Label
            total_count = len(self.log_entries)
            filtered_count = len(self.filtered_entries)
            self.info_label.configure(text=f"Log-Einträge: {total_count} | Gefiltert: {filtered_count}")
            
            # Auto-Scroll
            if self.auto_scroll:
                self.scroll_to_bottom()
                
        except Exception as e:
            print(f"[ERROR] Log Display Update Error: {e}")
    
    def insert_log_entry(self, entry):
        """Fügt einen Log-Eintrag in die Anzeige ein"""
        try:
            # Füge Nachricht hinzu
            start_pos = self.log_display.index("end-1c")
            self.log_display.insert("end", entry['formatted_message'] + "\n")
            end_pos = self.log_display.index("end-1c")
            
            # Wende Tags an (wenn möglich)
            try:
                # Level-Tag
                self.log_display._textbox.tag_add(entry['level'], start_pos, end_pos)
                
                # Bot-Tag
                bot_tag = entry['bot_type'].upper().replace(' ', '_')
                self.log_display._textbox.tag_add(bot_tag, start_pos, end_pos)
                
                # Message Source Tag
                source_tag = entry['message_source'].upper().replace(' ', '_')
                self.log_display._textbox.tag_add(source_tag, start_pos, end_pos)
                
                # Message Type Tag
                type_tag = entry['message_type'].upper().replace(' ', '_')
                self.log_display._textbox.tag_add(type_tag, start_pos, end_pos)

                # Relevance Tag
                relevance_tag = entry['relevance'].upper().replace(' ', '_')
                self.log_display._textbox.tag_add(relevance_tag, start_pos, end_pos)

                # Channel Log Tag
                if entry['is_channel_log']:
                    self.log_display._textbox.tag_add("CHANNEL_LOG", start_pos, end_pos)

                # Noise Tag
                if entry['is_noise']:
                    self.log_display._textbox.tag_add("NOISE", start_pos, end_pos)

                # Bot Action Tag
                if entry['message_type'] == 'bot_action':
                    self.log_display._textbox.tag_add("BOT_ACTION", start_pos, end_pos)

                # Command Tag
                if entry['message_type'] == 'command':
                    self.log_display._textbox.tag_add("COMMAND", start_pos, end_pos)

                # Channel Message Tag
                if entry['message_type'] == 'channel_message':
                    self.log_display._textbox.tag_add("CHANNEL_MSG", start_pos, end_pos)

            except Exception as tag_error:
                print(f"[DEBUG] Tag-Anwendung fehlgeschlagen: {tag_error}")
            
        except Exception as e:
            print(f"[ERROR] Log Entry Insert Error: {e}")
    
    def on_search_changed(self, event):
        """Wird aufgerufen wenn sich die Suche ändert"""
        # Verzögere die Suche um 500ms
        if hasattr(self, '_search_timer'):
            self.root.after_cancel(self._search_timer)
        
        self._search_timer = self.root.after(500, self.apply_filters)
    
    def clear_search(self):
        """Leert die Suche"""
        self.search_entry.delete(0, "end")
        self.apply_filters()
    
    def toggle_auto_scroll(self):
        """Schaltet Auto-Scroll ein/aus"""
        self.auto_scroll = self.auto_scroll_var.get()
        if self.auto_scroll:
            self.scroll_to_bottom()
    
    def scroll_to_bottom(self):
        """Scrollt zum Ende der Logs"""
        try:
            self.log_display.see("end")
        except Exception as e:
            print(f"[DEBUG] Scroll Error: {e}")
    
    def clear_logs(self):
        """Leert alle Log-Einträge"""
        self.log_entries.clear()
        self.filtered_entries.clear()
        self.update_log_display()
    
    def export_logs(self):
        """Exportiert Logs in eine Datei"""
        try:
            from tkinter import filedialog
            from datetime import datetime
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_filename = f"detektiv_pikachu_logs_{timestamp}.txt"
            
            filename = filedialog.asksaveasfilename(
                title="Logs exportieren",
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
                initialname=default_filename
            )
            
            if filename:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(f"Detektiv Pikachu Bot Logs - Export vom {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write("=" * 80 + "\n\n")
                    
                    for entry in self.filtered_entries:
                        f.write(entry['formatted_message'] + "\n")
                
                self.show_status_message(f"Logs exportiert: {filename.split('/')[-1]}", "success")
                
        except Exception as e:
            print(f"[ERROR] Log Export Error: {e}")
            self.show_status_message(f"Export fehlgeschlagen: {e}", "error")
    
    def refresh_logs(self):
        """Aktualisiert die Log-Anzeige"""
        self.apply_filters()
        self.show_status_message("Logs aktualisiert", "info")

    # Quick Filter Methods (NEU)
    def filter_bot_only(self):
        """Quick Filter: Nur Bot-Aktionen"""
        self.relevance_filter.set("Nur Bot-Aktionen")
        self.channel_filter.set("Keine Channel-Logs")
        self.noise_filter_var.set(True)
        self.apply_filters()
    
    def filter_errors_only(self):
        """Quick Filter: Nur Fehler"""
        self.level_filter.set("ERROR")
        self.relevance_filter.set("Nur Fehler")
        self.apply_filters()
    
    def filter_commands_only(self):
        """Quick Filter: Nur Commands"""
        self.relevance_filter.set("Nur Commands")
        self.source_filter.set("Commands")
        self.apply_filters()
    
    def filter_system_only(self):
        """Quick Filter: Nur System"""
        self.channel_filter.set("Nur System")
        self.noise_filter_var.set(True)
        self.apply_filters()
    
    def filter_show_all(self):
        """Quick Filter: Alle anzeigen"""
        self.level_filter.set("Alle")
        self.bot_filter.set("Alle")
        self.source_filter.set("Alle")
        self.relevance_filter.set("Alle")
        self.channel_filter.set("Alle")
        self.noise_filter_var.set(False)
        self.live_filter_var.set(False)
        self.search_entry.delete(0, "end")
        self.apply_filters()