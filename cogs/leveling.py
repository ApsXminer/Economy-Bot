import discord
from discord.ext import commands, tasks
import json
import random
import os
from datetime import datetime, timedelta
import asyncio
from PIL import Image, ImageDraw, ImageFont, ImageOps
import io
import aiohttp

class Leveling(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data_file = "data/users.json" # Ensure this path is correct relative to where your bot runs

    async def get_bank_data(self):
        """Reads user data from the JSON file."""
        # Ensure the file exists before trying to read
        if not os.path.exists(self.data_file):
            return {}
        with open(self.data_file, 'r') as f:
            users = json.load(f)
        return users

    async def save_bank_data(self, users):
        """Saves user data to the JSON file."""
        os.makedirs(os.path.dirname(self.data_file), exist_ok=True) # Ensure directory exists
        with open(self.data_file, 'w') as f:
            json.dump(users, f, indent=4)
            
    async def open_account(self, user: discord.Member):
        """Opens a bank account for a new user, ensuring all necessary fields are present."""
        users = await self.get_bank_data()
        user_id = str(user.id)
        if user_id not in users:
            # Initialize all fields required by both Economy and Leveling cogs
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
            # Ensure new fields are added to existing accounts if they don't exist
            if "wallet" not in users[user_id]:
                users[user_id]["wallet"] = 100
            if "bank" not in users[user_id]:
                users[user_id]["bank"] = 0
            if "level" not in users[user_id]:
                users[user_id]["level"] = 1
            if "xp" not in users[user_id]:
                users[user_id]["xp"] = 0
            if "inventory" not in users[user_id]:
                users[user_id]["inventory"] = []
            if "daily_streak" not in users[user_id]:
                users[user_id]["daily_streak"] = 0
            if "last_daily" not in users[user_id]:
                users[user_id]["last_daily"] = None
            if "pet" not in users[user_id]:
                users[user_id]["pet"] = None
            if "job" not in users[user_id]:
                users[user_id]["job"] = None
            await self.save_bank_data(users)
            return False

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        await self.open_account(message.author)
        users = await self.get_bank_data()
        user_id = str(message.author.id)

        # Grant more substantial XP for messages
        xp_to_add = random.randint(15, 30) 
        users[user_id]["xp"] += xp_to_add
        
        # Check for level up
        level = users[user_id]["level"]
        xp = users[user_id]["xp"]
        # Exponential XP needed formula
        xp_needed = 5 * (level ** 2) + (50 * level) + 100

        if xp >= xp_needed:
            users[user_id]["level"] += 1
            users[user_id]["xp"] -= xp_needed
            new_level = users[user_id]["level"]
            
            # Level Up Reward: Higher reward for higher levels
            reward = 100 * new_level
            users[user_id]["wallet"] += reward
            
            await self.save_bank_data(users)

            # Generate level up image
            card = await self.generate_rank_card(message.author)
            
            with io.BytesIO() as image_binary:
                card.save(image_binary, 'PNG')
                image_binary.seek(0)
                await message.channel.send(
                    f"🎉 Congrats {message.author.mention}, you leveled up to **Level {new_level}** and received **{reward}** coins!", 
                    file=discord.File(fp=image_binary, filename='rank.png')
                )
        else:
            await self.save_bank_data(users) # Save XP even if not leveled up

    @commands.Cog.listener()
    async def on_command_completion(self, ctx):
        if ctx.author.bot:
            return
        
        await self.open_account(ctx.author)
        users = await self.get_bank_data()
        user_id = str(ctx.author.id)

        # Grant extra XP for using commands
        xp_to_add = random.randint(20, 40)
        users[user_id]["xp"] += xp_to_add
        await self.save_bank_data(users)


    @commands.command(aliases=['lvl', 'rank'])
    async def level(self, ctx, member: discord.Member = None):
        """Checks the user's or another member's level and shows a rank card."""
        if member is None:
            member = ctx.author

        await self.open_account(member)
        
        card = await self.generate_rank_card(member)
        
        with io.BytesIO() as image_binary:
            card.save(image_binary, 'PNG')
            image_binary.seek(0)
            await ctx.send(file=discord.File(fp=image_binary, filename='rank.png'))

    async def generate_rank_card(self, user: discord.Member):
        """Generates a user's rank card with enhanced visuals."""
        from PIL import ImageFilter
        users = await self.get_bank_data()
        user_id = str(user.id)
        
        level = users[user_id]["level"]
        xp = users[user_id]["xp"]
        xp_needed = 5 * (level ** 2) + (50 * level) + 100
        
        # Card dimensions
        width, height = 900, 250
        
        # Fonts - Attempt to use a common font, fallback to default
        try:
            font_large = ImageFont.truetype("arial.ttf", 70)
            font_medium = ImageFont.truetype("arial.ttf", 50)
            font_small = ImageFont.truetype("arial.ttf", 40)
            font_level = ImageFont.truetype("arial.ttf", 80)
            font_watermark = ImageFont.truetype("arial.ttf", 20)
        except IOError:
            font_large = ImageFont.load_default()
            font_medium = ImageFont.load_default()
            font_small = ImageFont.load_default()
            font_level = ImageFont.load_default()
            font_watermark = ImageFont.load_default()

        # Get user avatar for background
        async with aiohttp.ClientSession() as session:
            async with session.get(str(user.avatar.url)) as resp:
                if resp.status == 200:
                    avatar_data = await resp.read()
                    bg_avatar = Image.open(io.BytesIO(avatar_data)).convert("RGBA")
                    bg_avatar = bg_avatar.resize((width, height))
                    bg_avatar = bg_avatar.filter(ImageFilter.GaussianBlur(5))
                    card = bg_avatar
                else:
                    card = Image.new("RGB", (width, height), "#2C2F33")
        
        draw = ImageDraw.Draw(card)
        
        # Overlay to darken the background for better text readability
        overlay = Image.new('RGBA', card.size, (0, 0, 0, 150))
        card.paste(overlay, (0, 0), overlay)

        # Get user avatar
        avatar_size = 180
        avatar_pos_x, avatar_pos_y = 35, 35
        mask = Image.new('L', (avatar_size, avatar_size), 0)
        draw_mask = ImageDraw.Draw(mask) 
        draw_mask.ellipse((0, 0, avatar_size, avatar_size), fill=255)

        async with aiohttp.ClientSession() as session:
            async with session.get(str(user.avatar.url)) as resp:
                if resp.status == 200:
                    avatar_data = await resp.read()
                    avatar = Image.open(io.BytesIO(avatar_data)).convert("RGBA")
                    
                    output = ImageOps.fit(avatar, (avatar_size, avatar_size), centering=(0.5, 0.5))
                    output.putalpha(mask)
                    
                    card.paste(output, (avatar_pos_x, avatar_pos_y), output)
                    
                    draw.ellipse((avatar_pos_x - 5, avatar_pos_y - 5, avatar_pos_x + avatar_size + 5, avatar_pos_y + avatar_size + 5), 
                                 outline="#7289DA", width=5)

        # Draw progress bar background
        progress_bar_x = 240
        progress_bar_y = 170
        progress_bar_width = 610
        progress_bar_height = 40
        draw.rounded_rectangle((progress_bar_x, progress_bar_y, progress_bar_x + progress_bar_width, progress_bar_y + progress_bar_height), 
                               radius=20, fill="#484b4e")

        # Draw progress bar
        if xp_needed > 0:
            progress = (xp / xp_needed) * progress_bar_width
            draw.rounded_rectangle((progress_bar_x, progress_bar_y, progress_bar_x + progress, progress_bar_y + progress_bar_height), 
                                   radius=20, fill="#57F287")

        # Draw text
        name_text = f"{user.display_name}"
        draw.text((240, 50), name_text, fill="#FFFFFF", font=font_medium)
        
        xp_text = f"{xp} / {xp_needed} XP"
        xp_text_width = draw.textlength(xp_text, font=font_small)
        draw.text((840 - xp_text_width, 120), xp_text, fill="#BBBBBB", font=font_small)

        level_label_text = "LEVEL"
        level_number_text = f"{level}"

        level_label_x = 240
        level_label_y = 110
        draw.text((level_label_x, level_label_y), level_label_text, fill="#AAAAAA", font=font_small)

        level_number_x = 840
        level_number_y = 45
        level_number_width = draw.textlength(level_number_text, font=font_level)
        draw.text((level_number_x - level_number_width, level_number_y), level_number_text, fill="#FEE75C", font=font_level)

        # Watermark
        watermark_text = ".gg/code-verse"
        watermark_width = draw.textlength(watermark_text, font=font_watermark)
        draw.text((width - watermark_width - 20, height - 40), watermark_text, fill="#FFFFFF", font=font_watermark)

        return card


async def setup(bot):
    await bot.add_cog(Leveling(bot))
