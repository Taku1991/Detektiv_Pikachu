from enum import Enum

class BotStatus(Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    PROBLEM = "problem"
    MAINTENANCE = "maintenance"

    @classmethod
    def from_str(cls, status: str) -> 'BotStatus':
        """Convert string to BotStatus"""
        try:
            return cls(status.lower())
        except ValueError:
            raise ValueError(f"Invalid status: {status}. Valid values are: {', '.join([s.value for s in cls])}")
