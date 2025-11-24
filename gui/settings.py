#!/usr/bin/env python3
"""
Settings Component
Einstellungen und Konfiguration
"""

import customtkinter as ctk
import json
from pathlib import Path
from .base import BaseGUIComponent
from .components.forms import ConfigForm
from .components.dialogs import InfoDialog

class Settings(BaseGUIComponent):
    """Einstellungs-Komponente"""
    
    def __init__(self, parent, main_window):
        super().__init__(parent, main_window)
        self.settings_data = {}
        self.setup_settings()
        self.load_current_settings()
        
    def setup_settings(self):
        """Erstellt die Einstellungs-Oberfläche"""
        # Notebook für verschiedene Einstellungs-Kategorien
        self.settings_notebook = ctk.CTkTabview(self.parent)
        self.settings_notebook.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Appearance Settings
        self.setup_appearance_settings()
        
        # Bot Settings
        self.setup_bot_settings()
        
        # Notification Settings
        self.setup_notification_settings()
        
        # Advanced Settings
        self.setup_advanced_settings()
        
        # Save Button
        self.setup_save_section()
        
    def setup_appearance_settings(self):
        """Erstellt die Erscheinungsbild-Einstellungen"""
        appearance_tab = self.settings_notebook.add("🎨 Erscheinungsbild")
        
        # Appearance Form
        self.appearance_form = ConfigForm(appearance_tab, "🎨 Design-Einstellungen")
        
        # Appearance Mode
        self.appearance_form.add_field(
            "appearance_mode",
            "Erscheinungsbild:",
            "dropdown",
            values=["dark", "light", "system"],
            default_value="dark"
        )
        
        # Color Theme
        self.appearance_form.add_field(
            "color_theme",
            "Farbschema:",
            "dropdown", 
            values=["blue", "green", "dark-blue"],
            default_value="blue"
        )
        
        # UI Scale
        self.appearance_form.add_field(
            "ui_scale",
            "UI-Skalierung:",
            "dropdown",
            values=["0.8", "0.9", "1.0", "1.1", "1.2"],
            default_value="1.0"
        )
        
        # Font Size
        self.appearance_form.add_field(
            "font_size",
            "Schriftgröße:",
            "dropdown",
            values=["10", "11", "12", "13", "14"],
            default_value="12"
        )
        
        self.appearance_form.pack(fill="both", expand=True, padx=10, pady=10)
        
    def setup_bot_settings(self):
        """Erstellt die Bot-Einstellungen"""
        bot_tab = self.settings_notebook.add("🤖 Bot-Einstellungen")
        
        # Auto-Start Settings
        autostart_form = ConfigForm(bot_tab, "🚀 Auto-Start")
        
        autostart_form.add_field(
            "autostart_main",
            "Main Bot automatisch starten",
            "checkbox"
        )
        
        autostart_form.add_field(
            "autostart_helper", 
            "Helper Bot automatisch starten",
            "checkbox"
        )
        
        autostart_form.add_field(
            "autostart_delay",
            "Start-Verzögerung (Sekunden):",
            "entry",
            placeholder="5",
            default_value="5"
        )
        
        autostart_form.pack(fill="x", padx=10, pady=10)
        self.autostart_form = autostart_form
        
        # Update Settings
        update_form = ConfigForm(bot_tab, "🔄 Update-Einstellungen")
        
        update_form.add_field(
            "update_interval",
            "Update-Intervall (Sekunden):",
            "entry",
            placeholder="60",
            default_value="60"
        )
        
        update_form.add_field(
            "auto_refresh_channels",
            "Channel-Daten automatisch aktualisieren",
            "checkbox"
        )
        
        update_form.add_field(
            "refresh_interval",
            "Refresh-Intervall (Minuten):",
            "entry",
            placeholder="5",
            default_value="5"
        )
        
        update_form.pack(fill="x", padx=10, pady=10)
        self.update_form = update_form
        
    def setup_notification_settings(self):
        """Erstellt die Benachrichtigungs-Einstellungen"""
        notification_tab = self.settings_notebook.add("🔔 Benachrichtigungen")
        
        # Notification Form
        self.notification_form = ConfigForm(notification_tab, "🔔 Benachrichtigungs-Einstellungen")
        
        self.notification_form.add_field(
            "notify_errors",
            "Bei Fehlern benachrichtigen",
            "checkbox",
            default_value="true"
        )
        
        self.notification_form.add_field(
            "notify_status_changes",
            "Bei Statusänderungen benachrichtigen", 
            "checkbox",
            default_value="true"
        )
        
        self.notification_form.add_field(
            "notify_bot_start_stop",
            "Bei Bot-Start/Stop benachrichtigen",
            "checkbox"
        )
        
        self.notification_form.add_field(
            "notification_sound",
            "Benachrichtigungs-Sound",
            "checkbox"
        )
        
        self.notification_form.add_field(
            "popup_duration",
            "Popup-Dauer (Sekunden):",
            "entry",
            placeholder="3",
            default_value="3"
        )
        
        self.notification_form.pack(fill="both", expand=True, padx=10, pady=10)
        
    def setup_advanced_settings(self):
        """Erstellt die erweiterten Einstellungen"""
        advanced_tab = self.settings_notebook.add("⚙️ Erweitert")
        
        # Logging Settings
        logging_form = ConfigForm(advanced_tab, "📝 Logging-Einstellungen")
        
        logging_form.add_field(
            "log_level",
            "Log-Level:",
            "dropdown",
            values=["DEBUG", "INFO", "WARNING", "ERROR"],
            default_value="INFO"
        )
        
        logging_form.add_field(
            "max_log_entries",
            "Max. Log-Einträge:",
            "entry",
            placeholder="10000",
            default_value="10000"
        )
        
        logging_form.add_field(
            "log_to_file",
            "In Datei loggen",
            "checkbox"
        )
        
        logging_form.pack(fill="x", padx=10, pady=10)
        self.logging_form = logging_form
        
        # Performance Settings
        performance_form = ConfigForm(advanced_tab, "⚡ Performance")
        
        performance_form.add_field(
            "gui_update_interval",
            "GUI-Update-Intervall (ms):",
            "entry",
            placeholder="1000",
            default_value="1000"
        )
        
        performance_form.add_field(
            "enable_threading",
            "Threading aktivieren",
            "checkbox",
            default_value="true"
        )
        
        performance_form.add_field(
            "cache_channel_names",
            "Channel-Namen cachen",
            "checkbox",
            default_value="true"
        )
        
        performance_form.pack(fill="x", padx=10, pady=10)
        self.performance_form = performance_form
        
    def setup_save_section(self):
        """Erstellt den Speichern-Bereich"""
        save_frame = ctk.CTkFrame(self.parent)
        save_frame.pack(fill="x", padx=10, pady=10)
        
        button_frame = ctk.CTkFrame(save_frame)
        button_frame.pack(pady=15)
        
        # Load Defaults Button
        defaults_btn = ctk.CTkButton(
            button_frame,
            text="🔄 Standardwerte",
            command=self.load_defaults,
            width=140,
            fg_color="gray"
        )
        defaults_btn.pack(side="left", padx=5)
        
        # Export Settings Button
        export_btn = ctk.CTkButton(
            button_frame,
            text="📤 Exportieren",
            command=self.export_settings,
            width=140
        )
        export_btn.pack(side="left", padx=5)
        
        # Import Settings Button
        import_btn = ctk.CTkButton(
            button_frame,
            text="📥 Importieren",
            command=self.import_settings,
            width=140,
            fg_color="orange"
        )
        import_btn.pack(side="left", padx=5)
        
        # Save Settings Button
        save_btn = ctk.CTkButton(
            button_frame,
            text="💾 Einstellungen speichern",
            command=self.save_settings,
            width=200,
            height=40,
            font=ctk.CTkFont(size=14, weight="bold")
        )
        save_btn.pack(side="right", padx=10)
        
    def load_current_settings(self):
        """Lädt die aktuellen Einstellungen"""
        try:
            settings_path = Path('gui_settings.json')
            if settings_path.exists():
                with open(settings_path, 'r', encoding='utf-8') as f:
                    self.settings_data = json.load(f)
                
                # Anwenden auf Formulare
                self.apply_settings_to_forms()
            else:
                # Standard-Einstellungen laden
                self.load_defaults()
                
        except Exception as e:
            print(f"Settings loading error: {e}")
            self.load_defaults()
            
    def apply_settings_to_forms(self):
        """Wendet Einstellungen auf die Formulare an"""
        try:
            # Appearance Settings
            if hasattr(self, 'appearance_form'):
                appearance_values = {
                    'appearance_mode': self.settings_data.get('appearance_mode', 'dark'),
                    'color_theme': self.settings_data.get('color_theme', 'blue'),
                    'ui_scale': str(self.settings_data.get('ui_scale', 1.0)),
                    'font_size': str(self.settings_data.get('font_size', 12))
                }
                self.appearance_form.set_values(appearance_values)
            
            # Bot Settings
            if hasattr(self, 'autostart_form'):
                autostart_values = {
                    'autostart_main': self.settings_data.get('autostart_main', False),
                    'autostart_helper': self.settings_data.get('autostart_helper', False),
                    'autostart_delay': str(self.settings_data.get('autostart_delay', 5))
                }
                self.autostart_form.set_values(autostart_values)
            
            if hasattr(self, 'update_form'):
                update_values = {
                    'update_interval': str(self.settings_data.get('update_interval', 60)),
                    'auto_refresh_channels': self.settings_data.get('auto_refresh_channels', True),
                    'refresh_interval': str(self.settings_data.get('refresh_interval', 5))
                }
                self.update_form.set_values(update_values)
            
            # Notification Settings
            if hasattr(self, 'notification_form'):
                notification_values = {
                    'notify_errors': self.settings_data.get('notify_errors', True),
                    'notify_status_changes': self.settings_data.get('notify_status_changes', True),
                    'notify_bot_start_stop': self.settings_data.get('notify_bot_start_stop', False),
                    'notification_sound': self.settings_data.get('notification_sound', False),
                    'popup_duration': str(self.settings_data.get('popup_duration', 3))
                }
                self.notification_form.set_values(notification_values)
            
            # Advanced Settings
            if hasattr(self, 'logging_form'):
                logging_values = {
                    'log_level': self.settings_data.get('log_level', 'INFO'),
                    'max_log_entries': str(self.settings_data.get('max_log_entries', 10000)),
                    'log_to_file': self.settings_data.get('log_to_file', False)
                }
                self.logging_form.set_values(logging_values)
            
            if hasattr(self, 'performance_form'):
                performance_values = {
                    'gui_update_interval': str(self.settings_data.get('gui_update_interval', 1000)),
                    'enable_threading': self.settings_data.get('enable_threading', True),
                    'cache_channel_names': self.settings_data.get('cache_channel_names', True)
                }
                self.performance_form.set_values(performance_values)
                
        except Exception as e:
            print(f"Apply settings error: {e}")
            
    def collect_settings_from_forms(self):
        """Sammelt Einstellungen aus allen Formularen"""
        settings = {}
        
        try:
            # Appearance Settings
            if hasattr(self, 'appearance_form'):
                appearance_values = self.appearance_form.get_values()
                settings.update(appearance_values)
            
            # Bot Settings
            if hasattr(self, 'autostart_form'):
                autostart_values = self.autostart_form.get_values()
                settings.update(autostart_values)
            
            if hasattr(self, 'update_form'):
                update_values = self.update_form.get_values()
                settings.update(update_values)
            
            # Notification Settings
            if hasattr(self, 'notification_form'):
                notification_values = self.notification_form.get_values()
                settings.update(notification_values)
            
            # Advanced Settings
            if hasattr(self, 'logging_form'):
                logging_values = self.logging_form.get_values()
                settings.update(logging_values)
            
            if hasattr(self, 'performance_form'):
                performance_values = self.performance_form.get_values()
                settings.update(performance_values)
                
        except Exception as e:
            print(f"Collect settings error: {e}")
            
        return settings
    
    def save_settings(self):
        """Speichert alle Einstellungen"""
        try:
            # Sammle Einstellungen
            settings = self.collect_settings_from_forms()
            
            # Validierung
            validation_errors = self.validate_settings(settings)
            if validation_errors:
                InfoDialog.show_error("Validierungsfehler", "\n".join(validation_errors))
                return
            
            # Speichere in Datei
            settings_path = Path('gui_settings.json')
            with open(settings_path, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2)
            
            # Aktualisiere interne Daten
            self.settings_data = settings
            
            # Anwenden der Einstellungen
            self.apply_appearance_settings(settings)
            
            self.show_status_message("Einstellungen erfolgreich gespeichert", "success")
            
        except Exception as e:
            self.show_status_message(f"Fehler beim Speichern: {e}", "error")
            
    def validate_settings(self, settings):
        """Validiert die Einstellungen"""
        errors = []
        
        try:
            # Numeric validations
            numeric_fields = [
                ('autostart_delay', 'Auto-Start-Verzögerung'),
                ('update_interval', 'Update-Intervall'),
                ('refresh_interval', 'Refresh-Intervall'),
                ('popup_duration', 'Popup-Dauer'),
                ('max_log_entries', 'Max. Log-Einträge'),
                ('gui_update_interval', 'GUI-Update-Intervall')
            ]
            
            for field, display_name in numeric_fields:
                if field in settings:
                    try:
                        value = int(settings[field])
                        if value < 0:
                            errors.append(f"{display_name} muss positiv sein")
                    except ValueError:
                        errors.append(f"{display_name} muss eine Zahl sein")
            
            # UI Scale validation
            if 'ui_scale' in settings:
                try:
                    scale = float(settings['ui_scale'])
                    if not 0.5 <= scale <= 2.0:
                        errors.append("UI-Skalierung muss zwischen 0.5 und 2.0 liegen")
                except ValueError:
                    errors.append("UI-Skalierung muss eine Zahl sein")
                    
        except Exception as e:
            errors.append(f"Validierungsfehler: {e}")
            
        return errors
    
    def apply_appearance_settings(self, settings):
        """Wendet Erscheinungsbild-Einstellungen an"""
        try:
            # Appearance Mode
            if 'appearance_mode' in settings:
                ctk.set_appearance_mode(settings['appearance_mode'])
            
            # UI Scale
            if 'ui_scale' in settings:
                try:
                    scale = float(settings['ui_scale'])
                    ctk.set_widget_scaling(scale)
                except ValueError:
                    pass
                    
        except Exception as e:
            print(f"Apply appearance settings error: {e}")
    
    def load_defaults(self):
        """Lädt Standard-Einstellungen"""
        defaults = {
            'appearance_mode': 'dark',
            'color_theme': 'blue',
            'ui_scale': '1.0',
            'font_size': '12',
            'autostart_main': False,
            'autostart_helper': False,
            'autostart_delay': '5',
            'update_interval': '60',
            'auto_refresh_channels': True,
            'refresh_interval': '5',
            'notify_errors': True,
            'notify_status_changes': True,
            'notify_bot_start_stop': False,
            'notification_sound': False,
            'popup_duration': '3',
            'log_level': 'INFO',
            'max_log_entries': '10000',
            'log_to_file': False,
            'gui_update_interval': '1000',
            'enable_threading': True,
            'cache_channel_names': True
        }
        
        self.settings_data = defaults
        self.apply_settings_to_forms()
        self.show_status_message("Standard-Einstellungen geladen", "info")
    
    def export_settings(self):
        """Exportiert Einstellungen in eine Datei"""
        try:
            from tkinter import filedialog
            from datetime import datetime
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_filename = f"gui_settings_export_{timestamp}.json"
            
            filename = filedialog.asksaveasfilename(
                title="Einstellungen exportieren",
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
                initialname=default_filename
            )
            
            if filename:
                settings = self.collect_settings_from_forms()
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(settings, f, indent=2)
                
                self.show_status_message(f"Einstellungen exportiert: {Path(filename).name}", "success")
                
        except Exception as e:
            self.show_status_message(f"Export fehlgeschlagen: {e}", "error")
    
    def import_settings(self):
        """Importiert Einstellungen aus einer Datei"""
        try:
            from tkinter import filedialog
            
            filename = filedialog.askopenfilename(
                title="Einstellungen importieren",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
            )
            
            if filename:
                with open(filename, 'r', encoding='utf-8') as f:
                    imported_settings = json.load(f)
                
                # Validierung
                validation_errors = self.validate_settings(imported_settings)
                if validation_errors:
                    InfoDialog.show_error("Import-Fehler", f"Ungültige Einstellungen:\n" + "\n".join(validation_errors))
                    return
                
                # Anwenden
                self.settings_data = imported_settings
                self.apply_settings_to_forms()
                
                self.show_status_message(f"Einstellungen importiert: {Path(filename).name}", "success")
                
        except Exception as e:
            self.show_status_message(f"Import fehlgeschlagen: {e}", "error") 