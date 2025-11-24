#!/usr/bin/env python3
"""
Base GUI Component
Basis-Klasse für alle GUI-Komponenten
"""

import customtkinter as ctk
from typing import Optional

class BaseGUIComponent:
    """Basis-Klasse für alle GUI-Komponenten"""
    
    def __init__(self, parent, main_window):
        self.parent = parent
        self.main_window = main_window
        self.main_bot = main_window.main_bot
        self.helper_bot = main_window.helper_bot
        self.root = main_window.root
    
    def show_status_message(self, message: str, msg_type: str = "info"):
        """Zeigt eine temporäre Statusmeldung an"""
        self.main_window.show_status_message(message, msg_type)
    
    def log_gui_action_threaded(self, action_type: str, details: str, 
                               guild_id: str = None, channel_id: str = None):
        """Thread-sichere Version der GUI-Action-Logging"""
        self.main_window.log_gui_action_threaded(action_type, details, guild_id, channel_id)
    
    def create_header_frame(self, parent, title: str, subtitle: str = None) -> ctk.CTkFrame:
        """Erstellt einen Standard-Header-Frame"""
        header_frame = ctk.CTkFrame(parent)
        header_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(header_frame, text=title, 
                     font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)
        
        if subtitle:
            ctk.CTkLabel(header_frame, text=subtitle, 
                         font=ctk.CTkFont(size=12), text_color="gray").pack()
        
        return header_frame
    
    def create_button_frame(self, parent, buttons: list) -> ctk.CTkFrame:
        """Erstellt einen Frame mit Standard-Buttons
        
        Args:
            parent: Parent-Widget
            buttons: Liste von Tuples (text, command, width, color)
        """
        button_frame = ctk.CTkFrame(parent)
        button_frame.pack(fill="x", padx=10, pady=10)
        
        for button_config in buttons:
            text, command = button_config[:2]
            width = button_config[2] if len(button_config) > 2 else 120
            color = button_config[3] if len(button_config) > 3 else None
            
            btn = ctk.CTkButton(button_frame, text=text, command=command, width=width)
            if color:
                btn.configure(fg_color=color)
            btn.pack(side="left", padx=5, pady=5)
        
        return button_frame
    
    def create_info_grid(self, parent, info_items: dict) -> ctk.CTkFrame:
        """Erstellt ein Info-Grid mit Labels
        
        Args:
            parent: Parent-Widget
            info_items: Dict mit {label_name: initial_text}
        """
        info_frame = ctk.CTkFrame(parent)
        info_frame.pack(fill="x", padx=10, pady=10)
        
        grid_frame = ctk.CTkFrame(info_frame)
        grid_frame.pack(fill="x", padx=10, pady=10)
        
        labels = {}
        row, col = 0, 0
        
        for name, text in info_items.items():
            label = ctk.CTkLabel(grid_frame, text=text)
            label.grid(row=row, column=col, sticky="w", padx=10, pady=5)
            labels[name] = label
            
            col += 1
            if col >= 2:  # 2 Spalten
                col = 0
                row += 1
        
        return info_frame, labels 