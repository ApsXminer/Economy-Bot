import discord
from discord.ext import commands
import json
import os

class Prefix(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.prefix_file = "data/prefixes.json"

    def get_prefix_data(self):
        if not os.path.exists(self.prefix_file):
            return {}
        try:
            with open(self.prefix_file, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}

    def save_prefix_data(self, data):
        os.makedirs("data", exist_ok=True)
        with open(self.prefix_file, "w") as f:
            json.dump(data, f, indent=4)

    @commands.command(name="setprefix", help="Change the bot prefix for this server (owner only).")
    @commands.has_permissions(administrator=True)
    async def setprefix(self, ctx, new_prefix: str):
        if ctx.author.id != ctx.guild.owner_id:
            return await ctx.send(embed=discord.Embed(
                description="❌ Only the **server owner** can change the prefix.",
                color=discord.Color.red()
            ))

        new_prefix = new_prefix.strip()
        if not new_prefix.endswith(" "):
            new_prefix += " "

        prefixes = self.get_prefix_data()
        prefixes[str(ctx.guild.id)] = new_prefix
        self.save_prefix_data(prefixes)

        embed = discord.Embed(
            title="✅ Prefix Updated",
            description=f"New prefix for **{ctx.guild.name}** is now `{new_prefix}`",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)

    @commands.command(name="viewprefix", help="View the current prefix for this server.")
    async def viewprefix(self, ctx):
        prefixes = self.get_prefix_data()
        prefix = prefixes.get(str(ctx.guild.id), "cx ")

        embed = discord.Embed(
            title="🔧 Current Prefix",
            description=f"The current prefix for this server is: `{prefix}`",
            color=discord.Color.blurple()
        )
        await ctx.send(embed=embed)

    def get_np_users(self):
        np_file = "data/np_users.json"
        if not os.path.exists(np_file):
            return {}
        try:
            with open(np_file, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}

    def save_np_users(self, data):
        os.makedirs("data", exist_ok=True)
        with open("data/np_users.json", "w") as f:
            json.dump(data, f, indent=4)

    def parse_duration(self, duration_str):
        """Parse duration string to calculate expiration time."""
        import datetime
        duration_str = duration_str.lower().strip()
        if duration_str == "lifetime":
            return "lifetime"
        
        time_units = {
            'm': ('minutes', 1),
            'h': ('hours', 1),
            'd': ('days', 1),
            'w': ('weeks', 1),
            'week': ('weeks', 1),
            'month': ('days', 30),
            'y': ('days', 365),
            'year': ('days', 365)
        }
        
        try:
            for unit, (unit_name, multiplier) in time_units.items():
                if duration_str.endswith(unit):
                    value = int(duration_str[:-len(unit)])
                    if unit_name == 'weeks':
                        value *= 7  # Convert weeks to days
                    elif unit_name == 'days' and multiplier > 1:
                        value *= multiplier  # Handle months and years
                    return (datetime.datetime.now() + datetime.timedelta(**{unit_name: value})).isoformat()
            return None
        except (ValueError, KeyError):
            return None

    @commands.group(name="np", help="Manage no-prefix access for users (bot owner only).")
    async def np(self, ctx):
        if ctx.invoked_subcommand is None:
            embed = discord.Embed(
                title="No-Prefix Commands",
                description=(
                    "Use `np add @user [duration]` to grant no-prefix access for a specific time.\n"
                    "Durations: `10m`, `1h`, `12h`, `24h`, `1week`, `1month`, `3month`, `1year`, `3year`, `lifetime`.\n"
                    "Use `np remove @user` to revoke no-prefix access.\n"
                    "Use `np list` to view users with no-prefix access."
                ),
                color=discord.Color.blurple()
            )
            await ctx.send(embed=embed)

    @np.command(name="add", help="Add a user to no-prefix access with optional duration (bot owner only).")
    async def np_add(self, ctx, user: discord.User, duration: str = "lifetime"):
        if ctx.author.id != self.bot.owner_id:
            await ctx.send(embed=discord.Embed(
                description="❌ Only the **bot owner** can manage no-prefix access.",
                color=discord.Color.red()
            ))
            return

        expires_at = self.parse_duration(duration)
        if expires_at is None:
            await ctx.send(embed=discord.Embed(
                title="❌ Invalid Duration",
                description=(
                    "Invalid duration format. Use formats like `10m`, `1h`, `12h`, `24h`, `1week`, "
                    "`1month`, `3month`, `1year`, `3year`, or `lifetime`."
                ),
                color=discord.Color.red()
            ))
            return

        np_users = self.get_np_users()
        np_users[str(user.id)] = {
            "active": True,
            "expires_at": expires_at
        }
        self.save_np_users(np_users)

        duration_text = "for a lifetime" if expires_at == "lifetime" else f"until <t:{int(float(expires_at.split('.')[0].replace('-', '').replace(':', '').replace('T', '')))}:F>"
        embed = discord.Embed(
            title="✅ No-Prefix Access Granted",
            description=f"{user.mention} can now use commands without a prefix {duration_text}.",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)

    @np.command(name="remove", help="Remove a user from no-prefix access (bot owner only).")
    async def np_remove(self, ctx, user: discord.User):
        if ctx.author.id != self.bot.owner_id:
            await ctx.send(embed=discord.Embed(
                description="❌ Only the **bot owner** can manage no-prefix access.",
                color=discord.Color.red()
            ))
            return

        np_users = self.get_np_users()
        if str(user.id) in np_users:
            del np_users[str(user.id)]
            self.save_np_users(np_users)
            embed = discord.Embed(
                title="✅ No-Prefix Access Revoked",
                description=f"{user.mention} can no longer use commands without a prefix.",
                color=discord.Color.green()
            )
        else:
            embed = discord.Embed(
                title="❌ User Not Found",
                description=f"{user.mention} does not have no-prefix access.",
                color=discord.Color.red()
            )
        await ctx.send(embed=embed)

    @np.command(name="list", help="List users with no-prefix access (bot owner only).")
    async def np_list(self, ctx):
        if ctx.author.id != self.bot.owner_id:
            await ctx.send(embed=discord.Embed(
                description="❌ Only the **bot owner** can manage no-prefix access.",
                color=discord.Color.red()
            ))
            return

        np_users = self.get_np_users()
        if not np_users:
            embed = discord.Embed(
                title="No-Prefix Users",
                description="No users have no-prefix access.",
                color=discord.Color.blurple()
            )
        else:
            user_list = []
            for user_id, data in np_users.items():
                expires_at = data.get("expires_at", "lifetime")
                active = data.get("active", False)
                status = "Active" if active else "Expired"
                expiry_text = "Lifetime" if expires_at == "lifetime" else f"Expires: <t:{int(float(expires_at.split('.')[0].replace('-', '').replace(':', '').replace('T', '')))}:R>"
                user_list.append(f"<@{user_id}> - {status} ({expiry_text})")
            embed = discord.Embed(
                title="No-Prefix Users",
                description="Users with no-prefix access:\n" + "\n".join(user_list),
                color=discord.Color.blurple()
            )
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Prefix(bot))
