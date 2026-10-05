import os
import subprocess
import logging
import discord
from discord.ext import commands
from discord import app_commands
from app.bot.client import security_gate
from app.security.lock_detector import lock_detector
from app.logging.audit_logger import audit_logger

logger = logging.getLogger(__name__)

class ScreenshotCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="screenshot", description="Capture screenshot of the desktop screen when unlocked")
    @security_gate(is_transfer=False)
    async def screenshot_command(self, interaction: discord.Interaction):
        # Defer reply as screenshot capture may take 1-2 seconds
        await interaction.response.defer(ephemeral=True)
        
        user_id = interaction.user.id
        username = f"{interaction.user.name}#{interaction.user.discriminator}"
        
        # 1. Enforce safety check: PC must be unlocked
        if lock_detector.is_locked():
            audit_logger.log_audit(user_id, username, "/screenshot", None, False, "PC Locked")
            await interaction.followup.send("❌ Operation Denied: Screenshot is disabled while PC is locked for privacy.", ephemeral=True)
            return

        screenshot_path = "/tmp/screenshot.png"
        
        # Cleanup any old screenshot
        if os.path.exists(screenshot_path):
            try:
                os.remove(screenshot_path)
            except OSError:
                pass
                
        # 2. Setup display session environment variables for the subprocess
        env = os.environ.copy()
        if "WAYLAND_DISPLAY" not in env:
            env["WAYLAND_DISPLAY"] = "wayland-0"
        if "DISPLAY" not in env:
            env["DISPLAY"] = ":0"
        if "XDG_RUNTIME_DIR" not in env:
            env["XDG_RUNTIME_DIR"] = f"/run/user/{os.getuid()}"
            
        # 3. Attempt capture using gnome-screenshot
        try:
            res = subprocess.run(
                ["gnome-screenshot", "-f", screenshot_path],
                env=env,
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if res.returncode == 0 and os.path.exists(screenshot_path):
                # Send the captured file
                with open(screenshot_path, "rb") as f:
                    file_to_send = discord.File(f, filename="screenshot.png")
                    await interaction.followup.send(
                        content="📸 Screenshot captured successfully:",
                        file=file_to_send,
                        ephemeral=True
                    )
                
                # Audit and clean up
                audit_logger.log_audit(user_id, username, "/screenshot", "screenshot.png", True)
                try:
                    os.remove(screenshot_path)
                except OSError:
                    pass
            else:
                error_msg = res.stderr or "gnome-screenshot failed without error output"
                logger.error(f"gnome-screenshot failed: {error_msg}")
                
                # Check if tool is missing
                if "not found" in error_msg.lower() or res.returncode == 127:
                    err_response = (
                        "❌ Screenshot failed: `gnome-screenshot` utility is not installed on your laptop.\n"
                        "Please run this command on your laptop terminal to install it:\n"
                        "`sudo apt install gnome-screenshot`"
                    )
                else:
                    err_response = f"❌ Failed to capture screenshot: {error_msg}"
                    
                audit_logger.log_audit(user_id, username, "/screenshot", None, False, error_msg)
                await interaction.followup.send(err_response, ephemeral=True)
                
        except subprocess.TimeoutExpired:
            logger.error("gnome-screenshot execution timed out.")
            audit_logger.log_audit(user_id, username, "/screenshot", None, False, "Timeout")
            await interaction.followup.send("❌ Screenshot capture timed out.", ephemeral=True)
            
        except FileNotFoundError:
            logger.error("gnome-screenshot utility was not found on the system.")
            err_response = (
                "❌ Screenshot failed: `gnome-screenshot` utility is not installed on your laptop.\n"
                "Please run this command on your laptop terminal to install it:\n"
                "`sudo apt install gnome-screenshot`"
            )
            audit_logger.log_audit(user_id, username, "/screenshot", None, False, "gnome-screenshot not installed")
            await interaction.followup.send(err_response, ephemeral=True)
            
        except Exception as e:
            logger.exception(f"Exception during screenshot: {e}")
            audit_logger.log_audit(user_id, username, "/screenshot", None, False, str(e))
            await interaction.followup.send(f"❌ Failed to run screenshot command: {str(e)}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(ScreenshotCog(bot))
