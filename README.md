# 🕵️ Detektiv Pikachu Discord Bot

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/downloads/)
[![Discord.py](https://img.shields.io/badge/discord.py-2.0%2B-blue.svg)](https://discordpy.readthedocs.io/en/stable/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Release](https://img.shields.io/github/v/release/yourusername/Detektiv_Pikachu?include_prereleases)](https://github.com/yourusername/Detektiv_Pikachu/releases)
[![Discord](https://img.shields.io/badge/Discord-Pokemon%20Hideout-7289da?logo=discord)](https://discord.gg/pokemonhideout)

Ein intelligenter Discord-Bot zur **automatischen Überwachung und Verwaltung von Bot-Status** in Discord-Servern. Der Bot erkennt Bot-Status-Änderungen durch Log-Nachrichten und aktualisiert entsprechend die Kanalnamen mit Status-Emojis.

## 🎯 Was macht der Bot?

**Detektiv Pikachu** überwacht Discord-Kanäle auf bestimmte Nachrichten-Muster und aktualisiert automatisch die Kanalnamen basierend auf dem erkannten Status:

- 📈 **Automatische Statuserkennung**: Erkennt Bot-Start/Stop-Meldungen in konfigurierten Kanälen
- 🏷️ **Dynamische Kanalnamen**: Ändert Kanalnamen automatisch mit Status-Emojis (✅ Online, ❌ Offline, ❗ Problem, 🟦 Wartung)
- 🤖 **Dual-Bot-System**: Haupt-Bot + Helper-Bot für optimale Performance und Rate-Limit-Behandlung
- 📊 **Statusverfolgung**: Speichert Status-Verlauf und bietet detaillierte Übersicht
- 🛡️ **Robuste Architektur**: Automatisches Token-Balancing und Fehlerbehandlung

## ✨ Hauptfeatures

### 🔄 **Intelligente Status-Erkennung**
- Überwacht Kanäle auf vordefinierte Text-Muster
- Erkennt automatisch Online/Offline/Problem-Status
- Anpassbare Regex-Muster für verschiedene Bot-Typen
- Echzeit-Status-Updates

### 🏷️ **Automatische Kanalnamen-Updates**
- **✅ Online**: Bot läuft normal
- **❌ Offline**: Bot ist gestoppt/beendet
- **❗ Problem**: Fehler oder Probleme erkannt
- **🟦 Wartung**: Manuell gesetzter Wartungsmodus

### 🤖 **Dual-Bot-Architektur**
- **Haupt-Bot**: Primäre Überwachung und Status-Updates
- **Helper-Bot**: Backup-System für Rate-Limit-Situationen
- **Token-Balancer**: Intelligenter Wechsel zwischen Bot-Tokens
- **Automatische Wiederherstellung**: Bei Verbindungsproblemen oder Rate-Limits

### 📊 **Erweiterte Verwaltung**
- Status-Verlauf mit Zeitstempel
- Manuelle Status-Overrides
- Channel-Lock/Unlock-Funktionen für Rollen-basierte Berechtigungen
- Detaillierte Logging mit automatischer Rotation
- Admin-Dashboard mit umfassenden Statistiken

### 🔒 **Channel-Lock-System**
- **Automatische Rollensperrung**: Sperrt konfigurierte Rollen bei Bot-Problemen automatisch
- **Selektive Berechtigungen**: Verwaltet spezifische Rechte (Nachrichten senden, Reaktionen, Threads)
- **Flexibles Rollen-Management**: Pro-Channel konfigurierbare Rollenlisten
- **Intelligente Wiederherstellung**: Entsperrt Rollen automatisch bei Bot-Wiederherstellung

### 🛡️ **Weitere Features**
- **Automatische Log-Rotation**: Verhindert überfüllte Log-Verzeichnisse
- **Log-Kompression**: Spart Speicherplatz durch .gz-Komprimierung
- **Rate-Limit-Handling**: Intelligentes Token-Management
- **Fehlerresilienz**: Automatische Wiederverbindung und Retry-Mechanismen
- **Performance-Monitoring**: Detaillierte Statistiken und Metriken

## 📋 Befehlsliste

### 👑 **Admin-Befehle**
*Erfordern Administrator-Berechtigung*

| Befehl | Beschreibung | Verwendung |
|--------|-------------|------------|
| `/sethistory <channel>` | Setzt den History-Channel für Status-Änderungen | Bestimmt wo Status-Verlauf geloggt wird |
| `/toggle <status>` | Ändert Bot-Status manuell | Status: Online, Offline, Problem, Wartung |
| `/balancerstatus` | Zeigt Token-Balancer-Status an | Übersicht über Primary/Secondary Token-Nutzung |
| `/logstats` | Zeigt Log-Datei-Statistiken an | Dateigröße, Anzahl, Komprimierung, etc. |
| `/cleanlogs` | Startet manuelle Log-Bereinigung | Entfernt alte Log-Dateien und zeigt Statistiken |

### 🔧 **Channel-Management**
*Erfordern Administrator-Berechtigung*

| Befehl | Beschreibung | Parameter |
|--------|-------------|-----------|
| `/addchannels <log_channel> <update_channel> [owner]` | Fügt Log- und Update-Kanal-Paar hinzu | Log-Channel, Update-Channel, Bot-Owner (optional) |
| `/removechannels <log_channel>` | Entfernt Channel-Paar aus Überwachung | Log-Channel |
| `/listchannels` | Zeigt alle konfigurierten Channels | Übersicht aller Channel-Paare und Status |
| `/exclude <channel>` | Schließt Channel vom Inaktivitäts-Check aus | Channel der ignoriert werden soll |
| `/include <channel>` | Fügt Channel wieder zum Inaktivitäts-Check hinzu | Zuvor ausgeschlossener Channel |

### 🔒 **Channel-Lock-System**
*Für Rollen-basierte Berechtigungssteuerung*

| Befehl | Beschreibung | Details |
|--------|-------------|---------|
| `/addlockrole <role>` | Fügt Rolle zur automatischen Sperrung hinzu | Rolle wird bei Bot-Problemen automatisch gesperrt |
| `/removelockrole <role>` | Entfernt Rolle aus automatischer Sperrung | Rolle wird nicht mehr verwaltet |
| `/listlockroles` | Zeigt alle verwalteten Rollen an | Übersicht aller konfigurierten Lock-Rollen |

### 📊 **Status & Informationen**
*Für alle Benutzer verfügbar*

| Befehl | Beschreibung | Details |
|--------|-------------|---------|
| `/help` | Zeigt Hilfe-Menü an | Vollständige Befehlsübersicht |

## 🎮 Typische Anwendungsfälle

### 🤖 **Pokemon-Bot-Server**
- Überwacht Raid-Bots, Trade-Bots, etc.
- Zeigt sofort wenn ein Bot offline geht
- Automatische Benachrichtigungen bei Problemen
- Wartungsmodus für geplante Updates


## 🚀 Download & Installation

### 📦 **Einfache Installation (Windows)**
1. Gehe zu [Releases](https://github.com/yourusername/Detektiv_Pikachu/releases)
2. Lade die neueste `DetektivPikachu-Windows-vX.X.X.zip` herunter
3. Entpacke und konfiguriere deine Bot-Tokens
4. Starte mit `start_both_bots.bat`

### 🐍 **Entwickler-Installation**
```bash
git clone https://github.com/yourusername/Detektiv_Pikachu.git
cd Detektiv_Pikachu
pip install -r requirements.txt
# Konfiguration in .env-Datei
python main.py
```

## 🤝 Community & Support

- 💬 **Discord Server**: [Pokemon Hideout](https://discord.gg/pokemonhideout)
- 🐛 **Bug Reports**: [GitHub Issues](https://github.com/yourusername/Detektiv_Pikachu/issues)
- 💡 **Feature Requests**: [GitHub Discussions](https://github.com/yourusername/Detektiv_Pikachu/discussions)
- 📖 **Wiki**: [Detaillierte Dokumentation](https://github.com/yourusername/Detektiv_Pikachu/wiki)

## 🙏 Credits

Besonderer Dank geht an [@bdawg1989](https://github.com/bdawg1989) für das ursprüngliche **PixelPatrol** Programm, welches als Grundlage für diesen Bot diente. Obwohl das ursprüngliche Repository nicht mehr verfügbar ist, bildete seine Arbeit das Fundament für die Entwicklung von Detektiv Pikachu.

Weitere Projekte von bdawg1989:
- [SVRaidBot](https://github.com/bdawg1989/SVRaidBot) - Pokémon Scarlet/Violet Raid Bot
- [PKHeX-ALL-IN-ONE](https://github.com/bdawg1989/PKHeX-ALL-IN-ONE) - Pokémon Save File Editor
- [GenPKM.com](https://genpkm.com) - Free Pokemon trades platform

## 📜 License

Dieses Projekt steht unter der [MIT License](LICENSE). Du kannst es frei verwenden, modifizieren und verteilen.

---

**⚡ Erstellt mit ❤️ für die Discord-Bot-Community**

*Tritt unserem [Discord Server](https://discord.gg/pokemonhideout) bei für Support, Updates und Community-Diskussionen!* 