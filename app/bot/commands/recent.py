import os
import sqlite3
import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
from app.config.config import config
from app.bot.client import security_gate
from app.logging.audit_logger import audit_logger

class RecentCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="recent", description="List top 10 recently created files")
    @security_gate(is_transfer=False)
    async def recent_command(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        username = f"{interaction.user.name}#{interaction.user.discriminator}"
        
        folder = config.SEND_FILES_PATH
        if not os.path.exists(folder) or not os.path.isdir(folder):
            audit_logger.log_audit(user_id, username, "/recent", None, False, "Folder Not Found")
            await interaction.response.send_message("❌ Monitored directory does not exist.", ephemeral=True)
            return

        recent_files = [] # list of dicts: {"name": ..., "time": datetime_obj, "size_kb": ...}
        seen_paths = set()

        # 1. Query SQLite file_events for CREATE events
        try:
            # Retrieve DB connection safely from singleton audit_logger
            db_conn = sqlite3.connect(str(config.DB_PATH))
            cursor = db_conn.cursor()
            cursor.execute("""
                SELECT file_path, timestamp FROM file_events 
                WHERE event_type = 'CREATE' 
                ORDER BY id DESC LIMIT 50
            """)
            rows = cursor.fetchall()
            db_conn.close()

            for file_path, timestamp_str in rows:
                if len(recent_files) >= 10:
                    break
                # Verify file still exists on disk
                if os.path.exists(file_path):
                    rel_path = os.path.relpath(file_path, folder)
                    if rel_path not in seen_paths:
                        stats = os.stat(file_path)
                        size_kb = round(stats.st_size / 1024, 1)
                        # Parse timestamp
                        try:
                            created_time = datetime.fromisoformat(timestamp_str)
                        except Exception:
                            created_time = datetime.fromtimestamp(stats.st_ctime)
                        
                        recent_files.append({
                            "name": rel_path,
                            "time": created_time,
                            "size_kb": size_kb
                        })
                        seen_paths.add(rel_path)
        except Exception as e:
            # Log error internally but proceed with filesystem fallback
            import logging
            logging.getLogger(__name__).error(f"Error querying SQLite in /recent: {e}")

        # 2. Fallback/Complement: Scan filesystem sorted by ctime (metadata change/creation time)
        if len(recent_files) < 10:
            fs_files = []
            for root, _, files in os.walk(folder):
                for f in files:
                    fp = os.path.join(root, f)
                    try:
                        if os.path.exists(fp):
                            rel_path = os.path.relpath(fp, folder)
                            if rel_path not in seen_paths:
                                stats = os.stat(fp)
                                fs_files.append((rel_path, stats.st_ctime, stats.st_size))
                    except OSError:
                        pass
            
            # Sort files by ctime desc
            sorted_fs_files = sorted(fs_files, key=lambda x: x[1], reverse=True)
            for rel_path, ctime, size in sorted_fs_files:
                if len(recent_files) >= 10:
                    break
                size_kb = round(size / 1024, 1)
                recent_files.append({
                    "name": rel_path,
                    "time": datetime.fromtimestamp(ctime),
                    "size_kb": size_kb
                })
                seen_paths.add(rel_path)

        if not recent_files:
            audit_logger.log_audit(user_id, username, "/recent", None, True)
            await interaction.response.send_message("📁 No files found in the monitored directory.", ephemeral=True)
            return

        embed = discord.Embed(
            title="🆕 Recently Created Files",
            color=discord.Color.orange(),
            timestamp=datetime.utcnow()
        )
        
        description_lines = []
        for idx, item in enumerate(recent_files, 1):
            formatted_date = item["time"].strftime("%Y-%m-%d %H:%M")
            description_lines.append(
                f"**{idx}.** `{item['name']}`\n"
                f"   Size: `{item['size_kb']} KB` | Created: *{formatted_date}*"
            )
            
        embed.description = "\n\n".join(description_lines)
        embed.set_footer(text="Showing up to 10 most recent created files")
        
        audit_logger.log_audit(user_id, username, "/recent", None, True)
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(RecentCog(bot))
