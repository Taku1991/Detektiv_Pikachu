#!/usr/bin/env python3
"""
Dialog Components
Wiederverwendbare Dialog-Fenster
"""

import customtkinter as ctk
from tkinter import messagebox
from typing import Optional, Callable, Dict, Any

class ConfirmDialog:
    """Bestätigungs-Dialog"""
    
    @staticmethod
    def show(title: str, message: str, on_confirm: Optional[Callable] = None, on_cancel: Optional[Callable] = None) -> bool:
        """Zeigt einen Bestätigungs-Dialog"""
        result = messagebox.askyesno(title, message)
        
        if result and on_confirm:
            on_confirm()
        elif not result and on_cancel:
            on_cancel()
            
        return result

class InfoDialog:
    """Informations-Dialog"""
    
    @staticmethod
    def show_info(title: str, message: str):
        """Zeigt eine Info-Nachricht"""
        messagebox.showinfo(title, message)
    
    @staticmethod
    def show_warning(title: str, message: str):
        """Zeigt eine Warnung"""
        messagebox.showwarning(title, message)
    
    @staticmethod
    def show_error(title: str, message: str):
        """Zeigt einen Fehler"""
        messagebox.showerror(title, message)

class CustomDialog:
    """Anpassbarer Dialog mit Custom-Tkinter"""
    
    def __init__(self, parent, title: str, size: tuple = (400, 300)):
        self.parent = parent
        self.title = title
        self.size = size
        self.result = None
        
        self.window = None
        self.setup_window()
        
    def setup_window(self):
        """Erstellt das Dialog-Fenster"""
        self.window = ctk.CTkToplevel(self.parent)
        self.window.title(self.title)
        self.window.geometry(f"{self.size[0]}x{self.size[1]}")
        self.window.transient(self.parent)
        self.window.grab_set()  # Modal
        
        # Zentriere das Fenster
        self.center_window()
        
    def center_window(self):
        """Zentriert das Fenster auf dem Bildschirm"""
        self.window.update_idletasks()
        x = (self.window.winfo_screenwidth() // 2) - (self.size[0] // 2)
        y = (self.window.winfo_screenheight() // 2) - (self.size[1] // 2)
        self.window.geometry(f"{self.size[0]}x{self.size[1]}+{x}+{y}")
        
    def add_content(self, content_func):
        """Fügt Inhalte zum Dialog hinzu"""
        content_func(self.window)
        
    def add_buttons(self, buttons: list):
        """Fügt Buttons zum Dialog hinzu
        
        Args:
            buttons: Liste von Tuples (text, command, color)
        """
        button_frame = ctk.CTkFrame(self.window)
        button_frame.pack(fill="x", padx=20, pady=20)
        
        for button_config in buttons:
            text, command = button_config[:2]
            color = button_config[2] if len(button_config) > 2 else None
            
            btn = ctk.CTkButton(button_frame, text=text, command=command, width=120)
            if color:
                btn.configure(fg_color=color)
            btn.pack(side="right", padx=5)
    
    def show(self):
        """Zeigt den Dialog und wartet auf Schließung"""
        self.window.wait_window()
        return self.result
    
    def close(self, result=None):
        """Schließt den Dialog mit optionalem Ergebnis"""
        self.result = result
        self.window.destroy()

class InputDialog(CustomDialog):
    """Eingabe-Dialog"""
    
    def __init__(self, parent, title: str, prompt: str, default_value: str = ""):
        self.prompt = prompt
        self.default_value = default_value
        self.entry = None
        
        super().__init__(parent, title, (400, 200))
        self.setup_content()
        
    def setup_content(self):
        """Erstellt den Dialog-Inhalt"""
        # Prompt Label
        prompt_label = ctk.CTkLabel(self.window, text=self.prompt, font=ctk.CTkFont(size=14))
        prompt_label.pack(pady=(20, 10))
        
        # Entry Field
        self.entry = ctk.CTkEntry(self.window, width=300)
        self.entry.pack(pady=10)
        self.entry.insert(0, self.default_value)
        self.entry.focus()
        
        # Buttons
        self.add_buttons([
            ("Abbrechen", lambda: self.close(None), "gray"),
            ("OK", self.on_ok, None)
        ])
        
        # Enter-Taste für OK
        self.window.bind('<Return>', lambda e: self.on_ok())
        
    def on_ok(self):
        """OK-Button gedrückt"""
        value = self.entry.get().strip()
        self.close(value if value else None) 