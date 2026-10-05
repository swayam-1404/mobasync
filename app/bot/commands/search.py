import os
import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
from app.config.config import config
from app.bot.client import security_gate
from app.logging.audit_logger import audit_logger

class SearchCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="search", description="Search for files in SEND_FILES by keyword")
    @security_gate(is_transfer=False)
    async def search_command(self, interaction: discord.Interaction, keyword: str):
        user_id = interaction.user.id
        username = f"{interaction.user.name}#{interaction.user.discriminator}"
        
        keyword_clean = keyword.strip().lower()
        if not keyword_clean:
            await interaction.response.send_message("❌ Please provide a valid search keyword.", ephemeral=True)
            return
            
        folder = config.SEND_FILES_PATH
        if not os.path.exists(folder) or not os.path.isdir(folder):
            audit_logger.log_audit(user_id, username, f"/search {keyword}", None, False, "Folder Not Found")
            await interaction.response.send_message("❌ Monitored directory does not exist.", ephemeral=True)
            return
            
        matches = []
        for root, _, files in os.walk(folder):
            for f in files:
                fp = os.path.join(root, f)
                if os.path.exists(fp):
                    rel_path = os.path.relpath(fp, folder)
                    if keyword_clean in rel_path.lower():
                        stats = os.stat(fp)
                        size_kb = round(stats.st_size / 1024, 1)
                        matches.append((rel_path, size_kb))
                        
        if not matches:
            audit_logger.log_audit(user_id, username, f"/search {keyword}", None, True)
            await interaction.response.send_message(f"🔍 No files matching '{keyword}' were found.", ephemeral=True)
            return
            
        # Limit to top 20 matches
        results = matches[:20]
        
        embed = discord.Embed(
            title=f"🔍 Search results for '{keyword}'",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        description_lines = []
        for idx, (name, size) in enumerate(results, 1):
            description_lines.append(f"**{idx}.** `{name}` ({size} KB)")
            
        if len(matches) > 20:
            description_lines.append(f"\n*Showing first 20 of {len(matches)} matches.*")
            
        embed.description = "\n".join(description_lines)
        embed.set_footer(text=f"Total matches found: {len(matches)}")
        
        audit_logger.log_audit(user_id, username, f"/search {keyword}", None, True)
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(SearchCog(bot))
