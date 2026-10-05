import os
import subprocess
import logging
import discord
from discord.ext import commands
from discord import app_commands
from app.bot.client import security_gate
from app.security.validator import validate_user
from app.logging.audit_logger import audit_logger

logger = logging.getLogger(__name__)

class PowerConfirmView(discord.ui.View):
    """View to prompt the user with confirmation buttons for power actions."""
    
    def __init__(self, action: str, author_id: int):
        super().__init__(timeout=30)
        self.action = action
        self.author_id = author_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        # Only the user who ran the command can confirm or cancel
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ You are not authorized to respond to this prompt.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Confirm Action", style=discord.ButtonStyle.danger)
    async def confirm_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Disable buttons once clicked
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(content=f"⏳ Executing `{self.action}`...", view=self)
        
        username = f"{interaction.user.name}#{interaction.user.discriminator}"
        success = False
        error_msg = None
        
        try:
            if self.action == "lock":
                # Try locking GNOME screen first via DBus, fallback to loginctl
                try:
                    import dbus
                    bus = dbus.SessionBus()
                    obj = bus.get_object('org.gnome.ScreenSaver', '/org/gnome/ScreenSaver')
                    interface = dbus.Interface(obj, 'org.gnome.ScreenSaver')
                    interface.Lock()
                    success = True
                except Exception as e:
                    logger.debug(f"Failed to lock via GNOME ScreenSaver DBus: {e}")
                    # Fallback to loginctl lock-session
                    res = subprocess.run(["loginctl", "lock-session"], capture_output=True, text=True)
                    if res.returncode == 0:
                        success = True
                    else:
                        error_msg = res.stderr or "loginctl lock-session failed"
            
            elif self.action == "suspend":
                res = subprocess.run(["systemctl", "suspend"], capture_output=True, text=True)
                if res.returncode == 0:
                    success = True
                else:
                    error_msg = res.stderr or "systemctl suspend failed"
                    
            elif self.action == "reboot":
                res = subprocess.run(["systemctl", "reboot"], capture_output=True, text=True)
                if res.returncode == 0:
                    success = True
                else:
                    error_msg = res.stderr or "systemctl reboot failed"
                    
            elif self.action == "shutdown":
                res = subprocess.run(["systemctl", "poweroff"], capture_output=True, text=True)
                if res.returncode == 0:
                    success = True
                else:
                    error_msg = res.stderr or "systemctl poweroff failed"
            
            if success:
                audit_logger.log_audit(self.author_id, username, f"/power {self.action}", None, True)
                await interaction.followup.send(f"✅ Desktop power action `{self.action}` initiated successfully.", ephemeral=True)
            else:
                audit_logger.log_audit(self.author_id, username, f"/power {self.action}", None, False, error_msg)
                await interaction.followup.send(f"❌ Failed to execute `{self.action}`: {error_msg}", ephemeral=True)
                
        except Exception as e:
            logger.exception(f"Exception during /power {self.action}: {e}")
            audit_logger.log_audit(self.author_id, username, f"/power {self.action}", None, False, str(e))
            await interaction.followup.send(f"❌ An error occurred: {str(e)}", ephemeral=True)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(content="❌ Action cancelled.", view=self)
        self.stop()


class PowerCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="power", description="Execute system power controls remotely")
    @app_commands.choices(action=[
        app_commands.Choice(name="Lock Screen", value="lock"),
        app_commands.Choice(name="Suspend Laptop", value="suspend"),
        app_commands.Choice(name="Reboot Laptop", value="reboot"),
        app_commands.Choice(name="Shutdown Laptop", value="shutdown")
    ])
    @security_gate(is_transfer=False)
    async def power_command(self, interaction: discord.Interaction, action: app_commands.Choice[str]):
        user_id = interaction.user.id
        action_val = action.value
        
        view = PowerConfirmView(action_val, user_id)
        embed = discord.Embed(
            title="⚠️ Remote Power Action Confirmation",
            description=f"Are you sure you want to execute **{action.name}** (`{action_val}`) on your laptop?",
            color=discord.Color.red()
        )
        embed.set_footer(text="Action will auto-cancel in 30 seconds.")
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

async def setup(bot):
    await bot.add_cog(PowerCog(bot))
