import discord
from datetime import datetime
from typing import List, Tuple

class FilePaginationView(discord.ui.View):
    """View to handle paginated listing of files in the SEND_FILES folder."""
    
    def __init__(self, files: List[Tuple[str, float, str]], author_id: int):
        super().__init__(timeout=60)
        self.files = files
        self.author_id = author_id
        self.current_page = 0
        self.per_page = 5
        self.total_pages = max(1, (len(files) - 1) // self.per_page + 1)
        
        self.update_buttons()

    def update_buttons(self):
        """Enable or disable buttons based on current page index."""
        self.prev_page_btn.disabled = (self.current_page == 0)
        self.next_page_btn.disabled = (self.current_page >= self.total_pages - 1)

    def get_page_content(self) -> Tuple[str, discord.Embed]:
        """Generate the embed output for the current page."""
        start = self.current_page * self.per_page
        end = start + self.per_page
        page_files = self.files[start:end]
        
        embed = discord.Embed(
            title="📁 Monitored Files inside SEND_FILES",
            color=discord.Color.dark_blue(),
            timestamp=datetime.utcnow()
        )
        
        description_lines = []
        for idx, (name, size_kb, mod_time) in enumerate(page_files, start + 1):
            description_lines.append(
                f"**{idx}.** `{name}`\n"
                f"   Size: `{size_kb} KB` | Modified: *{mod_time}*\n"
            )
            
        embed.description = "\n".join(description_lines) if description_lines else "No files available."
        embed.set_footer(text=f"Page {self.current_page + 1} of {self.total_pages} | Total Files: {len(self.files)}")
        
        return "", embed

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Ensure only the user who ran the command can paginate."""
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("Access Denied: You cannot control this menu.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="⬅️ Previous", style=discord.ButtonStyle.grey)
    async def prev_page_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page > 0:
            self.current_page -= 1
            self.update_buttons()
            content, embed = self.get_page_content()
            await interaction.response.edit_message(content=content, embed=embed, view=self)

    @discord.ui.button(label="Next ➡️", style=discord.ButtonStyle.grey)
    async def next_page_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.update_buttons()
            content, embed = self.get_page_content()
            await interaction.response.edit_message(content=content, embed=embed, view=self)
