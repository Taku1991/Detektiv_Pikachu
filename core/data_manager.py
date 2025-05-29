import json
import logging
from pathlib import Path
from typing import Any, Union, Dict, List

logger = logging.getLogger('StatusBot')
logger.setLevel(logging.DEBUG)  # Debug-Level für detailliertere Logs

class DataManager:
    def __init__(self, data_dir: Path):
        """Initialize the DataManager with a data directory"""
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Initialized DataManager with directory: {data_dir}")

    def load_json(self, filename: str) -> Union[Dict, List, Any]:
        """Load data from a JSON file"""
        try:
            path = self.data_dir / "json" / filename  # Explizit json-Unterverzeichnis hinzufügen
            
            # Prüfe, ob die Datei existiert
            if not path.exists():
                fallback_path = self.data_dir / filename  # Versuche ohne json-Unterverzeichnis
                if fallback_path.exists():
                    path = fallback_path
                    logger.info(f"Datei {filename} im Hauptverzeichnis gefunden statt im json-Unterverzeichnis")
                else:
                    logger.warning(f"Datei {filename} existiert nicht unter {path} oder {fallback_path}")
                    return {}
            
            # Prüfe ob die Datei leer ist
            if path.stat().st_size == 0:
                logger.warning(f"Datei {filename} ist leer")
                return {}
                
            # Debug-Info
            logger.info(f"Lade JSON aus {path} (Dateigröße: {path.stat().st_size} Bytes)")
            
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                logger.info(f"Erfolgreich geladen: {filename} enthält {type(data).__name__} mit {len(data) if isinstance(data, (dict, list)) else 'N/A'} Elementen")
                return data
        except json.JSONDecodeError as e:
            logger.error(f"Fehler beim Dekodieren von JSON aus {filename}: {e}")
            return {}
        except UnicodeDecodeError as e:
            logger.error(f"Zeichenkodierungsfehler beim Lesen von {filename}: {e}")
            try:
                # Versuche mit Latin-1
                with open(self.data_dir / filename, 'r', encoding='latin-1') as f:
                    data = json.load(f)
                    logger.warning(f"Datei {filename} mit Latin-1-Kodierung geladen (sollte UTF-8 sein)")
                    return data
            except Exception as fallback_e:
                logger.error(f"Auch Fallback-Kodierung fehlgeschlagen: {fallback_e}")
                return {}
        except Exception as e:
            logger.error(f"Fehler beim Laden von {filename}: {e}")
            return {}

    def save_json(self, data: Union[Dict, List, Any], filename: str) -> bool:
        """Save data to a JSON file"""
        try:
            # Stelle sicher, dass das json-Verzeichnis existiert
            json_dir = self.data_dir / "json"
            json_dir.mkdir(parents=True, exist_ok=True)
            
            # Speichere im json-Unterverzeichnis
            path = json_dir / filename
            
            # Debug-Info
            logger.debug(f"Speichere JSON in {path}")
            
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
                
            # Überprüfe, ob die Datei erfolgreich geschrieben wurde
            if path.exists() and path.stat().st_size > 0:
                logger.info(f"Erfolgreich gespeichert: {filename} ({path.stat().st_size} Bytes)")
                return True
            else:
                logger.error(f"Datei {filename} wurde nicht korrekt geschrieben")
                return False
                
        except Exception as e:
            logger.error(f"Fehler beim Speichern von {filename}: {e}", exc_info=True)
            return False

    def delete_file(self, filename: str) -> bool:
        """Delete a file from the data directory"""
        try:
            path = self.data_dir / filename
            if path.exists():
                path.unlink()
                logger.debug(f"Successfully deleted {filename}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting {filename}: {e}")
            return False

    def list_files(self) -> List[str]:
        """List all files in the data directory"""
        try:
            return [f.name for f in self.data_dir.glob('*.json')]
        except Exception as e:
            logger.error(f"Error listing files: {e}")
            return []
