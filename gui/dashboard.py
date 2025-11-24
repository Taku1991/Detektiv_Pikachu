#!/usr/bin/env python3
"""
Verbesserte Dashboard Component
Fixes für Status-Anzeige und Updates
"""

import customtkinter as ctk
from .base import BaseGUIComponent

class Dashboard(BaseGUIComponent):
    """Verbesserte Dashboard mit Status-Übersicht"""
    
    def __init__(self, parent, main_window):
        super().__init__(parent, main_window)
        self.last_main_status = {}
        self.last_helper_status = {}
        self.last_balancer_status = {}
        self.setup_dashboard()
        
    def setup_dashboard(self):
        """Erstellt das Dashboard"""
        # Status Cards Frame
        self.status_cards_frame = ctk.CTkFrame(self.parent)
        self.status_cards_frame.pack(fill="x", padx=10, pady=10)
        
        # Main Bot Status Card
        self.main_bot_frame = ctk.CTkFrame(self.status_cards_frame)
        self.main_bot_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))
        
        ctk.CTkLabel(self.main_bot_frame, text="🤖 Main Bot", 
                     font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(10, 5))
        self.main_bot_status_label = ctk.CTkLabel(self.main_bot_frame, text="🔴 Offline", text_color="red")
        self.main_bot_status_label.pack()
        self.main_bot_info_label = ctk.CTkLabel(self.main_bot_frame, text="Server: 0 | Nutzer: 0")
        self.main_bot_info_label.pack(pady=(0, 10))
        
        # Helper Bot Status Card  
        self.helper_bot_frame = ctk.CTkFrame(self.status_cards_frame)
        self.helper_bot_frame.pack(side="right", fill="both", expand=True, padx=(5, 0))
        
        ctk.CTkLabel(self.helper_bot_frame, text="🔧 Helper Bot", 
                     font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(10, 5))
        self.helper_bot_status_label = ctk.CTkLabel(self.helper_bot_frame, text="🔴 Offline", text_color="red")
        self.helper_bot_status_label.pack()
        self.helper_bot_info_label = ctk.CTkLabel(self.helper_bot_frame, text="Server: 0 | Nutzer: 0")
        self.helper_bot_info_label.pack(pady=(0, 10))
        
        # Control Buttons
        self.setup_control_buttons()
        
        # Token Balancer Status
        self.setup_balancer_status()
        
        # API Server Status
        self.setup_api_status()
        
    def setup_control_buttons(self):
        """Erstellt die zentralen Kontroll-Buttons"""
        control_frame = ctk.CTkFrame(self.parent)
        control_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(control_frame, text="🎮 Bot-Kontrolle", 
                     font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(10, 5))
        
        buttons_frame = ctk.CTkFrame(control_frame)
        buttons_frame.pack(pady=10)
        
        # Start All Button
        self.start_all_btn = ctk.CTkButton(
            buttons_frame, 
            text="🚀 Alle Bots starten", 
            command=self.main_window.start_all_bots,
            width=150,
            height=40,
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.start_all_btn.pack(side="left", padx=5)
        
        # Stop All Button
        self.stop_all_btn = ctk.CTkButton(
            buttons_frame, 
            text="⏹️ Alle Bots stoppen", 
            command=self.main_window.stop_all_bots,
            width=150,
            height=40,
            fg_color="red",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.stop_all_btn.pack(side="left", padx=5)
        
        # Restart All Button
        self.restart_all_btn = ctk.CTkButton(
            buttons_frame, 
            text="🔄 Alle Bots neustarten", 
            command=self.main_window.restart_all_bots,
            width=150,
            height=40,
            fg_color="orange",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.restart_all_btn.pack(side="left", padx=5)
        
    def setup_balancer_status(self):
        """Erstellt die Token Balancer Status-Anzeige"""
        balancer_frame = ctk.CTkFrame(self.parent)
        balancer_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(balancer_frame, text="⚖️ Token Balancer", 
                     font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(10, 5))
        
        # Status Text
        self.balancer_status_label = ctk.CTkLabel(
            balancer_frame, 
            text="Primärer Bot aktiv",
            font=ctk.CTkFont(size=12)
        )
        self.balancer_status_label.pack(pady=(0, 10))
        
    def setup_api_status(self):
        """Erstellt die API-Server Status-Anzeige"""
        if not hasattr(self.main_window, 'api_manager'):
            return
            
        api_frame = ctk.CTkFrame(self.parent)
        api_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(api_frame, text="🌐 API-Server Status", 
                     font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(10, 5))
        
        self.api_status_label = ctk.CTkLabel(api_frame, text="🔴 Offline", text_color="red")
        self.api_status_label.pack()
        
        self.api_url_label = ctk.CTkLabel(api_frame, text="http://localhost:7000/api/status", 
                                         font=ctk.CTkFont(size=10), text_color="gray")
        self.api_url_label.pack(pady=(0, 10))
        
        # API Control Buttons
        api_buttons_frame = ctk.CTkFrame(api_frame)
        api_buttons_frame.pack(pady=5)
        
        ctk.CTkButton(api_buttons_frame, text="🚀 API starten", 
                      command=self.main_window.start_api_server, width=120).pack(side="left", padx=5)
        
        ctk.CTkButton(api_buttons_frame, text="🛑 API stoppen", 
                      command=self.main_window.stop_api_server, width=120, fg_color="red").pack(side="left", padx=5)

    def update_status(self):
        """Verbesserte Status-Aktualisierung mit Ängerungs-Erkennung"""
        try:
            self.update_bot_cards()
            self.update_balancer_display()
            self.update_api_status()
        except Exception as e:
            print(f"[ERROR] Dashboard Update Error: {e}")
        
    def update_bot_cards(self):
        """Verbesserte Bot-Status-Karten-Aktualisierung"""
        try:
            # Main Bot Status abrufen (Thread-sicher)
            main_status = self.main_window.status_manager.get_main_bot_status()
            
            # Nur aktualisieren wenn sich etwas geändert hat
            if main_status != self.last_main_status:
                self.last_main_status = main_status.copy()
                
                if main_status['online']:
                    self.main_bot_status_label.configure(text="🟢 Online", text_color="green")
                    latency_ms = round(main_status['latency'] * 1000) if main_status['latency'] > 0 else 0
                    info_text = f"Server: {main_status['guilds']} | Nutzer: {main_status['users']} | {latency_ms}ms"
                    self.main_bot_info_label.configure(text=info_text)
                else:
                    self.main_bot_status_label.configure(text="🔴 Offline", text_color="red")
                    self.main_bot_info_label.configure(text="Server: 0 | Nutzer: 0")
            
            # Helper Bot Status abrufen (Thread-sicher)
            helper_status = self.main_window.status_manager.get_helper_bot_status()
            
            # Nur aktualisieren wenn sich etwas geändert hat
            if helper_status != self.last_helper_status:
                self.last_helper_status = helper_status.copy()
                
                if helper_status['online']:
                    self.helper_bot_status_label.configure(text="🟢 Online", text_color="green")
                    latency_ms = round(helper_status['latency'] * 1000) if helper_status['latency'] > 0 else 0
                    info_text = f"Server: {helper_status['guilds']} | Nutzer: {helper_status['users']} | {latency_ms}ms"
                    self.helper_bot_info_label.configure(text=info_text)
                else:
                    self.helper_bot_status_label.configure(text="🔴 Offline", text_color="red")
                    self.helper_bot_info_label.configure(text="Server: 0 | Nutzer: 0")
                    
        except Exception as e:
            print(f"[ERROR] Bot Cards Update Error: {e}")
        
    def update_balancer_display(self):
        """Verbesserte Balancer-Anzeige-Aktualisierung"""
        try:
            balancer_status = self.main_window.status_manager.get_balancer_status()
            
            # Nur aktualisieren wenn sich etwas geändert hat
            if balancer_status != self.last_balancer_status:
                self.last_balancer_status = balancer_status.copy()
                status_text = balancer_status.get('status_text', 'Primärer Bot aktiv')
                self.balancer_status_label.configure(text=status_text)
                
        except Exception as e:
            print(f"[ERROR] Balancer Display Update Error: {e}")
        
    def update_api_status(self):
        """Verbesserte API-Server Status-Anzeige-Aktualisierung"""
        try:
            if not hasattr(self, 'api_status_label') or not hasattr(self.main_window, 'api_manager'):
                return
                
            if self.main_window.api_manager.is_running():
                self.api_status_label.configure(text="🟢 Online", text_color="green")
            else:
                self.api_status_label.configure(text="🔴 Offline", text_color="red")
                
        except Exception as e:
            print(f"[ERROR] API Status Update Error: {e}")