import discord
from discord.ext import commands
from .database import get_players_db, get_or_create_player, is_banned

class ProfileMixin:
    @commands.group(name="c", invoke_without_command=True)
    async def c_main(self, ctx):
        banned, msg = is_banned(self.bot, ctx.guild.id, ctx.author.id)
        if banned:
            return await ctx.send(msg)

        embed = discord.Embed(
            title="🎮 Character RPG Game — Command Center",
            description="Use subcommands below or access short aliases for faster gameplay!",
            color=0x5865F2
        )
        embed.add_field(
            name="👤 Profile & Stats",
            value="`!c profile` (`!c p`) - View Stats\n`!c lvl` (`!c l`) - EXP Progress\n`!c edit name <name>` - Rename\n`!c edit image <url>` - Change Art",
            inline=False
        )
        embed.add_field(
            name="🏹 Hunting & Shop",
            value="`!c hunt` (`!c h`) - Single Hunt\n`!c huntauto` (`!c ha`) - 20-Min Farming\n`!c shop` - View Items\n`!c buy <id>` - Purchase Buffs",
            inline=False
        )
        embed.add_field(
            name="⚔️ Battles & Teams",
            value="`!c battle @user` - 1v1 Duel\n`!c battle all` - Battle Royale\n`!c team create` - Player vs NPC Team\n`!c team room` - PvP Lobby with Mod Controls",
            inline=False
        )
        embed.add_field(
            name="🏆 Events & Leaderboard",
            value="`!c top` (`!c t`) - Leaderboards\n`!c ohelp` - Bot Owner Controls",
            inline=False
        )
        await ctx.send(embed=embed)

    @c_main.command(name="profile", aliases=["p"])
    async def c_profile(self, ctx, member: discord.Member = None):
        target = member or ctx.author
        banned, msg = is_banned(self.bot, ctx.guild.id, target.id)
        if banned: return await ctx.send(msg)

        player = get_or_create_player(self.bot, target)
        if not player: return await ctx.send("❌ Database Connection Error!")

        embed = discord.Embed(title=f"🛡️ {player['name']}", color=0x3498DB)
        embed.set_image(url=player['image'])
        embed.add_field(name="⭐ Level", value=f"`{player['level']}`", inline=True)
        embed.add_field(name="✨ EXP", value=f"`{player['xp']} / {player['max_xp']}`", inline=True)
        embed.add_field(name="🪙 Coins", value=f"`{player.get('coins', 0)}`", inline=True)
        embed.add_field(name="❤️ Max HP", value=f"`{player['max_hp']}`", inline=True)
        embed.add_field(name="⚔️ Attack Power", value=f"`{player['attack']}`", inline=True)
        embed.add_field(name="🛡️ Defense", value=f"`{player['defense']}`", inline=True)
        embed.add_field(name="🏆 Record", value=f"Wins: `{player['wins']}` | Losses: `{player['losses']}`", inline=True)
        await ctx.send(embed=embed)

    @c_main.command(name="lvl", aliases=["l"])
    async def c_lvl(self, ctx, member: discord.Member = None):
        target = member or ctx.author
        banned, msg = is_banned(self.bot, ctx.guild.id, target.id)
        if banned: return await ctx.send(msg)

        player = get_or_create_player(self.bot, target)
        needed_xp = player['max_xp'] - player['xp']
        progress = int((player['xp'] / player['max_xp']) * 10)
        bar = "🟦" * progress + "⬛" * (10 - progress)

        embed = discord.Embed(title=f"📊 Level Progress — {target.display_name}", color=0x9B59B6)
        embed.add_field(name="Current Level", value=f"**Level {player['level']}**", inline=False)
        embed.add_field(name="Progress Bar", value=f"{bar} (`{player['xp']}/{player['max_xp']}` EXP)", inline=False)
        embed.add_field(name="Next Level Requirement", value=f"⚡ Needs **{needed_xp} more EXP** to level up!", inline=False)
        await ctx.send(embed=embed)

    @c_main.group(name="edit", aliases=["e"], invoke_without_command=True)
    async def c_edit(self, ctx):
        await ctx.send("⚠️ Usage: `!c edit name <New Name>` or `!c edit image <Image URL>`")

    @c_edit.command(name="name", aliases=["n"])
    async def edit_name(self, ctx, *, new_name: str):
        banned, msg = is_banned(self.bot, ctx.guild.id, ctx.author.id)
        if banned: return await ctx.send(msg)

        db = get_players_db(self.bot)
        get_or_create_player(self.bot, ctx.author)
        db.update_one({"user_id": str(ctx.author.id)}, {"$set": {"name": new_name}})
        await ctx.send(f"✅ Character name updated to **{new_name}**!")

    @c_edit.command(name="image", aliases=["i"])
    async def edit_image(self, ctx, url: str):
        banned, msg = is_banned(self.bot, ctx.guild.id, ctx.author.id)
        if banned: return await ctx.send(msg)

        if not (url.startswith("http://") or url.startswith("https://")):
            return await ctx.send("❌ Invalid Image URL!")

        db = get_players_db(self.bot)
        get_or_create_player(self.bot, ctx.author)
        db.update_one({"user_id": str(ctx.author.id)}, {"$set": {"image": url}})
        
        embed = discord.Embed(title="✅ Character Image Updated!", color=0x00FF00)
        embed.set_image(url=url)
        await ctx.send(embed=embed)
      
