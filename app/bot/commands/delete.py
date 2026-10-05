import os
import discord
import logging
from discord.ext import commands
from discord import app_commands
from app.config.config import config
from app.bot.client import security_gate
from app.security.validator import validate_path
from app.logging.audit_logger import audit_logger

logger = logging.getLogger(__name__)

class DeleteCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="delete", description="Delete a file from the SEND_FILES directory on your PC")
    @security_gate(is_transfer=True)
    async def delete_command(self, interaction: discord.Interaction, filename: str):
        # Defer reply in case of slow disk operations
        await interaction.response.defer(ephemeral=True)
        
        user_id = interaction.user.id
        username = f"{interaction.user.name}#{interaction.user.discriminator}"
        
        # 1. Path validation boundary check
        if not validate_path(filename):
            logger.warning(f"Delete path validation failed for user {user_id} requesting: {filename}")
            audit_logger.log_audit(user_id, username, f"/delete {filename}", filename, False, "Path Validation Failed")
            await interaction.followup.send("❌ Delete Denied: Invalid path structure.", ephemeral=True)
            return

        # Resolve full path
        full_path = os.path.realpath(os.path.join(config.SEND_FILES_PATH, filename))
        
        # 2. Check if file exists and is indeed a file (restrict directory deletion for safety)
        if not os.path.exists(full_path):
            audit_logger.log_audit(user_id, username, f"/delete {filename}", filename, False, "File Not Found")
            await interaction.followup.send("❌ File does not exist.", ephemeral=True)
            return
            
        if not os.path.isfile(full_path):
            audit_logger.log_audit(user_id, username, f"/delete {filename}", filename, False, "Not A File")
            await interaction.followup.send("❌ Delete Denied: You can only delete files, not directories.", ephemeral=True)
            return
            
        try:
            # 3. Delete the file
            os.remove(full_path)
            
            logger.info(f"Successfully deleted file: {filename} from {full_path}")
            audit_logger.log_audit(user_id, username, f"/delete {filename}", filename, True)
            
            await interaction.followup.send(f"🗑️ File `{filename}` has been successfully deleted from your PC.", ephemeral=True)
            
        except Exception as e:
            logger.exception(f"Exception during file deletion: {e}")
            audit_logger.log_audit(user_id, username, f"/delete {filename}", filename, False, str(e))
            await interaction.followup.send(f"❌ Failed to delete file: {str(e)}", ephemeral=True)

    @delete_command.autocomplete('filename')
    async def filename_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        """Autocomplete file names recursively from SEND_FILES directory."""
        folder = config.SEND_FILES_PATH
        if not os.path.exists(folder) or not os.path.isdir(folder):
            return []
            
        choices = []
        for root, _, files in os.walk(folder):
            for f in files:
                fp = os.path.join(root, f)
                if os.path.exists(fp):
                    rel_path = os.path.relpath(fp, folder)
                    if current.lower() in rel_path.lower():
                        choices.append(rel_path)
                        if len(choices) >= 25:
                            break
            if len(choices) >= 25:
                break
                
        return [app_commands.Choice(name=c, value=c) for c in choices]

async def setup(bot):
    await bot.add_cog(DeleteCog(bot))
