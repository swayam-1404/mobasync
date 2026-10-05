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

class UploadCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="upload", description="Upload a file from your phone/Discord directly to the SEND_FILES folder")
    @security_gate(is_transfer=True)
    async def upload_command(self, interaction: discord.Interaction, file: discord.Attachment):
        # Defer immediately to allow time for downloading and writing
        await interaction.response.defer(ephemeral=True)
        
        user_id = interaction.user.id
        username = f"{interaction.user.name}#{interaction.user.discriminator}"
        
        # 1. Clean the filename to prevent path traversal
        clean_name = os.path.basename(file.filename)
        
        # 2. Path validation boundary check
        if not validate_path(clean_name):
            logger.warning(f"Upload path validation failed for user {user_id} requesting filename: {clean_name}")
            audit_logger.log_audit(user_id, username, f"/upload {clean_name}", clean_name, False, "Path Validation Failed")
            await interaction.followup.send("❌ Upload Denied: Invalid path structure.", ephemeral=True)
            return

        # Resolve full path
        dest_folder = config.SEND_FILES_PATH
        full_path = os.path.realpath(os.path.join(dest_folder, clean_name))

        # Double check directory existence
        os.makedirs(dest_folder, exist_ok=True)
        
        # 3. File size check (e.g. max 50MB)
        MAX_SIZE_BYTES = 50 * 1024 * 1024
        if file.size > MAX_SIZE_BYTES:
            audit_logger.log_audit(user_id, username, f"/upload {clean_name}", clean_name, False, "File Exceeds Max Upload Size")
            await interaction.followup.send("❌ Upload Denied: File exceeds the 50MB limit.", ephemeral=True)
            return
            
        try:
            # 4. Save the file attachment
            await file.save(full_path)
            
            logger.info(f"Successfully uploaded file: {clean_name} to {full_path}")
            audit_logger.log_audit(user_id, username, f"/upload {clean_name}", clean_name, True)
            
            # Formulate response
            size_kb = round(os.path.getsize(full_path) / 1024, 1)
            await interaction.followup.send(
                f"📥 **Upload Successful**\n"
                f"File `{clean_name}` ({size_kb} KB) has been saved to your laptop.",
                ephemeral=True
            )
            
        except Exception as e:
            logger.exception(f"Exception during file upload: {e}")
            audit_logger.log_audit(user_id, username, f"/upload {clean_name}", clean_name, False, str(e))
            await interaction.followup.send(f"❌ Failed to upload file: {str(e)}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(UploadCog(bot))
