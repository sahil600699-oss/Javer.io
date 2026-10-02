import asyncio
import random
import discord
from discord.ext import commands
from .database import get_players_db, get_or_create_player, is_banned
from .battle import BattleMixin

class KickBanUserSelect(discord.ui.UserSelect):
    def __init__(self, lobby_view, action):
        super().__init__(placeholder=f"Select user to {action}...", min_values=1, max_values=1)
        self.lobby_view = lobby_view
        self.action = action

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.lobby_view.host.id:
            return await interaction.response.send_message("❌ Only Host can perform moderation actions!", ephemeral=True)

        target = self.values[0]
        if self.action == "kick":
            if target in self.lobby_view.team_a: self.lobby_view.team_a.remove(target)
            if target in self.lobby_view.team_b: self.lobby_view.team_b.remove(target)
            msg = f"🥾 Kicked **{target.display_name}** from lobby!"
        elif self.action == "ban":
            if target in self.lobby_view.team_a: self.lobby_view.team_a.remove(target)
            if target in self.lobby_view.team_b: self.lobby_view.team_b.remove(target)
            self.lobby_view.banned_users.append(target)
            msg = f"🔨 Banned **{target.display_name}** from lobby!"

        await interaction.response.edit_message(embed=self.lobby_view.build_embed(), view=self.lobby_view)
        await interaction.followup.send(msg, ephemeral=True)

class TeamLobbyView(discord.ui.View):
    def __init__(self, cog, host: discord.Member):
        super().__init__(timeout=300)
        self.cog = cog
        self.host = host
        self.team_a = [host]
        self.team_b = []
        self.banned_users = []
        self.timer = 300
        self.message = None

    def build_embed(self):
        embed = discord.Embed(
            title="⚔️ PVP TEAM ROOM — LOBBY ARENA",
            description=f"**Host:** {self.host.mention}\n⏳ **Auto-starting in:** `{self.timer // 60}m {self.timer % 60}s`",
            color=0x3498DB
        )
        t_a = "\n".join([f"• **{m.display_name}**" for m in self.team_a]) or "*Empty*"
        t_b = "\n".join([f"• **{m.display_name}**" for m in self.team_b]) or "*Empty*"
        b_u = ", ".join([m.display_name for m in self.banned_users]) or "None"

        embed.add_field(name=f"🔴 Team A ({len(self.team_a)})", value=t_a, inline=True)
        embed.add_field(name=f"🔵 Team B ({len(self.team_b)})", value=t_b, inline=True)
        embed.add_field(name="🚫 Banned Users", value=f"`{b_u}`", inline=False)
        return embed

    @discord.ui.button(label="Join Team A", style=discord.ButtonStyle.danger, emoji="🔴")
    async def join_a(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user in self.banned_users:
            return await interaction.response.send_message("❌ You are banned from this lobby!", ephemeral=True)
        if interaction.user in self.team_b: self.team_b.remove(interaction.user)
        if interaction.user not in self.team_a: self.team_a.append(interaction.user)
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    @discord.ui.button(label="Join Team B", style=discord.ButtonStyle.primary, emoji="🔵")
    async def join_b(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user in self.banned_users:
            return await interaction.response.send_message("❌ You are banned from this lobby!", ephemeral=True)
        if interaction.user in self.team_a: self.team_a.remove(interaction.user)
        if interaction.user not in self.team_b: self.team_b.append(interaction.user)
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    @discord.ui.button(label="Start Match ⚔️", style=discord.ButtonStyle.success, row=1)
    async def start_game(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.host.id:
            return await interaction.response.send_message("❌ Only Host can start the match!", ephemeral=True)
        await self.execute_match(interaction)

    @discord.ui.button(label="Kick Member", style=discord.ButtonStyle.secondary, row=1)
    async def kick_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.host.id:
            return await interaction.response.send_message("❌ Only Host can kick!", ephemeral=True)
        v = discord.ui.View()
        v.add_item(KickBanUserSelect(self, "kick"))
        await interaction.response.send_message("Select user to kick:", view=v, ephemeral=True)

    @discord.ui.button(label="Ban Member", style=discord.ButtonStyle.secondary, row=1)
    async def ban_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.host.id:
            return await interaction.response.send_message("❌ Only Host can ban!", ephemeral=True)
        v = discord.ui.View()
        v.add_item(KickBanUserSelect(self, "ban"))
        await interaction.response.send_message("Select user to ban:", view=v, ephemeral=True)

    async def execute_match(self, interaction=None):
        self.stop()
        for child in self.children: child.disabled = True
        db = get_players_db(self.cog.bot)

        pow_a = sum([get_or_create_player(self.cog.bot, m)['attack'] for m in self.team_a]) or 10
        pow_b = sum([get_or_create_player(self.cog.bot, m)['attack'] for m in self.team_b]) or 10

        winning_team = "🔴 TEAM A" if (pow_a + random.randint(1, 50)) >= (pow_b + random.randint(1, 50)) else "🔵 TEAM B"
        winners = self.team_a if "TEAM A" in winning_team else self.team_b

        for m in winners:
            p = get_or_create_player(self.cog.bot, m)
            p['xp'] += 150
            p['coins'] = p.get('coins', 0) + 200
            db.update_one({"user_id": str(m.id)}, {"$set": p})

        res_embed = self.build_embed()
        res_embed.title = f"🏆 MATCH FINISHED — {winning_team} WINS!"
        res_embed.add_field(name="🎁 Rewards", value="All winners earned +`150` EXP & +`200` Coins!", inline=False)

        if interaction:
            await interaction.response.edit_message(embed=res_embed, view=self)
        elif self.message:
            await self.message.edit(embed=res_embed, view=self)

class TeamNpcLobbyView(discord.ui.View):
    def __init__(self, cog, host: discord.Member):
        super().__init__(timeout=300)
        self.cog = cog
        self.host = host
        self.team = [host]
        self.timer = 300
        self.message = None

    def build_embed(self):
        embed = discord.Embed(
            title="🛡️ PLAYER TEAM VS NPC SQUAD — LOBBY",
            description=f"**Host:** {self.host.mention}\nJoin the squad to fight the NPC Bosses together!\n⏳ **Auto-starting in:** `{self.timer // 60}m {self.timer % 60}s`",
            color=0x3498DB
        )
        t_str = "\n".join([f"• **{m.display_name}**" for m in self.team]) or "*Empty*"
        embed.add_field(name=f"👥 Player Alliance ({len(self.team)})", value=t_str, inline=False)
        return embed

    @discord.ui.button(label="Join Squad 🛡️", style=discord.ButtonStyle.primary)
    async def join_squad(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user not in self.team:
            self.team.append(interaction.user)
            await interaction.response.edit_message(embed=self.build_embed(), view=self)
        else:
            await interaction.response.send_message("❌ Already in squad!", ephemeral=True)

    @discord.ui.button(label="Start Battle ⚔️", style=discord.ButtonStyle.success)
    async def start_npc_battle(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.host.id:
            return await interaction.response.send_message("❌ Only Host can start the match!", ephemeral=True)
        await self.execute_npc_match(interaction)

    async def execute_npc_match(self, interaction=None):
        self.stop()
        for child in self.children: child.disabled = True
        db = get_players_db(self.cog.bot)

        total_player_pow = sum([get_or_create_player(self.cog.bot, m)['attack'] for m in self.team]) + random.randint(1, 50)
        npc_pow = len(self.team) * 35 + random.randint(20, 60)

        embed = self.build_embed()
        embed.title = "🛡️ TEAM VS NPC BATTLE RESULTS"

        if total_player_pow >= npc_pow:
            for m in self.team:
                p = get_or_create_player(self.cog.bot, m)
                p['xp'] += 150
                p['coins'] = p.get('coins', 0) + 180
                db.update_one({"user_id": str(m.id)}, {"$set": p})
            embed.description = f"🏆 **VICTORY!** Player Team (`Power: {total_player_pow}`) defeated NPC Squad (`Power: {npc_pow}`)!\n🎉 All team members earned +`150` EXP & +`180` Coins!"
        else:
            embed.description = f"❌ **DEFEAT!** NPC Boss Squad (`Power: {npc_pow}`) overwhelmed Player Team (`Power: {total_player_pow}`)."

        if interaction:
            await interaction.response.edit_message(embed=embed, view=self)
        elif self.message:
            await self.message.edit(embed=embed, view=self)

class TeamMixin(BattleMixin):
    @BattleMixin.c_main.group(name="team", invoke_without_command=True)
    async def c_team(self, ctx):
        await ctx.send("⚠️ Usage: `!c team create` (VS NPC Lobby) or `!c team room` (PvP Lobby)")

    @c_team.command(name="create")
    async def team_create(self, ctx):
        banned, msg = is_banned(self.bot, ctx.guild.id, ctx.author.id)
        if banned: return await ctx.send(msg)

        view = TeamNpcLobbyView(self, ctx.author)
        msg_obj = await ctx.send(embed=view.build_embed(), view=view)
        view.message = msg_obj

        for _ in range(60):
            await asyncio.sleep(5)
            if view.is_finished(): break
            view.timer -= 5
            if view.timer <= 0:
                return await view.execute_npc_match()
            try: await msg_obj.edit(embed=view.build_embed())
            except Exception: break

    @c_team.command(name="room")
    async def team_room(self, ctx):
        banned, msg = is_banned(self.bot, ctx.guild.id, ctx.author.id)
        if banned: return await ctx.send(msg)

        view = TeamLobbyView(self, ctx.author)
        msg_obj = await ctx.send(embed=view.build_embed(), view=view)
        view.message = msg_obj

        for _ in range(60):
            await asyncio.sleep(5)
            if view.is_finished(): break
            view.timer -= 5
            if view.timer <= 0:
                return await view.execute_match()
            try: await msg_obj.edit(embed=view.build_embed())
            except Exception: break
                       
