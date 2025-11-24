#!/usr/bin/env python3
"""
Form Components
Wiederverwendbare Formular-Komponenten
"""

import customtkinter as ctk
from typing import Dict, Any, Optional, Callable

class ConfigForm:
    """Konfigurations-Formular Komponente"""
    
    def __init__(self, parent, title: str):
        self.parent = parent
        self.title = title
        self.fields = {}
        self.entries = {}
        
        self.frame = ctk.CTkFrame(parent)
        self.setup_form()
        
    def setup_form(self):
        """Erstellt das Basis-Formular"""
        # Titel
        title_label = ctk.CTkLabel(
            self.frame, 
            text=self.title, 
            font=ctk.CTkFont(size=16, weight="bold")
        )
        title_label.pack(pady=(15, 10))
        
        # Content Frame für Felder
        self.content_frame = ctk.CTkFrame(self.frame)
        self.content_frame.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        
    def add_field(self, field_name: str, label: str, field_type: str = "entry", 
                  placeholder: str = "", default_value: str = "", 
                  values: list = None, **kwargs):
        """Fügt ein Feld zum Formular hinzu"""
        # Label
        label_widget = ctk.CTkLabel(
            self.content_frame, 
            text=label,
            font=ctk.CTkFont(weight="bold")
        )
        label_widget.pack(anchor="w", padx=15, pady=(10, 5))
        
        # Entry-Widget basierend auf Typ
        if field_type == "entry":
            widget = ctk.CTkEntry(
                self.content_frame, 
                placeholder_text=placeholder,
                **kwargs
            )
            if default_value:
                widget.insert(0, default_value)
                
        elif field_type == "password":
            widget = ctk.CTkEntry(
                self.content_frame, 
                placeholder_text=placeholder,
                show="*",
                **kwargs
            )
            if default_value:
                widget.insert(0, default_value)
                
        elif field_type == "dropdown":
            widget = ctk.CTkOptionMenu(
                self.content_frame,
                values=values or ["Option 1"],
                **kwargs
            )
            if default_value and default_value in (values or []):
                widget.set(default_value)
                
        elif field_type == "checkbox":
            widget = ctk.CTkCheckBox(
                self.content_frame,
                text=label,
                **kwargs
            )
            if default_value:
                widget.select()
                
        else:
            # Fallback zu Entry
            widget = ctk.CTkEntry(
                self.content_frame, 
                placeholder_text=placeholder,
                **kwargs
            )
        
        # Widget packen
        if field_type != "checkbox":
            widget.pack(fill="x", padx=15, pady=(0, 10))
        else:
            widget.pack(anchor="w", padx=15, pady=(0, 10))
        
        # Speichern
        self.fields[field_name] = {
            'type': field_type,
            'label': label,
            'widget': widget
        }
        self.entries[field_name] = widget
        
    def get_values(self) -> Dict[str, Any]:
        """Gibt alle Formular-Werte zurück"""
        values = {}
        
        for field_name, field_info in self.fields.items():
            widget = field_info['widget']
            field_type = field_info['type']
            
            if field_type in ["entry", "password"]:
                values[field_name] = widget.get().strip()
            elif field_type == "dropdown":
                values[field_name] = widget.get()
            elif field_type == "checkbox":
                values[field_name] = widget.get()
                
        return values
    
    def set_values(self, values: Dict[str, Any]):
        """Setzt Formular-Werte"""
        for field_name, value in values.items():
            if field_name in self.fields:
                widget = self.fields[field_name]['widget']
                field_type = self.fields[field_name]['type']
                
                if field_type in ["entry", "password"]:
                    widget.delete(0, "end")
                    widget.insert(0, str(value))
                elif field_type == "dropdown":
                    widget.set(str(value))
                elif field_type == "checkbox":
                    if value:
                        widget.select()
                    else:
                        widget.deselect()
    
    def clear(self):
        """Leert alle Formular-Felder"""
        for field_name, field_info in self.fields.items():
            widget = field_info['widget']
            field_type = field_info['type']
            
            if field_type in ["entry", "password"]:
                widget.delete(0, "end")
            elif field_type == "checkbox":
                widget.deselect()
    
    def validate(self, validators: Dict[str, Callable]) -> tuple:
        """Validiert Formular-Werte
        
        Args:
            validators: Dict mit {field_name: validator_function}
            
        Returns:
            tuple: (is_valid, error_messages)
        """
        values = self.get_values()
        errors = []
        
        for field_name, validator in validators.items():
            if field_name in values:
                try:
                    if not validator(values[field_name]):
                        errors.append(f"{self.fields[field_name]['label']}: Ungültiger Wert")
                except Exception as e:
                    errors.append(f"{self.fields[field_name]['label']}: {str(e)}")
        
        return len(errors) == 0, errors
    
    def add_buttons(self, buttons: list):
        """Fügt Buttons zum Formular hinzu
        
        Args:
            buttons: Liste von Tuples (text, command, width, color)
        """
        button_frame = ctk.CTkFrame(self.frame)
        button_frame.pack(fill="x", padx=15, pady=(0, 15))
        
        for button_config in buttons:
            text, command = button_config[:2]
            width = button_config[2] if len(button_config) > 2 else 120
            color = button_config[3] if len(button_config) > 3 else None
            
            btn = ctk.CTkButton(button_frame, text=text, command=command, width=width)
            if color:
                btn.configure(fg_color=color)
            btn.pack(side="right", padx=5, pady=10)
    
    def pack(self, **kwargs):
        """Packt das Formular"""
        self.frame.pack(**kwargs)
    
    def grid(self, **kwargs):
        """Griddet das Formular"""
        self.frame.grid(**kwargs) 