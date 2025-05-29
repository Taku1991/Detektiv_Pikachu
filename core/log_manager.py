import logging
from logging.handlers import TimedRotatingFileHandler, RotatingFileHandler
import os
import gzip
import shutil
from datetime import datetime, timedelta
from pathlib import Path
import threading

class AdvancedLogManager:
    def __init__(self, 
                 log_dir: str = 'logs', 
                 max_days: int = 7,
                 max_file_size_mb: int = 50,
                 max_backup_count: int = 10,
                 compress_old_logs: bool = True):
        """
        Erweiterter Log-Manager mit automatischer Rotation, Kompression und Bereinigung
        
        Args:
            log_dir: Verzeichnis für Log-Dateien
            max_days: Maximale Anzahl Tage für Log-Aufbewahrung
            max_file_size_mb: Maximale Dateigröße in MB vor Rotation
            max_backup_count: Anzahl der Backup-Dateien
            compress_old_logs: Ob alte Logs komprimiert werden sollen
        """
        self.log_dir = Path(log_dir)
        self.max_days = max_days
        self.max_file_size_mb = max_file_size_mb
        self.max_backup_count = max_backup_count
        self.compress_old_logs = compress_old_logs
        
        # Erstelle Log-Verzeichnis
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Lock für Thread-sichere Operationen
        self._lock = threading.Lock()
        
        # Setup Logging
        self.setup_logging()
        
        # Starte Cleanup-Thread
        self.start_cleanup_thread()

    def setup_logging(self):
        """Konfiguriert das Logging-System mit Rotation"""
        # Entferne existierende Handler um Duplikate zu vermeiden
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # Base Logger konfigurieren
        root_logger.setLevel(logging.DEBUG)

    def create_logger(self, name: str, log_level: int = logging.INFO) -> logging.Logger:
        """
        Erstellt einen Logger mit automatischer Rotation
        
        Args:
            name: Name des Loggers (z.B. 'MainBot', 'HelperBot')
            log_level: Log-Level für Console-Output
            
        Returns:
            Konfigurierter Logger
        """
        logger = logging.getLogger(name)
        
        # Entferne existierende Handler um Duplikate zu vermeiden
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        
        logger.setLevel(logging.DEBUG)
        logger.propagate = False  # Verhindert Propagation zum Root-Logger
        
        # File Handler mit Größen-basierter Rotation
        log_file = self.log_dir / f"{name.lower()}.log"
        file_handler = RotatingFileHandler(
            filename=log_file,
            maxBytes=self.max_file_size_mb * 1024 * 1024,  # MB zu Bytes
            backupCount=self.max_backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        
        # Zeitbasierte Rotation zusätzlich implementieren
        timed_handler = TimedRotatingFileHandler(
            filename=self.log_dir / f"{name.lower()}_daily.log",
            when="midnight",
            interval=1,
            backupCount=self.max_days,
            encoding='utf-8'
        )
        timed_handler.setLevel(logging.INFO)
        
        # Custom Formatter mit mehr Details
        detailed_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
        )
        file_handler.setFormatter(detailed_formatter)
        timed_handler.setFormatter(detailed_formatter)
        
        # Console Handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        
        # Custom Rotator für Kompression
        if self.compress_old_logs:
            file_handler.rotator = self._compress_rotator
            timed_handler.rotator = self._compress_rotator
        
        # Handler hinzufügen
        logger.addHandler(file_handler)
        logger.addHandler(timed_handler)
        logger.addHandler(console_handler)
        
        # Discord Library Logging reduzieren
        discord_logger = logging.getLogger('discord')
        discord_logger.setLevel(logging.WARNING)
        
        aiohttp_logger = logging.getLogger('aiohttp')
        aiohttp_logger.setLevel(logging.WARNING)
        
        return logger

    def _compress_rotator(self, source, dest):
        """Komprimiert rotierte Log-Dateien"""
        try:
            with open(source, 'rb') as f_in:
                with gzip.open(f"{dest}.gz", 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            os.remove(source)
        except Exception as e:
            # Fallback: normale Rotation ohne Kompression
            shutil.move(source, dest)

    def start_cleanup_thread(self):
        """Startet einen Background-Thread für regelmäßige Bereinigung"""
        def cleanup_worker():
            import time
            while True:
                try:
                    self.cleanup_old_logs()
                    time.sleep(3600)  # Cleanup alle Stunde
                except Exception as e:
                    # Fehler beim Cleanup sollten den Bot nicht stoppen
                    pass
        
        cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
        cleanup_thread.start()

    def cleanup_old_logs(self):
        """Bereinigt alte Log-Dateien basierend auf Alter und Anzahl"""
        with self._lock:
            try:
                current_time = datetime.now()
                
                # Pattern für verschiedene Log-Dateien
                patterns = ['*.log', '*.log.*', '*.log.*.gz']
                
                for pattern in patterns:
                    for log_file in self.log_dir.glob(pattern):
                        try:
                            # Skip aktuelle Log-Dateien ohne Datum/Nummer im Namen
                            if not any(char.isdigit() for char in log_file.stem):
                                continue
                                
                            file_time = datetime.fromtimestamp(log_file.stat().st_mtime)
                            file_age = (current_time - file_time).days
                            
                            if file_age > self.max_days:
                                log_file.unlink()
                                print(f"🗑️ Alte Log-Datei gelöscht: {log_file.name} (Alter: {file_age} Tage)")
                                
                        except Exception as e:
                            # Einzelne Datei-Fehler sollten Cleanup nicht stoppen
                            continue
                            
                # Zusätzlich: Größen-basierte Bereinigung falls zu viele Dateien
                self._cleanup_by_count()
                
            except Exception as e:
                # Cleanup-Fehler sollten still sein
                pass

    def _cleanup_by_count(self):
        """Bereinigt überschüssige Log-Dateien basierend auf Anzahl"""
        try:
            # Gruppiere Dateien nach Logger-Namen
            log_groups = {}
            
            for log_file in self.log_dir.glob('*.log*'):
                base_name = log_file.name.split('.')[0]  # z.B. 'mainbot' aus 'mainbot.log.1'
                if base_name not in log_groups:
                    log_groups[base_name] = []
                log_groups[base_name].append(log_file)
            
            # Bereinige jede Gruppe
            for group_name, files in log_groups.items():
                # Sortiere nach Änderungszeit (neueste zuerst)
                files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
                
                # Behalte nur die neuesten Dateien
                max_files_per_logger = self.max_backup_count * 2  # Für beide Handler
                if len(files) > max_files_per_logger:
                    for old_file in files[max_files_per_logger:]:
                        try:
                            old_file.unlink()
                            print(f"🗑️ Überschüssige Log-Datei gelöscht: {old_file.name}")
                        except:
                            continue
                            
        except Exception:
            pass

    def get_log_stats(self) -> dict:
        """Gibt Statistiken über Log-Dateien zurück"""
        stats = {
            'total_files': 0,
            'total_size_mb': 0,
            'oldest_file': None,
            'newest_file': None,
            'compressed_files': 0
        }
        
        try:
            log_files = list(self.log_dir.glob('*.log*'))
            stats['total_files'] = len(log_files)
            
            if log_files:
                total_size = sum(f.stat().st_size for f in log_files)
                stats['total_size_mb'] = round(total_size / (1024 * 1024), 2)
                
                # Älteste und neueste Datei
                oldest = min(log_files, key=lambda f: f.stat().st_mtime)
                newest = max(log_files, key=lambda f: f.stat().st_mtime)
                
                stats['oldest_file'] = {
                    'name': oldest.name,
                    'age_days': (datetime.now() - datetime.fromtimestamp(oldest.stat().st_mtime)).days
                }
                
                stats['newest_file'] = {
                    'name': newest.name,
                    'age_hours': (datetime.now() - datetime.fromtimestamp(newest.stat().st_mtime)).total_seconds() / 3600
                }
                
                # Anzahl komprimierter Dateien
                stats['compressed_files'] = len([f for f in log_files if f.name.endswith('.gz')])
                
        except Exception:
            pass
            
        return stats

# Singleton-Instanz für globale Verwendung
_log_manager_instance = None

def get_log_manager(**kwargs) -> AdvancedLogManager:
    """
    Gibt die globale LogManager-Instanz zurück (Singleton)
    """
    global _log_manager_instance
    if _log_manager_instance is None:
        _log_manager_instance = AdvancedLogManager(**kwargs)
    return _log_manager_instance

def setup_bot_logging(bot_name: str, log_level: int = logging.INFO) -> logging.Logger:
    """
    Convenience-Funktion für Bot-Logging-Setup
    
    Args:
        bot_name: Name des Bots ('MainBot', 'HelperBot', etc.)
        log_level: Console-Log-Level
        
    Returns:
        Konfigurierter Logger
    """
    log_manager = get_log_manager()
    return log_manager.create_logger(bot_name, log_level)

# Beispielverwendung
if __name__ == "__main__":
    # Test des Log-Systems
    logger = setup_bot_logging('TestBot')
    
    logger.debug("Dies ist eine Debug-Nachricht")
    logger.info("Dies ist eine Info-Nachricht")
    logger.warning("Dies ist eine Warnung")
    logger.error("Dies ist eine Fehlermeldung")
    
    # Statistiken anzeigen
    log_manager = get_log_manager()
    stats = log_manager.get_log_stats()
    print(f"Log-Statistiken: {stats}")