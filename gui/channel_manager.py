#!/usr/bin/env python3
"""
Verbesserte Channel Management GUI Component
Fixes für bessere Datenverarbeitung und Fehlerbehandlung
"""

import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
import threading
import asyncio
import json
from pathlib import Path
from typing import Optional, Dict, Any
import re

from .base import BaseGUIComponent

class ChannelManager(BaseGUIComponent):
    """Verbesserte Channel-Management Komponente"""
    
    def __init__(self, parent, main_window):
        super().__init__(parent, main_window)
        self.channel_data_loaded = False
        self.channel_entries = []
        self.last_bot_status = None
        self.setup_channel_tabs()
    
    def setup_channel_tabs(self):
        """Erstellt alle Channel-Management Tabs"""
        # Notebook für Sub-Tabs
        self.channel_notebook = ctk.CTkTabview(self.parent)
        self.channel_notebook.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Channel Status Sub-Tab
        self.channel_notebook.add("📊 Status Übersicht")
        self.setup_channel_status_tab(self.channel_notebook.tab("📊 Status Übersicht"))
        
        # Channel Lock Sub-Tab
        self.channel_notebook.add("🔒 Lock Management")
        self.setup_channel_lock_tab(self.channel_notebook.tab("🔒 Lock Management"))
        
        # Channel Config Sub-Tab
        self.channel_notebook.add("⚙️ Konfiguration")
        self.setup_channel_config_tab(self.channel_notebook.tab("⚙️ Konfiguration"))
    
    def setup_channel_status_tab(self, parent):
        """Erstellt das Channel Status Sub-Tab"""
        # Header
        header_frame = ctk.CTkFrame(parent)
        header_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(header_frame, text="📊 Channel Status Übersicht", 
                     font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)
        
        # Bot Status Indicator
        self.bot_status_indicator = ctk.CTkLabel(header_frame, text="🔴 Bot Offline", text_color="red")
        self.bot_status_indicator.pack(side="right", padx=10)
        
        # Refresh Button
        refresh_btn = ctk.CTkButton(header_frame, text="🔄 Aktualisieren", 
                                   command=self.refresh_channel_data_safe, width=120)
        refresh_btn.pack(side="right", padx=10)
        
        # Scrollable Frame für Channel-Liste
        self.channel_list_frame = ctk.CTkScrollableFrame(parent, label_text="Konfigurierte Channels")
        self.channel_list_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Manual Status Control
        self._setup_manual_status_control(parent)
        
        # Automatisches Laden der Daten
        self.root.after(1000, self.initial_load_channel_data)
    
    def _setup_manual_status_control(self, parent):
        """Erstellt die manuelle Status-Kontrolle"""
        manual_control_frame = ctk.CTkFrame(parent)
        manual_control_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(manual_control_frame, text="📝 Manueller Status-Wechsel", 
                     font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(10, 5))
        
        control_inner_frame = ctk.CTkFrame(manual_control_frame)
        control_inner_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(control_inner_frame, text="Channel:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.selected_channel_var = ctk.StringVar()
        self.channel_dropdown = ctk.CTkOptionMenu(control_inner_frame, variable=self.selected_channel_var,
                                                 values=["Keine Channels geladen"])
        self.channel_dropdown.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        
        ctk.CTkLabel(control_inner_frame, text="Neuer Status:").grid(row=0, column=2, padx=5, pady=5, sticky="w")
        self.status_var = ctk.StringVar()
        self.status_dropdown = ctk.CTkOptionMenu(control_inner_frame, variable=self.status_var,
                                               values=["online", "offline", "problem", "maintenance"])
        self.status_dropdown.grid(row=0, column=3, padx=5, pady=5, sticky="ew")
        
        apply_status_btn = ctk.CTkButton(control_inner_frame, text="✅ Status setzen", 
                                        command=self.apply_manual_status_safe, width=120)
        apply_status_btn.grid(row=0, column=4, padx=10, pady=5)
        
        # Configure grid weights
        control_inner_frame.grid_columnconfigure(1, weight=1)
        control_inner_frame.grid_columnconfigure(3, weight=1)
    
    def setup_channel_lock_tab(self, parent):
        """Erstellt das Channel Lock Sub-Tab"""
        # Placeholder für Lock Management
        info_frame = ctk.CTkFrame(parent)
        info_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        ctk.CTkLabel(info_frame, text="🔒 Lock Management", 
                     font=ctk.CTkFont(size=16, weight="bold")).pack(pady=20)
        
        ctk.CTkLabel(info_frame, text="Lock Management Funktionen\nwerden hier implementiert...", 
                     font=ctk.CTkFont(size=12)).pack(pady=10)
    
    def setup_channel_config_tab(self, parent):
        """Erstellt das Channel Config Sub-Tab"""
        # Placeholder für Configuration
        config_frame = ctk.CTkFrame(parent)
        config_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        ctk.CTkLabel(config_frame, text="⚙️ Konfiguration", 
                     font=ctk.CTkFont(size=16, weight="bold")).pack(pady=20)
        
        ctk.CTkLabel(config_frame, text="Konfigurationsmöglichkeiten\nwerden hier implementiert...", 
                     font=ctk.CTkFont(size=12)).pack(pady=10)
    
    def initial_load_channel_data(self):
        """Erste Ladung der Channel-Daten"""
        try:
            if not self.channel_data_loaded:
                self.refresh_channel_data_safe()
        except Exception as e:
            print(f"[ERROR] Initial Channel Data Load Error: {e}")
    
    def refresh_channel_data_safe(self):
        """Thread-sichere Channel-Daten-Aktualisierung"""
        try:
            print("[DEBUG] Starte Channel-Daten-Refresh...")
            
            # Lade Channel-Paare
            self.load_channel_pairs_safe()
            
            # Aktualisiere Dropdowns
            self.update_channel_dropdowns_safe()
            
            self.channel_data_loaded = True
            self.show_status_message("Channel-Daten aktualisiert", "success")
            
        except Exception as e:
            print(f"[ERROR] Fehler beim Laden der Channel-Daten: {e}")
            self.show_status_message(f"Fehler beim Laden der Channel-Daten: {e}", "error")
    
    def load_channel_pairs_safe(self):
        """Sichere Ladung der Channel-Paare mit verbesserter Fehlerbehandlung"""
        try:
            pairs_file = Path('data/json/guild_channels.json')
            
            if not pairs_file.exists():
                print("[DEBUG] Channel-Paare-Datei nicht gefunden, erstelle leere Anzeige")
                self.clear_channel_list()
                return
            
            # Datei lesen
            with open(pairs_file, 'r', encoding='utf-8') as f:
                guild_channels = json.load(f)
            
            # Lösche alte Einträge
            self.clear_channel_list()
            
            # Zeige Channel-Paare an
            entries_created = 0
            for guild_id, channels in guild_channels.items():
                for log_channel_id, update_data in channels.items():
                    try:
                        # Unterstütze sowohl alte (str) als auch neue (list) Struktur
                        if isinstance(update_data, str):
                            # Alte Struktur: Ein Update-Channel
                            self.create_channel_status_entry_safe(guild_id, log_channel_id, [update_data])
                        elif isinstance(update_data, list):
                            # Neue Struktur: Mehrere Update-Channels
                            self.create_channel_status_entry_safe(guild_id, log_channel_id, update_data)
                        else:
                            print(f"[WARNING] Ungültiger Update-Data-Typ für {log_channel_id}: {type(update_data)}")
                            continue
                        
                        entries_created += 1
                        
                    except Exception as e:
                        print(f"[ERROR] Fehler beim Erstellen des Channel-Eintrags für {log_channel_id}: {e}")
                        continue
            
            print(f"[DEBUG] {entries_created} Channel-Einträge erstellt")
            
        except json.JSONDecodeError as e:
            print(f"[ERROR] JSON-Dekodier-Fehler: {e}")
            self.show_status_message("Fehler beim Lesen der Channel-Konfiguration", "error")
        except Exception as e:
            print(f"[ERROR] Fehler beim Laden der Channel-Paare: {e}")
            self.show_status_message(f"Fehler beim Laden der Channel-Paare: {e}", "error")
    
    def clear_channel_list(self):
        """Leert die Channel-Liste"""
        try:
            for widget in self.channel_list_frame.winfo_children():
                widget.destroy()
            self.channel_entries.clear()
        except Exception as e:
            print(f"[ERROR] Fehler beim Leeren der Channel-Liste: {e}")
    
    def create_channel_status_entry_safe(self, guild_id, log_channel_id, update_channel_ids):
        """Sichere Erstellung eines Channel-Status-Eintrags"""
        try:
            entry_frame = ctk.CTkFrame(self.channel_list_frame)
            entry_frame.pack(fill="x", padx=5, pady=5)
            
            # Channel Info mit Namen
            guild_name = self.resolve_guild_name_safe(guild_id)
            log_channel_name = self.resolve_channel_name_safe(log_channel_id)
            
            # Update-Channels formatieren
            if len(update_channel_ids) == 1:
                update_info = f"Update: {self.resolve_channel_name_safe(update_channel_ids[0])}"
            else:
                update_names = [self.resolve_channel_name_safe(uid) for uid in update_channel_ids[:2]]
                update_info = f"Updates ({len(update_channel_ids)}): {', '.join(update_names)}"
                if len(update_channel_ids) > 2:
                    update_info += f" +{len(update_channel_ids) - 2} weitere"
            
            info_text = f"{guild_name}\nLog: {log_channel_name}\n{update_info}"
            info_label = ctk.CTkLabel(entry_frame, text=info_text, font=ctk.CTkFont(family="Consolas", size=10), 
                                      justify="left")
            info_label.pack(side="left", padx=10, pady=5)
            
            # Quick Actions für alle Update-Channels
            self._create_quick_action_buttons_safe(entry_frame, log_channel_id, update_channel_ids)
            
            # Eintrag zur Liste hinzufügen
            self.channel_entries.append({
                'frame': entry_frame,
                'guild_id': guild_id,
                'log_channel_id': log_channel_id,
                'update_channel_ids': update_channel_ids
            })
            
        except Exception as e:
            print(f"[ERROR] Fehler beim Erstellen des Channel-Status-Eintrags: {e}")
    
    def _create_quick_action_buttons_safe(self, parent, log_channel_id, update_channel_ids):
        """Sichere Erstellung der Quick-Action-Buttons"""
        try:
            actions_frame = ctk.CTkFrame(parent)
            actions_frame.pack(side="right", padx=5)
            
            buttons = [
                ("🟢 Online", "online", "green"),
                ("🔴 Offline", "offline", "red"),
                ("⚠️ Problem", "problem", "orange"),
                ("🔧 Wartung", "maintenance", "purple")
            ]
            
            for text, status, color in buttons:
                btn = ctk.CTkButton(actions_frame, text=text, width=80, height=30,
                                  fg_color=color if color != "green" else None,
                                  command=lambda s=status, lcid=log_channel_id, ucids=update_channel_ids: 
                                          self.quick_status_change_multi_safe(lcid, ucids, s))
                btn.pack(side="left", padx=2, pady=2)
                
        except Exception as e:
            print(f"[ERROR] Fehler beim Erstellen der Quick-Action-Buttons: {e}")
    
    def quick_status_change_multi_safe(self, log_channel_id, update_channel_ids, status):
        """Sichere Änderung des Status für mehrere Update-Channels"""
        try:
            if not self.main_bot:
                messagebox.showwarning("Warnung", "Main Bot ist nicht verbunden")
                return
            
            if not hasattr(self.main_bot, 'status_manager'):
                messagebox.showwarning("Warnung", "Status Manager ist nicht verfügbar")
                return
                
            # Finde Guild-ID für Log-Channel
            guild_id = self._find_guild_for_log_channel_safe(log_channel_id)
            
            if not guild_id:
                messagebox.showerror("Fehler", f"Keine Guild für Log-Channel {log_channel_id} gefunden")
                return
            
            # Führe Status-Update aus
            self._execute_status_update_safe(log_channel_id, status, update_channel_ids[0])
            
            # Logging
            self._log_status_change_multi_safe(log_channel_id, update_channel_ids, status, guild_id)
            
            # Erfolgs-Nachricht
            channel_count = len(update_channel_ids)
            if channel_count == 1:
                messagebox.showinfo("Erfolg", f"Status für Log-Channel {log_channel_id} auf '{status}' gesetzt!")
            else:
                messagebox.showinfo("Erfolg", f"Status für Log-Channel {log_channel_id} auf '{status}' gesetzt!\n{channel_count} Update-Channels wurden aktualisiert.")
                
        except Exception as e:
            print(f"[ERROR] Fehler beim Status-Wechsel: {e}")
            messagebox.showerror("Fehler", f"Fehler beim Status-Wechsel: {e}")
    
    def _execute_status_update_safe(self, log_channel_id, status, update_channel_id):
        """Sichere Ausführung des Status-Updates"""
        def update_status():
            try:
                from bot_status import BotStatus
                bot_status = BotStatus.from_str(status)
                
                if hasattr(self.main_bot, 'loop') and self.main_bot.loop:
                    future = asyncio.run_coroutine_threadsafe(
                        self.main_bot.status_manager.update_status(
                            log_channel_id, 
                            bot_status, 
                            f"Manueller Status-Wechsel über GUI: {status}"
                        ),
                        self.main_bot.loop
                    )
                    future.result(timeout=30)
                
                # GUI-Update
                self.main_window.root.after(1000, self.refresh_channel_data_safe)
                
            except Exception as e:
                print(f"[ERROR] Status-Update-Fehler: {e}")
                # Fehler-Nachricht in GUI-Thread
                self.main_window.root.after(0, lambda: messagebox.showerror("Status-Update Fehler", f"Fehler beim Status-Update: {e}"))
        
        threading.Thread(target=update_status, daemon=True).start()
    
    def resolve_guild_name_safe(self, guild_id):
        """Sichere Auflösung eines Guild-Namens"""
        try:
            if self.main_bot and hasattr(self.main_bot, 'guilds'):
                guild = self.main_bot.get_guild(int(guild_id))
                if guild:
                    return f"{guild.name} ({guild_id})"
            return f"Guild {guild_id}"
        except Exception as e:
            print(f"[DEBUG] Guild Name Resolution Error: {e}")
            return f"Guild {guild_id}"
    
    def resolve_channel_name_safe(self, channel_id):
        """Sichere Auflösung eines Channel-Namens"""
        try:
            if self.main_bot and hasattr(self.main_bot, 'guilds'):
                for guild in self.main_bot.guilds:
                    channel = guild.get_channel(int(channel_id))
                    if channel:
                        return f"#{channel.name} ({channel_id})"
            return f"Channel {channel_id}"
        except Exception as e:
            print(f"[DEBUG] Channel Name Resolution Error: {e}")
            return f"Channel {channel_id}"
    
    def _find_guild_for_log_channel_safe(self, log_channel_id):
        """Sichere Suche nach Guild-ID für Log-Channel"""
        try:
            if hasattr(self.main_bot, 'guild_channels'):
                for guild_id, channels in self.main_bot.guild_channels.items():
                    if str(log_channel_id) in channels:
                        return guild_id
            return None
        except Exception as e:
            print(f"[DEBUG] Guild Search Error: {e}")
            return None
    
    def _log_status_change_multi_safe(self, log_channel_id, update_channel_ids, status, guild_id):
        """Sichere Protokollierung des Status-Wechsels"""
        try:
            log_channel_name = self.resolve_channel_name_safe(log_channel_id)
            
            if len(update_channel_ids) == 1:
                update_channel_name = self.resolve_channel_name_safe(update_channel_ids[0])
                message = f"Status manuell auf '{status}' gesetzt für {update_channel_name}"
            else:
                message = f"Status manuell auf '{status}' gesetzt für Log-Channel {log_channel_name} ({len(update_channel_ids)} Update-Channels)"
            
            self.main_window.log_gui_action_threaded(
                "manual_status_change",
                message,
                guild_id,
                log_channel_id
            )
        except Exception as e:
            print(f"[ERROR] Logging Error: {e}")
    
    def update_channel_dropdowns_safe(self):
        """Sichere Aktualisierung der Channel-Dropdown-Menüs"""
        try:
            pairs_file = Path('data/json/guild_channels.json')
            channels = []
            
            if pairs_file.exists():
                with open(pairs_file, 'r', encoding='utf-8') as f:
                    guild_channels = json.load(f)
                
                for guild_id, guild_channels_dict in guild_channels.items():
                    for log_channel_id, update_data in guild_channels_dict.items():
                        log_name = self.resolve_channel_name_safe(log_channel_id)
                        
                        # Unterstütze sowohl alte (str) als auch neue (list) Struktur
                        if isinstance(update_data, str):
                            # Alte Struktur: Ein Update-Channel
                            update_name = self.resolve_channel_name_safe(update_data)
                            channels.append(f"{log_name} → {update_name}")
                        elif isinstance(update_data, list):
                            # Neue Struktur: Mehrere Update-Channels
                            if len(update_data) == 1:
                                update_name = self.resolve_channel_name_safe(update_data[0])
                                channels.append(f"{log_name} → {update_name}")
                            else:
                                channels.append(f"{log_name} → {len(update_data)} Update-Channels")
            
            if channels:
                self.channel_dropdown.configure(values=channels)
                print(f"[DEBUG] {len(channels)} Channels für Dropdown geladen")
            else:
                self.channel_dropdown.configure(values=["Keine Channels konfiguriert"])
                print("[DEBUG] Keine Channels für Dropdown gefunden")
                
        except Exception as e:
            print(f"[ERROR] Fehler beim Aktualisieren der Dropdowns: {e}")
            self.channel_dropdown.configure(values=["Fehler beim Laden"])
    
    def apply_manual_status_safe(self):
        """Sichere Anwendung des manuellen Status"""
        try:
            selected_channel = self.selected_channel_var.get()
            new_status = self.status_var.get()
            
            if not selected_channel or selected_channel == "Keine Channels geladen":
                messagebox.showwarning("Warnung", "Bitte wählen Sie einen Channel aus")
                return
            
            if not new_status:
                messagebox.showwarning("Warnung", "Bitte wählen Sie einen Status aus")
                return
            
            # Extrahiere Channel-ID aus dem ausgewählten Text
            match = re.search(r'\((\d+)\)', selected_channel)
            if match:
                channel_id = match.group(1)
                
                # Finde entsprechenden Log-Channel und Update-Channels
                for entry in self.channel_entries:
                    if (str(entry['log_channel_id']) == channel_id or 
                        channel_id in [str(uid) for uid in entry['update_channel_ids']]):
                        
                        self.quick_status_change_multi_safe(
                            entry['log_channel_id'], 
                            entry['update_channel_ids'], 
                            new_status
                        )
                        return
                
                # Fallback für einzelnen Channel
                messagebox.showinfo("Info", f"Status-Wechsel für Channel {channel_id} auf '{new_status}' eingeleitet")
            else:
                messagebox.showwarning("Warnung", "Konnte Channel-ID nicht extrahieren")
                
        except Exception as e:
            print(f"[ERROR] Manual Status Apply Error: {e}")
            messagebox.showerror("Fehler", f"Fehler beim manuellen Status-Wechsel: {e}")
    
    def update_bot_status(self):
        """Aktualisiert den Bot-Status-Indikator"""
        try:
            # Hole aktuellen Bot-Status
            current_status = self.main_window.status_manager.get_main_bot_status()
            
            # Nur aktualisieren wenn sich etwas geändert hat
            if current_status != self.last_bot_status:
                self.last_bot_status = current_status.copy()
                
                if current_status['online']:
                    self.bot_status_indicator.configure(text="🟢 Bot Online", text_color="green")
                else:
                    self.bot_status_indicator.configure(text="🔴 Bot Offline", text_color="red")
                    
        except Exception as e:
            print(f"[ERROR] Bot Status Update Error: {e}")
            self.bot_status_indicator.configure(text="⚠️ Bot Status Fehler", text_color="orange")