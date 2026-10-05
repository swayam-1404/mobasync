import os
import pwd
import psutil
import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
from app.bot.client import security_gate
from app.logging.audit_logger import audit_logger

class ProcessesCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="processes", description="Show top CPU and memory consuming processes running on the PC")
    @security_gate(is_transfer=False)
    async def processes_command(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        username = f"{interaction.user.name}#{interaction.user.discriminator}"
        
        # Determine username of the runner process
        try:
            current_user = pwd.getpwuid(os.getuid()).pw_name
        except Exception:
            current_user = None

        cpu_list = []
        mem_list = []
        
        # Iterate over all running processes
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info', 'username']):
            try:
                info = proc.info
                # Calculate Memory in MB
                mem_bytes = info['memory_info'].rss if info['memory_info'] else 0
                mem_mb = round(mem_bytes / (1024 * 1024), 1)
                
                proc_data = {
                    "pid": info['pid'],
                    "name": info['name'],
                    "cpu": info['cpu_percent'] or 0.0,
                    "mem": mem_mb,
                    "username": info['username']
                }
                
                # Filter to current user's processes or active processes to avoid spamming system daemons
                if not current_user or info['username'] == current_user:
                    cpu_list.append(proc_data)
                    mem_list.append(proc_data)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass

        # Sort by CPU usage descending, take top 5
        top_cpu = sorted(cpu_list, key=lambda x: x['cpu'], reverse=True)[:5]
        
        # Sort by memory RSS descending, take top 5
        top_mem = sorted(mem_list, key=lambda x: x['mem'], reverse=True)[:5]

        embed = discord.Embed(
            title="📊 Active System Processes",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        # Format Top CPU Processes field
        cpu_lines = []
        for p in top_cpu:
            cpu_lines.append(f"`{p['pid']}` **{p['name']}** - `{p['cpu']}%` CPU | `{p['mem']} MB` RAM")
        embed.add_field(
            name="🔥 Top CPU Consumers",
            value="\n".join(cpu_lines) if cpu_lines else "No active user processes.",
            inline=False
        )

        # Format Top Memory Processes field
        mem_lines = []
        for p in top_mem:
            mem_lines.append(f"`{p['pid']}` **{p['name']}** - `{p['mem']} MB` RAM | `{p['cpu']}%` CPU")
        embed.add_field(
            name="💾 Top Memory Consumers",
            value="\n".join(mem_lines) if mem_lines else "No active user processes.",
            inline=False
        )

        embed.set_footer(text=f"Filtered by local user: {current_user or 'All'}")

        audit_logger.log_audit(user_id, username, "/processes", None, True)
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(ProcessesCog(bot))
