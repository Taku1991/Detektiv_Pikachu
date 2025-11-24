#!/usr/bin/env python3
"""
Verbesserte Bot Control Component
Fixes für Status-Updates und Threading
"""

import customtkinter as ctk
import threading
import time
import asyncio
from tkinter import messagebox
from .base import BaseGUIComponent

class BotControl(BaseGUIComponent):
    """Verbesserte Bot-Steuerungs-Komponente"""
    
    def __init__(self, parent, main_window):
        super().__init__(parent, main_window)
        self.last_main_status = {}
        self.last_helper_status = {}
        self.last_balancer_status = ""
        self.setup_bot_control()
        
    def setup_bot_control(self):
        """Erstellt die Bot-Steuerung"""
        # Main Bot Section
        self.setup_main_bot_section()
        
        # Helper Bot Section  
        self.setup_helper_bot_section()
        
        # Token Balancer Section
        self.setup_token_balancer_section()
        
    def setup_main_bot_section(self):
        """Erstellt die Main Bot Sektion"""
        # Status Frame
        main_frame = ctk.CTkFrame(self.parent)
        main_frame.pack(fill="x", padx=10, pady=10)
        
        # Titel
        ctk.CTkLabel(main_frame, text="🤖 Main Bot Kontrolle", 
                     font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(10, 5))
        
        # Status Display
        status_frame = ctk.CTkFrame(main_frame)
        status_frame.pack(fill="x", padx=10, pady=10)
        
        self.main_status_label = ctk.CTkLabel(status_frame, text="🔴 Offline", text_color="red")
        self.main_status_label.pack()
        
        self.main_latency_label = ctk.CTkLabel(status_frame, text="Latenz: 0ms")
        self.main_latency_label.pack()
        
        self.main_guilds_label = ctk.CTkLabel(status_frame, text="Server: 0")
        self.main_guilds_label.pack()
        
        self.main_users_label = ctk.CTkLabel(status_frame, text="Nutzer: 0")
        self.main_users_label.pack(pady=(0, 10))
        
        # Control Buttons
        buttons_frame = ctk.CTkFrame(main_frame)
        buttons_frame.pack(pady=10)
        
        ctk.CTkButton(buttons_frame, text="▶️ Starten", command=self.start_main_bot, width=100).pack(side="left", padx=5)
        ctk.CTkButton(buttons_frame, text="⏹️ Stoppen", command=self.stop_main_bot, width=100, fg_color="red").pack(side="left", padx=5)
        ctk.CTkButton(buttons_frame, text="🔄 Neustart", command=self.restart_main_bot, width=100, fg_color="orange").pack(side="left", padx=5)
        
    def setup_helper_bot_section(self):
        """Erstellt die Helper Bot Sektion"""
        # Status Frame
        helper_frame = ctk.CTkFrame(self.parent)
        helper_frame.pack(fill="x", padx=10, pady=10)
        
        # Titel
        ctk.CTkLabel(helper_frame, text="🔧 Helper Bot Kontrolle", 
                     font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(10, 5))
        
        # Status Display
        status_frame = ctk.CTkFrame(helper_frame)
        status_frame.pack(fill="x", padx=10, pady=10)
        
        self.helper_status_label = ctk.CTkLabel(status_frame, text="🔴 Offline", text_color="red")
        self.helper_status_label.pack()
        
        self.helper_latency_label = ctk.CTkLabel(status_frame, text="Latenz: 0ms")
        self.helper_latency_label.pack()
        
        self.helper_guilds_label = ctk.CTkLabel(status_frame, text="Server: 0")
        self.helper_guilds_label.pack()
        
        self.helper_users_label = ctk.CTkLabel(status_frame, text="Nutzer: 0")
        self.helper_users_label.pack(pady=(0, 10))
        
        # Control Buttons
        buttons_frame = ctk.CTkFrame(helper_frame)
        buttons_frame.pack(pady=10)
        
        ctk.CTkButton(buttons_frame, text="▶️ Starten", command=self.start_helper_bot, width=100).pack(side="left", padx=5)
        ctk.CTkButton(buttons_frame, text="⏹️ Stoppen", command=self.stop_helper_bot, width=100, fg_color="red").pack(side="left", padx=5)
        ctk.CTkButton(buttons_frame, text="🔄 Neustart", command=self.restart_helper_bot, width=100, fg_color="orange").pack(side="left", padx=5)
        
    def setup_token_balancer_section(self):
        """Erstellt die Token Balancer Sektion"""
        balancer_frame = ctk.CTkFrame(self.parent)
        balancer_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(balancer_frame, text="⚖️ Token Balancer Kontrolle", 
                     font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(10, 5))
        
        # Status Display
        self.balancer_status_display = ctk.CTkTextbox(balancer_frame, height=100)
        self.balancer_status_display.pack(fill="x", padx=10, pady=10)
        
    def update_status(self):
        """Verbesserte Status-Aktualisierung mit Ängerungs-Erkennung"""
        try:
            self.update_main_bot_status()
            self.update_helper_bot_status()
            self.update_balancer_status()
        except Exception as e:
            print(f"[ERROR] Bot Control Status Update Error: {e}")
        
    def update_main_bot_status(self):
        """Verbesserte Main Bot Status-Aktualisierung"""
        try:
            # Thread-sichere Status-Abfrage
            status = self.main_window.status_manager.get_main_bot_status()
            
            # Nur aktualisieren wenn sich etwas geändert hat
            if status != self.last_main_status:
                self.last_main_status = status.copy()
                
                if status['online']:
                    self.main_status_label.configure(text="🟢 Online", text_color="green")
                    latency_ms = round(status['latency'] * 1000) if status['latency'] > 0 else 0
                    self.main_latency_label.configure(text=f"Latenz: {latency_ms}ms")
                    self.main_guilds_label.configure(text=f"Server: {status['guilds']}")
                    self.main_users_label.configure(text=f"Nutzer: {status['users']}")
                else:
                    self.main_status_label.configure(text="🔴 Offline", text_color="red")
                    self.main_latency_label.configure(text="Latenz: 0ms")
                    self.main_guilds_label.configure(text="Server: 0")
                    self.main_users_label.configure(text="Nutzer: 0")
                    
        except Exception as e:
            print(f"[ERROR] Main Bot Status Update Error: {e}")
            
    def update_helper_bot_status(self):
        """Verbesserte Helper Bot Status-Aktualisierung"""
        try:
            # Thread-sichere Status-Abfrage
            status = self.main_window.status_manager.get_helper_bot_status()
            
            # Nur aktualisieren wenn sich etwas geändert hat
            if status != self.last_helper_status:
                self.last_helper_status = status.copy()
                
                if status['online']:
                    self.helper_status_label.configure(text="🟢 Online", text_color="green")
                    latency_ms = round(status['latency'] * 1000) if status['latency'] > 0 else 0
                    self.helper_latency_label.configure(text=f"Latenz: {latency_ms}ms")
                    self.helper_guilds_label.configure(text=f"Server: {status['guilds']}")
                    self.helper_users_label.configure(text=f"Nutzer: {status['users']}")
                else:
                    self.helper_status_label.configure(text="🔴 Offline", text_color="red")
                    self.helper_latency_label.configure(text="Latenz: 0ms")
                    self.helper_guilds_label.configure(text="Server: 0")
                    self.helper_users_label.configure(text="Nutzer: 0")
                    
        except Exception as e:
            print(f"[ERROR] Helper Bot Status Update Error: {e}")
            
    def update_balancer_status(self):
        """Verbesserte Token Balancer Status-Aktualisierung"""
        try:
            if self.main_window.token_balancer:
                try:
                    # Sichere Abfrage des Balancer-Status
                    status_text = "Balancer Status nicht verfügbar"
                    
                    if hasattr(self.main_window.token_balancer, 'get_status_text'):
                        status_text = self.main_window.token_balancer.get_status_text()
                    else:
                        # Fallback-Status-Text erstellen
                        is_primary = getattr(self.main_window.token_balancer, 'is_using_primary', lambda: True)()
                        retry_count = getattr(self.main_window.token_balancer, 'retry_count', 0)
                        max_retries = getattr(self.main_window.token_balancer, 'max_retries', 3)
                        
                        primary_text = "Primär" if is_primary else "Sekundär"
                        status_text = f"Aktueller Status: {primary_text} Bot aktiv\nRetry-Zähler: {retry_count}/{max_retries}"
                    
                    # Nur aktualisieren wenn sich etwas geändert hat
                    if status_text != self.last_balancer_status:
                        self.last_balancer_status = status_text
                        
                        self.balancer_status_display.delete("1.0", "end")
                        self.balancer_status_display.insert("1.0", status_text)
                        
                except Exception as e:
                    print(f"[DEBUG] Balancer Status Detail Error: {e}")
                    error_text = f"Balancer-Fehler: {str(e)[:100]}"
                    
                    if error_text != self.last_balancer_status:
                        self.last_balancer_status = error_text
                        self.balancer_status_display.delete("1.0", "end")
                        self.balancer_status_display.insert("1.0", error_text)
            else:
                no_balancer_text = "Token Balancer nicht initialisiert"
                if no_balancer_text != self.last_balancer_status:
                    self.last_balancer_status = no_balancer_text
                    self.balancer_status_display.delete("1.0", "end")
                    self.balancer_status_display.insert("1.0", no_balancer_text)
                    
        except Exception as e:
            print(f"[ERROR] Balancer Status Update Error: {e}")
    
    # Bot Control Methods (Delegiere an MainWindow)
    def start_main_bot(self):
        """Startet den Main Bot"""
        try:
            self.main_window.start_main_bot()
        except Exception as e:
            print(f"[ERROR] Start Main Bot Error: {e}")
            messagebox.showerror("Fehler", f"Fehler beim Starten des Main Bots: {e}")
    
    def stop_main_bot(self):
        """Stoppt den Main Bot"""
        try:
            self.main_window.stop_main_bot()
        except Exception as e:
            print(f"[ERROR] Stop Main Bot Error: {e}")
            messagebox.showerror("Fehler", f"Fehler beim Stoppen des Main Bots: {e}")
    
    def restart_main_bot(self):
        """Startet den Main Bot neu"""
        try:
            self.main_window.restart_main_bot()
        except Exception as e:
            print(f"[ERROR] Restart Main Bot Error: {e}")
            messagebox.showerror("Fehler", f"Fehler beim Neustart des Main Bots: {e}")
    
    def start_helper_bot(self):
        """Startet den Helper Bot"""
        try:
            self.main_window.start_helper_bot()
        except Exception as e:
            print(f"[ERROR] Start Helper Bot Error: {e}")
            messagebox.showerror("Fehler", f"Fehler beim Starten des Helper Bots: {e}")
    
    def stop_helper_bot(self):
        """Stoppt den Helper Bot"""
        try:
            self.main_window.stop_helper_bot()
        except Exception as e:
            print(f"[ERROR] Stop Helper Bot Error: {e}")
            messagebox.showerror("Fehler", f"Fehler beim Stoppen des Helper Bots: {e}")
    
    def restart_helper_bot(self):
        """Startet den Helper Bot neu"""
        try:
            self.main_window.restart_helper_bot()
        except Exception as e:
            print(f"[ERROR] Restart Helper Bot Error: {e}")
            messagebox.showerror("Fehler", f"Fehler beim Neustart des Helper Bots: {e}")