import logging
import os
import importlib
import asyncio
from pathlib import Path

logger = logging.getLogger('StatusBot')

async def setup_cogs(bot):
    """
    Lädt alle Cogs aus den Unterverzeichnissen des cogs-Ordners
    """
    logger.info("Lade Cogs...")
    
    # Verzeichnisse, die Cogs enthalten
    cog_dirs = ['admin', 'channel', 'system']
    
    # Sammle alle Cogs zum parallelen Laden
    cog_tasks = []
    
    # Lade Cogs aus allen Verzeichnissen
    for cog_dir in cog_dirs:
        cog_path = Path(__file__).parent / cog_dir
        
        if not cog_path.exists():
            logger.warning(f"Cog-Verzeichnis {cog_dir} nicht gefunden!")
            continue
            
        logger.debug(f"Durchsuche Cog-Verzeichnis: {cog_dir}")
        
        # Alle Python-Dateien im Verzeichnis finden
        cog_files = [f for f in cog_path.glob("*.py") if f.is_file() and f.name != "__init__.py"]
        
        for cog_file in cog_files:
            cog_name = cog_file.stem
            module_path = f"cogs.{cog_dir}.{cog_name}"
            
            # Erstelle Task für paralleles Laden
            cog_tasks.append(load_cog(bot, module_path))
    
    # Lade alle Cogs parallel
    if cog_tasks:
        results = await asyncio.gather(*cog_tasks, return_exceptions=True)
        
        # Auswertung der Ergebnisse
        loaded_count = 0
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Fehler beim Laden von Cog: {result}")
            else:
                loaded_count += 1
        
        logger.info(f"Erfolgreich {loaded_count} von {len(cog_tasks)} Cogs geladen")
    else:
        logger.warning("Keine Cogs zum Laden gefunden!")

async def load_cog(bot, module_path):
    """
    Lädt ein einzelnes Cog
    """
    try:
        await bot.load_extension(module_path)
        logger.debug(f"Cog geladen: {module_path}")
        return module_path
    except Exception as e:
        logger.error(f"Fehler beim Laden der Extension {module_path}: {e}")
        raise 