#!/usr/bin/env python3
"""
Setup Wizard Component
Erstkonfiguration für neue Installationen
"""

import customtkinter as ctk
from .components.dialogs import InfoDialog

class SetupWizard:
    """Setup-Wizard für die Erstkonfiguration"""
    
    def __init__(self, parent, main_window):
        self.parent = parent
        self.main_window = main_window
        
    def show(self):
        """Zeigt den Setup-Wizard"""
        self.setup_window = ctk.CTkToplevel(self.parent)
        self.setup_window.title("🚀 Detektiv Pikachu Bot - Erste Einrichtung")
        self.setup_window.geometry("600x500")
        self.setup_window.transient(self.parent)
        self.setup_window.grab_set()  # Modal
        
        # Center window
        self.center_window()
        
        # Setup content
        self.setup_wizard_content()
        
    def center_window(self):
        """Zentriert das Setup-Fenster"""
        self.setup_window.update_idletasks()
        x = (self.setup_window.winfo_screenwidth() // 2) - (300)
        y = (self.setup_window.winfo_screenheight() // 2) - (250)
        self.setup_window.geometry(f"600x500+{x}+{y}")
    
    def setup_wizard_content(self):
        """Erstellt den Wizard-Inhalt"""
        # Header
        header_frame = ctk.CTkFrame(self.setup_window)
        header_frame.pack(fill="x", padx=20, pady=20)
        
        ctk.CTkLabel(header_frame, text="🔍 Detektiv Pikachu Bot", 
                     font=ctk.CTkFont(size=28, weight="bold")).pack(pady=10)
        ctk.CTkLabel(header_frame, text="Erste Einrichtung", 
                     font=ctk.CTkFont(size=18)).pack()
        
        # Info Text
        info_frame = ctk.CTkFrame(self.setup_window)
        info_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        info_text = """🚀 Willkommen bei der Erstkonfiguration!

📋 Was Sie benötigen:
• Zwei Discord Bot-Tokens
• Ihre Discord User-ID (als Administrator)

🔧 Konfiguration:
Erstellen Sie eine .env Datei mit folgenden Inhalten:

PRIMARY_BOT_TOKEN=ihr_primärer_bot_token
SECONDARY_BOT_TOKEN=ihr_sekundärer_bot_token  
ADMIN_USER_ID=ihre_discord_user_id

💡 Tipp: Verwenden Sie einen Texteditor und speichern Sie
die Datei als '.env' (ohne Dateierweiterung) im Bot-Ordner.

📖 Weitere Hilfe finden Sie in der Dokumentation."""
        
        ctk.CTkLabel(info_frame, text=info_text, justify="left", 
                     font=ctk.CTkFont(size=12)).pack(padx=20, pady=20)
        
        # Buttons
        button_frame = ctk.CTkFrame(self.setup_window)
        button_frame.pack(fill="x", padx=20, pady=20)
        
        ctk.CTkButton(button_frame, text="❌ Schließen", 
                      command=self.setup_window.destroy, width=120).pack(side="left", padx=10)
        
        ctk.CTkButton(button_frame, text="📖 Hilfe anzeigen", 
                      command=self.show_help, width=120).pack(side="right", padx=10)
    
    def show_help(self):
        """Zeigt erweiterte Hilfe"""
        help_text = """🔗 Discord Bot erstellen:

1. Besuchen Sie https://discord.com/developers/applications
2. Klicken Sie auf "New Application"
3. Geben Sie einen Namen ein
4. Gehen Sie zu "Bot" im linken Menü
5. Klicken Sie auf "Add Bot"
6. Kopieren Sie den Token unter "Token"
7. Wiederholen Sie dies für einen zweiten Bot

🆔 Discord User-ID finden:
1. Aktivieren Sie den Entwicklermodus in Discord
   (Einstellungen → Erweitert → Entwicklermodus)
2. Rechtsklick auf Ihren Namen → "ID kopieren"

⚠️ Wichtig: Teilen Sie Ihre Bot-Tokens niemals!"""
        
        InfoDialog.show_info("Discord Bot Setup Hilfe", help_text) 