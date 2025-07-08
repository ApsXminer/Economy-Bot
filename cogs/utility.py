import discord
from discord.ext import commands
import time
import datetime
import json

class Utility(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.start_time = time.time()

    @commands.command()
    async def ping(self, ctx):
        """Shows the bot's latency."""
        latency = round(self.bot.latency * 1000)
        await ctx.send(f"Pong! Latency: {latency}ms")

    @commands.command()
    async def invite(self, ctx):
        """Get the bot's invite link."""
        app_info = await self.bot.application_info()
        permissions = discord.Permissions(8) # Administrator
        invite_url = discord.utils.oauth_url(app_info.id, permissions=permissions)
        await ctx.send(f"Invite me to your server: <{invite_url}>")

    @commands.command()
    async def support(self, ctx):
        """Get the link to the support server."""
        await ctx.send("Join the support server: https://discord.gg/code-verse")

    @commands.command()
    async def uptime(self, ctx):
        """Shows the bot's uptime."""
        current_time = time.time()
        uptime_seconds = int(round(current_time - self.start_time))
        uptime_str = str(datetime.timedelta(seconds=uptime_seconds))
        await ctx.send(f"Uptime: {uptime_str}")

    @commands.command(aliases=['bs'])
    async def botstats(self, ctx):
        """Shows statistics about the bot."""
        total_guilds = len(self.bot.guilds)
        total_users = len(self.bot.users)
        
        em = discord.Embed(title="Bot Statistics", color=discord.Color.blue())
        em.add_field(name="Servers", value=total_guilds)
        em.add_field(name="Users", value=total_users)
        em.set_footer(text=f"Bot created by {self.bot.get_user(self.bot.owner_id).name}")
        await ctx.send(embed=em)

    @commands.command()
    async def profile(self, ctx, member: discord.Member = None):
        """Shows a user's profile."""
        if member is None:
            member = ctx.author

        # This is not ideal, but for simplicity we'll read the file here.
        # A better solution would be a shared data manager class.
        with open("data/users.json", 'r') as f:
            users = json.load(f)
        
        user_id = str(member.id)
        if user_id not in users:
            await ctx.send("This user doesn't have a profile yet. They need to use a command first.")
            return

        user_data = users[user_id]
        
        em = discord.Embed(title=f"{member.name}'s Profile", color=member.color)
        em.set_thumbnail(url=member.avatar.url)
        
        # Economy Info
        em.add_field(name="Wallet", value=f"{user_data.get('wallet', 0)} coins")
        em.add_field(name="Bank", value=f"{user_data.get('bank', 0)} coins")
        
        # Leveling Info
        level = user_data.get('level', 1)
        xp = user_data.get('xp', 0)
        xp_needed = 5 * (level ** 2) + (50 * level) + 100
        em.add_field(name="Level", value=level)
        em.add_field(name="XP", value=f"{xp}/{xp_needed}")

        # Daily Streak
        streak = user_data.get('daily_streak', 0)
        em.add_field(name="Daily Streak", value=f"{streak} days")

        await ctx.send(embed=em)


async def setup(bot):
    await bot.add_cog(Utility(bot))
