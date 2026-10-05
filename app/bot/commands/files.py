import os
import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
from app.config.config import config
from app.bot.client import security_gate
from app.bot.views.pagination import FilePaginationView
from app.logging.audit_logger import audit_logger

class FilesCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="files", description="List files inside the monitored directory")
    @security_gate(is_transfer=False)
    async def files_command(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        username = f"{interaction.user.name}#{interaction.user.discriminator}"
        
        folder = config.SEND_FILES_PATH
        if not os.path.exists(folder) or not os.path.isdir(folder):
            audit_logger.log_audit(user_id, username, "/files", None, False, "Folder Not Found")
            await interaction.response.send_message("❌ Monitored directory does not exist.", ephemeral=True)
            return
            
        file_list = []
        for root, _, files in os.walk(folder):
            for f in files:
                fp = os.path.join(root, f)
                if os.path.exists(fp):
                    rel_path = os.path.relpath(fp, folder)
                    stats = os.stat(fp)
                    size_kb = round(stats.st_size / 1024, 1)
                    mod_time = datetime.fromtimestamp(stats.st_mtime).strftime("%Y-%m-%d %H:%M")
                    file_list.append((rel_path, size_kb, mod_time))
                    
        if not file_list:
            audit_logger.log_audit(user_id, username, "/files", None, True)
            await interaction.response.send_message("📁 SEND_FILES directory is currently empty.", ephemeral=True)
            return

        # Sort files alphabetically
        sorted_files = sorted(file_list, key=lambda x: x[0])
        
        # Instantiate pagination view
        view = FilePaginationView(sorted_files, author_id=user_id)
        content, embed = view.get_page_content()
        
        audit_logger.log_audit(user_id, username, "/files", None, True)
        await interaction.response.send_message(content=content, embed=embed, view=view, ephemeral=True)

async def setup(bot):
    await bot.add_cog(FilesCog(bot))
