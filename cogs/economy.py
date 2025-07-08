import discord
from discord.ext import commands, tasks
import json
import random
import os
from datetime import datetime, timedelta
import asyncio
from .emojis import emojis

class ConfirmView(discord.ui.View):
    def __init__(self, author: discord.Member):
        super().__init__(timeout=60.0)
        self.author = author
        self.confirmed = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author.id:
            await interaction.response.send_message("This is not for you!", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.confirmed = True
        await interaction.response.defer()
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.confirmed = False
        await interaction.response.defer()
        self.stop()

class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data_file = "data/users.json"
        self.shop_items = [
            {"name": "Fishing Rod", "price": 250, "description": "Use to go fishing."},
            {"name": "Hunting Rifle", "price": 500, "description": "Use to go hunting."},
            {"name": "Shovel", "price": 100, "description": "Use to dig for treasure."},
            {"name": "Laptop", "price": 1000, "description": "Use to hack for money."},
            {"name": "Pickaxe", "price": 300, "description": "Use to mine for gems."},
            {"name": "Energy Drink", "price": 50, "description": "Reduces work cooldown by 5 minutes. (Consumable)"},
            {"name": "Medkit", "price": 150, "description": "Heals you after a failed rob attempt. (Consumable)"}
        ]
        self.career_options = [
            {"name": "Programmer", "payout_min": 300, "payout_max": 700, "cooldown": 3600, "requirements": []},
            {"name": "Chef", "payout_min": 200, "payout_max": 500, "cooldown": 2400, "requirements": []},
            {"name": "Gamer", "payout_min": 100, "payout_max": 300, "cooldown": 1800, "requirements": []}
        ]
        self.pet_options = [
            {"name": "Dog", "price": 750, "bonus": 0.05, "description": "Earn 5% more from work."},
            {"name": "Cat", "price": 600, "bonus": 0.03, "description": "Earn 3% more from daily."},
            {"name": "Parrot", "price": 400, "bonus": 0.02, "description": "Small chance to find extra coins."}
        ]
        self.sellable_items = {
            "rare pelt": 250,
            "old relic": 150,
            "shiny bracelet": 200,
            "rare gem": 700,
            "gold ore": 300,
            "diamond": 1200,
            "upgraded fishing rod": 200, 
            "hunting rifle": 250,
            "laptop": 500,
            "pickaxe": 150,
            "shovel": 50,
            "fishing rod": 100,
            # Fish sell prices
            "salmon": 40,
            "tuna": 60,
            "cod": 30,
            "sardine": 15,
            "rare salmon": 80,
            "giant tuna": 120,
            "deep sea cod": 70,
            "golden fish": 500,
            "diamond ring": 1000,
            # Other items you might want to add for selling
            "apple": 20,
            "orange": 25,
            "banana": 15
        }
        self.fish_types = ["salmon", "tuna", "cod", "sardine", "rare salmon", "giant tuna", "deep sea cod", "golden fish", "shiny bracelet", "diamond ring"]
        self.interest_task.start()
        self.tax_task.start()
        self.ensure_data_file()

    def cog_unload(self):
        self.interest_task.cancel()
        self.tax_task.cancel()

    def ensure_data_file(self):
        os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
        if not os.path.exists(self.data_file):
            with open(self.data_file, 'w') as f:
                json.dump({}, f)

    @tasks.loop(hours=24)
    async def interest_task(self):
        with open('config.json', 'r') as f:
            config = json.load(f)
        interest_rate = config.get('interest_rate', 0.01)

        users = await self.get_bank_data()
        for user_id in users:
            if users[user_id]["bank"] > 0:
                interest = int(users[user_id]["bank"] * interest_rate)
                users[user_id]["bank"] += interest
        await self.save_bank_data(users)
        print(f"Applied daily interest of {interest_rate * 100}% to all bank accounts.")

    @interest_task.before_loop
    async def before_interest_task(self):
        await self.bot.wait_until_ready()

    @tasks.loop(hours=24)
    async def tax_task(self):
        with open('config.json', 'r') as f:
            config = json.load(f)
        tax_rate = config.get('tax_rate', 0.02)

        users = await self.get_bank_data()
        for user_id in users:
            if users[user_id]["wallet"] > 0:
                tax = int(users[user_id]["wallet"] * tax_rate)
                users[user_id]["wallet"] -= tax
                try:
                    user = await self.bot.fetch_user(int(user_id))
                    await user.send(f"You have been taxed **{tax:,}** coins ({tax_rate * 100}% of your wallet). Your new wallet balance is **{users[user_id]['wallet']:,}** coins.")
                except discord.Forbidden:
                    print(f"Could not send tax DM to user {user_id} (DMs disabled).")
                except Exception as e:
                    print(f"Failed to send tax DM to user {user_id}: {e}")

        await self.save_bank_data(users)
        print(f"Applied daily tax of {tax_rate * 100}% to all wallets.")

    @tax_task.before_loop
    async def before_tax_task(self):
        await self.bot.wait_until_ready()

    async def open_account(self, user: discord.Member):
        users = await self.get_bank_data()
        user_id = str(user.id)
        if user_id not in users:
            # Initialize new user with all default keys
            users[user_id] = {
                "wallet": 100,
                "bank": 0,
                "level": 1,
                "xp": 0,
                "inventory": [],
                "daily_streak": 0,
                "last_daily": None,
                "pet": None,
                "job": None
            }
            await self.save_bank_data(users)
            return True
        else:
            # Ensure all new keys are present for existing users
            # This handles schema changes for existing users gracefully
            modified = False
            if "inventory" not in users[user_id]:
                users[user_id]["inventory"] = []
                modified = True
            if "daily_streak" not in users[user_id]:
                users[user_id]["daily_streak"] = 0
                modified = True
            if "last_daily" not in users[user_id]:
                users[user_id]["last_daily"] = None
                modified = True
            if "pet" not in users[user_id]:
                users[user_id]["pet"] = None
                modified = True
            if "job" not in users[user_id]:
                users[user_id]["job"] = None
                modified = True
            
            if modified:
                await self.save_bank_data(users)
            return False

    async def get_bank_data(self):
        with open(self.data_file, 'r') as f:
            users = json.load(f)
        return users

    async def save_bank_data(self, users):
        with open(self.data_file, 'w') as f:
            json.dump(users, f, indent=4)

    async def add_xp(self, user_id, amount):
        users = await self.get_bank_data()
        users[user_id]["xp"] += amount
        current_level = users[user_id]["level"]
        xp_needed = current_level * 100 + 50 # XP needed to level up increases with level
        
        level_up_occurred = False
        if users[user_id]["xp"] >= xp_needed:
            users[user_id]["level"] += 1
            users[user_id]["xp"] -= xp_needed # Carry over excess XP
            level_up_occurred = True
        
        await self.save_bank_data(users)
        return level_up_occurred

    @commands.command(aliases=['bal', 'cash'])
    async def balance(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        await self.open_account(member)
        users = await self.get_bank_data()
        user_id = str(member.id)
        wallet_amt = users[user_id]["wallet"]
        bank_amt = users[user_id]["bank"]
        level = users[user_id]["level"]
        xp = users[user_id]["xp"]
        xp_needed = level * 100 + 50
        pet = users[user_id]["pet"]
        job = users[user_id]["job"]

        em = discord.Embed(title=f"{emojis['money_bag']} {member.name}'s Financial Report {emojis['money_bag']}", color=discord.Color.green())
        em.add_field(name=f"{emojis['wallet']} Wallet", value=f"**{wallet_amt:,.0f}** coins", inline=True)
        em.add_field(name=f"{emojis['bank']} Bank", value=f"**{bank_amt:,.0f}** coins", inline=True)
        em.add_field(name=f"{emojis['levelup_gif']} Level", value=f"**{level}** (XP: {xp}/{xp_needed})", inline=True)
        em.add_field(name=f"{emojis['green_pet']} Pet", value=f"{pet if pet else 'None'}", inline=True)
        em.add_field(name=f"{emojis['worker']} Job", value=f"{job if job else 'Unemployed'}", inline=True)
        await ctx.send(embed=em)

    @commands.command(name="bank")
    async def bank_info(self, ctx):
        with open('config.json', 'r') as f:
            config = json.load(f)
        interest_rate = config.get('interest_rate', 0.01)
        tax_rate = config.get('tax_rate', 0.02)

        await self.open_account(ctx.author)
        users = await self.get_bank_data()
        user_id = str(ctx.author.id)
        bank_amt = users[user_id]["bank"]

        em = discord.Embed(title=f"{emojis['bank']} Bank Information", color=discord.Color.blue())
        em.add_field(name="Your Bank Balance", value=f"**{bank_amt:,}** coins", inline=False)
        em.add_field(name="Daily Interest Rate", value=f"**{interest_rate * 100:.2f}%**", inline=False)
        em.add_field(name="Daily Tax Rate", value=f"**{tax_rate * 100:.2f}%** (on wallet)", inline=False)
        await ctx.send(embed=em)

    @commands.command()
    @commands.is_owner()
    async def setinterest(self, ctx, rate: float):
        if not (0 <= rate <= 1):
            await ctx.send("Interest rate must be between 0 and 1 (e.g., 0.01 for 1%).")
            return
        
        with open('config.json', 'r+') as f:
            config = json.load(f)
            config['interest_rate'] = rate
            f.seek(0)
            json.dump(config, f, indent=4)
            f.truncate()
        
        await ctx.send(f"Daily interest rate has been set to **{rate * 100:.2f}%**.")

    @commands.command()
    @commands.is_owner()
    async def settax(self, ctx, rate: float):
        if not (0 <= rate <= 1):
            await ctx.send("Tax rate must be between 0 and 1 (e.g., 0.02 for 2%).")
            return
        
        with open('config.json', 'r+') as f:
            config = json.load(f)
            config['tax_rate'] = rate
            f.seek(0)
            json.dump(config, f, indent=4)
            f.truncate()
        
        await ctx.send(f"Daily tax rate has been set to **{rate * 100:.2f}%**.")

    @commands.command(aliases=['wrk'])
    @commands.cooldown(1, 1800, commands.BucketType.user)
    async def work(self, ctx):
        await self.open_account(ctx.author)
        users = await self.get_bank_data()
        user_id = str(ctx.author.id)
        
        earnings = random.randrange(50, 201)
        if users[user_id]["pet"] == "Dog":
            earnings = int(earnings * 1.05)

        users[user_id]["wallet"] += earnings
        level_up = await self.add_xp(user_id, 10)
        await self.save_bank_data(users)
        
        response = f"You worked diligently and earned **{earnings}** coins! {emojis['money']}"
        if level_up:
            response += f"\n{emojis['levelup_gif']} Congratulations! You leveled up to **Level {users[user_id]['level']}**!"
        await ctx.send(response)

    @commands.command(aliases=['dly'])
    @commands.cooldown(1, 86400, commands.BucketType.user)
    async def daily(self, ctx):
        await self.open_account(ctx.author)
        users = await self.get_bank_data()
        user_id = str(ctx.author.id)

        today = datetime.now().date() # Use datetime.now() for current date
        last_daily_str = users[user_id].get("last_daily")
        
        if last_daily_str:
            last_daily = datetime.fromisoformat(last_daily_str).date() # Convert string to date object
            if last_daily == today - timedelta(days=1):
                users[user_id]["daily_streak"] += 1
            elif last_daily < today - timedelta(days=1):
                users[user_id]["daily_streak"] = 1 # Reset streak if skipped a day
        else:
            users[user_id]["daily_streak"] = 1

        streak = users[user_id]["daily_streak"]
        base_earnings = 1000
        streak_bonus = streak * 100
        total_earnings = base_earnings + streak_bonus

        if users[user_id]["pet"] == "Cat":
            total_earnings = int(total_earnings * 1.03)

        users[user_id]["wallet"] += total_earnings
        users[user_id]["last_daily"] = today.isoformat()
        
        await self.save_bank_data(users)
        
        em = discord.Embed(title=f"{emojis['tada_green']} Daily Reward Claimed! {emojis['tada_green']}", color=discord.Color.gold())
        em.add_field(name=f"{emojis['green_coin']} Base Reward", value=f"**{base_earnings}** coins", inline=False)
        em.add_field(name="🔥 Streak Bonus", value=f"**{streak_bonus}** coins (Day **{streak}**)", inline=False)
        em.add_field(name=f"{emojis['money_bag']} Total Earned", value=f"**{total_earnings}** coins", inline=False)
        await ctx.send(embed=em)

    @commands.command(aliases=['w'])
    async def withdraw(self, ctx, amount: str):
        await self.open_account(ctx.author)
        users = await self.get_bank_data()
        user_id = str(ctx.author.id)
        
        if amount.lower() == 'max':
            amount = users[user_id]["bank"]
        else:
            try:
                amount = int(amount)
            except ValueError:
                await ctx.send("Please specicx a valid amount or 'max'.")
                return
        
        if amount <= 0:
            await ctx.send("You can't withdraw a negative or zero amount!")
            return
        if users[user_id]["bank"] < amount:
            await ctx.send("You don't have that much in your bank account!")
            return
        
        users[user_id]["wallet"] += amount
        users[user_id]["bank"] -= amount
        await self.save_bank_data(users)
        await ctx.send(f"{emojis['withdraw']} You successfully withdrew **{amount:,.0f}** coins from your bank!")

    @commands.command(aliases=['d'])
    async def deposit(self, ctx, amount: str):
        await self.open_account(ctx.author)
        users = await self.get_bank_data()
        user_id = str(ctx.author.id)
        
        if amount.lower() == 'max':
            amount = users[user_id]["wallet"]
        else:
            try:
                amount = int(amount)
            except ValueError:
                await ctx.send("Please specicx a valid amount or 'max'.")
                return
        
        if amount <= 0:
            await ctx.send("You can't deposit a negative or zero amount!")
            return
        if users[user_id]["wallet"] < amount:
            await ctx.send("You don't have that much in your wallet!")
            return
        
        users[user_id]["wallet"] -= amount
        users[user_id]["bank"] += amount
        await self.save_bank_data(users)
        await ctx.send(f"{emojis['deposit']} You successfully deposited **{amount:,.0f}** coins into your bank!")

    @commands.command(aliases=['g', 'pay'])
    async def give(self, ctx, member: discord.Member, amount: int):
        await self.open_account(ctx.author)
        await self.open_account(member)
        if amount <= 0:
            await ctx.send("You can only give positive amounts of coins!")
            return
        if member.id == ctx.author.id:
            await ctx.send("You can't give money to yourself!")
            return

        users = await self.get_bank_data()
        author_id = str(ctx.author.id)
        if users[author_id]["wallet"] < amount:
            await ctx.send("You don't have enough coins in your wallet to give that much.")
            return
        
        view = ConfirmView(ctx.author)
        msg = await ctx.send(f"Are you sure you want to give **{amount:,.0f}** coins to {member.mention}?", view=view)
        
        await view.wait()
        
        if view.confirmed:
            users = await self.get_bank_data() # Reload data in case it changed during wait
            member_id = str(member.id)
            users[author_id]["wallet"] -= amount
            users[member_id]["wallet"] += amount
            await self.save_bank_data(users)
            await msg.edit(content=f"{emojis['tada_green']} {ctx.author.mention} generously gave **{amount:,.0f}** coins to {member.mention}!", view=None)
        elif view.confirmed is False:
            await msg.edit(content=f"{emojis['red_cross']} Transaction cancelled.", view=None)
        else:
            await msg.edit(content=f"{emojis['green_timer']} Transaction timed out. Please try again.", view=None)

    @commands.command(aliases=['s'])
    async def shop(self, ctx):
        em = discord.Embed(title=f"{emojis['shop']} The Grand Emporium {emojis['shop']}", description="A fine selection of goods for the discerning adventurer!", color=discord.Color.purple())
        for item in self.shop_items:
            em.add_field(name=f"{emojis.get(item['name'].lower().replace(' ', '_'), '✨')} {item['name']} - **{item['price']:,}** coins", value=item['description'], inline=False)
        em.set_footer(text=f"Use {ctx.prefix}buy <item name> to purchase!")
        await ctx.send(embed=em)

    @commands.command(aliases=['b'])
    async def buy(self, ctx, *, item_name: str):
        await self.open_account(ctx.author)
        item_to_buy = next((item for item in self.shop_items if item["name"].lower() == item_name.lower()), None)
        
        if item_to_buy is None:
            await ctx.send("That item isn't in stock right now. Check the shop again!")
            return
        
        users = await self.get_bank_data()
        user_id = str(ctx.author.id)
        
        if users[user_id]["wallet"] < item_to_buy["price"]:
            await ctx.send(f"You're a bit short on coins for a **{item_to_buy['name']}**! You need **{item_to_buy['price'] - users[user_id]['wallet']:,.0f}** more.")
            return
        
        users[user_id]["wallet"] -= item_to_buy["price"]
        users[user_id]["inventory"].append(item_to_buy["name"])
        await self.save_bank_data(users)
        await ctx.send(f"{emojis['tada_green']} You successfully purchased a **{item_to_buy['name']}** for **{item_to_buy['price']:,}** coins!")

    @commands.command(aliases=['inv', 'i'])
    async def inventory(self, ctx):
        await self.open_account(ctx.author)
        users = await self.get_bank_data()
        user_id = str(ctx.author.id)
        inv = users[user_id].get("inventory", [])
        
        if not inv:
            await ctx.send("Your inventory feels suspiciously light... It's empty!")
            return
        
        em = discord.Embed(title=f"{emojis['inventory']} {ctx.author.name}'s Backpack {emojis['inventory']}", color=discord.Color.orange())
        item_counts = {}
        for item in inv:
            item_counts[item] = item_counts.get(item, 0) + 1
        
        for item_name, count in item_counts.items():
            em.add_field(name=f"{emojis.get(item_name.lower().replace(' ', '_'), '📦')} {item_name}", value=f"Quantity: **{count}**", inline=False)
        await ctx.send(embed=em)

    @commands.command(aliases=['fsh'])
    @commands.cooldown(1, 600, commands.BucketType.user)
    async def fish(self, ctx):
        await self.open_account(ctx.author)
        users = await self.get_bank_data()
        user_id = str(ctx.author.id)
        
        if "Fishing Rod" not in users[user_id].get("inventory", []):
            await ctx.send(f"You need a **Fishing Rod** to cast your line! Find one in the shop using `{ctx.prefix}shop`.")
            self.fish.reset_cooldown(ctx)
            return
        
        fish_caught_choices = ["Salmon", "Tuna", "Cod", "Sardine", "Old Boot", "Shiny Bracelet"]
        fish_caught = random.choice(fish_caught_choices)
        
        if fish_caught == "Old Boot":
            await ctx.send(f"You went fishing and reeled in an old, soggy **Old Boot**... What a catch! {emojis['boots']}")
            users[user_id]["inventory"].append(fish_caught)
        elif fish_caught == "Shiny Bracelet":
            users[user_id]["inventory"].append(fish_caught)
            await ctx.send(f"Woah! You found a **Shiny Bracelet** while fishing! Sell it for coins with `{ctx.prefix}sell Shiny Bracelet`!")
        else:
            users[user_id]["inventory"].append(fish_caught)
            await ctx.send(f"You skillfully caught a **{fish_caught}**! Check your inventory (`{ctx.prefix}inv`) to sell it (`{ctx.prefix}sell {fish_caught}`).")
        
        await self.save_bank_data(users)

    @commands.command(aliases=['hnt'])
    @commands.cooldown(1, 1200, commands.BucketType.user)
    async def hunt(self, ctx):
        await self.open_account(ctx.author)
        users = await self.get_bank_data()
        user_id = str(ctx.author.id)
        
        if "Hunting Rifle" not in users[user_id].get("inventory", []):
            await ctx.send(f"To venture into the wilds, you'll need a **Hunting Rifle** from the shop using `{ctx.prefix}shop`.")
            self.hunt.reset_cooldown(ctx)
            return
        
        animal_hunted = random.choice(["Rabbit", "Deer", "Boar", "Fox", "Squirrel", "Rare Pelt"])
        
        if animal_hunted == "Rare Pelt":
            users[user_id]["inventory"].append(animal_hunted)
            await ctx.send(f"Amazing! You spotted and hunted a **Rare Pelt**! Sell it for a hefty sum with `{ctx.prefix}sell Rare Pelt`!")
        else:
            earnings = random.randrange(50, 251)
            users[user_id]["wallet"] += earnings
            await ctx.send(f"You successfully hunted a **{animal_hunted}** and sold it for **{earnings:,.0f}** coins!")
        
        await self.save_bank_data(users)

    @commands.command(aliases=['rb'])
    @commands.cooldown(1, 3600, commands.BucketType.user)
    async def rob(self, ctx, member: discord.Member):
        await self.open_account(ctx.author)
        await self.open_account(member)
        
        if member.id == ctx.author.id:
            await ctx.send("Trying to rob yourself? That's just giving yourself extra steps!")
            self.rob.reset_cooldown(ctx)
            return
        
        users = await self.get_bank_data()
        author_id = str(ctx.author.id)
        member_id = str(member.id)
        
        if users[member_id]["wallet"] < 200: # Minimum amount in victim's wallet to be worth robbing
            await ctx.send(f"{member.mention} is practically broke. Not worth the risk!")
            self.rob.reset_cooldown(ctx) 
            return

        success_chance = 0.4 # 40% chance of success
        if random.random() < success_chance:
            stolen_amount = random.randrange(int(users[member_id]["wallet"] * 0.2), int(users[member_id]["wallet"] * 0.5) + 1)
            stolen_amount = min(stolen_amount, users[member_id]["wallet"]) # Ensure not to steal more than they have
            
            users[author_id]["wallet"] += stolen_amount
            users[member_id]["wallet"] -= stolen_amount
            await self.save_bank_data(users)
            await ctx.send(f"😈 You masterfully outsmarted {member.mention} and snatched **{stolen_amount:,.0f}** coins from their wallet!")
        else:
            fine = random.randrange(50, 151)
            if "Medkit" in users[author_id]["inventory"]:
                users[author_id]["inventory"].remove("Medkit")
                await ctx.send(f"Oops! Your robbery attempt on {member.mention} failed! Luckily, your **Medkit** softened the blow, no fine this time!")
            else:
                users[author_id]["wallet"] -= fine
                await ctx.send(f"🚨 You were caught trying to rob {member.mention} and fined **{fine:,.0f}** coins! Better luck next time, criminal.")
            await self.save_bank_data(users)

    @commands.command(aliases=['dg'])
    @commands.cooldown(1, 1800, commands.BucketType.user)
    async def dig(self, ctx):
        await self.open_account(ctx.author)
        users = await self.get_bank_data()
        user_id = str(ctx.author.id)

        if "Shovel" not in users[user_id].get("inventory", []):
            await ctx.send(f"You need a **Shovel** to dig for hidden treasures! Check the shop using `{ctx.prefix}shop`.")
            self.dig.reset_cooldown(ctx)
            return
        
        treasure_found = random.choice(["nothing", "a few coins", "Old Relic", "Rare Gem"])
        
        if treasure_found == "nothing":
            await ctx.send("You dug and dug, but only found more dirt. Maybe try another spot!")
        elif treasure_found == "a few coins":
            earnings = random.randrange(30, 81)
            users[user_id]["wallet"] += earnings
            await self.save_bank_data(users)
            await ctx.send(f"You dug up **{earnings:,.0f}** coins! Every little bit helps.")
        else:
            users[user_id]["inventory"].append(treasure_found)
            await self.save_bank_data(users)
            await ctx.send(f"You unearthed a **{treasure_found}**! Check your inventory (`{ctx.prefix}inv`) to sell it (`{ctx.prefix}sell {treasure_found}`).")

    @commands.command(aliases=['hk'])
    @commands.cooldown(1, 3600, commands.BucketType.user)
    async def hack(self, ctx):
        await self.open_account(ctx.author)
        users = await self.get_bank_data()
        user_id = str(ctx.author.id)

        if "Laptop" not in users[user_id].get("inventory", []):
            await ctx.send(f"You need a **Laptop** to hack for digital riches! Check the shop using `{ctx.prefix}shop`.")
            self.hack.reset_cooldown(ctx)
            return

        success_chance = 0.6 # 60% chance of success
        if random.random() < success_chance:
            earnings = random.randrange(300, 801)
            users[user_id]["wallet"] += earnings
            await self.save_bank_data(users)
            await ctx.send(f"{emojis['laptop']} You successfully hacked into a secure server and siphoned off **{earnings:,.0f}** coins!")
        else:
            fine = random.randrange(100, 301)
            users[user_id]["wallet"] -= fine
            await self.save_bank_data(users)
            await ctx.send(f"🚨 Your hack attempt failed! The system detected you and fined you **{fine:,.0f}** coins.")

    @commands.command(aliases=['mn'])
    @commands.cooldown(1, 2400, commands.BucketType.user)
    async def mine(self, ctx):
        await self.open_account(ctx.author)
        users = await self.get_bank_data()
        user_id = str(ctx.author.id)

        if "Pickaxe" not in users[user_id].get("inventory", []):
            await ctx.send(f"You need a **Pickaxe** to mine for precious minerals! Visit the shop using `{ctx.prefix}shop`.")
            self.mine.reset_cooldown(ctx)
            return
        
        mineral_found = random.choice(["Stone", "Iron Ore", "Copper Ore", "Gold Ore", "Diamond"])
        
        if mineral_found == "Stone":
            await ctx.send("You swung your pickaxe and hit solid **Stone**. Nothing valuable here.")
        else:
            users[user_id]["inventory"].append(mineral_found)
            await self.save_bank_data(users)
            await ctx.send(f"{emojis['pickaxe']} You mined some **{mineral_found}**! Check your inventory (`{ctx.prefix}inv`) to sell it (`{ctx.prefix}sell {mineral_found}`).")

    @commands.command(aliases=['pets'])
    async def petshop(self, ctx):
        em = discord.Embed(title=f"{emojis['pets']} Pet Emporium {emojis['pets']}", description="Find your purr-fect companion here!", color=discord.Color.blue())
        for pet in self.pet_options:
            em.add_field(name=f"{emojis.get(pet['name'].lower(), '🐾')} {pet['name']} - **{pet['price']:,}** coins", value=pet['description'], inline=False)
        em.set_footer(text=f"Use {ctx.prefix}adopt <pet name> to adopt a new friend!")
        await ctx.send(embed=em)

    @commands.command(aliases=['adpt'])
    async def adopt(self, ctx, *, pet_name: str):
        await self.open_account(ctx.author)
        users = await self.get_bank_data()
        user_id = str(ctx.author.id)

        if users[user_id]["pet"] is not None:
            await ctx.send(f"You already have a **{users[user_id]['pet']}**! You can only have one pet at a time.")
            return

        pet_to_adopt = next((p for p in self.pet_options if p["name"].lower() == pet_name.lower()), None)

        if pet_to_adopt is None:
            await ctx.send(f"That's not a pet we have in stock. Check the pet shop using `{ctx.prefix}petshop`!")
            return

        if users[user_id]["wallet"] < pet_to_adopt["price"]:
            await ctx.send(f"You don't have enough coins to adopt a **{pet_to_adopt['name']}**. You need **{pet_to_adopt['price'] - users[user_id]['wallet']:,.0f}** more.")
            return

        users[user_id]["wallet"] -= pet_to_adopt["price"]
        users[user_id]["pet"] = pet_to_adopt["name"]
        await self.save_bank_data(users)
        await ctx.send(f"💖 Congratulations! You've adopted a lovely **{pet_to_adopt['name']}**!")

    @commands.command(aliases=['jobs'])
    async def joblist(self, ctx):
        em = discord.Embed(title="👨‍🏭 Available Professions 👩‍🏭", description="Choose a career and climb the ranks!", color=discord.Color.teal())
        for job in self.career_options:
            em.add_field(name=f"💼 {job['name']}", value=f"Payout: {job['payout_min']:,}-{job['payout_max']:,} coins | Cooldown: {job['cooldown'] // 60} mins", inline=False)
        em.set_footer(text=f"Use {ctx.prefix}apply <job name> to start your new career!")
        await ctx.send(embed=em)

    @commands.command(aliases=['joinjob'])
    async def apply(self, ctx, *, job_name: str = None):
        await self.open_account(ctx.author)
        users = await self.get_bank_data()
        user_id = str(ctx.author.id)

        if job_name is None: # If no job name is provided, show job list
            await ctx.send(f"Please specicx a job to apply for. Type `{ctx.prefix}joblist` to see available professions.")
            return

        if users[user_id]["job"] is not None:
            await ctx.send(f"You already have a job as a **{users[user_id]['job']}**. Use `{ctx.prefix}quit` if you want a new one.")
            return

        job_to_apply = next((j for j in self.career_options if j["name"].lower() == job_name.lower()), None)

        if job_to_apply is None:
            await ctx.send(f"That's not a recognized profession. Check the job list using `{ctx.prefix}joblist`!")
            return

        users[user_id]["job"] = job_to_apply["name"]
        await self.save_bank_data(users)
        await ctx.send(f"🎉 You are now officially a **{job_to_apply['name']}**! Get to work!")

    @commands.command(aliases=['collect'])
    @commands.cooldown(1, 3600, commands.BucketType.user)
    async def paycheck(self, ctx):
        await self.open_account(ctx.author)
        users = await self.get_bank_data()
        user_id = str(ctx.author.id)

        current_job_name = users[user_id]["job"]
        if current_job_name is None:
            await ctx.send(f"You need a job to earn a paycheck! Use `{ctx.prefix}joblist` to find one.")
            self.paycheck.reset_cooldown(ctx)
            return
        
        job_info = next((j for j in self.career_options if j["name"] == current_job_name), None)

        if job_info is None:
            await ctx.send("Error: Could not find information for your current job. Please report this!")
            self.paycheck.reset_cooldown(ctx)
            return

        earnings = random.randrange(job_info["payout_min"], job_info["payout_max"] + 1)
        users[user_id]["wallet"] += earnings
        await self.save_bank_data(users)
        await ctx.send(f"💸 Your hard work as a **{current_job_name}** paid off! You received **{earnings:,.0f}** coins as your paycheck.")
    
    @commands.command(aliases=['leavejob'])
    async def quit(self, ctx):
        await self.open_account(ctx.author)
        users = await self.get_bank_data()
        user_id = str(ctx.author.id)

        if users[user_id]["job"] is None:
            await ctx.send("You don't have a job to quit!")
            return
        
        old_job = users[user_id]["job"]
        users[user_id]["job"] = None
        await self.save_bank_data(users)
        await ctx.send(f"💔 You've decided to quit your job as a **{old_job}**. Time for new adventures!")

    @commands.command(aliases=['bet'])
    async def slots(self, ctx, amount: int):
        await self.open_account(ctx.author)
        users = await self.get_bank_data()
        user_id = str(ctx.author.id)

        if amount <= 0:
            await ctx.send("You must bet a positive amount!")
            return
        if users[user_id]["wallet"] < amount:
            await ctx.send("You don't have that much in your wallet to bet!")
            return
        
        emojis = ["🍒", "🔔", "💰", "💎", "🍋"]
        result = [random.choice(emojis) for _ in range(3)]
        
        payout = 0
        if result[0] == result[1] == result[2]:
            payout = amount * 3
            message = f"🎉 **{result[0]} {result[1]} {result[2]}** 🎉\nJackpot! You tripled your bet and won **{payout:,.0f}** coins!"
        elif result[0] == result[1] or result[1] == result[2]: # Two in a row (e.g., Chery Cherry Lemon or Lemon Cherry Cherry)
            payout = amount * 1.5
            message = f"🎰 **{result[0]} {result[1]} {result[2]}** 🎰\nSo close! You won **{int(payout):,.0f}** coins!"
        else:
            payout = -amount
            message = f"💔 **{result[0]} {result[1]} {result[2]}** 💔\nBetter luck next time! You lost **{amount:,.0f}** coins."
        
        users[user_id]["wallet"] += int(payout)
        await self.save_bank_data(users)
        await ctx.send(message)

    @commands.command(aliases=['cf'])
    async def coinflip(self, ctx, amount: int, choice: str = None):
        """Flip a coin and bet on the outcome."""
        await self.open_account(ctx.author)
        users = await self.get_bank_data()
        user_id = str(ctx.author.id)

        if amount <= 0:
            await ctx.send("You must bet a positive amount!")
            return
        if users[user_id]["wallet"] < amount:
            await ctx.send("You don't have that much in your wallet to bet!")
            return

        valid_choices = ['h', 't', 'heads', 'tails']
        if choice:
            choice = choice.lower()
            if choice not in valid_choices:
                await ctx.send("Invalid choice. Please use 'h' for heads or 't' for tails.")
                return
            if choice == 'heads':
                choice = 'h'
            if choice == 'tails':
                choice = 't'
        else:
            choice = random.choice(['h', 't'])

        result = random.choice(['h', 't'])
        result_full = "Heads" if result == 'h' else "Tails"
        choice_full = "Heads" if choice == 'h' else "Tails"

        em = discord.Embed(title="Coinflip Result", color=discord.Color.gold())
        em.add_field(name="Your Choice", value=choice_full, inline=True)
        em.add_field(name="Coin Landed On", value=result_full, inline=True)

        if result == choice:
            users[user_id]["wallet"] += amount
            em.description = f"🎉 You won! You earned **{amount:,}** coins."
            em.color = discord.Color.green()
        else:
            users[user_id]["wallet"] -= amount
            em.description = f"💔 You lost! You lost **{amount:,}** coins."
            em.color = discord.Color.red()
        
        em.set_footer(text=f"New balance: {users[user_id]['wallet']:,} coins")
        await self.save_bank_data(users)
        await ctx.send(embed=em)

    @commands.command(aliases=['triv'])
    @commands.cooldown(1, 10 * 60, commands.BucketType.user)
    async def trivia(self, ctx):
        await self.open_account(ctx.author)
        users = await self.get_bank_data()
        user_id = str(ctx.author.id)

        trivia_questions = [
            {"question": "What is the capital of France?", "answer": "Paris", "reward": 75},
            {"question": "What is 2 + 2?", "answer": "4", "reward": 50},
            {"question": "Which planet is known as the Red Planet?", "answer": "Mars", "reward": 100},
            {"question": "How many continents are there?", "answer": "7", "reward": 60},
            {"question": "What is the largest ocean on Earth?", "answer": "Pacific Ocean", "reward": 120},
            {"question": "What is the chemical symbol for water?", "answer": "H2O", "reward": 80},
            {"question": "Who wrote 'Romeo and Juliet'?", "answer": "William Shakespeare", "reward": 90},
            {"question": "What is the tallest mountain in the world?", "answer": "Mount Everest", "reward": 110},
            {"question": "What is the currency of Japan?", "answer": "Yen", "reward": 70},
            {"question": "Who painted the Mona Lisa?", "answer": "Leonardo da Vinci", "reward": 100},
            {"question": "What is the largest country in the world by area?", "answer": "Russia", "reward": 110},
            {"question": "What is the main ingredient in guacamole?", "answer": "Avocado", "reward": 60},
            {"question": "How many states are in the United States of America?", "answer": "50", "reward": 70},
            {"question": "What is the name of the galaxy we live in?", "answer": "Milky Way", "reward": 90},
            {"question": "What is the most spoken language in the world?", "answer": "Mandarin Chinese", "reward": 100}
        ]
        
        q = random.choice(trivia_questions)
        
        await ctx.send(f"🧠 **Trivia Time!** You have 15 seconds to answer:\n**{q['question']}**")
        
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel

        try:
            msg = await self.bot.wait_for('message', check=check, timeout=15.0)
        except asyncio.TimeoutError:
            await ctx.send("⏰ Time's up! You didn't answer in time.")
            return

        if msg.content.lower() == q["answer"].lower():
            users[user_id]["wallet"] += q["reward"]
            await self.save_bank_data(users)
            await ctx.send(f"✅ Correct! You earned **{q['reward']:,}** coins!")
        else:
            await ctx.send(f"❌ Incorrect! The answer was **{q['answer']}**.")

    @commands.command()
    async def use(self, ctx, *, item_name: str):
        await self.open_account(ctx.author)
        users = await self.get_bank_data()
        user_id = str(ctx.author.id)

        normalized_item_name = item_name.lower()
        item_in_inventory = next((item for item in users[user_id]["inventory"] if item.lower() == normalized_item_name), None)

        if item_in_inventory is None:
            await ctx.send("You don't have that item in your inventory!")
            return

        if normalized_item_name == "energy drink":
            if "Energy Drink" in users[user_id]["inventory"]:
                users[user_id]["inventory"].remove("Energy Drink")
                self.bot.get_command('work').reset_cooldown(ctx) # Reset cooldown for the 'work' command
                await ctx.send(f"{emojis['energy_drink']} You chugged an **Energy Drink**! Your work cooldown has been reset.")
            else:
                await ctx.send("You don't have an Energy Drink to use!")
        elif normalized_item_name == "medkit":
            await ctx.send("A Medkit is automatically used when you fail a rob attempt and would be fined.")
        else:
            await ctx.send("That item cannot be used directly or has no active effect.")
        
        await self.save_bank_data(users)

    @commands.command(aliases=['crm'])
    @commands.cooldown(1, 12 * 60 * 60, commands.BucketType.user) # 12 hours
    async def crime(self, ctx):
        await self.open_account(ctx.author)
        users = await self.get_bank_data()
        user_id = str(ctx.author.id)

        if users[user_id]["level"] < 5:
            await ctx.send("You need to be at least **Level 5** to commit a serious crime!")
            self.crime.reset_cooldown(ctx)
            return

        outcomes = {
            "success": {"message": "You pulled off a daring bank heist and escaped with **{amount}** coins!", "min": 1000, "max": 5000},
            "partial_success": {"message": "You managed to snag some cash from a back alley deal, getting **{amount}** coins.", "min": 500, "max": 1500},
            "caught": {"message": "You were caught! You were fined **{fine}** coins.", "fine_min": 300, "fine_max": 800},
            "injured": {"message": "Your crime went wrong and you got injured! You lost **{fine}** coins in medical bills.", "fine_min": 200, "fine_max": 600}
        }

        roll = random.random()
        if roll < 0.3: # 30% chance of success
            outcome = outcomes["success"]
            earnings = random.randrange(outcome["min"], outcome["max"] + 1)
            users[user_id]["wallet"] += earnings
            await ctx.send(outcome["message"].format(amount=f"{earnings:,.0f}"))
        elif roll < 0.6: # 30% chance of partial success (0.3 to 0.6)
            outcome = outcomes["partial_success"]
            earnings = random.randrange(outcome["min"], outcome["max"] + 1)
            users[user_id]["wallet"] += earnings
            await ctx.send(outcome["message"].format(amount=f"{earnings:,.0f}"))
        elif roll < 0.85: # 25% chance of being caught (0.6 to 0.85)
            outcome = outcomes["caught"]
            fine = random.randrange(outcome["fine_min"], outcome["fine_max"] + 1)
            users[user_id]["wallet"] -= fine
            await ctx.send(outcome["message"].format(fine=f"{fine:,.0f}"))
        else: # 15% chance of getting injured (0.85 to 1.0)
            outcome = outcomes["injured"]
            fine = random.randrange(outcome["fine_min"], outcome["fine_max"] + 1)
            users[user_id]["wallet"] -= fine
            await ctx.send(outcome["message"].format(fine=f"{fine:,.0f}"))
        
        await self.save_bank_data(users)

    @commands.command(aliases=['lb'])
    async def leaderboard(self, ctx, sort_by: str = "wallet"):
        users = await self.get_bank_data()
        
        valid_sorts = ["wallet", "bank", "level"]
        if sort_by.lower() not in valid_sorts:
            await ctx.send(f"Invalid sort option. Please choose from: **{', '.join(valid_sorts)}**.")
            return

        sorted_users = []
        for user_id, data in users.items():
            user = self.bot.get_user(int(user_id))
            if user: # Only include users the bot can see
                sorted_users.append({"name": user.name, "wallet": data["wallet"], "bank": data["bank"], "level": data["level"]})

        if sort_by.lower() == "wallet":
            sorted_users.sort(key=lambda x: x["wallet"], reverse=True)
            title = f"{emojis['money_bag']} Top 10 Richest by Wallet {emojis['money_bag']}"
        elif sort_by.lower() == "bank":
            sorted_users.sort(key=lambda x: x["bank"], reverse=True)
            title = f"{emojis['bank']} Top 10 Richest by Bank {emojis['bank']}"
        elif sort_by.lower() == "level":
            sorted_users.sort(key=lambda x: x["level"], reverse=True)
            title = f"{emojis['levelup_gif']} Top 10 Highest Level Players {emojis['levelup_gif']}"

        em = discord.Embed(title=title, color=discord.Color.blue())
        for i, user in enumerate(sorted_users[:10]):
            if sort_by.lower() == "wallet":
                value_str = f"Wallet: **{user['wallet']:,}** coins"
            elif sort_by.lower() == "bank":
                value_str = f"Bank: **{user['bank']:,}** coins"
            elif sort_by.lower() == "level":
                value_str = f"Level: **{user['level']}**"
            em.add_field(name=f"#{i+1}. {user['name']}", value=value_str, inline=False)
        
        if not sorted_users:
            em.description = "No users found in the database."
            
        await ctx.send(embed=em)

    @commands.command(aliases=['gbl'])
    async def gamble(self, ctx, amount: int):
        await self.open_account(ctx.author)
        users = await self.get_bank_data()
        user_id = str(ctx.author.id)

        if amount <= 0:
            await ctx.send("You must bet a positive amount!")
            return
        if users[user_id]["wallet"] < amount:
            await ctx.send("You don't have that much in your wallet to gamble!")
            return
        
        outcome = random.choice(["win", "lose"])
        
        if outcome == "win":
            users[user_id]["wallet"] += amount
            await ctx.send(f"🎉 You gambled **{amount:,.0f}** coins and doubled it! You now have **{users[user_id]['wallet']:,}** coins.")
        else:
            users[user_id]["wallet"] -= amount
            await ctx.send(f"💔 You gambled **{amount:,.0f}** coins and lost it all. You now have **{users[user_id]['wallet']:,}** coins.")
        
        await self.save_bank_data(users)

    @commands.command()
    @commands.cooldown(1, 10 * 60, commands.BucketType.user)
    async def beg(self, ctx):
        await self.open_account(ctx.author)
        users = await self.get_bank_data()
        user_id = str(ctx.author.id)

        outcomes = [
            {"text": "A kind stranger gave you **{amount}** coins.", "min": 10, "max": 50, "success": True},
            {"text": "Someone ignored you.", "min": 0, "max": 0, "success": False},
            {"text": "A police officer told you to move along.", "min": 0, "max": 0, "success": False},
            {"text": "You found **{amount}** coins on the ground!", "min": 20, "max": 70, "success": True}
        ]

        chosen_outcome = random.choice(outcomes)
        
        if chosen_outcome["success"]:
            earnings = random.randrange(chosen_outcome["min"], chosen_outcome["max"] + 1)
            users[user_id]["wallet"] += earnings
            await self.save_bank_data(users)
            await ctx.send(chosen_outcome["text"].format(amount=f"{earnings:,.0f}"))
        else:
            await ctx.send(chosen_outcome["text"])

    @commands.command(aliases=['exp'])
    @commands.cooldown(1, 6 * 60 * 60, commands.BucketType.user) # 6 hours
    async def explore(self, ctx):
        await self.open_account(ctx.author)
        users = await self.get_bank_data()
        user_id = str(ctx.author.id)

        explore_outcomes = [
            {"text": "You discovered a hidden cave and found **{amount}** coins!", "min": 200, "max": 500, "type": "money"},
            {"text": "You stumbled upon an ancient artifact. You found an **Old Relic**!", "item": "Old Relic", "type": "item"},
            {"text": "You got lost in the wilderness and found nothing.", "min": 0, "max": 0, "type": "nothing"},
            {"text": "You encountered a rare animal! You captured it and received a **Rare Pelt**.", "item": "Rare Pelt", "type": "item"},
            {"text": "You found a forgotten chest containing **{amount}** coins!", "min": 300, "max": 700, "type": "money"}
        ]

        outcome = random.choice(explore_outcomes)

        if outcome["type"] == "money":
            earnings = random.randrange(outcome["min"], outcome["max"] + 1)
            users[user_id]["wallet"] += earnings
            await self.save_bank_data(users)
            await ctx.send(outcome["text"].format(amount=f"{earnings:,.0f}"))
        elif outcome["type"] == "item":
            item = outcome["item"]
            users[user_id]["inventory"].append(item)
            await self.save_bank_data(users)
            await ctx.send(outcome["text"].format(item=item))
        else:
            await ctx.send(outcome["text"])

    @commands.command(aliases=['upg'])
    async def upgrade(self, ctx, item_name: str):
        await self.open_account(ctx.author)
        users = await self.get_bank_data()
        user_id = str(ctx.author.id)

        if item_name.lower() == "fishing rod":
            if "Fishing Rod" not in users[user_id]["inventory"]:
                await ctx.send(f"You need a basic Fishing Rod before you can upgrade it! Buy one from `{ctx.prefix}shop`.")
                return
            if "Upgraded Fishing Rod" in users[user_id]["inventory"]:
                await ctx.send("Your Fishing Rod is already upgraded!")
                return
            
            upgrade_cost = 500
            if users[user_id]["wallet"] < upgrade_cost:
                await ctx.send(f"You need **{upgrade_cost:,.0f}** coins to upgrade your Fishing Rod.")
                return

            users[user_id]["wallet"] -= upgrade_cost
            users[user_id]["inventory"].remove("Fishing Rod")
            users[user_id]["inventory"].append("Upgraded Fishing Rod")
            await self.save_bank_data(users)
            await ctx.send(f"{emojis['fishing_rod']} Your Fishing Rod has been upgraded! You'll now catch better fish using `{ctx.prefix}upgraded_fish`.")
        else:
            await ctx.send("That item cannot be upgraded or is not recognized for upgrades.")

    @commands.command(aliases=['upgfish'])
    @commands.cooldown(1, 600, commands.BucketType.user)
    async def upgraded_fish(self, ctx):
        await self.open_account(ctx.author)
        users = await self.get_bank_data()
        user_id = str(ctx.author.id)

        if "Upgraded Fishing Rod" not in users[user_id].get("inventory", []):
            await ctx.send(f"You need an **Upgraded Fishing Rod** to use this command! Upgrade yours with `{ctx.prefix}upgrade Fishing Rod`.")
            self.upgraded_fish.reset_cooldown(ctx)
            return
        
        upgraded_fish_choices = ["Rare Salmon", "Giant Tuna", "Deep Sea Cod", "Golden Fish", "Diamond Ring"]
        fish_caught = random.choice(upgraded_fish_choices)
        
        users[user_id]["inventory"].append(fish_caught)
        await self.save_bank_data(users)
        await ctx.send(f"With your upgraded rod, you caught a magnificent **{fish_caught}**! Check your inventory (`{ctx.prefix}inv`) to sell it (`{ctx.prefix}sell {fish_caught}`).")

    @commands.group(aliases=['sl'], invoke_without_command=True)
    async def sell(self, ctx, *, item_name: str = None):
        if item_name is None:
            # This is the default behavior if only `.sell` is typed
            await ctx.send(f"To sell an item, use `{ctx.prefix}sell <item name>`. To sell multiple items, use `{ctx.prefix}sell all [fish | <item name>]`. To see prices, use `{ctx.prefix}sell prices`.")
            return

        await self.open_account(ctx.author)
        users = await self.get_bank_data()
        user_id = str(ctx.author.id)

        item_name_lower = item_name.lower()
        
        found_item = None
        # Check if the user has the item (case-insensitive search)
        for item_in_inv in users[user_id]["inventory"]:
            if item_in_inv.lower() == item_name_lower:
                found_item = item_in_inv
                break

        if not found_item:
            await ctx.send(f"You don't have a **{item_name}** to sell!")
            return
        
        sell_price = self.sellable_items.get(item_name_lower)
        if sell_price is None:
            await ctx.send(f"That item (**{found_item}**) cannot be sold or has no set sell price. You can check prices with `{ctx.prefix}sell prices`.")
            return

        users[user_id]["inventory"].remove(found_item)
        users[user_id]["wallet"] += sell_price
        await self.save_bank_data(users)
        await ctx.send(f"You sold your **{found_item}** for **{sell_price:,.0f}** coins!")

    @sell.command(name="prices", aliases=["price", "list"])
    async def sell_prices(self, ctx):
        em = discord.Embed(title="🏷️ Item Sell Prices 🏷️", description="Here's what your treasures are worth!", color=discord.Color.blue())
        
        sorted_items = sorted(self.sellable_items.items(), key=lambda x: x[0])
        
        if not sorted_items:
            em.description = "No items with set sell prices."
        else:
            for item_name, price in sorted_items:
                em.add_field(name=item_name.title(), value=f"**{price:,.0f}** coins", inline=True)
        
        await ctx.send(embed=em)

    @sell.command(name="all", aliases=["a"])
    async def sell_all_items_or_type(self, ctx, *, item_type_or_name: str = None):
        await self.open_account(ctx.author)
        users = await self.get_bank_data()
        user_id = str(ctx.author.id)
        inventory = users[user_id]["inventory"]
        total_sold_count = 0
        total_earnings = 0
        sold_items_details = {} # To store counts of each item sold

        items_to_sell_in_this_batch = []

        if item_type_or_name is None: # .sell all (sell all sellable items)
            for item in list(inventory): # Iterate over a copy to allow modification during removal
                normalized_item = item.lower()
                if normalized_item in self.sellable_items:
                    items_to_sell_in_this_batch.append(item)
        elif item_type_or_name.lower() == "fish": # .sell all fish
            for item in list(inventory):
                normalized_item = item.lower()
                if normalized_item in self.fish_types and normalized_item in self.sellable_items:
                    items_to_sell_in_this_batch.append(item)
        else: # .sell all <specific_item_name>
            specific_item_lower = item_type_or_name.lower()
            if specific_item_lower not in self.sellable_items:
                await ctx.send(f"I don't know how to sell '{item_type_or_name}'. It's not a recognized sellable item.")
                return

            for item in list(inventory):
                if item.lower() == specific_item_lower:
                    items_to_sell_in_this_batch.append(item)

        if not items_to_sell_in_this_batch:
            if item_type_or_name is None:
                await ctx.send("Your inventory doesn't contain any items I can sell!")
            elif item_type_or_name.lower() == "fish":
                await ctx.send("You don't have any fish to sell in your inventory.")
            else:
                await ctx.send(f"You don't have any **{item_type_or_name.title()}** to sell in your inventory.")
            return

        # Process selling
        for item_name_to_sell in items_to_sell_in_this_batch:
            sell_price = self.sellable_items.get(item_name_to_sell.lower(), 0)
            total_earnings += sell_price
            total_sold_count += 1
            sold_items_details[item_name_to_sell] = sold_items_details.get(item_name_to_sell, 0) + 1
            inventory.remove(item_name_to_sell) # Remove item from actual inventory list

        users[user_id]["wallet"] += total_earnings
        await self.save_bank_data(users)

        summary_lines = []
        for item, count in sold_items_details.items():
            summary_lines.append(f"• {count}x {item} (for {self.sellable_items.get(item.lower(), 0) * count:,.0f} coins)")

        if item_type_or_name is None:
            title_text = f"{emojis['money_bag']} All Sellable Items Sold! {emojis['money_bag']}"
            description_text = f"You've cleared out your inventory and earned a tidy sum!"
        elif item_type_or_name.lower() == "fish":
            title_text = "🐟 All Fish Sold! 🐟"
            description_text = f"Your fishing haul has been converted into coins!"
        else:
            title_text = f"📦 All {item_type_or_name.title()} Sold! 📦"
            description_text = f"You've sold all your {item_type_or_name} and gained some coins!"

        em = discord.Embed(
            title=title_text,
            description=description_text,
            color=discord.Color.green()
        )
        em.add_field(name="Items Sold:", value="\n".join(summary_lines) if summary_lines else "None", inline=False)
        em.add_field(name="Total Items Sold", value=f"**{total_sold_count}**", inline=True)
        em.add_field(name="Total Earnings", value=f"**{total_earnings:,}** coins", inline=True)
        em.set_footer(text=f"Your new wallet balance: {users[user_id]['wallet']:,} coins")
        await ctx.send(embed=em)


    @commands.command(aliases=['setp'])
    @commands.is_owner()
    async def setprice(self, ctx, item_name: str, new_price: int):
        if new_price < 0:
            await ctx.send("Price cannot be negative!")
            return
        
        item_name_lower = item_name.lower()

        if item_name_lower in self.sellable_items:
            self.sellable_items[item_name_lower] = new_price
            await ctx.send(f"💰 The sell price of **{item_name.title()}** has been updated to **{new_price:,.0f}** coins!")
        else:
            await ctx.send(f"Item **{item_name}** not found in the sellable items list. If it's a new item, you'll need to add it to the bot's code first.")

    @work.error
    @daily.error
    @fish.error
    @hunt.error
    @rob.error
    @dig.error
    @hack.error
    @mine.error
    @paycheck.error
    @slots.error
    @trivia.error
    @beg.error
    @explore.error
    @crime.error
    @upgraded_fish.error
    async def command_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            seconds = int(error.retry_after)
            minutes, seconds = divmod(seconds, 60)
            hours, minutes = divmod(minutes, 60)
            
            time_left_parts = []
            if hours > 0:
                time_left_parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
            if minutes > 0:
                time_left_parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
            if seconds > 0:
                time_left_parts.append(f"{seconds} second{'s' if seconds != 1 else ''}")
            
            time_left_str = ", ".join(time_left_parts) or "a moment"

            command_name = ctx.command.name.replace('_', ' ').title()
            
            em = discord.Embed(
                title=f"{emojis['green_timer']} Hold Your Horses!",
                description=f"You're on cooldown for **{command_name}**.",
                color=discord.Color.red()
            )
            em.add_field(name="⏰ Time Remaining", value=f"Try again in **{time_left_str}**.", inline=False)
            em.set_footer(text="Patience, my friend, patience!")
            await ctx.send(embed=em)
        elif isinstance(error, commands.MissingRequiredArgument):
            # Custom messages for missing arguments based on command
            if ctx.command.name == 'sell' and not ctx.invoked_subcommand:
                await ctx.send(f"To sell an item, use `{ctx.prefix}sell <item name>`. To sell multiple items, use `{ctx.prefix}sell all [fish | <item name>]`. To see prices, use `{ctx.prefix}sell prices`.")
            elif ctx.command.name == 'sell_all_items_or_type': # This will catch .sell all without a type
                 await ctx.send(f"To sell all of a specific item, use `{ctx.prefix}sell all <item name>`. To sell all fish, use `{ctx.prefix}sell all fish`. To sell all sellable items, just use `{ctx.prefix}sell all`.")
            elif ctx.command.name == 'apply':
                await ctx.send(f"Please specicx a job to apply for. Type `{ctx.prefix}joblist` to see available professions.")
            else:
                # Default message for other commands with missing arguments
                await ctx.send(f"Oops! You missed an argument for this command. Usage: `{ctx.prefix}{ctx.command.name} {ctx.command.signature}`")
        elif isinstance(error, commands.BadArgument):
            await ctx.send("Hmm, I couldn't understand that argument. Please double-check your input!")
        elif isinstance(error, commands.NotOwner):
            await ctx.send("🚫 You need to be the bot's owner to use this command!")
        else:
            print(f"An unhandled error occurred in command {ctx.command}: {error}")
            await ctx.send("An unexpected error occurred. Please try again later.") # Generic fallback message

async def setup(bot):
    await bot.add_cog(Economy(bot))
