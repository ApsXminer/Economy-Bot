import discord
from discord.ext import commands
import aiohttp
from datetime import datetime, timezone
import json
import os

class Dev(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Load owner ID from config.json if it exists
        self.owner_id = bot.owner_id
        if not self.owner_id:
            try:
                if os.path.exists("config.json"):
                    with open("config.json", "r") as config_file:
                        config = json.load(config_file)
                        self.owner_id = config.get("owner_id", 1383706658315960330)
                else:
                    self.owner_id = 1383706658315960330
            except (json.JSONDecodeError, KeyError):
                self.owner_id = 1383706658315960330

    def is_owner():
        async def predicate(ctx):
            return ctx.author.id == ctx.bot.owner_id
        return commands.check(predicate)

    async def cog_command_error(self, ctx, error):
        if isinstance(error, commands.CheckFailure):
            return  # silently ignore
        raise error

    # Bot Identity Commands
    @commands.command(name="botname")
    @is_owner()
    async def change_name(self, ctx, *, new_name: str):
        await self.bot.user.edit(username=new_name)
        await ctx.send(f"✅ Bot name changed to `{new_name}`")

    @commands.command(name="botavatar")
    @is_owner()
    async def change_avatar(self, ctx, url: str):
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    return
                data = await resp.read()
                await self.bot.user.edit(avatar=data)
                await ctx.send("✅ Bot avatar updated.")

    @commands.command(name="botbanner")
    @is_owner()
    async def change_banner(self, ctx, url: str):
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    return
                data = await resp.read()
                await self.bot.user.edit(banner=data)
                await ctx.send("✅ Bot banner updated.")

    # Server Commands
    @commands.command(name="serverlist")
    @is_owner()
    async def server_list(self, ctx):
        em = discord.Embed(title="📋 Server List", color=discord.Color.green())
        for guild in self.bot.guilds:
            em.add_field(
                name=guild.name,
                value=f"🆔 `{guild.id}`\n👥 {guild.member_count} members\n👑 {guild.owner} ({guild.owner_id})",
                inline=False
            )
        await ctx.send(embed=em)

    @commands.command(name="guildinfo")
    @is_owner()
    async def guild_info(self, ctx, guild_id: int):
        guild = self.bot.get_guild(guild_id)
        if not guild:
            await ctx.send("❌ Bot is not in a server with that ID.")
            return

        em = discord.Embed(title=f"📑 Info for {guild.name}", color=discord.Color.blurple())
        em.set_thumbnail(url=guild.icon.url if guild.icon else discord.Embed.Empty)
        em.add_field(name="ID", value=guild.id)
        em.add_field(name="Owner", value=f"{guild.owner} ({guild.owner_id})", inline=False)
        em.add_field(name="Members", value=guild.member_count)
        em.add_field(name="Text Channels", value=len(guild.text_channels))
        em.add_field(name="Voice Channels", value=len(guild.voice_channels))
        em.add_field(name="Roles", value=len(guild.roles))

        # Try to create or fetch invite
        invite_link = None
        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).create_instant_invite:
                try:
                    invite = await channel.create_invite(max_age=300, reason="Dev info request")
                    invite_link = invite.url
                    break
                except:
                    continue
        if not invite_link:
            # fallback to existing invite links if any
            try:
                invites = await guild.invites()
                if invites:
                    invite_link = invites[0].url
            except:
                pass

        em.add_field(name="Invite", value=invite_link or "No invite available", inline=False)
        await ctx.send(embed=em)

    @commands.command(name="leaveguild")
    @is_owner()
    async def leave_guild(self, ctx, guild_id: int):
        guild = self.bot.get_guild(guild_id)
        if guild:
            await guild.leave()
            await ctx.send(f"✅ Left guild `{guild.name}` (`{guild.id}`)")

    # Announce and DM
    @commands.command()
    @is_owner()
    async def announce(self, ctx, channel: discord.TextChannel, *, msg: str):
        await channel.send(msg)
        await ctx.send(f"📢 Sent message to {channel.mention}")

    @commands.command()
    @is_owner()
    async def dm(self, ctx, user: discord.User, *, msg: str):
        try:
            await user.send(msg)
            await ctx.send(f"✉️ DM sent to `{user}`")
        except:
            await ctx.send("❌ Could not DM user.")

    # Shutdown
    @commands.command()
    @is_owner()
    async def shutdown(self, ctx):
        await ctx.send("⚠️ Shutting down...")
        await self.bot.close()

    # Add your custom useful admin-only commands here
    @commands.command()
    @is_owner()
    async def guildcount(self, ctx):
        await ctx.send(f"📊 I'm in `{len(self.bot.guilds)}` servers.")

    @commands.command()
    @is_owner()
    async def usercount(self, ctx):
        unique_users = len(set(self.bot.get_all_members()))
        await ctx.send(f"👥 I can see `{unique_users}` unique users across all servers.")

    @commands.command(name="setstatus")
    @is_owner()
    async def set_status(self, ctx, status_type: str, *, activity: str = None):
        """Set the bot's status (online, idle, dnd) with an optional activity message."""
        status_type = status_type.lower()
        if status_type == "online":
            status = discord.Status.online
        elif status_type == "idle":
            status = discord.Status.idle
        elif status_type == "dnd" or status_type == "do_not_disturb":
            status = discord.Status.dnd
        else:
            await ctx.send("❌ Invalid status type. Use 'online', 'idle', or 'dnd'.")
            return

        if activity:
            await self.bot.change_presence(status=status, activity=discord.Game(name=activity))
            await ctx.send(f"✅ Bot status set to `{status_type}` with activity `{activity}`.")
        else:
            await self.bot.change_presence(status=status)
            await ctx.send(f"✅ Bot status set to `{status_type}` with no activity.")

async def setup(bot):
    await bot.add_cog(Dev(bot))
