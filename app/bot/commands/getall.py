import os
import logging
import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
from app.config.config import config
from app.bot.client import security_gate
from app.services.large_file_handler import zip_directory, cleanup_files, get_large_file_strategy
from app.logging.audit_logger import audit_logger

logger = logging.getLogger(__name__)

class GetAllCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="getall", description="Zip and send all files in the monitored directory")
    @security_gate(is_transfer=True)
    async def getall_command(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        user_id = interaction.user.id
        username = f"{interaction.user.name}#{interaction.user.discriminator}"
        
        folder = config.SEND_FILES_PATH
        if not os.path.exists(folder) or not os.path.isdir(folder) or not os.listdir(folder):
            audit_logger.log_audit(user_id, username, "/getall", None, False, "Folder Empty or Missing")
            await interaction.followup.send("❌ No files available to send.", ephemeral=True)
            return
            
        await interaction.followup.send("📦 Preparing archive of all files...", ephemeral=True)
        temp_files = []
        
        try:
            archive_name = f"all_files_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
            zip_path = zip_directory(folder, archive_name)
            temp_files.append(zip_path)
            
            file_size_mb = os.path.getsize(zip_path) / (1024 * 1024)
            
            if file_size_mb > 25:
                strategy = get_large_file_strategy()
                result = strategy.handle_large_file(zip_path)
                
                if result.action == "upload":
                    await interaction.followup.send(f"📤 {result.message} Uploading chunks...", ephemeral=True)
                    temp_files.extend(result.files)
                    
                    for part in result.files:
                        with open(part, 'rb') as f:
                            await interaction.followup.send(
                                file=discord.File(f, filename=os.path.basename(part)),
                                ephemeral=True
                            )
                elif result.action == "message":
                    await interaction.followup.send(result.message, ephemeral=True)
                else:
                    await interaction.followup.send(f"❌ Error: {result.message}", ephemeral=True)
            else:
                with open(zip_path, 'rb') as f:
                    await interaction.followup.send(
                        file=discord.File(f, filename=os.path.basename(zip_path)),
                        ephemeral=True
                    )
            
            audit_logger.log_audit(user_id, username, "/getall", archive_name, True)
        except Exception as e:
            logger.error(f"Error handling /getall command: {e}")
            audit_logger.log_audit(user_id, username, "/getall", None, False, str(e))
            await interaction.followup.send(f"❌ Failed to send archive: {str(e)}", ephemeral=True)
        finally:
            cleanup_files(temp_files)

async def setup(bot):
    await bot.add_cog(GetAllCog(bot))
