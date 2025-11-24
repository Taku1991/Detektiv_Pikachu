#!/usr/bin/env python3
"""
Detektiv Pikachu Bot GUI Package
Modularisierte GUI-Komponenten
"""

from .main_window import MainWindow

__version__ = "2.0.0"
__author__ = "Detektiv Pikachu Bot Team"

# Hauptklasse für Rückwärtskompatibilität
BotGUI = MainWindow

__all__ = ["MainWindow", "BotGUI"] 