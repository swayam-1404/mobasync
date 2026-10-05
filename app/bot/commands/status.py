import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
from app.bot.client import security_gate
from app.security.lock_detector import lock_detector
from app.monitoring.system_monitor import check_internet_connectivity, get_files_count
from app.logging.audit_logger import audit_logger

class StatusCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="status", description="Get system online, network, and desktop status")
    @security_gate(is_transfer=False)
    async def status_command(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        username = f"{interaction.user.name}#{interaction.user.discriminator}"
        
        internet_status = "🟢 Connected" if check_internet_connectivity() else "🔴 Disconnected"
        lock_status = "🔒 Locked" if lock_detector.is_locked() else "🔓 Unlocked"
        files_count = get_files_count()
        
        embed = discord.Embed(
            title="🖥️ Desktop File Sender Status",
            color=discord.Color.dark_green(),
            timestamp=datetime.utcnow()
        )
        embed.add_field(name="System Status", value="🟢 Online", inline=True)
        embed.add_field(name="Internet Access", value=internet_status, inline=True)
        embed.add_field(name="Session State", value=lock_status, inline=True)
        embed.add_field(name="Monitored Files", value=f"📁 {files_count} files", inline=False)
        embed.set_footer(text="Desktop File Sender Service")
        
        audit_logger.log_audit(user_id, username, "/status", None, True)
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(StatusCog(bot))
