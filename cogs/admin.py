import discord
from discord.ext import commands
import json
import os

class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data_file = "data/users.json"
        self.blacklist_file = "data/blacklist.json"
        self.prefix_file = "data/prefixes.json"

    async def get_prefixes(self):
        """Reads the prefixes from the JSON file."""
        if not os.path.exists(self.prefix_file):
            with open(self.prefix_file, 'w') as f:
                json.dump({}, f)
            return {}
        with open(self.prefix_file, 'r') as f:
            return json.load(f)

    async def save_prefixes(self, prefixes):
        """Saves the prefixes to the JSON file."""
        with open(self.prefix_file, 'w') as f:
            json.dump(prefixes, f, indent=4)

    async def get_blacklist(self):
        """Reads the blacklist from the JSON file."""
        if not os.path.exists(self.blacklist_file):
            with open(self.blacklist_file, 'w') as f:
                json.dump([], f)
            return []
        with open(self.blacklist_file, 'r') as f:
            return json.load(f)

    async def save_blacklist(self, blacklist):
        """Saves the blacklist to the JSON file."""
        with open(self.blacklist_file, 'w') as f:
            json.dump(blacklist, f, indent=4)

    async def get_bank_data(self):
        """Reads user data from the JSON file."""
        with open(self.data_file, 'r') as f:
            users = json.load(f)
        return users

    async def save_bank_data(self, users):
        """Saves user data to the JSON file."""
        with open(self.data_file, 'w') as f:
            json.dump(users, f, indent=4)

    @commands.group(hidden=True, invoke_without_command=True)
    @commands.is_owner()
    async def admin(self, ctx):
        """Admin command group."""
        await ctx.send("Invalid admin command. Use `cx help admin` to see available commands.")

    @admin.command(name="addmoney")
    @commands.has_permissions(administrator=True)
    async def add_money(self, ctx, member: discord.Member, amount: int):
        """Adds a specified amount of money to a user's wallet."""
        users = await self.get_bank_data()
        user_id = str(member.id)
        if user_id not in users:
            await ctx.send("This user does not have an account.")
            return
        users[user_id]["wallet"] += amount
        await self.save_bank_data(users)
        await ctx.send(f"Added {amount} coins to {member.mention}'s wallet.")

    @admin.command(name="removemoney")
    @commands.has_permissions(administrator=True)
    async def remove_money(self, ctx, member: discord.Member, amount: int):
        """Removes a specified amount of money from a user's wallet."""
        users = await self.get_bank_data()
        user_id = str(member.id)
        if user_id not in users:
            await ctx.send("This user does not have an account.")
            return
        users[user_id]["wallet"] -= amount
        await self.save_bank_data(users)
        await ctx.send(f"Removed {amount} coins from {member.mention}'s wallet.")

    @admin.command(name="resetacc")
    @commands.has_permissions(administrator=True)
    async def reset_account(self, ctx, member: discord.Member):
        """Resets a user's account to the default state."""
        users = await self.get_bank_data()
        user_id = str(member.id)
        if user_id not in users:
            await ctx.send("This user does not have an account to reset.")
            return
        users[user_id] = {"wallet": 100, "bank": 0, "level": 1, "xp": 0, "inventory": [], "daily_streak": 0, "last_daily": None}
        await self.save_bank_data(users)
        await ctx.send(f"Reset {member.mention}'s account.")

    @admin.command(name="reload")
    @commands.is_owner()
    async def reload_cog(self, ctx, cog_name: str):
        """Reloads a cog."""
        try:
            await self.bot.reload_extension(f"cogs.{cog_name}")
            await ctx.send(f"Reloaded `{cog_name}` cog.")
        except Exception as e:
            await ctx.send(f"Error reloading cog: {e}")

    @admin.command(name="blacklist")
    @commands.is_owner()
    async def blacklist_user(self, ctx, member: discord.Member):
        """Blacklists a user from using the bot."""
        blacklist = await self.get_blacklist()
        if member.id in blacklist:
            await ctx.send("This user is already blacklisted.")
            return
        blacklist.append(member.id)
        await self.save_blacklist(blacklist)
        await ctx.send(f"{member.mention} has been blacklisted.")

    @admin.command(name="unblacklist")
    @commands.is_owner()
    async def unblacklist_user(self, ctx, member: discord.Member):
        """Unblacklists a user."""
        blacklist = await self.get_blacklist()
        if member.id not in blacklist:
            await ctx.send("This user is not blacklisted.")
            return
        blacklist.remove(member.id)
        await self.save_blacklist(blacklist)
        await ctx.send(f"{member.mention} has been unblacklisted.")


async def setup(bot):
    await bot.add_cog(Admin(bot))
