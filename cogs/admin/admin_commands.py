import discord
from discord import app_commands
from typing import Optional
import logging
from discord.ext import commands
from bot_status import BotStatus
from datetime import datetime

logger = logging.getLogger('StatusBot')

class AdminCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="sethistory")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_history_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """Setzt den History-Channel für Status-Änderungen"""
        try:
            # Setze die Channel ID
            self.bot.history_channel_id = channel.id
            
            # Speichere in der JSON
            history_data = {"history_channel": channel.id}
            self.bot.data_manager.save_json(history_data, "history_channel.json")
            
            await interaction.response.send_message(
                f"✅ History Channel wurde auf {channel.mention} gesetzt",
                ephemeral=True
            )
            logger.info(f"History Channel gesetzt auf: {channel.id} ({channel.name})")
            
        except Exception as e:
            logger.error(f"Error setting history channel: {e}", exc_info=True)
            await interaction.response.send_message(
                "❌ Es gab einen Fehler beim Setzen des History Channels",
                ephemeral=True
            )

    @app_commands.command(name="toggle")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.choices(status=[
        app_commands.Choice(name="Online", value="online"),
        app_commands.Choice(name="Offline", value="offline"),
        app_commands.Choice(name="Problem", value="problem"),
        app_commands.Choice(name="Wartung", value="wartung")
    ])
    async def toggle_status(self, interaction: discord.Interaction, status: app_commands.Choice[str]):
        """Ändert den Bot-Status manuell"""
        try:
            # Sofort eine Antwort senden
            await interaction.response.defer(ephemeral=True)
            
            guild_id = str(interaction.guild_id)
            channel_id = str(interaction.channel_id)
            
            log_channel_id = self.bot.channel_manager.get_log_channel(guild_id, channel_id)
            if not log_channel_id:
                await interaction.followup.send(
                    "⚠️ Dieser Befehl muss in einem Update-Channel verwendet werden.",
                    ephemeral=True
                )
                return
            
            try:
                if status.value.lower() == "wartung":
                    new_status = BotStatus.MAINTENANCE
                else:
                    new_status = BotStatus[status.value.upper()]
                    
                reason = f"Manueller Toggle durch {interaction.user.name} ({interaction.user.id})"
                await self.bot.status_manager.update_status(log_channel_id, new_status, reason)
                await interaction.followup.send(
                    f"✅ Status erfolgreich auf `{new_status.value}` geändert.",
                    ephemeral=True
                )
                
            except (KeyError, ValueError):
                await interaction.followup.send(
                    "⚠️ Ein unerwarteter Fehler ist beim Status-Update aufgetreten.",
                    ephemeral=True
                )
                
        except Exception as e:
            logger.error(f"Error in toggle command: {e}", exc_info=True)
            try:
                await interaction.followup.send(
                    "❌ Ein Fehler ist aufgetreten. Bitte überprüfe die Logs.",
                    ephemeral=True
                )
            except discord.errors.NotFound:
                pass

    @app_commands.command(name="balancerstatus")
    @app_commands.checks.has_permissions(administrator=True)
    async def balancer_status(self, interaction: discord.Interaction):
        """Zeigt den aktuellen Status des Token-Balancers an"""
        try:
            if not hasattr(self.bot, 'token_balancer'):
                await interaction.response.send_message(
                    "⚠️ Dieser Bot verwendet keinen Token-Balancer.",
                    ephemeral=True
                )
                return
                
            balancer = self.bot.token_balancer
            
            embed = discord.Embed(
                title="🔄 Token Balancer Status",
                color=discord.Color.blue(),
                description=f"Status: {balancer.get_status_text()}"
            )
            
            # Füge weitere Informationen hinzu
            if not balancer.using_primary:
                current_time = discord.utils.utcnow()
                # Umwandlung in timestamp für Unix-Zeit
                unblock_time = current_time.timestamp() + max(0, balancer.primary_blocked_until - int(discord.utils.utcnow().timestamp()))
                embed.add_field(
                    name="Primärer Bot wird freigeschaltet",
                    value=f"<t:{int(unblock_time)}:R>",
                    inline=False
                )
                
            embed.add_field(
                name="Verbindungsversuche",
                value=f"{balancer.retry_count}/{balancer.max_retries}",
                inline=True
            )
            
            embed.add_field(
                name="Cooldown-Zeit",
                value=f"{balancer.cooldown_time} Sekunden",
                inline=True
            )
            
            if balancer.gradual_return_chance > 0:
                embed.add_field(
                    name="Graduelle Rückkehr",
                    value=f"{balancer.gradual_return_chance:.1%} Chance",
                    inline=True
                )
                
            embed.set_footer(text=f"Abgefragt von {interaction.user.name}")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error in balancer status command: {e}", exc_info=True)
            await interaction.response.send_message(
                "❌ Fehler beim Abrufen des Balancer-Status.",
                ephemeral=True
            )

    @app_commands.command(name="logstats", description="Zeigt Log-Datei-Statistiken an")
    @app_commands.describe()
    async def log_stats(self, interaction: discord.Interaction):
        """Zeigt Statistiken über Log-Dateien an"""
        try:
            from core.log_manager import get_log_manager
            
            log_manager = get_log_manager()
            stats = log_manager.get_log_stats()
            
            embed = discord.Embed(
                title="📊 Log-Datei-Statistiken",
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            
            # Grundlegende Statistiken
            embed.add_field(
                name="📁 Dateien",
                value=f"**Gesamt:** {stats['total_files']}\n**Komprimiert:** {stats['compressed_files']}",
                inline=True
            )
            
            embed.add_field(
                name="💾 Speicherplatz",
                value=f"**Gesamt:** {stats['total_size_mb']} MB",
                inline=True
            )
            
            # Älteste und neueste Datei
            if stats['oldest_file']:
                embed.add_field(
                    name="⏰ Älteste Datei",
                    value=f"**{stats['oldest_file']['name']}**\n{stats['oldest_file']['age_days']} Tage alt",
                    inline=True
                )
            
            if stats['newest_file']:
                embed.add_field(
                    name="🕐 Neueste Datei",
                    value=f"**{stats['newest_file']['name']}**\n{stats['newest_file']['age_hours']:.1f} Stunden alt",
                    inline=True
                )
            
            # Zusatzinformationen
            embed.add_field(
                name="⚙️ Konfiguration",
                value="• **Max Dateigröße:** 50 MB\n• **Aufbewahrung:** 7 Tage\n• **Kompression:** Aktiviert\n• **Rotation:** Automatisch",
                inline=False
            )
            
            embed.set_footer(text="Log-Rotation erfolgt automatisch bei Größen- oder Zeitlimits")
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            embed = discord.Embed(
                title="❌ Fehler",
                description=f"Fehler beim Abrufen der Log-Statistiken: {str(e)}",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="cleanlogs", description="Startet manuelle Log-Bereinigung")
    @app_commands.describe()
    async def clean_logs(self, interaction: discord.Interaction):
        """Startet eine manuelle Log-Bereinigung"""
        try:
            from core.log_manager import get_log_manager
            
            # Defer für längere Operation
            await interaction.response.defer(ephemeral=True)
            
            log_manager = get_log_manager()
            
            # Statistiken vor Bereinigung
            stats_before = log_manager.get_log_stats()
            
            # Bereinigung durchführen
            log_manager.cleanup_old_logs()
            
            # Statistiken nach Bereinigung
            stats_after = log_manager.get_log_stats()
            
            files_removed = stats_before['total_files'] - stats_after['total_files']
            space_freed = stats_before['total_size_mb'] - stats_after['total_size_mb']
            
            embed = discord.Embed(
                title="🧹 Log-Bereinigung abgeschlossen",
                color=discord.Color.green(),
                timestamp=datetime.now()
            )
            
            embed.add_field(
                name="📁 Dateien entfernt",
                value=f"**{files_removed}** Dateien",
                inline=True
            )
            
            embed.add_field(
                name="💾 Speicher befreit",
                value=f"**{space_freed:.2f} MB**",
                inline=True
            )
            
            embed.add_field(
                name="📊 Verbleibend",
                value=f"**{stats_after['total_files']}** Dateien\n**{stats_after['total_size_mb']} MB**",
                inline=True
            )
            
            embed.set_footer(text="Automatische Bereinigung läuft weiterhin im Hintergrund")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            embed = discord.Embed(
                title="❌ Fehler bei Log-Bereinigung",
                description=f"Fehler: {str(e)}",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(AdminCommands(bot)) 