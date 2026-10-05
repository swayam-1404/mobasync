import discord
import logging
from discord import app_commands
from discord.ext import commands
from app.config.config import config
from app.security.validator import validate_user
from app.security.lock_detector import lock_detector
from app.security.rate_limiter import command_limiter, transfer_limiter
from app.monitoring.system_monitor import check_internet_connectivity
from app.logging.audit_logger import audit_logger

logger = logging.getLogger(__name__)

class SecurityException(app_commands.AppCommandError):
    """Custom exception raised when a security gate check fails."""
    def __init__(self, message: str, audit_reason: str):
        super().__init__(message)
        self.message = message
        self.audit_reason = audit_reason


def security_gate(is_transfer: bool = False):
    """Decorator to enforce zero-trust checks on slash commands."""
    async def predicate(interaction: discord.Interaction) -> bool:
        user_id = interaction.user.id
        username = f"{interaction.user.name}#{interaction.user.discriminator}"
        command = f"/{interaction.command.name}" if interaction.command else "UNKNOWN"
        
        # 1. Authorize User
        if not validate_user(user_id):
            logger.warning(f"Unauthorized user {user_id} ({username}) tried to run: {command}")
            audit_logger.log_audit(user_id, username, command, None, False, "Access Denied")
            raise SecurityException("Access Denied", "Access Denied")
            
        # 2. Command Rate Limit
        if not command_limiter.is_allowed(user_id):
            logger.warning(f"User {user_id} command rate limit exceeded")
            audit_logger.log_audit(user_id, username, command, None, False, "Command Rate Limit Exceeded")
            raise SecurityException("Rate limit exceeded. Please try again later.", "Command Rate Limit Exceeded")
            
        # 3. System Lock Status
        if lock_detector.is_locked():
            logger.warning(f"Blocked {command} from {user_id} - desktop is locked")
            audit_logger.log_audit(user_id, username, command, None, False, "Desktop Locked")
            raise SecurityException("Desktop Locked.\nOperation Denied.", "Desktop Locked")
            

        # 5. Transfer Rate Limit (if applicable)
        if is_transfer:
            if not transfer_limiter.is_allowed(user_id):
                logger.warning(f"User {user_id} transfer rate limit exceeded")
                audit_logger.log_audit(user_id, username, command, None, False, "Transfer Rate Limit Exceeded")
                raise SecurityException("Transfer rate limit exceeded. Please wait a minute.", "Transfer Rate Limit Exceeded")
                
        return True
    return app_commands.check(predicate)


class FileSenderBot(commands.Bot):
    """Custom Discord Bot Client that synchronizes slash commands and handles central security errors."""
    
    def __init__(self):
        # Slash commands don't require privileged message_content intent
        intents = discord.Intents.default()
        super().__init__(command_prefix="!", intents=intents)
        
    async def setup_hook(self):
        # We will load cogs dynamically
        await self.load_extension("app.bot.commands.files")
        await self.load_extension("app.bot.commands.get")
        await self.load_extension("app.bot.commands.getall")
        await self.load_extension("app.bot.commands.status")
        await self.load_extension("app.bot.commands.recent")
        await self.load_extension("app.bot.commands.storage")
        await self.load_extension("app.bot.commands.search")
        await self.load_extension("app.bot.commands.help")
        await self.load_extension("app.bot.commands.power")
        await self.load_extension("app.bot.commands.screenshot")
        await self.load_extension("app.bot.commands.processes")
        await self.load_extension("app.bot.commands.upload")
        await self.load_extension("app.bot.commands.delete")
        await self.load_extension("app.bot.commands.rename")
        await self.load_extension("app.bot.commands.ask")
        
        # Load event handlers
        await self.load_extension("app.bot.events.event_handlers")
        
        # Command Tree Sync
        if config.DISCORD_GUILD_ID:
            guild = discord.Object(id=config.DISCORD_GUILD_ID)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            logger.info(f"Synchronized Slash Commands for Guild: {config.DISCORD_GUILD_ID}")
        else:
            await self.tree.sync()
            logger.info("Synchronized Slash Commands globally.")

        # Register tree error handler
        self.tree.on_error = self.on_app_command_error

    async def on_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        """Centralized handler for all command errors/security gate failures."""
        if isinstance(error, SecurityException):
            if not interaction.response.is_done():
                await interaction.response.send_message(error.message, ephemeral=True)
            else:
                await interaction.followup.send(error.message, ephemeral=True)
        elif isinstance(error, app_commands.CheckFailure):
            # General fallback check failure message
            if not interaction.response.is_done():
                await interaction.response.send_message("Security check failed.", ephemeral=True)
            else:
                await interaction.followup.send("Security check failed.", ephemeral=True)
        else:
            logger.exception(f"Unhandled Slash Command exception: {error}")
            err_msg = f"An unexpected error occurred: {str(error)}"
            if not interaction.response.is_done():
                await interaction.response.send_message(err_msg, ephemeral=True)
            else:
                await interaction.followup.send(err_msg, ephemeral=True)
