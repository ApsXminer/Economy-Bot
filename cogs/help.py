import discord
from discord.ext import commands
import json
import os
from .emojis import emojis

class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="help")
    async def help_command(self, ctx):
        # Load configurations from config.json if it exists
        config = {}
        owner_id = self.bot.owner_id
        log_channel_id = bug_channel_id = feedback_channel_id = 0
        
        try:
            if os.path.exists("config.json"):
                with open("config.json", "r") as config_file:
                    config = json.load(config_file)
                    if not owner_id:
                        owner_id = config.get("owner_id", 1383706658315960330)
                    log_channel_id = config.get("log_channel_id", 0)
                    bug_channel_id = config.get("bug_channel_id", 0)
                    feedback_channel_id = config.get("feedback_channel_id", 0)
            else:
                if not owner_id:
                    owner_id = 1383706658315960330
        except (json.JSONDecodeError, KeyError):
            if not owner_id:
                owner_id = 1383706658315960330
                
        is_owner = ctx.author.id == owner_id

        # Initial embed with a brief overview
        embed = discord.Embed(
            title=f"{emojis['economy']} THIS IS BOT HELP MENU",
            description=f"Hey {ctx.author.mention},\nHere are the available command categories.",
            color=discord.Color.blurple()
        )
        embed.set_thumbnail(url=self.bot.user.avatar.url)

        # Define categories and their commands
        categories = {
            "economy": {
                "name": f"{emojis['economy']} Economy",
                "value": (
                    "`balance`, `work`, `daily`, `withdraw`, `deposit`, `give`,\n"
                    "`shop`, `buy`, `inventory`, `use`, `leaderboard`,\n"
                    "`fish`, `hunt`, `dig`, `hack`, `mine`, `explore`,\n"
                    "`upgraded_fish`, `upgrade`,\n"
                    "`petshop`, `adopt`, `joblist`, `apply`, `paycheck`, `quit`,\n"
                    "`slots`, `gamble`, `beg`, `trivia`, `coinflip`\n"
                    "`rob`, `crime`,\n"
                    "`sell`, `sell all`, `sell prices`"
                )
            },
            "utility": {
                "name": f"{emojis['utility']} Utility",
                "value": "`ping`, `invite`, `support`, `uptime`, `botstats`, `profile`"
            },
            "configuration": {
                "name": f"{emojis['configuration']} Configuration",
                "value": "`bugreport`, `feedback`, `setprefix`, `viewprefix`"
            }
        }

        for key, cat in categories.items():
            embed.add_field(name=cat["name"], value=f"`{ctx.prefix}help {key}`", inline=True)

        if is_owner:
            categories["dev"] = {
                "name": f"{emojis['developer']} Dev (Owner Only)",
                "value": (
                    "`botname`, `botavatar`, `botbanner`, `serverlist`,\n"
                    "`leaveguild`, `announce`, `dm`, `shutdown`,\n"
                    "`guildcount`, `usercount`, `guildinfo`, `setprice`,\n"
                    "`setstatus`"
                )
            }

        # Create dropdown menu
        class HelpDropdown(discord.ui.Select):
            def __init__(self, bot_user_avatar):
                self.bot_user_avatar = bot_user_avatar
                options = []
                for key, cat in categories.items():
                    emoji_part = cat["name"].split(" ")[0]
                    label_part = " ".join(cat["name"].split(" ")[1:])
                    options.append(discord.SelectOption(label=label_part, value=key, emoji=emoji_part))

                super().__init__(placeholder="Select a category...", min_values=1, max_values=1, options=options)

            async def callback(self, interaction: discord.Interaction):
                if interaction.user.id != ctx.author.id:
                    await interaction.response.send_message("This dropdown is not for you!", ephemeral=True)
                    return

                category_key = self.values[0]
                category = categories[category_key]
                new_embed = discord.Embed(
                    title=f"{category['name']} Commands",
                    description=category['value'],
                    color=discord.Color.blurple()
                )
                new_embed.set_thumbnail(url=self.bot_user_avatar)
                await interaction.response.edit_message(embed=new_embed)

        view = discord.ui.View(timeout=60)
        view.add_item(HelpDropdown(self.bot.user.avatar.url))
        # Add a button for support server
        support_button = discord.ui.Button(label="Support Server", style=discord.ButtonStyle.link, url="https://discord.gg/code-verse")
        view.add_item(support_button)

        await ctx.send(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(Help(bot))
