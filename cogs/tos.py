import discord
from discord.ext import commands
import json
import os

TOS_FILE = "data/accepted_tos.json"

def get_accepted_tos():
    """Reads the list of users who have accepted the ToS."""
    if not os.path.exists(TOS_FILE):
        return []
    with open(TOS_FILE, 'r') as f:
        return json.load(f)

def add_user_to_tos(user_id: int):
    """Adds a user to the list of those who have accepted the ToS."""
    accepted = get_accepted_tos()
    if user_id not in accepted:
        accepted.append(user_id)
        with open(TOS_FILE, 'w') as f:
            json.dump(accepted, f, indent=4)

class TosView(discord.ui.View):
    def __init__(self, author: discord.Member):
        super().__init__(timeout=180.0)
        self.author = author
        self.accepted = False

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author.id:
            await interaction.response.send_message("This is not for you!", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="I Accept", style=discord.ButtonStyle.green)
    async def accept_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        add_user_to_tos(self.author.id)
        self.accepted = True
        
        # Edit the original message
        new_embed = interaction.message.embeds[0]
        new_embed.description = "You have accepted the Terms of Service. Welcome!"
        new_embed.color = discord.Color.green()
        
        # Disable buttons
        for item in self.children:
            item.disabled = True
        
        await interaction.response.edit_message(embed=new_embed, view=self)
        self.stop()

class Tos(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @staticmethod
    async def require_tos(ctx: commands.Context):
        """A check that ensures a user has accepted the ToS."""
        if ctx.command.name == 'help': # Allow help command
             return True

        accepted_users = get_accepted_tos()
        if ctx.author.id in accepted_users:
            return True

        # User has not accepted ToS
        em = discord.Embed(
            title="Terms of Service",
            description=(
                "Welcome! Before you can use Fyno, you must agree to our Terms of Service.\n\n"
                "**1. Data Collection & Privacy**\n"
                "We store your Discord User ID and command usage data to provide and improve our services. We respect your privacy and will not share this data with third parties.\n\n"
                "**2. Fair Use Policy**\n"
                "Do not abuse, spam, or exploit bugs in the bot. Automated scripts or macros are strictly forbidden. Violation of this policy will result in a permanent blacklist.\n\n"
                "**3. Economy & Virtual Items**\n"
                "All currency and items within the bot are virtual and hold no real-world value. We are not responsible for any loss of virtual currency or items due to bugs, data loss, or other issues.\n\n"
                "**4. Code of Conduct**\n"
                "You must adhere to Discord's own Terms of Service while using this bot. Any form of harassment or hate speech conducted through the bot is not tolerated.\n\n"
                "By clicking 'I Accept', you acknowledge that you have read and agree to these terms."
            ),
            color=discord.Color.blue()
        )
        view = TosView(ctx.author)
        # Using ephemeral=True makes the message only visible to the user.
        # The check will fail if the message is not visible for the bot to edit later.
        # A better approach is to send a public message and delete it after a timeout.
        # For now, we will send it publicly.
        message = await ctx.send(embed=em, view=view)
        
        await view.wait()
        
        # Clean up the ToS message after timeout if not accepted
        if not view.accepted:
            try:
                await message.delete()
            except discord.NotFound:
                pass # Message was already deleted or could not be found

        return view.accepted

async def setup(bot):
    # Add the check globally
    bot.add_check(Tos.require_tos)
    await bot.add_cog(Tos(bot))
