import asyncio
import datetime
import random
import discord
from discord.ext import commands
from .database import get_players_db, get_or_create_player, is_banned
from .profile import ProfileMixin

class HuntMixin(ProfileMixin):
    @ProfileMixin.c_main.command(name="hunt", aliases=["h"])
    async def c_hunt(self, ctx):
        banned, msg = is_banned(self.bot, ctx.guild.id, ctx.author.id)
        if banned: return await ctx.send(msg)

        player = get_or_create_player(self.bot, ctx.author)
        db = get_players_db(self.bot)

        mobs = [{"name": "Zombie 🧟", "xp": 100}, {"name": "Skeleton 💀", "xp": 150}, {"name": "Dragon Hatchling 🐉", "xp": 350}]
        mob = random.choice(mobs)
        
        gained_xp = mob["xp"] * 2 if player.get("buffs", {}).get("double_xp") else mob["xp"]
        gained_coins = random.randint(50, 150)

        player["xp"] += gained_xp
        player["coins"] = player.get("coins", 0) + gained_coins

        if player.get("buffs", {}).get("double_xp"):
            player["buffs"]["double_xp"] = False

        leveled_up = False
        if player["xp"] >= player["max_xp"]:
            player["level"] += 1
            player["xp"] -= player["max_xp"]
            player["max_xp"] = int(player["max_xp"] * 1.5)
            player["max_hp"] += 20
            player["attack"] += 5
            leveled_up = True

        db.update_one({"user_id": str(ctx.author.id)}, {"$set": player})

        embed = discord.Embed(title="⚔️ HUNT SUCCESSFUL!", color=0x2ECC71)
        embed.description = f"**{player['name']}** defeated a **{mob['name']}**!\n+`{gained_xp}` EXP | +`{gained_coins}` Coins Gained."
        if leveled_up:
            embed.add_field(name="🎉 LEVEL UP!", value=f"Reached **Level {player['level']}**!\n+20 Max HP | +5 Attack")
        await ctx.send(embed=embed)

    @ProfileMixin.c_main.command(name="huntauto", aliases=["ha"])
    async def c_huntauto(self, ctx):
        banned, msg = is_banned(self.bot, ctx.guild.id, ctx.author.id)
        if banned: return await ctx.send(msg)

        player = get_or_create_player(self.bot, ctx.author)
        db = get_players_db(self.bot)

        now = datetime.datetime.utcnow()
        if player.get("autohunt_until") and now < player["autohunt_until"]:
            rem = int((player["autohunt_until"] - now).total_seconds())
            return await ctx.send(f"⏳ **Auto-Hunt Active!** Finishes in `{rem // 60}m {rem % 60}s`.")

        finish_time = now + datetime.timedelta(minutes=20)
        db.update_one({"user_id": str(ctx.author.id)}, {"$set": {"autohunt_until": finish_time}})

        await ctx.send("🚀 **20-Minute Auto-Hunt Started!** Summary will be sent to your DMs upon completion.")

        await asyncio.sleep(1200)

        total_xp = random.randint(3000, 4500)
        total_coins = random.randint(1000, 2000)

        updated_p = db.find_one({"user_id": str(ctx.author.id)})
        updated_p["xp"] += total_xp
        updated_p["coins"] = updated_p.get("coins", 0) + total_coins

        levels_gained = 0
        while updated_p["xp"] >= updated_p["max_xp"]:
            updated_p["level"] += 1
            updated_p["xp"] -= updated_p["max_xp"]
            updated_p["max_xp"] = int(updated_p["max_xp"] * 1.5)
            updated_p["max_hp"] += 20
            updated_p["attack"] += 5
            levels_gained += 1

        updated_p["autohunt_until"] = None
        db.update_one({"user_id": str(ctx.author.id)}, {"$set": updated_p})

        try:
            dm_embed = discord.Embed(title="📜 AUTO-HUNT COMPLETED!", color=0xF1C40F)
            dm_embed.add_field(name="🎁 Rewards", value=f"+`{total_xp}` EXP | +`{total_coins}` Coins", inline=False)
            if levels_gained > 0:
                dm_embed.add_field(name="🎉 LEVEL UP!", value=f"Gained **{levels_gained} Level(s)**!", inline=False)
            await ctx.author.send(embed=dm_embed)
        except Exception:
            pass
          
