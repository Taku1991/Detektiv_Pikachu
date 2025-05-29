import discord
import logging
import os
import asyncio
from typing import Optional, List, Tuple
from config.constants import BotConstants
from bot_status import BotStatus

logger = logging.getLogger('StatusBot')

class MessageManager:
    def __init__(self, bot):
        self.bot = bot
        self.message_ids = {}

    async def send_with_retry(
        self,
        channel: discord.TextChannel,
        embed: discord.Embed,
        gif_path: str,
        retries: int = BotConstants.MAX_RETRIES
    ) -> Optional[discord.Message]:
        """Send a message with retries on failure"""
        for attempt in range(retries):
            try:
                if os.path.exists(gif_path):
                    logger.info(f"Sending message with gif: {gif_path}")
                    return await channel.send(embed=embed, file=discord.File(gif_path))
                else:
                    logger.warning(f"GIF file not found: {gif_path}, sending embed only")
                    return await channel.send(embed=embed)
            except discord.errors.HTTPException as e:
                logger.warning(f"HTTP error when sending message (attempt {attempt + 1}/{retries}): {e}")
                if attempt == retries - 1:
                    logger.error(f"Failed to send message after {retries} attempts")
                    return None
                await asyncio.sleep(BotConstants.RETRY_DELAY)
            except Exception as e:
                logger.error(f"Unexpected error when sending message: {e}", exc_info=True)
                return None
        return None

    async def purge_bot_messages(self, channel: discord.TextChannel) -> List[discord.Message]:
        """Delete all bot messages in a channel"""
        try:
            # Hole alle Nachrichten im Kanal
            messages = []
            async for message in channel.history(limit=100):
                if message.author == self.bot.user:
                    messages.append(message)
            
            if messages:
                try:
                    # Versuche Bulk-Delete
                    await channel.delete_messages(messages)
                    logger.info(f"Successfully bulk deleted {len(messages)} messages")
                except discord.errors.HTTPException as e:
                    if e.code == 50034:  # Nachricht zu alt zum Bulk-Delete
                        logger.info("Messages too old for bulk delete, trying individual deletion")
                        for message in messages:
                            try:
                                await message.delete()
                                await asyncio.sleep(0.5)  # Kleine Verzögerung zwischen Löschungen
                            except Exception as delete_error:
                                logger.error(f"Error deleting individual message: {delete_error}")
                    else:
                        raise  # Andere HTTPException weitergeben
            
            return messages

        except discord.errors.Forbidden:
            logger.error(f"Bot doesn't have permission to delete messages in channel {channel.name}")
            return []
        except Exception as e:
            logger.error(f"Error purging messages in channel {channel.name}: {e}")
            return []

    async def create_status_embed(self, status: BotStatus, log_channel_id: str, guild_id: str) -> Tuple[discord.Embed, str]:
        """Create a status embed with the corresponding gif name"""
        try:
            # Hole den channel-spezifischen Owner oder den Standard-Admin
            owner_id = self.bot.channel_manager.get_channel_owner(guild_id, log_channel_id)
            owner_mention = f"<@{owner_id}>" if owner_id else f"<@{BotConstants.ADMIN_USER_ID}>"
            
            message = self.bot.config.status_messages[status].format(owner_mention=owner_mention)
            
            embed = discord.Embed(
                title="Bot Status Update",
                description=message,
                color=self.bot.config.status_colors[status],
                timestamp=discord.utils.utcnow()
            )
            
            gif_name = self.bot.config.status_gifs[status]
            embed.set_image(url=f"attachment://{gif_name}")
            
            return embed, gif_name
            
        except Exception as e:
            logger.error(f"Error creating status embed: {e}")
            raise

    def save_message_id(self, channel_id: str, message_id: int):
        """Save a message ID for a channel"""
        self.message_ids[channel_id] = message_id
        try:
            self.bot.data_manager.save_json(self.message_ids, "message_ids.json")
        except Exception as e:
            logger.error(f"Error saving message ID: {e}")

    async def edit_message(
        self,
        channel: discord.TextChannel,
        message_id: int,
        embed: discord.Embed,
        gif_path: str
    ) -> Optional[discord.Message]:
        """Edit an existing message with new content"""
        try:
            message = await channel.fetch_message(message_id)
            if message:
                if os.path.exists(gif_path):
                    await message.edit(embed=embed, attachments=[discord.File(gif_path)])
                else:
                    await message.edit(embed=embed)
                return message
        except discord.NotFound:
            logger.warning(f"Message {message_id} not found in channel {channel.name}")
        except discord.Forbidden:
            logger.error(f"Bot doesn't have permission to edit messages in channel {channel.name}")
        except Exception as e:
            logger.error(f"Error editing message: {e}")
        return None

    def load_data(self):
        """Load message related data"""
        self.message_ids = self.bot.data_manager.load_json("message_ids.json")
        logger.info(f"Message Manager: {len(self.message_ids)} gespeicherte Nachrichten-IDs geladen")
