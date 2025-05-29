import re
from typing import List, Optional
from dataclasses import dataclass, field
import logging
from bot_status import BotStatus

logger = logging.getLogger('StatusBot')

@dataclass
class StatusPatterns:
    offline: List[str] = field(default_factory=lambda: [
        r'Ending PokeTrade',
        r'Disconnecting from device',
        r'Detaching controllers on routine exit',
        r'Ending RotatingRaidBotSV'
    ])
    
    online: List[str] = field(default_factory=lambda: [
        r'\bconnected\b',
        r'Starting main PokeTradeBot',
        r'Starting main',
        r'Connected',
        r'Detaching on startup',
        r'Bot startup',
        r'identified as',
        r'Connecting to lobby'
    ])
    
    error: List[str] = field(default_factory=lambda: [
        r'Error occurred during raid',
        r'Exception',
        r'Failed to connect',
        r'Failed to establish',
        r'Failed to initialize',
        r'Timeout',
        r'Connection refused',
        r'Unable to connect',
        r'Critical error',
    ])

    def get_status_emoji(self, status: BotStatus) -> str:
        """Gibt das entsprechende Emoji für einen Status zurück"""
        if status == BotStatus.ONLINE:
            return "✅"
        elif status == BotStatus.OFFLINE:
            return "❌"
        elif status == BotStatus.PROBLEM:
            return "❗"
        elif status == BotStatus.MAINTENANCE:
            return "🟦"
        else:
            return "❌"  # Standardmäßig offline

    def remove_status_emoji(self, channel_name: str) -> str:
        """Entfernt Status-Emojis vom Kanalnamen"""
        # Entferne alle bekannten Status-Emojis und den Separator
        return re.sub(r'^[✅❌❗🟦]+︱', '', channel_name)

    def check_patterns(self, content: str) -> Optional[BotStatus]:
        """Verbesserte Mustererkennung mit detailliertem Logging"""
        if not content:
            return None
            
        content = content.lower()
        logger.debug(f"Prüfe Muster für Nachricht: {content}")

        # Prüfe Muster mit detaillierterem Logging
        for pattern in self.offline:
            if re.search(pattern.lower(), content, re.IGNORECASE):
                logger.info(f"Offline-Muster '{pattern}' erkannt in Nachricht: {content[:100]}")
                return BotStatus.OFFLINE

        for pattern in self.error:
            if re.search(pattern.lower(), content, re.IGNORECASE):
                logger.info(f"Fehler-Muster '{pattern}' erkannt in Nachricht: {content[:100]}")
                return BotStatus.PROBLEM

        for pattern in self.online:
            if re.search(pattern.lower(), content, re.IGNORECASE):
                logger.info(f"Online-Muster '{pattern}' erkannt in Nachricht: {content[:100]}")
                return BotStatus.ONLINE

        logger.debug(f"Kein Muster gefunden für Nachricht: {content[:100]}")
        return None
