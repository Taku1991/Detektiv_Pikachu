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
        r'Disconnecting from device',  # Spezifisch für Device-Disconnect
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
        r'Connecting to lobby',
        r'Confirming trade',
        r'Disconnecting from trade',
        r'Exiting trade to overworld',
        r'Trade cancelled',
        r'Hey! Pick a Pokemon',
        r'Partner did not disconnect',
        r'Searching for trade',
        r'Trade partner found'
    ])

    error: List[str] = field(default_factory=lambda: [
        r'Error occurred during raid',
        r'Exception',
        r'Failed to connect',
        r'Failed to establish',
        r'Failed to initialize',
        r'Connection timeout',  # Spezifischer für Connection-Timeouts
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
        """Verbesserte Mustererkennung: Jede Aktivität = Online, außer bei expliziten Offline/Error-Mustern"""
        if not content:
            return None
            
        content_lower = content.lower()
        logger.debug(f"Prüfe Muster für Nachricht: {content}")

        # Prüfe zuerst Offline-Muster
        for pattern in self.offline:
            if re.search(pattern.lower(), content_lower, re.IGNORECASE):
                logger.info(f"Offline-Muster '{pattern}' erkannt in Nachricht: {content[:100]}")
                return BotStatus.OFFLINE

        # Prüfe Error-Muster
        for pattern in self.error:
            if re.search(pattern.lower(), content_lower, re.IGNORECASE):
                logger.info(f"Fehler-Muster '{pattern}' erkannt in Nachricht: {content[:100]}")
                return BotStatus.PROBLEM

        # Prüfe explizite Online-Muster
        for pattern in self.online:
            if re.search(pattern.lower(), content_lower, re.IGNORECASE):
                logger.info(f"Online-Muster '{pattern}' erkannt in Nachricht: {content[:100]}")
                return BotStatus.ONLINE

        # NEUE LOGIK: Jede andere Aktivität wird als Online betrachtet
        # Ausnahme: Sehr kurze oder irrelevante Nachrichten
        content_stripped = content.strip()
        if len(content_stripped) >= 10:  # Mindestens 10 Zeichen für relevante Aktivität
            logger.info(f"Bot-Aktivität erkannt (keine spezifischen Muster) -> Status: Online. Nachricht: {content[:100]}")
            return BotStatus.ONLINE

        logger.debug(f"Nachricht zu kurz oder irrelevant für Status-Update: {content[:100]}")
        return None
