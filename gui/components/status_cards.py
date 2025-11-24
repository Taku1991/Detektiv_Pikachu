#!/usr/bin/env python3
"""
Status Cards Components
Wiederverwendbare Status-Karten für Bot-Anzeigen
"""

import customtkinter as ctk
from typing import Optional, Callable

class StatusCard:
    """Wiederverwendbare Status-Karte für Bot-Anzeigen"""
    
    def __init__(self, parent, title: str, icon: str = "🤖"):
        self.parent = parent
        self.title = title
        self.icon = icon
        
        self.frame = ctk.CTkFrame(parent)
        self.setup_card()
        
    def setup_card(self):
        """Erstellt die Status-Karte"""
        # Titel mit Icon
        title_label = ctk.CTkLabel(
            self.frame, 
            text=f"{self.icon} {self.title}", 
            font=ctk.CTkFont(size=16, weight="bold")
        )
        title_label.pack(pady=(10, 5))
        
        # Status Label
        self.status_label = ctk.CTkLabel(
            self.frame, 
            text="🔴 Offline", 
            text_color="red"
        )
        self.status_label.pack()
        
        # Info Label
        self.info_label = ctk.CTkLabel(
            self.frame, 
            text="Server: 0 | Nutzer: 0"
        )
        self.info_label.pack(pady=(0, 10))
        
    def update_status(self, online: bool, guild_count: int = 0, user_count: int = 0, latency: float = 0.0):
        """Aktualisiert den Status der Karte"""
        if online:
            self.status_label.configure(text="🟢 Online", text_color="green")
            latency_ms = round(latency * 1000) if latency > 0 else 0
            self.info_label.configure(text=f"Server: {guild_count} | Nutzer: {user_count} | {latency_ms}ms")
        else:
            self.status_label.configure(text="🔴 Offline", text_color="red")
            self.info_label.configure(text="Server: 0 | Nutzer: 0")
    
    def pack(self, **kwargs):
        """Packt die Karte"""
        self.frame.pack(**kwargs)
    
    def grid(self, **kwargs):
        """Griddet die Karte"""
        self.frame.grid(**kwargs)

class BotControlCard:
    """Erweiterte Status-Karte mit Kontroll-Buttons"""
    
    def __init__(self, parent, title: str, icon: str = "🤖", 
                 start_callback: Optional[Callable] = None,
                 stop_callback: Optional[Callable] = None,
                 restart_callback: Optional[Callable] = None):
        self.parent = parent
        self.title = title
        self.icon = icon
        self.start_callback = start_callback
        self.stop_callback = stop_callback
        self.restart_callback = restart_callback
        
        self.frame = ctk.CTkFrame(parent)
        self.setup_card()
        
    def setup_card(self):
        """Erstellt die erweiterte Status-Karte"""
        # Status-Bereich
        status_frame = ctk.CTkFrame(self.frame)
        status_frame.pack(fill="x", padx=10, pady=10)
        
        # Titel
        title_label = ctk.CTkLabel(
            status_frame, 
            text=f"{self.icon} {self.title}", 
            font=ctk.CTkFont(size=16, weight="bold")
        )
        title_label.pack(pady=(10, 5))
        
        # Status Labels
        self.status_label = ctk.CTkLabel(status_frame, text="🔴 Offline", text_color="red")
        self.status_label.pack()
        
        self.latency_label = ctk.CTkLabel(status_frame, text="Latenz: 0ms")
        self.latency_label.pack()
        
        self.guilds_label = ctk.CTkLabel(status_frame, text="Server: 0")
        self.guilds_label.pack()
        
        self.users_label = ctk.CTkLabel(status_frame, text="Nutzer: 0")
        self.users_label.pack(pady=(0, 10))
        
        # Kontroll-Buttons
        self.setup_control_buttons()
        
    def setup_control_buttons(self):
        """Erstellt die Kontroll-Buttons"""
        control_frame = ctk.CTkFrame(self.frame)
        control_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        buttons_frame = ctk.CTkFrame(control_frame)
        buttons_frame.pack(pady=10)
        
        # Start Button
        self.start_btn = ctk.CTkButton(
            buttons_frame, 
            text="▶️ Starten", 
            command=self.start_callback,
            width=100
        )
        self.start_btn.pack(side="left", padx=5)
        
        # Stop Button
        self.stop_btn = ctk.CTkButton(
            buttons_frame, 
            text="⏹️ Stoppen", 
            command=self.stop_callback,
            width=100, 
            fg_color="red"
        )
        self.stop_btn.pack(side="left", padx=5)
        
        # Restart Button
        self.restart_btn = ctk.CTkButton(
            buttons_frame, 
            text="🔄 Neustart", 
            command=self.restart_callback,
            width=100, 
            fg_color="orange"
        )
        self.restart_btn.pack(side="left", padx=5)
        
    def update_status(self, online: bool, guild_count: int = 0, user_count: int = 0, latency: float = 0.0):
        """Aktualisiert den Status der Karte"""
        if online:
            self.status_label.configure(text="🟢 Online", text_color="green")
            latency_ms = round(latency * 1000) if latency > 0 else 0
            self.latency_label.configure(text=f"Latenz: {latency_ms}ms")
            self.guilds_label.configure(text=f"Server: {guild_count}")
            self.users_label.configure(text=f"Nutzer: {user_count}")
        else:
            self.status_label.configure(text="🔴 Offline", text_color="red")
            self.latency_label.configure(text="Latenz: 0ms")
            self.guilds_label.configure(text="Server: 0")
            self.users_label.configure(text="Nutzer: 0")
    
    def pack(self, **kwargs):
        """Packt die Karte"""
        self.frame.pack(**kwargs)
    
    def grid(self, **kwargs):
        """Griddet die Karte"""
        self.frame.grid(**kwargs) 