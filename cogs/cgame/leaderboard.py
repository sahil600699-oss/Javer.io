import discord
from discord.ext import commands
import config
from .database import get_players_db, get_owner_db, get_bans_db, get_or_create_player
from .shop import ShopMixin

class LeaderboardView(discord.ui.View):
    def __init__(self, cog, ctx):
        super().__init__(timeout=60)
        self.cog = cog
        self.ctx = ctx

    @discord.ui.select(
        placeholder="Select Leaderboard...",
        options=[
            discord.SelectOption(label="Server Leaderboard", value="server", emoji="🏠"),
            discord.SelectOption(label="Global Leaderboard", value="global", emoji="🌐")
        ]
    )
    async def select_callback(self, interaction: discord.Interaction, select: discord.ui.Select):
        if interaction.user.id != self.ctx.author.id:
            return await interaction.response.send_message("❌ Apex User Only!", ephemeral=True)

        db = get_players_db(self.cog.bot)

        if select.values[0] == "server":
            m_ids = [str(m.id) for m in self.ctx.guild.members]
            players = list(db.find({"user_id": {"$in": m_ids}}).sort("level", -1).limit(10))
            title = f"🏆 Server Leaderboard - {self.ctx.guild.name}"
        else:
            players = list(db.find().sort("level", -1).limit(10))
            title = "🌐 Global Leaderboard"

        embed = discord.Embed(title=title, color=0xFFD700)
        desc = ""
        for idx, p in enumerate(players, start=1):
            desc += f"**#{idx}** | `{p['name']}` — **Lv. {p['level']}** ({p['xp']} XP)\n"
        embed.description = desc or "No players found."
        await interaction.response.edit_message(embed=embed, view=self)

class CharacterGame(commands.Cog, ShopMixin):
    def __init__(self, bot):
        self.bot = bot

    async def is_bot_owner(self, user: discord.User):
        owner_id = getattr(config, 'OWNER_ID', None)
        if owner_id and user.id == int(owner_id):
            return True
        return await self.bot.is_owner(user)

    @ShopMixin.c_main.command(name="top", aliases=["t"])
    async def c_top(self, ctx):
        view = LeaderboardView(self, ctx)
        await ctx.send(embed=discord.Embed(title="🏆 Select Leaderboard", color=0xF1C40F), view=view)

    # ---------------- OWNER HELP MENU ----------------
    @ShopMixin.c_main.command(name="ohelp", aliases=["ownerhelp", "owner"])
    async def c_ohelp(self, ctx):
        if not await self.is_bot_owner(ctx.author):
            return await ctx.send("❌ **Access Denied!** This command is restricted to the Bot Owner.")

        embed = discord.Embed(
            title="👑 Bot Owner Command Menu",
            description="Exclusive controls for managing character profiles, events, and server bans.",
            color=0xFF0000
        )
        embed.add_field(
            name="📋 Card Vault Management",
            value="`!c copy @user <savename>` (`!c c`) - Save card to vault\n"
                  "`!c clist` (`!c cl`) - View all vault cards\n"
                  "`!c give <savename> @user` (`!c g`) - Overwrite profile with vault card",
            inline=False
        )
        embed.add_field(
            name="⚡ Level Modifications",
            value="`!c give lvl @user <amount>` - Direct level booster for target user",
            inline=False
        )
        embed.add_field(
            name="🐉 Event Controls",
            value="`!c raid spawn <Boss> <HP>` - Trigger Boss Event\n"
                  "`!c raid start` - Force start raid combat",
            inline=False
        )
        embed.add_field(
            name="🚫 Ban & Security System",
            value="`!c ban server` - Disable RPG in current server\n"
                  "`!c unban server` - Enable RPG in current server\n"
                  "`!c pban @user` - Permanently ban user from RPG\n"
                  "`!c punban @user` - Unban user from RPG",
            inline=False
        )
        await ctx.send(embed=embed)

    # ---------------- OWNER BAN COMMANDS ----------------
    @ShopMixin.c_main.command(name="ban")
    async def ban_server(self, ctx, option: str = None):
        if not await self.is_bot_owner(ctx.author) or option != "server":
            return
        bans_db = get_bans_db(self.bot)
        bans_db.update_one({"type": "server", "id": str(ctx.guild.id)}, {"$set": {"type": "server", "id": str(ctx.guild.id)}}, upsert=True)
        await ctx.send(f"🚫 RPG Game has been **Banned** in server `{ctx.guild.name}`!")

    @ShopMixin.c_main.command(name="unban")
    async def unban_server(self, ctx, option: str = None):
        if not await self.is_bot_owner(ctx.author) or option != "server":
            return
        bans_db = get_bans_db(self.bot)
        bans_db.delete_one({"type": "server", "id": str(ctx.guild.id)})
        await ctx.send(f"✅ RPG Game has been **Unbanned** in server `{ctx.guild.name}`!")

    @ShopMixin.c_main.command(name="pban")
    async def permaban_user(self, ctx, member: discord.Member):
        if not await self.is_bot_owner(ctx.author):
            return
        bans_db = get_bans_db(self.bot)
        bans_db.update_one({"type": "user", "id": str(member.id)}, {"$set": {"type": "user", "id": str(member.id)}}, upsert=True)
        await ctx.send(f"🔨 User **{member.display_name}** has been **Permanently Banned** from RPG Game!")

    @ShopMixin.c_main.command(name="punban")
    async def unpermaban_user(self, ctx, member: discord.Member):
        if not await self.is_bot_owner(ctx.author):
            return
        bans_db = get_bans_db(self.bot)
        bans_db.delete_one({"type": "user", "id": str(member.id)})
        await ctx.send(f"✅ User **{member.display_name}** has been **Unbanned** from RPG Game!")

async def setup(bot):
    await bot.add_cog(CharacterGame(bot))
