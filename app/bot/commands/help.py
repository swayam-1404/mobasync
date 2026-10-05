import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
from app.bot.client import security_gate
from app.logging.audit_logger import audit_logger

class HelpCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="help", description="Show all available filesender commands")
    @security_gate(is_transfer=False)
    async def help_command(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        username = f"{interaction.user.name}#{interaction.user.discriminator}"
        
        embed = discord.Embed(
            title="🔒 Secure Desktop File Sender Menu",
            color=discord.Color.dark_purple(),
            timestamp=datetime.utcnow()
        )
        embed.description = "Here are the commands you can use to interact with your PC files remotely:"
        
        embed.add_field(name="`/status`", value="Show PC online, screen lock, and files count.", inline=False)
        embed.add_field(name="`/files`", value="List files in `SEND_FILES` recursively (supports pagination).", inline=False)
        embed.add_field(name="`/get <filename>`", value="Retrieve a file or compressed directory (zipped/split if large).", inline=False)
        embed.add_field(name="`/getall`", value="Zip and download all monitored files.", inline=False)
        embed.add_field(name="`/recent`", value="Show the 10 most recently created or modified files.", inline=False)
        embed.add_field(name="`/storage`", value="Display disk size usage and folder metrics.", inline=False)
        embed.add_field(name="`/search <keyword>`", value="Search files by matching keyword name.", inline=False)
        embed.add_field(name="`/help`", value="Show this commands index menu.", inline=False)
        embed.set_footer(text="Desktop File Sender Bot | Authorised Access Only")
        
        audit_logger.log_audit(user_id, username, "/help", None, True)
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(HelpCog(bot))
