import discord
from discord.ext import commands
from .database import get_players_db, get_or_create_player
from .team import TeamMixin

class RaidLobbyView(discord.ui.View):
    def __init__(self, cog, boss_name, boss_hp):
        super().__init__(timeout=600)
        self.cog = cog
        self.boss_name = boss_name
        self.boss_hp = int(boss_hp)
        self.raiders = []

    @discord.ui.button(label="Join Raid Alliance ⚔️", style=discord.ButtonStyle.danger)
    async def join_raid(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user not in self.raiders:
            self.raiders.append(interaction.user)
            embed = interaction.message.embeds[0]
            embed.set_field_at(0, name=f"🛡️ Joined Raiders ({len(self.raiders)})", value="\n".join([f"• {m.display_name}" for m in self.raiders]), inline=False)
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.send_message("❌ Already joined!", ephemeral=True)

class RaidMixin(TeamMixin):
    @TeamMixin.c_main.group(name="raid", invoke_without_command=True)
    async def c_raid(self, ctx):
        await ctx.send("⚠️ Owner Command: `!c raid spawn <Boss> <HP>` or `!c raid start`")

    @c_raid.command(name="spawn")
    async def raid_spawn(self, ctx, boss_name: str, boss_hp: int):
        if not await self.bot.is_owner(ctx.author): return
        view = RaidLobbyView(self, boss_name, boss_hp)
        embed = discord.Embed(title="🐉 MEGA BOSS RAID EVENT HAS BEGUN!", description=f"**Boss:** `{boss_name}` | **HP:** `{boss_hp:,}`", color=0xFF0000)
        embed.add_field(name="🛡️ Joined Raiders (0)", value="*None*", inline=False)
        self.current_raid = {"view": view, "boss_name": boss_name, "boss_hp": boss_hp}
        await ctx.send(embed=embed, view=view)

    @c_raid.command(name="start")
    async def raid_start(self, ctx):
        if not await self.bot.is_owner(ctx.author) or not hasattr(self, 'current_raid'): return
        view = self.current_raid["view"]
        db = get_players_db(self.bot)

        total_pow = sum([get_or_create_player(self.bot, m)['attack'] * 5 for m in view.raiders])
        
        embed = discord.Embed(title=f"⚔️ RAID RESULTS — {self.current_raid['boss_name']}", color=0xFFD700)
        if total_pow >= self.current_raid['boss_hp']:
            for m in view.raiders:
                p = get_or_create_player(self.bot, m)
                p['xp'] += 1000
                p['coins'] = p.get('coins', 0) + 1500
                db.update_one({"user_id": str(m.id)}, {"$set": p})
            embed.description = f"🎉 **BOSS DEFEATED!** Total Damage Dealt: `{total_pow:,}`\nAll raiders earned **+1,000 EXP & +1,500 Coins**!"
        else:
            embed.description = f"💀 **RAID FAILED!** Damage Dealt: `{total_pow:,}` / HP: `{self.current_raid['boss_hp']:,}`"
        await ctx.send(embed=embed)
      
