#!/usr/bin/env python3
"""
Detektiv Pikachu Bot API Server
Stellt UPDATE-Channel-Status-Daten für externe Webseiten bereit
Fokus auf Online, Offline, Problem, Wartung Status

WICHTIG: Die API zeigt UPDATE-Channels an, nicht Log-Channels!
- Log-Channels: Werden überwacht für Bot-Nachrichten
- Update-Channels: Werden für Nutzer sichtbar und status-aktualisiert
"""

import json
import time
import threading
from datetime import datetime
from pathlib import Path
from flask import Flask, jsonify, request
from flask_cors import CORS
import logging
import sys
import os
import signal
from functools import wraps

# Importiere Bot-Module
try:
    from config.constants import BotConstants
    from core.bot_core import StatusBot
except ImportError as e:
    print(f"Import-Fehler: {e}")
    sys.exit(1)

# Flask-App erstellen
app = Flask(__name__)
CORS(app)  # Erlaubt Cross-Origin-Requests

# Logging für API
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('BotAPI')

# Cache für Bot-Status
status_cache = {}
cache_timestamp = 0
CACHE_DURATION = 30

# Timeout-Decorator
def timeout_handler(func):
    """Decorator für Funktions-Timeouts - Windows-kompatibel"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        import threading
        import time
        
        result = [None]
        exception = [None]
        
        def target():
            try:
                result[0] = func(*args, **kwargs)
            except Exception as e:
                exception[0] = e
        
        # Starte Thread mit Timeout
        thread = threading.Thread(target=target)
        thread.daemon = True
        thread.start()
        thread.join(timeout=10)
        
        if thread.is_alive():
            print(f"❌ Timeout bei {func.__name__}")
            raise TimeoutError("Funktion dauerte zu lange")
        
        if exception[0]:
            raise exception[0]
        
        return result[0]
    return wrapper

def load_json_file_safe(file_path, timeout=5):
    """Lädt eine JSON-Datei sicher mit Timeout-Schutz."""
    try:
        if not os.path.exists(file_path):
            print(f"⚠️ Datei {file_path} existiert nicht")
            return {}
        
        # Prüfe ob die Datei leer ist
        file_size = os.path.getsize(file_path)
        if file_size == 0:
            print(f"⚠️ Datei {file_path} ist leer")
            return {}
            
        # Größe-Check für Performance
        if file_size > 1024 * 1024:  # 1MB
            print(f"⚠️ Datei {file_path} ist sehr groß ({file_size} bytes)")
            
        # Zeitüberwachung
        start_time = time.time()
        
        # Schneller UTF-8 Load
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            load_time = time.time() - start_time
            
            if load_time > timeout:
                print(f"⚠️ {file_path} lud langsam ({load_time:.2f}s)")
                
            print(f"✅ {file_path}: {len(data) if isinstance(data, (dict, list)) else 'N/A'} Elemente in {load_time:.2f}s")
            return data
            
        except UnicodeDecodeError:
            print(f"❌ Unicode-Fehler in {file_path}")
            return {}
        except json.JSONDecodeError as e:
            print(f"❌ JSON-Fehler in {file_path}: {str(e)[:100]}...")
            return {}
            
    except Exception as e:
        print(f"❌ Kritischer Fehler bei {file_path}: {str(e)[:100]}...")
        return {}

def save_json_file(file_path, data):
    """Speichert Daten in eine JSON-Datei mit UTF-8 Encoding."""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"❌ Fehler beim Speichern von {file_path}: {e}")
        return False

@timeout_handler
def get_bot_status():
    """Lädt den aktuellen Bot-Status - optimiert mit Timeout-Schutz."""
    global status_cache, cache_timestamp
    
    current_time = datetime.now().timestamp()
    
    # Verwende Cache wenn noch gültig
    if current_time - cache_timestamp < CACHE_DURATION and status_cache:
        print(f"🔄 Cache verwendet - Alter: {current_time - cache_timestamp:.1f}s")
        return status_cache
    
    try:
        print("📋 Starte Bot-Status-Ladung (optimiert)...")
        start_time = time.time()
        
        # Lade die kritischen JSON-Dateien
        last_known_status = {}
        guild_channels = {}
        
        print("🔍 Lade last_known_status.json...")
        try:
            last_known_status = load_json_file_safe('data/json/last_known_status.json', timeout=3)
            print(f"✅ last_known_status.json: {len(last_known_status)} Log-Channels")
        except Exception as e:
            print(f"❌ Fehler bei last_known_status.json: {e}")
            last_known_status = {}
            
        print("🔍 Lade guild_channels.json...")
        try:
            guild_channels = load_json_file_safe('data/json/guild_channels.json', timeout=3)
            print(f"✅ guild_channels.json: {len(guild_channels)} Guilds")
        except Exception as e:
            print(f"❌ Fehler bei guild_channels.json: {e}")
            guild_channels = {}
        
        print("📊 Erstelle optimierte Update-Channel-Liste...")
        
        # Sammle alle UPDATE-Channels (die sichtbaren Channels)
        all_channels = {}
        total_channels = 0
        
        # Gehe durch alle Guild-Channels und sammle Update-Channels
        if guild_channels:
            for guild_id, channels in guild_channels.items():
                for log_channel_id, update_data in channels.items():
                    # Hole Status vom Log-Channel
                    log_status = last_known_status.get(str(log_channel_id), 'offline')
                    
                    # Unterstütze sowohl alte (str) als auch neue (list) Struktur
                    update_channel_ids = []
                    if isinstance(update_data, str):
                        update_channel_ids = [update_data]
                    elif isinstance(update_data, list):
                        update_channel_ids = update_data
                    
                    # Erstelle Einträge für alle Update-Channels
                    for update_channel_id in update_channel_ids:
                        update_channel_id_str = str(update_channel_id)
                        all_channels[update_channel_id_str] = {
                            'id': update_channel_id_str,
                            'name': f'Channel {update_channel_id_str}',
                            'status': log_status,  # Status vom Log-Channel
                            'guild_id': guild_id,
                            'log_channel_id': str(log_channel_id),  # Referenz zum Log-Channel
                            'type': 'update_channel'
                        }
                        total_channels += 1
        else:
            print("⚠️ Keine guild_channels.json Daten - Fallback zu Log-Channels")
            # Fallback: Zeige Log-Channels wenn keine guild_channels verfügbar
            for log_channel_id, status in last_known_status.items():
                channel_id_str = str(log_channel_id)
                all_channels[channel_id_str] = {
                    'id': channel_id_str,
                    'name': f'Log-Channel {channel_id_str}',
                    'status': status,
                    'guild_id': 'unknown',
                    'log_channel_id': channel_id_str,
                    'type': 'log_channel_fallback'
                }
                total_channels += 1
        
        print(f"📊 Berechne Statistiken für {total_channels} Channels...")
        
        # Statistiken berechnen - optimiert mit Counter
        status_counts = {'online': 0, 'offline': 0, 'problem': 0, 'maintenance': 0}
        
        for channel in all_channels.values():
            status = channel.get('status', 'offline')
            if status in status_counts:
                status_counts[status] += 1
        
        # Prozentsätze berechnen
        status_percentages = {}
        if total_channels > 0:
            for status, count in status_counts.items():
                status_percentages[status] = round((count / total_channels) * 100, 1)
        else:
            status_percentages = {'online': 0.0, 'offline': 0.0, 'problem': 0.0, 'maintenance': 0.0}
        
        # Status-Daten zusammenstellen
        status_data = {
            'channels': all_channels,
            'summary': {
                'total_channels': total_channels,
                'status_counts': status_counts,
                'status_percentages': status_percentages
            },
            'last_updated': datetime.now().isoformat()
        }
        
        # Cache aktualisieren
        status_cache = status_data
        cache_timestamp = current_time
        
        processing_time = time.time() - start_time
        channel_type = "Update-Channels" if guild_channels else "Log-Channels (Fallback)"
        print(f"✅ Bot-Status geladen: {total_channels} {channel_type} in {processing_time:.2f}s")
        
        return status_data
        
    except TimeoutError:
        print("❌ Timeout beim Laden des Bot-Status")
        return create_fallback_response("Timeout beim Laden der Bot-Status-Daten")
    except Exception as e:
        print(f"❌ Kritischer Fehler beim Laden des Bot-Status: {e}")
        import traceback
        traceback.print_exc()
        return create_fallback_response(f"Fehler beim Laden der Bot-Status-Daten: {str(e)}")

def create_fallback_response(error_message):
    """Erstellt eine Fallback-Antwort bei Fehlern"""
    return {
        'error': error_message,
        'channels': {},
        'summary': {
            'total_channels': 0,
            'status_counts': {'online': 0, 'offline': 0, 'problem': 0, 'maintenance': 0},
            'status_percentages': {'online': 0.0, 'offline': 0.0, 'problem': 0.0, 'maintenance': 0.0}
        },
        'last_updated': datetime.now().isoformat()
    }

# API-Endpunkte

@app.route('/api/status', methods=['GET'])
def get_status():
    """Hauptendpunkt für Bot-Status mit Timeout-Schutz"""
    try:
        status_data = get_bot_status()
        
        # Prüfe auf Fehler
        if 'error' in status_data:
            return jsonify(status_data), 500
            
        return jsonify(status_data)
    except Exception as e:
        print(f"❌ API-Fehler in /api/status: {e}")
        return jsonify(create_fallback_response(f"API-Fehler: {str(e)}")), 500

@app.route('/api/status/summary', methods=['GET'])
def get_status_summary():
    """Kurze Zusammenfassung des Bot-Status"""
    try:
        full_status = get_bot_status()
        
        if 'error' in full_status:
            return jsonify(full_status), 500
        
        summary = full_status.get('summary', {})
        
        return jsonify({
            'total_channels': summary.get('total_channels', 0),
            'status_counts': summary.get('status_counts', {}),
            'status_percentages': summary.get('status_percentages', {}),
            'last_updated': full_status.get('last_updated', datetime.now().isoformat())
        })
    except Exception as e:
        print(f"❌ API-Fehler in /api/status/summary: {e}")
        return jsonify(create_fallback_response(f"API-Fehler: {str(e)}")), 500

@app.route('/api/status/channels', methods=['GET'])
def get_channels():
    """Detaillierte Channel-Informationen"""
    try:
        full_status = get_bot_status()
        
        if 'error' in full_status:
            return jsonify(full_status), 500
        
        # Filter-Parameter
        status_filter = request.args.get('status')
        
        channels = full_status.get('channels', {})
        
        # Konvertiere Dict zu Liste
        channels_list = list(channels.values())
        
        if status_filter:
            channels_list = [ch for ch in channels_list if ch['status'] == status_filter]
        
        return jsonify({
            'last_updated': full_status.get('last_updated', datetime.now().isoformat()),
            'channels': channels_list,
            'total': len(channels_list),
            'filtered_by': status_filter if status_filter else None
        })
    except Exception as e:
        print(f"❌ API-Fehler in /api/status/channels: {e}")
        return jsonify(create_fallback_response(f"API-Fehler: {str(e)}")), 500

@app.route('/api/status/channel/<channel_id>', methods=['GET'])
def get_channel_status(channel_id):
    """Status eines spezifischen Channels"""
    try:
        full_status = get_bot_status()
        
        if 'error' in full_status:
            return jsonify(full_status), 500
        
        # Suche Channel
        channels = full_status.get('channels', {})
        channel = channels.get(channel_id)
        
        if not channel:
            return jsonify({
                'error': f'Channel {channel_id} nicht gefunden',
                'last_updated': datetime.now().isoformat()
            }), 404
        
        return jsonify(channel)
    except Exception as e:
        print(f"❌ API-Fehler in /api/status/channel/{channel_id}: {e}")
        return jsonify(create_fallback_response(f"API-Fehler: {str(e)}")), 500

@app.route('/api/test', methods=['GET'])
def test_endpoint():
    """Schneller Test-Endpunkt"""
    return jsonify({
        'status': 'ok',
        'message': 'API läuft',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/status/quick', methods=['GET'])
def get_quick_status():
    """Schneller Status ohne komplexe Verarbeitung - empfohlen für Homepage"""
    try:
        print("⚡ Schneller Status-Abruf...")
        start_time = time.time()
        
        # Lade beide JSON-Dateien - minimal
        last_known_status = load_json_file_safe('data/json/last_known_status.json', timeout=2)
        guild_channels = load_json_file_safe('data/json/guild_channels.json', timeout=2)
        
        if not last_known_status or not guild_channels:
            return jsonify({
                'error': 'Keine Status-Daten verfügbar',
                'total_channels': 0,
                'status_counts': {'online': 0, 'offline': 0, 'problem': 0, 'maintenance': 0},
                'status_percentages': {'online': 0.0, 'offline': 0.0, 'problem': 0.0, 'maintenance': 0.0},
                'last_updated': datetime.now().isoformat()
            }), 503
        
        # Zähle Update-Channels und deren Status
        total = 0
        status_counts = {'online': 0, 'offline': 0, 'problem': 0, 'maintenance': 0}
        
        if guild_channels:
            for guild_id, channels in guild_channels.items():
                for log_channel_id, update_data in channels.items():
                    # Hole Status vom Log-Channel
                    log_status = last_known_status.get(str(log_channel_id), 'offline')
                    
                    # Unterstütze sowohl alte (str) als auch neue (list) Struktur
                    update_channel_ids = []
                    if isinstance(update_data, str):
                        update_channel_ids = [update_data]
                    elif isinstance(update_data, list):
                        update_channel_ids = update_data
                    
                    # Zähle alle Update-Channels
                    for _ in update_channel_ids:
                        total += 1
                        if log_status in status_counts:
                            status_counts[log_status] += 1
        else:
            print("⚠️ Keine guild_channels.json Daten - Fallback zu Log-Channels")
            # Fallback: Zähle Log-Channels
            for status in last_known_status.values():
                total += 1
                if status in status_counts:
                    status_counts[status] += 1
        
        # Prozentsätze
        status_percentages = {}
        if total > 0:
            for status, count in status_counts.items():
                status_percentages[status] = round((count / total) * 100, 1)
        else:
            status_percentages = {'online': 0.0, 'offline': 0.0, 'problem': 0.0, 'maintenance': 0.0}
        
        processing_time = time.time() - start_time
        channel_type = "Update-Channels" if guild_channels else "Log-Channels (Fallback)"
        print(f"⚡ Schneller Status in {processing_time:.2f}s - {total} {channel_type}")
        
        return jsonify({
            'total_channels': total,
            'status_counts': status_counts,
            'status_percentages': status_percentages,
            'last_updated': datetime.now().isoformat(),
            'processing_time': f"{processing_time:.2f}s"
        })
        
    except Exception as e:
        print(f"❌ Fehler im schnellen Status: {e}")
        return jsonify({
            'error': f'Fehler beim Abrufen des schnellen Status: {str(e)}',
            'total_channels': 0,
            'status_counts': {'online': 0, 'offline': 0, 'problem': 0, 'maintenance': 0},
            'status_percentages': {'online': 0.0, 'offline': 0.0, 'problem': 0.0, 'maintenance': 0.0},
            'last_updated': datetime.now().isoformat()
        }), 500

@app.route('/api/status/simple', methods=['GET'])
def get_simple_status():
    """Einfacher Status mit Channel-IDs und Status - PERFEKT für Homepage-Widgets"""
    try:
        start_time = time.time()
        full_status = get_bot_status()
        
        if 'error' in full_status:
            return jsonify(full_status), 500
        
        # Versuche Channel-Namen zu laden
        channel_names = {}
        try:
            names_data = load_json_file_safe('data/json/guild_channels_with_names.json', timeout=2)
            if names_data:
                for guild_id, categories in names_data.items():
                    for category_id, channels in categories.items():
                        for channel_id, channel_info in channels.items():
                            channel_names[channel_id] = channel_info.get('name', f'Channel {channel_id}')
        except Exception as e:
            print(f"⚠️ Konnte Channel-Namen nicht laden: {e}")
        
        # Erstelle einfache Channel-Liste mit ID und Status
        channels = full_status.get('channels', {})
        simple_channels = []
        
        for channel_id, channel_data in channels.items():
            # Verwende gespeicherte Namen wenn verfügbar
            channel_name = channel_names.get(channel_id, f'Channel {channel_id}')
            
            simple_channels.append({
                'id': channel_id,
                'status': channel_data.get('status', 'unknown'),
                'name': channel_name,
                'type': channel_data.get('type', 'update_channel'),
                'log_channel_id': channel_data.get('log_channel_id', 'unknown')
            })
        
        # Sortiere nach Status (online zuerst)
        status_priority = {'online': 0, 'offline': 1, 'problem': 2, 'maintenance': 3}
        simple_channels.sort(key=lambda x: status_priority.get(x['status'], 4))
        
        summary = full_status.get('summary', {})
        processing_time = f"{time.time() - start_time:.3f}s"
        
        return jsonify({
            'channels': simple_channels,
            'total_channels': summary.get('total_channels', 0),
            'status_counts': summary.get('status_counts', {}),
            'status_percentages': summary.get('status_percentages', {}),
            'last_updated': full_status.get('last_updated', datetime.now().isoformat()),
            'processing_time': processing_time
        })
    except Exception as e:
        print(f"❌ API-Fehler in /api/status/simple: {e}")
        return jsonify(create_fallback_response(f"API-Fehler: {str(e)}")), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Gesundheitsprüfung der API"""
    try:
        # Teste grundlegende Funktionalität
        test_file = 'data/json/last_known_status.json'
        file_accessible = os.path.exists(test_file)
        
        return jsonify({
            'status': 'healthy',
            'file_access': file_accessible,
            'cache_age': time.time() - cache_timestamp if cache_timestamp > 0 else 0,
            'timestamp': datetime.now().isoformat(),
            'api_version': '1.1.0'
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/info', methods=['GET'])
def api_info():
    """API-Informationen"""
    return jsonify({
        'name': 'Detektiv Pikachu Bot API',
        'version': '1.2.0',
        'description': 'Stellt Update-Channel-Status-Daten für externe Webseiten bereit (Korrigiert)',
        'endpoints': {
            '/api/status/simple': 'Update-Channel-IDs + Status (EMPFOHLEN für Homepage)',
            '/api/status/quick': 'Schneller Status-Überblick für Update-Channels',
            '/api/status': 'Kompletter Update-Channel-Status',
            '/api/status/summary': 'Status-Zusammenfassung für Update-Channels',
            '/api/status/channels': 'Update-Channel-Liste (mit ?status=online Filter)',
            '/api/status/channel/<id>': 'Einzelner Update-Channel-Status',
            '/api/health': 'API-Gesundheitsprüfung',
            '/api/info': 'API-Informationen'
        },
        'recommended_endpoint': '/api/status/simple',
        'status_types': ['online', 'offline', 'problem', 'maintenance'],
        'cache_duration': CACHE_DURATION,
        'channel_types': {
            'log_channels': 'Channels die überwacht werden (nicht in API)',
            'update_channels': 'Channels die für Nutzer sichtbar sind (in API)'
        },
        'note': 'API zeigt jetzt UPDATE-Channels an, nicht Log-Channels',
        'timestamp': datetime.now().isoformat()
    })

if __name__ == '__main__':
    logger.info("Starte Detektiv Pikachu Bot API Server (Update-Channels)...")
    
    # Standardmäßig auf Port 7000, kann überschrieben werden
    port = int(os.getenv('API_PORT', 7000))
    host = os.getenv('API_HOST', '0.0.0.0')  # Wichtig: 0.0.0.0 für externe Zugriffe
    debug = os.getenv('API_DEBUG', 'false').lower() == 'true'
    
    print(f"🚀 API Server startet auf {host}:{port}")
    print(f"📊 Cache-Dauer: {CACHE_DURATION} Sekunden")
    print(f"⚡ Empfohlener Endpunkt für Homepage: /api/status/simple")
    print(f"🌐 Zugriff von extern: http://{host}:{port}/api/status/simple")
    print(f"🎯 API zeigt jetzt UPDATE-Channels an (sichtbar für Nutzer)")
    print("=" * 50)
    
    # Prüfe ob Data-Ordner existiert
    if not os.path.exists('data/json'):
        print("⚠️ Warnung: data/json Ordner nicht gefunden!")
        print("📁 Erstelle leere Datenstruktur...")
        os.makedirs('data/json', exist_ok=True)
        
        # Erstelle eine leere last_known_status.json
        with open('data/json/last_known_status.json', 'w') as f:
            json.dump({}, f)
        print("✅ Leere Datenstruktur erstellt")
    
    app.run(host=host, port=port, debug=debug, threaded=True) 