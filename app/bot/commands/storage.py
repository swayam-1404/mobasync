import discord
from discord.ext import commands
from discord import app_commands
from app.bot.client import security_gate
from app.monitoring.system_monitor import get_storage_info
from app.logging.audit_logger import audit_logger

class StorageCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="storage", description="Check storage usage metrics of the monitored directory")
    @security_gate(is_transfer=False)
    async def storage_command(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        username = f"{interaction.user.name}#{interaction.user.discriminator}"
        
        info = get_storage_info()
        
        # Format folder size dynamically to GB if it exceeds 1024 MB
        folder_size_mb = info["folder_size_mb"]
        if folder_size_mb >= 1024:
            folder_size_str = f"{round(folder_size_mb / 1024, 2)} GB"
        else:
            folder_size_str = f"{folder_size_mb} MB"
            
        free_space_gb = info["disk_free_gb"]
        
        # Create output exactly as formatted by user
        response_text = (
            "💾 **Storage**\n"
            f"Files: {info['file_count']}\n"
            f"Folder Size: {folder_size_str}\n"
            f"Free Space: {free_space_gb} GB"
        )
        
        audit_logger.log_audit(user_id, username, "/storage", None, True)
        await interaction.response.send_message(response_text, ephemeral=True)

async def setup(bot):
    await bot.add_cog(StorageCog(bot))
