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

class RenameCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="rename", description="Rename a file inside the SEND_FILES directory on your PC")
    @security_gate(is_transfer=True)
    async def rename_command(self, interaction: discord.Interaction, old_name: str, new_name: str):
        # Defer reply
        await interaction.response.defer(ephemeral=True)
        
        user_id = interaction.user.id
        username = f"{interaction.user.name}#{interaction.user.discriminator}"
        
        # 1. Path validation boundary check for both names
        if not validate_path(old_name) or not validate_path(new_name):
            logger.warning(f"Rename path validation failed for user {user_id} requesting: {old_name} -> {new_name}")
            audit_logger.log_audit(user_id, username, f"/rename {old_name} {new_name}", old_name, False, "Path Validation Failed")
            await interaction.followup.send("❌ Rename Denied: Invalid path structure.", ephemeral=True)
            return

        # Resolve paths
        old_path = os.path.realpath(os.path.join(config.SEND_FILES_PATH, old_name))
        new_path = os.path.realpath(os.path.join(config.SEND_FILES_PATH, new_name))
        
        # 2. Check if source exists and destination does not exist (avoid overwrite)
        if not os.path.exists(old_path):
            audit_logger.log_audit(user_id, username, f"/rename {old_name} {new_name}", old_name, False, "Source File Not Found")
            await interaction.followup.send("❌ Source file does not exist.", ephemeral=True)
            return
            
        if os.path.exists(new_path):
            audit_logger.log_audit(user_id, username, f"/rename {old_name} {new_name}", old_name, False, "Destination File Exists")
            await interaction.followup.send("❌ Rename Denied: Target filename already exists.", ephemeral=True)
            return
            
        try:
            # 3. Perform rename
            os.rename(old_path, new_path)
            
            logger.info(f"Successfully renamed file: {old_name} -> {new_name}")
            audit_logger.log_audit(user_id, username, f"/rename {old_name} {new_name}", old_name, True)
            
            await interaction.followup.send(f"✏️ File `{old_name}` has been successfully renamed to `{new_name}`.", ephemeral=True)
            
        except Exception as e:
            logger.exception(f"Exception during file rename: {e}")
            audit_logger.log_audit(user_id, username, f"/rename {old_name} {new_name}", old_name, False, str(e))
            await interaction.followup.send(f"❌ Failed to rename file: {str(e)}", ephemeral=True)

    @rename_command.autocomplete('old_name')
    async def old_name_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        """Autocomplete source file names recursively from SEND_FILES directory."""
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
    await bot.add_cog(RenameCog(bot))
