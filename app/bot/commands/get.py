import os
import logging
import discord
from discord.ext import commands
from discord import app_commands
from app.config.config import config
from app.bot.client import security_gate
from app.security.validator import validate_path
from app.services.large_file_handler import zip_directory, cleanup_files, get_large_file_strategy
from app.logging.audit_logger import audit_logger

logger = logging.getLogger(__name__)

class GetCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="get", description="Send a specific file or compressed folder")
    @security_gate(is_transfer=True)
    async def get_command(self, interaction: discord.Interaction, filename: str):
        # Defer immediately to prevent timeout on slow disks or large uploads
        await interaction.response.defer(ephemeral=True)
        
        user_id = interaction.user.id
        username = f"{interaction.user.name}#{interaction.user.discriminator}"
        
        # Security: validate target path boundaries
        if not validate_path(filename):
            logger.warning(f"Path validation failed for user {user_id} requesting: {filename}")
            audit_logger.log_audit(user_id, username, f"/get {filename}", filename, False, "Path Validation Failed")
            await interaction.followup.send("❌ Access Denied: Invalid path.", ephemeral=True)
            return

        full_path = os.path.realpath(os.path.join(config.SEND_FILES_PATH, filename))
        
        # Verify file exists
        if not os.path.exists(full_path):
            audit_logger.log_audit(user_id, username, f"/get {filename}", filename, False, "File Not Found")
            await interaction.followup.send("❌ Requested file/folder does not exist.", ephemeral=True)
            return

        temp_files = []
        send_path = full_path
        
        try:
            # If target is a directory, compress it
            if os.path.isdir(full_path):
                # Update status for user
                await interaction.followup.send("📦 Target is a directory. Compressing into ZIP...", ephemeral=True)
                zip_name = f"{os.path.basename(full_path)}.zip"
                send_path = zip_directory(full_path, zip_name)
                temp_files.append(send_path)
                
            file_size_mb = os.path.getsize(send_path) / (1024 * 1024)
            
            # Check if file size exceeds Discord limit (25MB)
            if file_size_mb > 25:
                strategy = get_large_file_strategy()
                result = strategy.handle_large_file(send_path)
                
                if result.action == "upload":
                    await interaction.followup.send(f"📤 {result.message} Uploading chunks...", ephemeral=True)
                    # Add generated chunks to temp files so they are cleaned up
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
                # Send single file directly
                with open(send_path, 'rb') as f:
                    await interaction.followup.send(
                        file=discord.File(f, filename=os.path.basename(send_path)), 
                        ephemeral=True
                    )
                    
            audit_logger.log_audit(user_id, username, f"/get {filename}", os.path.basename(send_path), True)
        except Exception as e:
            logger.error(f"Error handling /get command: {e}")
            audit_logger.log_audit(user_id, username, f"/get {filename}", filename, False, str(e))
            await interaction.followup.send(f"❌ Failed to transfer file: {str(e)}", ephemeral=True)
        finally:
            cleanup_files(temp_files)

    @get_command.autocomplete('filename')
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
    await bot.add_cog(GetCog(bot))
