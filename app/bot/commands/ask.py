import os
import time
import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timedelta
from app.bot.client import security_gate
from app.logging.audit_logger import audit_logger

class AskCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ask", description="Show recent file changes on your laptop outside of SEND_FILES (last 24h)")
    @security_gate(is_transfer=False)
    async def ask_command(self, interaction: discord.Interaction):
        # Defer immediately as scanning the home directory can take a few seconds
        await interaction.response.defer(ephemeral=True)
        
        user_id = interaction.user.id
        username = f"{interaction.user.name}#{interaction.user.discriminator}"
        
        home_dir = "/home/swayam-sahu"
        if not os.path.exists(home_dir):
            audit_logger.log_audit(user_id, username, "/ask", None, False, "Home Directory Not Found")
            await interaction.followup.send("❌ Home directory not found.", ephemeral=True)
            return

        exclude_dirs = {
            "SEND_FILES", "Manager", "venv", "node_modules", 
            "__pycache__", ".config", ".cache", ".local", 
            ".gemini", ".mozilla", ".thunderbird", ".gnome", 
            ".ssh", ".cargo", ".rustup", ".npm", ".git",
            "Downloads", "Cache", "caches", "Caches",
            ".var", ".clf", ".cups", ".gconf", ".pki",
            ".themes", ".icons", ".flatpak"
        }

        changed_files = []
        now = time.time()
        time_limit = 24 * 3600  # 24 hours in seconds
        max_files_scanned = 15000
        scanned_count = 0

        # Traverse home directory
        for root, dirs, files in os.walk(home_dir):
            # Prune directories starting with '.' or in exclude_dirs in-place
            dirs[:] = [
                d for d in dirs 
                if not d.startswith('.') and d not in exclude_dirs
            ]
            
            for f in files:
                if f.startswith('.'):
                    continue
                
                fp = os.path.join(root, f)
                scanned_count += 1
                
                # Safeguard against scanning too many files
                if scanned_count > max_files_scanned:
                    break
                
                try:
                    stats = os.stat(fp)
                    mtime = stats.st_mtime
                    if now - mtime <= time_limit:
                        rel_path = os.path.relpath(fp, home_dir)
                        size_kb = round(stats.st_size / 1024, 1)
                        changed_files.append((rel_path, mtime, size_kb))
                except OSError:
                    pass
            
            if scanned_count > max_files_scanned:
                break

        if not changed_files:
            audit_logger.log_audit(user_id, username, "/ask", None, True)
            await interaction.followup.send("🔍 No files modified in your home directory (outside SEND_FILES) in the last 24 hours.", ephemeral=True)
            return

        # Sort by modification time desc, limit to top 15
        sorted_files = sorted(changed_files, key=lambda x: x[1], reverse=True)[:15]

        embed = discord.Embed(
            title="🔍 Recent File Changes (Outside SEND_FILES)",
            description="Here are the files modified or created in your home directory in the last 24 hours:",
            color=discord.Color.teal(),
            timestamp=datetime.utcnow()
        )

        lines = []
        for idx, (name, mtime, size_kb) in enumerate(sorted_files, 1):
            mod_date = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
            # Limit name length if too long
            display_name = name if len(name) < 70 else "..." + name[-67:]
            lines.append(f"**{idx}.** `{display_name}`\n   Size: `{size_kb} KB` | Modified: *{mod_date}*")

        embed.description = "\n\n".join(lines)
        
        # Add a warning if we aborted scanning early
        if scanned_count > max_files_scanned:
            embed.set_footer(text=f"Showing top matches. Scan limit reached ({max_files_scanned} files checked).")
        else:
            embed.set_footer(text=f"Scan complete. Checked {scanned_count} files.")

        audit_logger.log_audit(user_id, username, "/ask", None, True)
        await interaction.followup.send(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(AskCog(bot))
