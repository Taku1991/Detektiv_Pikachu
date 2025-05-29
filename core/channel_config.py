from dataclasses import dataclass, field
from typing import Dict
import discord
from bot_status import BotStatus
from config.constants import BotConstants

@dataclass
class ChannelConfig:
    status_emojis: Dict[BotStatus, str] = field(default_factory=lambda: {
        BotStatus.ONLINE: "✅",
        BotStatus.OFFLINE: "❌",
        BotStatus.PROBLEM: "❗",
        BotStatus.MAINTENANCE: BotConstants.MAINTENANCE_EMOJI
    })
    
    status_messages: Dict[BotStatus, str] = field(default_factory=lambda: {
        BotStatus.ONLINE: "Der Bot ist wieder Online! Viel Spaß!",
        BotStatus.OFFLINE: "Der Bot ist Offline! {owner_mention} kümmert sich um das Problem!",
        BotStatus.PROBLEM: "{owner_mention} Der Bot hat einen Fehler! Bitte beheben.",
        BotStatus.MAINTENANCE: "Es werden gerade Wartungsarbeiten durchgeführt, der Bot kommt so schnell wie möglich wieder online!"
    })
    
    status_colors: Dict[BotStatus, discord.Color] = field(default_factory=lambda: {
        BotStatus.ONLINE: discord.Color.green(),
        BotStatus.OFFLINE: discord.Color.red(),
        BotStatus.PROBLEM: discord.Color.red(),
        BotStatus.MAINTENANCE: discord.Color.blue()
    })
    
    status_gifs: Dict[BotStatus, str] = field(default_factory=lambda: {
        BotStatus.ONLINE: 'online.gif',
        BotStatus.OFFLINE: 'offline.gif',
        BotStatus.PROBLEM: 'problem.gif',
        BotStatus.MAINTENANCE: 'maintenance.gif'
    })