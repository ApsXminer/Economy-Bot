import discord
from discord.ext import commands
from datetime import datetime, timezone
import json
import os


class Logging(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Load channel IDs from config.json if it exists
        self.cmd_log_channel_id = 1390587764868776027
        self.guild_log_channel_id = 1391426042463518761
        self.bug_report_channel_id = 1391426072192614560
        try:
            if os.path.exists("config.json"):
                with open("config.json", "r") as config_file:
                    config = json.load(config_file)
                    self.cmd_log_channel_id = config.get("log_channel_id", self.cmd_log_channel_id)
                    self.guild_log_channel_id = config.get("log_channel_id", self.guild_log_channel_id)
                    self.bug_report_channel_id = config.get("bug_channel_id", self.bug_report_channel_id)
                    if "feedback_channel_id" in config:
                        self.bug_report_channel_id = config.get("feedback_channel_id", self.bug_report_channel_id)
        except (json.JSONDecodeError, KeyError):
            pass  # Use default hardcoded values if config loading fails

    @commands.Cog.listener()
    async def on_command_completion(self, ctx):
        """Logs when a command is successfully used."""
        log_channel = self.bot.get_channel(self.cmd_log_channel_id)
        if log_channel:
            em = discord.Embed(
                title="📝 Command Executed",
                color=discord.Color.blurple(),
                timestamp=datetime.now(timezone.utc)
            )
            em.add_field(name="👤 User", value=f"{ctx.author} (`{ctx.author.id}`)", inline=False)
            em.add_field(name="💬 Command", value=f"`{ctx.command.qualified_name}`", inline=False)
            em.add_field(name="📥 Message", value=f"```{ctx.message.content}```", inline=False)
            em.add_field(name="🌐 Server", value=f"{ctx.guild.name} (`{ctx.guild.id}`)", inline=False)
            em.add_field(name="📺 Channel", value=f"{ctx.channel.name} (`{ctx.channel.id}`)", inline=False)
            em.set_footer(text=f"Command by {ctx.author}", icon_url=ctx.author.display_avatar.url)
            await log_channel.send(embed=em)

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        """Logs when the bot joins a new server."""
        log_channel = self.bot.get_channel(self.guild_log_channel_id)
        if log_channel:
            em = discord.Embed(
                title="➕ Joined New Server",
                description=f"**Server Name:** {guild.name}\n**Server ID:** `{guild.id}`",
                color=discord.Color.green(),
                timestamp=datetime.now(timezone.utc)
            )
            if guild.icon:
                em.set_thumbnail(url=guild.icon.url)
            em.add_field(name="👥 Members", value=guild.member_count)
            em.add_field(name="👑 Owner", value=f"{guild.owner} (`{guild.owner.id}`)")
            await log_channel.send(embed=em)

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        """Logs when the bot leaves a server."""
        log_channel = self.bot.get_channel(self.guild_log_channel_id)
        if log_channel:
            em = discord.Embed(
                title="➖ Left a Server",
                description=f"**Server Name:** {guild.name}\n**Server ID:** `{guild.id}`",
                color=discord.Color.red(),
                timestamp=datetime.now(timezone.utc)
            )
            await log_channel.send(embed=em)

    @commands.command()
    async def bugreport(self, ctx, *, report: str):
        """Send a bug report to the bot developers with voting support."""
        log_channel = self.bot.get_channel(self.bug_report_channel_id)
        if log_channel:
            em = discord.Embed(
                title="🐞 Bug Report",
                description=report,
                color=discord.Color.orange(),
                timestamp=datetime.now(timezone.utc)
            )
            em.set_author(name=f"{ctx.author}", icon_url=ctx.author.display_avatar.url)
            em.add_field(name="🌐 Server", value=f"{ctx.guild.name} (`{ctx.guild.id}`)")
            msg = await log_channel.send(embed=em)

            # Add 👍👎 reactions for vote
            await msg.add_reaction("👍")
            await msg.add_reaction("👎")

            await ctx.send("✅ Your bug report has been submitted. Thank you!")
        else:
            await ctx.send("⚠️ Bug report system is not configured correctly.")

    @commands.command()
    async def feedback(self, ctx, *, feedback_msg: str):
        """Send feedback to the bot developers with vote reactions."""
        log_channel = self.bot.get_channel(self.bug_report_channel_id)
        if log_channel:
            em = discord.Embed(
                title="📬 New Feedback",
                description=feedback_msg,
                color=discord.Color.purple(),
                timestamp=datetime.now(timezone.utc)
            )
            em.set_author(name=f"{ctx.author}", icon_url=ctx.author.display_avatar.url)
            em.add_field(name="🌐 Server", value=f"{ctx.guild.name} (`{ctx.guild.id}`)")
            msg = await log_channel.send(embed=em)

            # Add vote reactions
            await msg.add_reaction("👍")
            await msg.add_reaction("👎")

            await ctx.send("✅ Your feedback has been submitted. Thank you!")
        else:
            await ctx.send("⚠️ Feedback system is not configured correctly.")


async def setup(bot):
    await bot.add_cog(Logging(bot))
