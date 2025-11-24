import discord
from discord import app_commands
from typing import Optional
import logging
from discord.ext import commands
from bot_status import BotStatus
from datetime import datetime
import time
import json

logger = logging.getLogger('StatusBot')

class AdminCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="tokenbalancer")
    @app_commands.checks.has_permissions(administrator=True)
    async def token_balancer_stats(self, interaction: discord.Interaction):
        """Zeigt Token Balancer Statistiken und Performance-Daten"""
        try:
            if not hasattr(self.bot, 'token_balancer') or not self.bot.token_balancer:
                await interaction.response.send_message(
                    "❌ Token Balancer ist nicht verfügbar",
                    ephemeral=True
                )
                return
            
            balancer = self.bot.token_balancer
            stats = balancer.get_performance_stats()
            
            if not stats:
                await interaction.response.send_message(
                    "❌ Statistiken konnten nicht abgerufen werden",
                    ephemeral=True
                )
                return
            
            # Erstelle Embed mit Statistiken
            embed = discord.Embed(
                title="⚖️ Token Balancer - Performance Statistiken",
                color=0xff0000 if stats['needs_second_helper'] else 0x00ff00,
                timestamp=discord.utils.utcnow()
            )
            
            # Aktueller Status
            status_text = balancer.get_status_text()
            embed.add_field(name="Aktueller Status", value=status_text, inline=False)
            
            # Grundstatistiken
            embed.add_field(name="Gesamte Wechsel", value=f"{stats['total_switches']}", inline=True)
            embed.add_field(name="Wechsel (letzte Stunde)", value=f"{stats['switches_last_hour']}", inline=True)
            embed.add_field(name="Rate Limit Anteil", value=f"{stats['rate_limit_ratio']:.1f}%", inline=True)
            
            # Detaillierte Statistiken
            embed.add_field(name="Rate Limit Wechsel", value=f"{balancer.stats['rate_limit_switches']}", inline=True)
            embed.add_field(name="Verbindungsfehler", value=f"{balancer.stats['connection_error_switches']}", inline=True)
            embed.add_field(name="Graduelle Rückkehr", value=f"{balancer.stats['gradual_return_switches']}", inline=True)
            
            # Uptime
            embed.add_field(name="Laufzeit", value=f"{stats['uptime_hours']:.1f} Stunden", inline=True)
            
            # Empfehlung
            if stats['needs_second_helper']:
                embed.add_field(
                    name="🚨 Empfehlung", 
                    value="**2. Helper Bot einrichten!**\nHohe API-Belastung erkannt", 
                    inline=False
                )
                embed.color = 0xff0000
            else:
                embed.add_field(
                    name="✅ Status", 
                    value="Performance ist gut", 
                    inline=False
                )
            
            # Tagesstatistiken (letzten 7 Tage)
            daily_stats = balancer.stats.get('daily_stats', {})
            if daily_stats:
                recent_days = sorted(daily_stats.keys())[-7:]  # Letzte 7 Tage
                stats_text = []
                for day in recent_days:
                    day_data = daily_stats[day]
                    stats_text.append(f"{day}: {day_data['switches']} Wechsel ({day_data['rate_limits']} Rate Limits)")
                
                if stats_text:
                    embed.add_field(
                        name="📊 Letzte 7 Tage", 
                        value="\n".join(stats_text[-5:]), 
                        inline=False
                    )
            
            await interaction.response.send_message(embed=embed)
            logger.info(f"Token Balancer Statistiken abgerufen von {interaction.user}")
            
        except Exception as e:
            logger.error(f"Error getting token balancer stats: {e}", exc_info=True)
            await interaction.response.send_message(
                "❌ Es gab einen Fehler beim Abrufen der Statistiken",
                ephemeral=True
            )

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
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in balancer_status command: {e}", exc_info=True)
            await interaction.response.send_message(
                "❌ Es gab einen Fehler beim Abrufen des Balancer-Status",
                ephemeral=True
            )

    @app_commands.command(name="balancerreset")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.choices(target=[
        app_commands.Choice(name="Primärer Bot", value="primary"),
        app_commands.Choice(name="Sekundärer Bot", value="secondary"),
        app_commands.Choice(name="Status zurücksetzen", value="reset")
    ])
    async def balancer_reset(self, interaction: discord.Interaction, target: app_commands.Choice[str]):
        """🚨 Notfall-Reset für den Token Balancer"""
        try:
            if not hasattr(self.bot, 'token_balancer') or not self.bot.token_balancer:
                await interaction.response.send_message(
                    "❌ Token Balancer ist nicht verfügbar",
                    ephemeral=True
                )
                return
                
            balancer = self.bot.token_balancer
            old_status = balancer.get_status_text()
            
            # Prüfe den echten Discord API Status vor dem Reset
            discord_status = balancer.get_real_discord_status()
            status_info = ""
            if discord_status:
                status_info = f"API-Status: Ready={discord_status['is_ready']}, Latenz={discord_status['latency']:.1f}ms"
            
            success = False
            
            if target.value == "primary":
                # Erzwinge primären Bot
                success = balancer.force_token_switch(True, 0, f"Admin-Reset durch {interaction.user}")
                
                embed = discord.Embed(
                    title="✅ Token Balancer Reset",
                    description="**Primärer Bot erzwungen**",
                    color=0x00ff00,
                    timestamp=discord.utils.utcnow()
                )
                embed.add_field(name="Vorher", value=old_status, inline=True)
                embed.add_field(name="Nachher", value="Primärer Bot aktiv", inline=True)
                embed.add_field(name="Durchgeführt von", value=interaction.user.mention, inline=True)
                
            elif target.value == "secondary":
                # Erzwinge sekundären Bot (für 5 Minuten)
                success = balancer.force_token_switch(False, 300, f"Admin-Reset durch {interaction.user}")
                
                embed = discord.Embed(
                    title="⚠️ Token Balancer Reset",
                    description="**Sekundärer Bot erzwungen (5 Minuten)**",
                    color=0xff9900,
                    timestamp=discord.utils.utcnow()
                )
                embed.add_field(name="Vorher", value=old_status, inline=True)
                embed.add_field(name="Nachher", value="Sekundärer Bot aktiv (5 Min)", inline=True)
                embed.add_field(name="Durchgeführt von", value=interaction.user.mention, inline=True)
                
            elif target.value == "reset":
                # Kompletter Reset - zurück zu primärem Bot
                success = balancer.force_token_switch(True, 0, f"Kompletter Reset durch {interaction.user}")
                
                # Lösche auch die Status-Datei für einen kompletten Neustart
                try:
                    if balancer.status_file.exists():
                        balancer.status_file.unlink()
                        logger.info("Token Balancer Status-Datei gelöscht für kompletten Reset")
                except Exception as e:
                    logger.warning(f"Konnte Status-Datei nicht löschen: {e}")
                
                embed = discord.Embed(
                    title="🔄 Token Balancer Reset",
                    description="**Kompletter Status-Reset durchgeführt**",
                    color=0x3498db,
                    timestamp=discord.utils.utcnow()
                )
                embed.add_field(name="Vorher", value=old_status, inline=True)
                embed.add_field(name="Nachher", value="Zurückgesetzt auf Standard", inline=True)
                embed.add_field(name="Durchgeführt von", value=interaction.user.mention, inline=True)
                embed.add_field(name="Hinweis", value="Status-Datei wurde gelöscht", inline=False)
            
            # Füge Discord API Status hinzu, falls verfügbar
            if status_info:
                embed.add_field(name="Discord API", value=status_info, inline=False)
            
            # Füge Erfolgsstatus hinzu
            if success:
                embed.add_field(name="Status", value="✅ Reset erfolgreich", inline=True)
            else:
                embed.add_field(name="Status", value="⚠️ Reset teilweise fehlgeschlagen", inline=True)
                embed.color = 0xff6b6b  # Rot-Orange bei Fehlern
            
            await interaction.response.send_message(embed=embed)
            logger.info(f"Token Balancer Reset durchgeführt von {interaction.user} - {target.name} (Erfolg: {success})")
            
        except Exception as e:
            logger.error(f"Error in balancer_reset command: {e}", exc_info=True)
            await interaction.response.send_message(
                "❌ Es gab einen Fehler beim Reset des Token Balancers",
                ephemeral=True
            )

    @app_commands.command(name="healthcheck")
    @app_commands.checks.has_permissions(administrator=True)
    async def health_check(self, interaction: discord.Interaction):
        """🏥 Vollständiger Gesundheitscheck aller Bot-Systeme"""
        try:
            embed = discord.Embed(
                title="🏥 System Health Check",
                description="Überprüfung aller Bot-Komponenten",
                color=0x3498db,
                timestamp=discord.utils.utcnow()
            )
            
            # Main Bot Status
            main_status = "❌ Offline"
            main_details = "Nicht erreichbar"
            
            if self.bot.is_ready():
                latency_ms = round(self.bot.latency * 1000)
                guild_count = len(self.bot.guilds)
                main_status = f"✅ Online ({latency_ms}ms)"
                main_details = f"🏠 {guild_count} Server"
                
                if latency_ms > 500:
                    main_status = f"⚠️ Langsam ({latency_ms}ms)"
            
            embed.add_field(
                name="🤖 Main Bot",
                value=f"{main_status}\n{main_details}",
                inline=True
            )
            
            # Token Balancer Status
            if hasattr(self.bot, 'token_balancer') and self.bot.token_balancer:
                balancer = self.bot.token_balancer
                balancer_status = balancer.get_status_text()
                
                # Prüfe Discord API Status
                discord_status = balancer.get_real_discord_status()
                api_info = "Nicht verfügbar"
                if discord_status:
                    if discord_status['is_ready'] and not discord_status['is_closed']:
                        api_info = f"✅ Verbunden ({discord_status['latency']:.1f}ms)"
                    else:
                        api_info = "❌ Getrennt"
                
                # Performance-Statistiken
                perf_stats = balancer.get_performance_stats()
                performance_info = "Keine Daten"
                if perf_stats:
                    if perf_stats['needs_second_helper']:
                        performance_info = f"⚠️ {perf_stats['switches_last_hour']} Wechsel/h"
                    else:
                        performance_info = f"✅ {perf_stats['total_switches']} Wechsel gesamt"
                
                embed.add_field(
                    name="⚖️ Token Balancer",
                    value=f"{balancer_status}\n{api_info}\n{performance_info}",
                    inline=True
                )
            else:
                embed.add_field(
                    name="⚖️ Token Balancer",
                    value="❌ Nicht verfügbar",
                    inline=True
                )
            
            # Helper Bot Status (über Dateien prüfen)
            helper_status = await self._check_helper_bot_status()
            embed.add_field(
                name="🤖 Helper Bot",
                value=helper_status,
                inline=True
            )
            
            # System-Performance
            system_performance = await self._check_system_performance()
            embed.add_field(
                name="⚡ System Performance",
                value=system_performance,
                inline=True
            )
            
            # Channel-Management Status
            channel_status = await self._check_channel_management()
            embed.add_field(
                name="📺 Channel Management",
                value=channel_status,
                inline=True
            )
            
            # Zusammenfassung
            overall_status = "🟢 Alle Systeme online"
            if "❌" in str(embed.to_dict()):
                overall_status = "🔴 Probleme erkannt"
            elif "⚠️" in str(embed.to_dict()):
                overall_status = "🟡 Einige Warnungen"
            
            embed.add_field(
                name="📊 Gesamtstatus",
                value=overall_status,
                inline=False
            )
            
            embed.set_footer(text=f"Abgefragt von {interaction.user.name}")
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in health_check command: {e}", exc_info=True)
            await interaction.response.send_message(
                "❌ Fehler beim Gesundheitscheck",
                ephemeral=True
            )
    
    async def _check_helper_bot_status(self) -> str:
        """Prüft den Helper Bot Status über Dateien"""
        try:
            from pathlib import Path
            
            # Prüfe Log-Dateien
            logs_dir = Path("logs")
            helper_log = logs_dir / "helperbot.log"
            
            if not helper_log.exists():
                return "❌ Keine Logs gefunden"
            
            # Prüfe Log-Größe und letzte Änderung
            log_size = helper_log.stat().st_size
            last_modified = helper_log.stat().st_mtime
            time_since_update = time.time() - last_modified
            
            if log_size == 0:
                return "⚠️ Logs sind leer"
            elif time_since_update > 600:  # 10 Minuten
                return f"⚠️ Keine Aktivität ({int(time_since_update/60)}min)"
            else:
                return f"✅ Aktiv (Log: {log_size}B)"
                
        except Exception as e:
            return f"❌ Prüfung fehlgeschlagen: {str(e)[:50]}"
    
    async def _check_system_performance(self) -> str:
        """Prüft die System-Performance"""
        try:
            # Prüfe Token Balancer Performance
            if hasattr(self.bot, 'token_balancer') and self.bot.token_balancer:
                perf_stats = self.bot.token_balancer.get_performance_stats()
                if perf_stats:
                    if perf_stats['switches_last_hour'] > 10:
                        return f"🔴 Hoch belastet ({perf_stats['switches_last_hour']} Wechsel/h)"
                    elif perf_stats['switches_last_hour'] > 5:
                        return f"⚠️ Erhöht ({perf_stats['switches_last_hour']} Wechsel/h)"
                    else:
                        return f"✅ Normal ({perf_stats['total_switches']} gesamt)"
            
            # Fallback: Prüfe Bot-Latenz
            if self.bot.latency > 0.5:
                return f"⚠️ Hohe Latenz ({round(self.bot.latency * 1000)}ms)"
            else:
                return f"✅ Gute Latenz ({round(self.bot.latency * 1000)}ms)"
                
        except Exception:
            return "❌ Prüfung fehlgeschlagen"
    
    async def _check_channel_management(self) -> str:
        """Prüft das Channel-Management-System"""
        try:
            from pathlib import Path
            
            # Prüfe channel_states.json
            states_file = Path("data/json/channel_states.json")
            
            if not states_file.exists():
                return "✅ Keine ausstehenden Tasks"
            
            with open(states_file, 'r', encoding='utf-8') as f:
                channel_states = json.loads(f.read())
            
            pending_tasks = sum(1 for state in channel_states.values() if not state.get('completed', False))
            total_channels = len(channel_states)
            
            if pending_tasks == 0:
                return f"✅ Alle aktuell ({total_channels} Channels)"
            elif pending_tasks > 10:
                return f"🔴 {pending_tasks} ausstehende Tasks"
            else:
                return f"⚠️ {pending_tasks} ausstehende Tasks"
                
        except Exception:
            return "❌ Prüfung fehlgeschlagen"

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

    @commands.command(name="sync")
    @commands.has_permissions(administrator=True)
    async def sync_prefix(self, ctx):
        """Synchronisiert die Slash Commands mit Discord (Prefix-Version)"""
        try:
            # Lösche die ursprüngliche Nachricht
            await ctx.message.delete()
            
            # Synchronisiere Commands
            synced = await self.bot.tree.sync()
            
            embed = discord.Embed(
                title="✅ Commands synchronisiert",
                description=f"**{len(synced)} Commands** wurden erfolgreich synchronisiert.",
                color=discord.Color.green(),
                timestamp=discord.utils.utcnow()
            )
            
            # Liste der synchronisierten Commands
            command_names = [cmd.name for cmd in synced]
            if command_names:
                embed.add_field(
                    name="Synchronisierte Commands",
                    value=", ".join(f"`/{name}`" for name in sorted(command_names)),
                    inline=False
                )
            
            embed.add_field(
                name="ℹ️ Hinweis",
                value="Die Commands sollten jetzt in Discord verfügbar sein. Falls nicht, warte 1-2 Minuten.",
                inline=False
            )
            
            embed.set_footer(text=f"Synchronisiert von {ctx.author.name}")
            
            # Sende temporäre Nachricht
            temp_msg = await ctx.send(embed=embed)
            
            # Lösche nach 30 Sekunden
            await temp_msg.delete(delay=30)
            
            logger.info(f"Commands via Prefix synchronisiert von {ctx.author.name}: {len(synced)} Commands")
            
            # Markiere Commands als synchronisiert
            if len(synced) > 0:
                self.bot.commands_synced = True
            
        except Exception as e:
            logger.error(f"Error syncing commands via prefix: {e}", exc_info=True)
            await ctx.send(
                "❌ Fehler beim Synchronisieren der Commands. Überprüfe die Logs.",
                delete_after=10
            )

    @app_commands.command(name="sync")
    @app_commands.checks.has_permissions(administrator=True)
    async def sync_commands(self, interaction: discord.Interaction):
        """Synchronisiert die Slash Commands mit Discord"""
        try:
            await interaction.response.defer(ephemeral=True)
            
            # Synchronisiere Commands
            synced = await self.bot.tree.sync()
            
            embed = discord.Embed(
                title="✅ Commands synchronisiert",
                description=f"**{len(synced)} Commands** wurden erfolgreich synchronisiert.",
                color=discord.Color.green(),
                timestamp=discord.utils.utcnow()
            )
            
            # Liste der synchronisierten Commands
            command_names = [cmd.name for cmd in synced]
            if command_names:
                embed.add_field(
                    name="Synchronisierte Commands",
                    value=", ".join(f"`/{name}`" for name in sorted(command_names)),
                    inline=False
                )
            
            embed.set_footer(text=f"Synchronisiert von {interaction.user.name}")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            logger.info(f"Commands synchronisiert von {interaction.user.name}: {len(synced)} Commands")
            
            # Markiere Commands als synchronisiert
            if len(synced) > 0:
                self.bot.commands_synced = True
            
        except Exception as e:
            logger.error(f"Error syncing commands: {e}", exc_info=True)
            await interaction.followup.send(
                "❌ Fehler beim Synchronisieren der Commands. Überprüfe die Logs.",
                ephemeral=True
            )

    @app_commands.command(name="reloadcogs")
    @app_commands.checks.has_permissions(administrator=True)
    async def reload_cogs(self, interaction: discord.Interaction):
        """Lädt alle Cogs neu (für Problembehebung)"""
        try:
            await interaction.response.defer(ephemeral=True)
            
            embed = discord.Embed(
                title="🔄 Cogs werden neu geladen...",
                color=discord.Color.orange(),
                timestamp=discord.utils.utcnow()
            )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
            # Erst alle Extensions entladen
            extensions_to_unload = []
            for extension_name in list(self.bot.extensions.keys()):
                if extension_name.startswith('cogs.'):
                    extensions_to_unload.append(extension_name)
            
            unloaded_count = 0
            for extension_name in extensions_to_unload:
                try:
                    await self.bot.unload_extension(extension_name)
                    unloaded_count += 1
                    logger.debug(f"Extension entladen: {extension_name}")
                except Exception as e:
                    logger.warning(f"Fehler beim Entladen von {extension_name}: {e}")
            
            # Dann neu laden
            try:
                from cogs import setup_cogs
                success = await setup_cogs(self.bot)
                
                # Command-Sync nach Reload
                try:
                    synced = await self.bot.tree.sync()
                    synced_count = len(synced)
                    logger.info(f"Commands nach Cog-Reload synchronisiert: {synced_count}")
                    
                    if synced_count > 0:
                        self.bot.commands_synced = True
                        
                except Exception as sync_error:
                    logger.error(f"Fehler bei Command-Sync nach Reload: {sync_error}")
                    synced_count = 0
                
                # Erfolgs-Embed
                if success:
                    available_commands = [cmd.name for cmd in self.bot.tree.get_commands()]
                    
                    embed = discord.Embed(
                        title="✅ Cogs erfolgreich neu geladen",
                        description=f"**{unloaded_count} Cogs** entladen und **{len(self.bot.extensions)} Extensions** geladen",
                        color=discord.Color.green(),
                        timestamp=discord.utils.utcnow()
                    )
                    
                    embed.add_field(
                        name="🎮 Verfügbare Commands",
                        value=", ".join(f"`/{cmd}`" for cmd in sorted(available_commands)) if available_commands else "Keine",
                        inline=False
                    )
                    
                    embed.add_field(
                        name="🔄 Command-Sync",
                        value=f"✅ {synced_count} Commands synchronisiert" if synced_count > 0 else "❌ Sync fehlgeschlagen",
                        inline=True
                    )
                    
                    embed.add_field(
                        name="📦 Geladene Extensions",
                        value=f"{len(self.bot.extensions)} aktiv",
                        inline=True
                    )
                    
                else:
                    embed = discord.Embed(
                        title="⚠️ Cog-Reload teilweise erfolgreich",
                        description="Einige Cogs konnten nicht geladen werden. Siehe Logs für Details.",
                        color=discord.Color.orange(),
                        timestamp=discord.utils.utcnow()
                    )
                    
            except Exception as load_error:
                logger.error(f"Fehler beim Laden der Cogs: {load_error}", exc_info=True)
                
                embed = discord.Embed(
                    title="❌ Cog-Reload fehlgeschlagen",
                    description=f"Fehler beim Laden der Cogs: {str(load_error)}",
                    color=discord.Color.red(),
                    timestamp=discord.utils.utcnow()
                )
            
            embed.set_footer(text=f"Ausgeführt von {interaction.user.name}")
            await interaction.edit_original_response(embed=embed)
            
            logger.info(f"Cog-Reload durchgeführt von {interaction.user.name}")
            
        except Exception as e:
            logger.error(f"Error in reload_cogs command: {e}", exc_info=True)
            
            error_embed = discord.Embed(
                title="❌ Fehler beim Cog-Reload",
                description=f"Ein unerwarteter Fehler ist aufgetreten: {str(e)}",
                color=discord.Color.red(),
                timestamp=discord.utils.utcnow()
            )
            
            if interaction.response.is_done():
                await interaction.edit_original_response(embed=error_embed)
            else:
                await interaction.response.send_message(embed=error_embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(AdminCommands(bot))
    logger.info("AdminCommands Cog geladen") 