import random
import discord
from discord.ext import commands
from .database import get_players_db, get_or_create_player, is_banned
from .hunt import HuntMixin

class BattleMixin(HuntMixin):
    @HuntMixin.c_main.group(name="battle", aliases=["b"], invoke_without_command=True)
    async def c_battle(self, ctx, user1: discord.Member = None, user2: discord.Member = None):
        banned, msg = is_banned(self.bot, ctx.guild.id, ctx.author.id)
        if banned: return await ctx.send(msg)

        if not user1:
            return await ctx.send("❌ Usage: `!c battle @user` or `!c battle @user1 @user2`")

        # Case 1: Custom Match between 2 third-party users (No EXP)
        if user1 and user2:
            if user1.bot or user2.bot or user1.id == user2.id:
                return await ctx.send("❌ Invalid target members!")
            
            p1 = get_or_create_player(self.bot, user1)
            p2 = get_or_create_player(self.bot, user2)

            embed = discord.Embed(title=f"⚔️ CUSTOM MATCH: {p1['name']} VS {p2['name']}", color=0xE74C3C)
            embed.set_image(url=p1['image'])

            p1_hp, p2_hp = p1['max_hp'], p2['max_hp']
            while p1_hp > 0 and p2_hp > 0:
                p2_hp -= max(1, p1['attack'] + random.randint(1, 5) - (p2['defense'] // 2))
                if p2_hp <= 0: break
                p1_hp -= max(1, p2['attack'] + random.randint(1, 5) - (p1['defense'] // 2))

            winner = p1 if p1_hp > 0 else p2
            embed.add_field(name="👑 WINNER", value=f"**{winner['name']}** won the custom match! *(No EXP Awarded)*", inline=False)
            return await ctx.send(embed=embed)

        # Case 2: Standard 1v1 Battle
        opponent = user1
        if opponent.bot or opponent.id == ctx.author.id:
            return await ctx.send("❌ Mention a valid server member to duel!")

        p1 = get_or_create_player(self.bot, ctx.author)
        p2 = get_or_create_player(self.bot, opponent)
        db = get_players_db(self.bot)

        p1_atk = p1['attack'] + p1.get('buffs', {}).get('attack', 0)
        p2_atk = p2['attack'] + p2.get('buffs', {}).get('attack', 0)

        embed = discord.Embed(title=f"⚔️ DUEL: {p1['name']} VS {p2['name']}", color=0xE74C3C)
        embed.set_image(url=p1['image'])

        p1_hp, p2_hp = p1['max_hp'], p2['max_hp']
        while p1_hp > 0 and p2_hp > 0:
            p2_hp -= max(1, p1_atk + random.randint(1, 5) - (p2['defense'] // 2))
            if p2_hp <= 0: break
            p1_hp -= max(1, p2_atk + random.randint(1, 5) - (p1['defense'] // 2))

        winner, loser = (p1, p2) if p1_hp > 0 else (p2, p1)

        earned_xp = random.randint(80, 150)
        earned_coins = random.randint(100, 250)

        winner['xp'] += earned_xp
        winner['coins'] = winner.get('coins', 0) + earned_coins
        winner['wins'] += 1
        loser['losses'] += 1

        db.update_one({"user_id": winner['user_id']}, {"$set": winner})
        db.update_one({"user_id": loser['user_id']}, {"$set": loser})

        embed.add_field(name="👑 WINNER", value=f"**{winner['name']}** won! +`{earned_xp}` EXP | +`{earned_coins}` Coins", inline=False)
        await ctx.send(embed=embed)

    @c_battle.command(name="all", aliases=["a"])
    async def battle_all(self, ctx):
        banned, msg = is_banned(self.bot, ctx.guild.id, ctx.author.id)
        if banned: return await ctx.send(msg)

        db = get_players_db(self.bot)
        guild_members = [str(m.id) for m in ctx.guild.members if not m.bot]
        players = list(db.find({"user_id": {"$in": guild_members}}))

        if len(players) < 2:
            return await ctx.send("❌ Need at least 2 registered players in the server!")

        winner = max(players, key=lambda p: p['level'] * 10 + p['attack'] + random.randint(1, 30))
        earned_xp = len(players) * 50
        winner['xp'] += earned_xp
        db.update_one({"user_id": winner['user_id']}, {"$set": winner})

        embed = discord.Embed(title="🏟️ MASS BATTLE ROYALE ARENA", color=0x9B59B6)
        embed.add_field(name="👑 LAST MAN STANDING", value=f"🏆 **{winner['name']}** won +`{earned_xp}` Mass EXP!", inline=False)
        embed.set_thumbnail(url=winner['image'])
        await ctx.send(embed=embed)
      
