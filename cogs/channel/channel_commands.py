import discord
from discord import app_commands
from typing import Optional
import logging
from discord.ext import commands
from bot_status import BotStatus

logger = logging.getLogger('StatusBot')

class ChannelCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="addchannels")
    @app_commands.checks.has_permissions(administrator=True)
    async def add_channels(
        self,
        interaction: discord.Interaction,
        log_channel: discord.TextChannel,
        update_channel: discord.TextChannel,
        owner: Optional[discord.Member] = None
    ):
        """
        Fügt einen Log- und Update-Kanal hinzu
        
        Parameters
        ----------
        log_channel : Der Kanal für Bot-Logs
        update_channel : Der Kanal für Status-Updates
        owner : Der Besitzer des Bots (optional)
        """
        try:
            guild_id = str(interaction.guild_id)
            
            existing_update = self.bot.channel_manager.get_update_channel(guild_id, str(log_channel.id))
            if existing_update:
                await interaction.response.send_message(
                    f"⚠️ Der Log-Kanal {log_channel.mention} ist bereits mit Update-Kanal <#{existing_update}> verbunden."
                )
                return

            owner_id = owner.id if owner else None
            self.bot.channel_manager.add_channel_pair(
                guild_id,
                str(log_channel.id),
                str(update_channel.id),
                owner_id
            )
            
            await self.bot.channel_manager.setup_update_channel(update_channel, BotStatus.ONLINE)
            
            response = f"✅ Erfolgreich verbunden:\nLog-Kanal: {log_channel.mention}\nUpdate-Kanal: {update_channel.mention}"
            if owner:
                response += f"\nBot-Owner: {owner.mention}"
            
            await interaction.response.send_message(response)
        
        except Exception as e:
            logger.error(f"Error adding channels: {e}", exc_info=True)
            await interaction.response.send_message("❌ Es gab einen Fehler beim Hinzufügen der Kanäle.")

    @app_commands.command(name="removechannels")
    @app_commands.checks.has_permissions(administrator=True)
    async def remove_channels(self, interaction: discord.Interaction, log_channel: discord.TextChannel):
        """Entfernt einen Log- und den zugehörigen Update-Kanal"""
        try:
            guild_id = str(interaction.guild_id)
            update_channel_id = self.bot.channel_manager.remove_channel_pair(guild_id, str(log_channel.id))
            
            if update_channel_id:
                if str(log_channel.id) in self.bot.status_manager.last_known_status:
                    del self.bot.status_manager.last_known_status[str(log_channel.id)]
                    self.bot.data_manager.save_json(self.bot.status_manager.last_known_status, "last_known_status.json")
                
                await interaction.response.send_message(
                    f"✅ Kanäle entfernt:\nLog-Kanal: {log_channel.mention}\nUpdate-Kanal: <#{update_channel_id}>"
                )
            else:
                await interaction.response.send_message(f"⚠️ Keine Konfiguration für {log_channel.mention} gefunden.")
                
        except Exception as e:
            logger.error(f"Error removing channels: {e}", exc_info=True)
            await interaction.response.send_message("❌ Es gab einen Fehler beim Entfernen der Kanäle.")

    @app_commands.command(name="exclude")
    @app_commands.checks.has_permissions(administrator=True)
    async def exclude_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """Schließt einen Kanal vom Inaktivitäts-Check aus"""
        try:
            channel_id = str(channel.id)
            if self.bot.channel_manager.exclude_channel(channel_id):
                await interaction.response.send_message(f"✅ {channel.mention} wird nun vom Inaktivitäts-Check ausgeschlossen.")
            else:
                await interaction.response.send_message(f"ℹ️ {channel.mention} ist bereits ausgeschlossen.")
        except Exception as e:
            logger.error(f"Error excluding channel: {e}", exc_info=True)
            await interaction.response.send_message("❌ Fehler beim Ausschließen des Kanals.")

    @app_commands.command(name="include")
    @app_commands.checks.has_permissions(administrator=True)
    async def include_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """Fügt einen Kanal wieder zum Inaktivitäts-Check hinzu"""
        try:
            channel_id = str(channel.id)
            if self.bot.channel_manager.include_channel(channel_id):
                await interaction.response.send_message(f"✅ {channel.mention} wird nun wieder vom Inaktivitäts-Check erfasst.")
            else:
                await interaction.response.send_message(f"ℹ️ {channel.mention} war nicht ausgeschlossen.")
        except Exception as e:
            logger.error(f"Error including channel: {e}", exc_info=True)
            await interaction.response.send_message("❌ Fehler beim Hinzufügen des Kanals.")

    @app_commands.command(name="listchannels")
    @app_commands.checks.has_permissions(administrator=True)
    async def list_channels(self, interaction: discord.Interaction):
        """Listet alle konfigurierten und ausgeschlossenen Kanäle auf"""
        try:
            guild_id = str(interaction.guild_id)
            
            embed = discord.Embed(
                title="📋 Konfigurierte Kanäle",
                color=discord.Color.blue(),
                timestamp=discord.utils.utcnow()
            )
            
            status_info = ""
            channel_pairs = self.bot.channel_manager.get_channel_pairs(guild_id)
            for pair in channel_pairs:
                log_id = pair['log_channel']
                update_id = pair['update_channel']
                status = self.bot.status_manager.last_known_status.get(log_id, "unbekannt")
                owner_id = self.bot.channel_manager.get_channel_owner(guild_id, log_id)
                owner_info = f" (Owner: <@{owner_id}>)" if owner_id else ""
                status_info += f"Log: <#{log_id}> → Update: <#{update_id}> (Status: {status}){owner_info}\n"
            
            embed.add_field(
                name="Eingerichtete Kanalpaare",
                value=status_info if status_info else "Keine Kanäle konfiguriert",
                inline=False
            )
            
            excluded = self.bot.channel_manager.get_excluded_channels()
            excluded_info = ""
            for channel_id in excluded:
                excluded_info += f"<#{channel_id}>\n"
                
            if excluded_info:
                embed.add_field(
                    name="Ausgeschlossene Kanäle (Inaktivitäts-Check)",
                    value=excluded_info,
                    inline=False
                )
                
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Error listing channels: {e}", exc_info=True)
            await interaction.response.send_message("❌ Fehler beim Auflisten der Kanäle.")
            
    @app_commands.command(name="addlockrole")
    @app_commands.checks.has_permissions(administrator=True)
    async def add_lock_role(self, interaction: discord.Interaction, role: discord.Role):
        """Fügt eine Rolle zur Liste der zu sperrenden Rollen hinzu"""
        try:
            guild_id = str(interaction.guild_id)
            role_id = str(role.id)
            
            if self.bot.channel_locker.add_lock_role(guild_id, role_id):
                await interaction.response.send_message(
                    f"✅ Die Rolle {role.mention} wird nun bei Bot-Problemen gesperrt/entsperrt.",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    f"ℹ️ Die Rolle {role.mention} ist bereits in der Sperrliste.",
                    ephemeral=True
                )
                
        except Exception as e:
            logger.error(f"Error adding lock role: {e}", exc_info=True)
            await interaction.response.send_message(
                "❌ Es gab einen Fehler beim Hinzufügen der Rolle.",
                ephemeral=True
            )

    @app_commands.command(name="removelockrole")
    @app_commands.checks.has_permissions(administrator=True)
    async def remove_lock_role(self, interaction: discord.Interaction, role: discord.Role):
        """Entfernt eine Rolle aus der Liste der zu sperrenden Rollen"""
        try:
            guild_id = str(interaction.guild_id)
            role_id = str(role.id)
            
            if self.bot.channel_locker.remove_lock_role(guild_id, role_id):
                await interaction.response.send_message(
                    f"✅ Die Rolle {role.mention} wird nicht mehr bei Bot-Problemen gesperrt/entsperrt.",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    f"ℹ️ Die Rolle {role.mention} war nicht in der Sperrliste.",
                    ephemeral=True
                )
                
        except Exception as e:
            logger.error(f"Error removing lock role: {e}", exc_info=True)
            await interaction.response.send_message(
                "❌ Es gab einen Fehler beim Entfernen der Rolle.",
                ephemeral=True
            )

    @app_commands.command(name="listlockroles")
    @app_commands.checks.has_permissions(administrator=True)
    async def list_lock_roles(self, interaction: discord.Interaction):
        """Zeigt alle Rollen an, die bei Offline/Problem gesperrt werden"""
        try:
            guild_id = str(interaction.guild_id)
            role_ids = self.bot.channel_locker.get_lock_roles(guild_id)
            
            if not role_ids:
                await interaction.response.send_message(
                    "ℹ️ Keine Rollen für automatische Sperrung konfiguriert.",
                    ephemeral=True
                )
                return
                
            guild = interaction.guild
            embed = discord.Embed(
                title="🔒 Zu sperrende Rollen",
                description="Diese Rollen werden bei Bot-Problemen gesperrt/entsperrt:",
                color=discord.Color.blue()
            )
            
            role_text = ""
            for role_id in role_ids:
                role = guild.get_role(int(role_id))
                role_name = role.name if role else f"Unbekannte Rolle (ID: {role_id})"
                role_text += f"• {role.mention if role else role_name}\n"
                
            embed.add_field(name="Konfigurierte Rollen", value=role_text, inline=False)
            embed.set_footer(text=f"Server: {guild.name}")
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error listing lock roles: {e}", exc_info=True)
            await interaction.response.send_message(
                "❌ Es gab einen Fehler beim Auflisten der Rollen.",
                ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(ChannelCommands(bot)) 