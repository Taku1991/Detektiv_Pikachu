import discord
from discord import app_commands
import logging
from discord.ext import commands

logger = logging.getLogger('StatusBot')

class HelpCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="help")
    async def status_help_command(self, interaction: discord.Interaction):
        """Zeigt alle verfügbaren Befehle des StatusBots an"""
        embed = discord.Embed(
            title="📋 Verfügbare StatusBot Befehle",
            color=discord.Color.blue(),
            description="Hier sind alle Befehle aufgelistet, die du mit dem StatusBot verwenden kannst:"
        )
        
        embed.add_field(
            name="Allgemeine Befehle",
            value="• `/help` - Zeigt diese Hilfe-Nachricht an\n",
            inline=False
        )
        
        admin_commands = (
            "• `/sethistory #channel` - Setzt den Kanal für Status-Verlauf\n"
            "• `/toggle <status>` - Ändert den Bot-Status manuell (online/offline/problem/wartung)\n"
            "• `/addchannels #log_channel #update_channel [@owner]` - Fügt Log- und Update-Kanal hinzu\n"
            "• `/removechannels #log_channel` - Entfernt Log- und zugehörigen Update-Kanal\n"
            "• `/exclude #channel` - Schließt einen Kanal vom Inaktivitäts-Check aus\n"
            "• `/include #channel` - Fügt einen Kanal wieder zum Inaktivitäts-Check hinzu\n"
            "• `/listchannels` - Listet alle konfigurierten und ausgeschlossenen Kanäle auf\n"
            "• `/balancerstatus` - Zeigt den aktuellen Status des Token-Balancers an\n"
        )
        embed.add_field(name="Administrator Befehle", value=admin_commands, inline=False)
        
        lock_commands = (
            "• `/addlockrole @rolle` - Fügt eine Rolle zur Liste der zu sperrenden Rollen hinzu\n"
            "• `/removelockrole @rolle` - Entfernt eine Rolle aus der Liste der zu sperrenden Rollen\n"
            "• `/listlockroles` - Zeigt alle Rollen an, die bei Offline/Problem gesperrt werden\n"
        )
        embed.add_field(name="Channel-Lock Befehle", value=lock_commands, inline=False)
        
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(HelpCommands(bot)) 