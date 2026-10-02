import os
import random
import discord
from discord.ext import commands
from pymongo import MongoClient

try:
    import config
except ImportError:
    config = None

MALE_TITLES = [
    "HANDSOME BOY LEGEND",
    "SEXY BOY MONSTER",
    "SMARTEST KING",
    "CHAD SUPREME"
]

FEMALE_TITLES = [
    "PRETTY DIVA QUEEN",
    "CUTE BADDIE LEGEND",
    "ROYAL PRINCESS",
    "AESTHETIC GODDESS"
]

class ProfileCard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._db = None

    def get_db(self):
        # 1. Check if bot.db is already available
        if hasattr(self.bot, 'db') and self.bot.db is not None:
            return self.bot.db["card_config"]
        
        # 2. Check MONGO_URL, MONGO_URI, and config.py
        if self._db is None:
            mongo_uri = (
                os.getenv("MONGO_URL") or 
                os.getenv("MONGO_URI") or 
                (getattr(config, 'MONGO_URI', None) if config else None) or
                (getattr(config, 'MONGO_URL', None) if config else None)
            )
            
            if mongo_uri:
                try:
                    cluster = MongoClient(mongo_uri)
                    db = cluster["javer_database"]
                    self._db = db["card_config"]
                except Exception as e:
                    print(f"[Card Cog DB Error]: {e}")
                    return None
        return self._db

    @commands.group(name="card", invoke_without_command=True)
    async def card_group(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        db_collection = self.get_db()

        male_role_id = None
        female_role_id = None

        if db_collection is not None:
            config_data = db_collection.find_one({"guild_id": str(ctx.guild.id)}) or {}
            male_role_id = config_data.get("male_role")
            female_role_id = config_data.get("female_role")

        user_role_ids = [str(r.id) for r in member.roles]
        
        is_female = (str(female_role_id) in user_role_ids) if female_role_id else False
        is_male = (str(male_role_id) in user_role_ids) if male_role_id else False

        if is_female:
            title = f"✨ {random.choice(FEMALE_TITLES)} ✨"
            role_text = "FEMALE"
            color = 0xFF1493
        elif is_male:
            title = f"🔥 {random.choice(MALE_TITLES)} 🔥"
            role_text = "MALE"
            color = 0xD4AF37
        else:
            title = "⭐ MEMBER CARD ⭐"
            role_text = "NOT SET"
            color = 0x2B2D31

        embed = discord.Embed(
            title=f"```\n{title}\n```",
            color=color
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(
            name="📋 MEMBER DETAILS",
            value=f"**NAME:** {member.display_name}\n**ROLE:** {role_text}",
            inline=False
        )
        embed.set_footer(
            text=f"👑 {ctx.guild.name.upper()}", 
            icon_url=ctx.guild.icon.url if ctx.guild.icon else None
        )

        await ctx.send(embed=embed)

    @card_group.group(name="role", invoke_without_command=True)
    async def role_group(self, ctx):
        await ctx.send("Usage: `!card role male @Role` or `!card role female @Role`")

    @role_group.command(name="male")
    async def set_male_role(self, ctx, role: discord.Role = None):
        if not role:
            return await ctx.send("❌ Kripya male role tag karein! Example: `!card role male @Male`")

        db_collection = self.get_db()
        if db_collection is None:
            return await ctx.send("❌ Database connect nahi hua! MongoDB connection check karein.")

        db_collection.update_one(
            {"guild_id": str(ctx.guild.id)},
            {"$set": {"male_role": str(role.id)}},
            upsert=True
        )
        await ctx.send(f"✅ **Male Role** successfully saved as: {role.mention}")

    @role_group.command(name="female")
    async def set_female_role(self, ctx, role: discord.Role = None):
        if not role:
            return await ctx.send("❌ Kripya female role tag karein! Example: `!card role female @Female`")

        db_collection = self.get_db()
        if db_collection is None:
            return await ctx.send("❌ Database connect nahi hua! MongoDB connection check karein.")

        db_collection.update_one(
            {"guild_id": str(ctx.guild.id)},
            {"$set": {"female_role": str(role.id)}},
            upsert=True
        )
        await ctx.send(f"✅ **Female Role** successfully saved as: {role.mention}")

async def setup(bot):
    await bot.add_cog(ProfileCard(bot))
      
