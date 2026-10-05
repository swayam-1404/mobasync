import logging
import discord
from discord.ext import commands

logger = logging.getLogger(__name__)

class EventsCog(commands.Cog):
    """Cog to handle standard discord.py event listeners."""
    
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        logger.info(f"Discord Bot successfully connected as {self.bot.user} (ID: {self.bot.user.id})")
        print(f"✅ Discord Bot is online: {self.bot.user}")

async def setup(bot):
    await bot.add_cog(EventsCog(bot))
