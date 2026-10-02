import discord
from discord.ext import commands

# In-memory storage for server permission settings
# Guild ID -> bool (True = Move Members Permission allowed, False = Admin/Owner Only)
GUILD_VC_PARMS = {}

class PullSelectView(discord.ui.View):
    def __init__(self, ctx):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.target_vc = None

        self.vc_select = discord.ui.ChannelSelect(
            placeholder="Select Target VC (Jahan sare members ko lana hai)",
            channel_types=[discord.ChannelType.voice],
            min_values=1,
            max_values=1,
            row=0
        )
        self.vc_select.callback = self.vc_callback
        self.add_item(self.vc_select)

    async def vc_callback(self, interaction: discord.Interaction):
        self.target_vc = self.vc_select.values[0]
        await interaction.response.send_message(f"🎯 **Target VC Selected:** {self.target_vc.name}", ephemeral=True)

    @discord.ui.button(label="✅ Confirm & Pull All", style=discord.ButtonStyle.green, row=1)
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.target_vc:
            return await interaction.response.send_message("❌ Pehle ek Target VC select karein!", ephemeral=True)

        target_channel = interaction.guild.get_channel(self.target_vc.id)
        await interaction.response.defer()

        moved_count = 0
        for vc in interaction.guild.voice_channels:
            if vc.id != target_channel.id:
                for member in list(vc.members):
                    try:
                        await member.edit(voice_channel=target_channel, reason=f"Pull S Command by {self.ctx.author}")
                        moved_count += 1
                    except discord.Forbidden:
                        continue

        await interaction.followup.send(f"🚚 **{moved_count} members** ko **{target_channel.name}** me successfully pull kar diya gaya!")
        self.stop()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ Ye controls aapke liye nahi hain!", ephemeral=True)
            return False
        return True


class VCDragView(discord.ui.View):
    def __init__(self, ctx):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.source_vc = None
        self.target_vc = None

        self.source_select = discord.ui.ChannelSelect(
            placeholder="Select Source VC (Jahan se members drag karne hain)",
            channel_types=[discord.ChannelType.voice],
            min_values=1,
            max_values=1,
            row=0
        )
        self.source_select.callback = self.source_callback
        self.add_item(self.source_select)

        self.target_select = discord.ui.ChannelSelect(
            placeholder="Select Target VC (Jahan members bhejne hain)",
            channel_types=[discord.ChannelType.voice],
            min_values=1,
            max_values=1,
            row=1
        )
        self.target_select.callback = self.target_callback
        self.add_item(self.target_select)

    async def source_callback(self, interaction: discord.Interaction):
        self.source_vc = self.source_select.values[0]
        await interaction.response.send_message(f"✅ **Source VC Selected:** {self.source_vc.name}", ephemeral=True)

    async def target_callback(self, interaction: discord.Interaction):
        self.target_vc = self.target_select.values[0]
        await interaction.response.send_message(f"🎯 **Target VC Selected:** {self.target_vc.name}", ephemeral=True)

    @discord.ui.button(label="🚀 Move All Members", style=discord.ButtonStyle.green, row=2)
    async def move_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.source_vc or not self.target_vc:
            return await interaction.response.send_message("❌ Pehle Source VC aur Target VC dono select karein!", ephemeral=True)

        if self.source_vc == self.target_vc:
            return await interaction.response.send_message("❌ Source VC aur Target VC same nahi ho sakte!", ephemeral=True)

        source_channel = interaction.guild.get_channel(self.source_vc.id)
        target_channel = interaction.guild.get_channel(self.target_vc.id)

        if not source_channel.members:
            return await interaction.response.send_message(f"❌ **{source_channel.name}** me koi member nahi hai!", ephemeral=True)

        moved_count = 0
        await interaction.response.defer()

        for member in list(source_channel.members):
            try:
                await member.edit(voice_channel=target_channel, reason=f"VC Drag by {self.ctx.author}")
                moved_count += 1
            except discord.Forbidden:
                continue

        await interaction.followup.send(f"🚚 Moved **{moved_count} members** from **{source_channel.name}** ➔ **{target_channel.name}**!")
        self.stop()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ Ye controls aapke liye nahi hain!", ephemeral=True)
            return False
        return True


class VCHelper(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def has_vc_permissions(self, ctx: commands.Context) -> bool:
        """Check user permissions based on Guild Settings"""
        if ctx.author.id == ctx.guild.owner_id or ctx.author.guild_permissions.administrator:
            return True

        move_perms_allowed = GUILD_VC_PARMS.get(ctx.guild.id, True)
        if move_perms_allowed and ctx.author.guild_permissions.move_members:
            return True

        return False

    @commands.command(name="vcall", aliases=["vcall parms"])
    async def vcall_perms_config(self, ctx: commands.Context, sub_command: str = None, setting: str = None):
        if ctx.author.id != ctx.guild.owner_id and not ctx.author.guild_permissions.administrator:
            return await ctx.send("❌ Sirf **Server Owner** ya **Administrators** hi is command ko run kar sakte hain!")

        status_input = setting or sub_command
        if not status_input:
            return await ctx.send("❓ Usage: `!vcall parms on` ya `!vcall parms off`")

        status_input = status_input.lower()
        if status_input == "on":
            GUILD_VC_PARMS[ctx.guild.id] = True
            await ctx.send("✅ **VC Permissions Settings ON!** Ab Jin members ke paas **Move Members** permission hai wo sabhi commands use kar sakte hain.")
        elif status_input == "off":
            GUILD_VC_PARMS[ctx.guild.id] = False
            await ctx.send("🔒 **VC Permissions Settings OFF!** Ab sirf **Server Owner** aur **Administrators** hi VC Commands use kar sakte hain.")
        else:
            await ctx.send("❓ Invalid option! Use `!vcall parms on` or `!vcall parms off`")

    @commands.command(name="pull")
    async def pull_cmd(self, ctx: commands.Context, option: str = None):
        if not self.has_vc_permissions(ctx):
            return await ctx.send("❌ Aapke paas VCHelper commands use karne ki permission nahi hai!")

        if option and option.lower() == "s":
            embed = discord.Embed(
                title="🧲 VC Pull Selector",
                description="1. Dropdown se target **VC Channel** select karein.\n"
                            "2. Bottom me **Confirm & Pull All** button click karein.",
                color=discord.Color.blue()
            )
            view = PullSelectView(ctx)
            return await ctx.send(embed=embed, view=view)

        if not ctx.author.voice or not ctx.author.voice.channel:
            return await ctx.send("❌ Is command ko use karne ke liye pehle kisi Voice Channel me join karein!")

        target_vc = ctx.author.voice.channel
        moved_count = 0

        for vc in ctx.guild.voice_channels:
            if vc.id != target_vc.id:
                for member in list(vc.members):
                    try:
                        await member.edit(voice_channel=target_vc, reason=f"Pull Command by {ctx.author}")
                        moved_count += 1
                    except discord.Forbidden:
                        continue

        await ctx.send(f"🧲 **{moved_count} members** ko baki saare VC Channels se **{target_vc.name}** me pull kar liya gaya!")

    @commands.group(name="vcm", invoke_without_command=True)
    async def vcm_group(self, ctx: commands.Context):
        await ctx.invoke(self.vcm_help)

    @vcm_group.command(name="help", aliases=["h"])
    async def vcm_help(self, ctx: commands.Context):
        embed = discord.Embed(
            title="🎙️ Voice Channel Helper Commands",
            description="Voice Channels ko control aur manage karne ke saare commands:",
            color=discord.Color.blue()
        )
        embed.add_field(name="!pull", value="Aap jis VC me ho, baki sare VC ke members ko aapke VC me pull kar dega.", inline=False)
        embed.add_field(name="!pull s", value="Channel Selection menu kholega. Target VC choose karke Confirm dabate hi sare members wahan shift ho jayenge.", inline=False)
        embed.add_field(name="!vcm drag", value="Source VC aur Target VC select karke specific members group drag karne ke liye.", inline=False)
        embed.add_field(name="!vcm mute all", value="Aapke VC me sabhi members ko Server Mute kar dega.", inline=False)
        embed.add_field(name="!vcm unmute all", value="Aapke VC me sabhi members ko Server Unmute kar dega.", inline=False)
        embed.add_field(name="!vcm def all", value="Aapke VC me sabhi members ko Server Deafen kar dega.", inline=False)
        embed.add_field(name="!vcm undef all", value="Aapke VC me sabhi members ko Server Undeafen kar dega.", inline=False)
        embed.add_field(name="!vcm kick all", value="Aapke VC ke sabhi members ko disconnect/kick kar dega.", inline=False)
        embed.add_field(name="!vcall parms on/off", value="[Admin/Owner Only] Toggle karein ki permissions waale log commands chala sakte hain ya sirf Owner/Admins.", inline=False)
        embed.set_footer(text="VCHelper Manager")
        await ctx.send(embed=embed)

    @vcm_group.command(name="drag")
    async def vcm_drag(self, ctx: commands.Context):
        if not self.has_vc_permissions(ctx):
            return await ctx.send("❌ Aapke paas VC Drag use karne ki permission nahi hai!")

        embed = discord.Embed(
            title="🚚 Voice Channel Dynamic Drag",
            description="1. **Source VC** select karein (Jahan se log drag karne hain).\n"
                        "2. **Target VC** select karein (Jahan log bhejne hain).\n"
                        "3. **Move All Members** button click karein.",
            color=discord.Color.blue()
        )
        view = VCDragView(ctx)
        await ctx.send(embed=embed, view=view)

    @vcm_group.command(name="mute")
    async def vcm_mute(self, ctx: commands.Context, mode: str = None):
        if not self.has_vc_permissions(ctx):
            return await ctx.send("❌ Aapke paas ye command chalane ki permission nahi hai!")

        if mode != "all":
            return await ctx.send("❓ Usage: `!vcm mute all`")

        if not ctx.author.voice or not ctx.author.voice.channel:
            return await ctx.send("❌ You must be in a Voice Channel to use this command!")

        vc = ctx.author.voice.channel
        muted_count = 0

        for member in vc.members:
            if member != ctx.author and not member.bot:
                try:
                    await member.edit(mute=True, reason=f"VC Mute All by {ctx.author}")
                    muted_count += 1
                except discord.Forbidden:
                    continue

        await ctx.send(f"🔇 **Muted {muted_count} members** in **{vc.name}**.")

    @vcm_group.command(name="unmute")
    async def vcm_unmute(self, ctx: commands.Context, mode: str = None):
        if not self.has_vc_permissions(ctx):
            return await ctx.send("❌ Aapke paas ye command chalane ki permission nahi hai!")

        if mode != "all":
            return await ctx.send("❓ Usage: `!vcm unmute all`")

        if not ctx.author.voice or not ctx.author.voice.channel:
            return await ctx.send("❌ You must be in a Voice Channel to use this command!")

        vc = ctx.author.voice.channel
        unmuted_count = 0

        for member in vc.members:
            if not member.bot:
                try:
                    await member.edit(mute=False, reason=f"VC Unmute All by {ctx.author}")
                    unmuted_count += 1
                except discord.Forbidden:
                    continue

        await ctx.send(f"🔊 **Unmuted {unmuted_count} members** in **{vc.name}**.")

    @vcm_group.command(name="def", aliases=["deaf"])
    async def vcm_def(self, ctx: commands.Context, mode: str = None):
        if not self.has_vc_permissions(ctx):
            return await ctx.send("❌ Aapke paas ye command chalane ki permission nahi hai!")

        if mode != "all":
            return await ctx.send("❓ Usage: `!vcm def all`")

        if not ctx.author.voice or not ctx.author.voice.channel:
            return await ctx.send("❌ You must be in a Voice Channel to use this command!")

        vc = ctx.author.voice.channel
        deaf_count = 0

        for member in vc.members:
            if member != ctx.author and not member.bot:
                try:
                    await member.edit(deafen=True, reason=f"VC Deafen All by {ctx.author}")
                    deaf_count += 1
                except discord.Forbidden:
                    continue

        await ctx.send(f"🎧 **Deafened {deaf_count} members** in **{vc.name}**.")

    @vcm_group.command(name="undef", aliases=["undeaf"])
    async def vcm_undef(self, ctx: commands.Context, mode: str = None):
        if not self.has_vc_permissions(ctx):
            return await ctx.send("❌ Aapke paas ye command chalane ki permission nahi hai!")

        if mode != "all":
            return await ctx.send("❓ Usage: `!vcm undef all`")

        if not ctx.author.voice or not ctx.author.voice.channel:
            return await ctx.send("❌ You must be in a Voice Channel to use this command!")

        vc = ctx.author.voice.channel
        undeaf_count = 0

        for member in vc.members:
            if not member.bot:
                try:
                    await member.edit(deafen=False, reason=f"VC Undeafen All by {ctx.author}")
                    undeaf_count += 1
                except discord.Forbidden:
                    continue

        await ctx.send(f"🎧 **Undeafened {undeaf_count} members** in **{vc.name}**.")

    @vcm_group.command(name="kick")
    async def vcm_kick(self, ctx: commands.Context, mode: str = None):
        if not self.has_vc_permissions(ctx):
            return await ctx.send("❌ Aapke paas ye command chalane ki permission nahi hai!")

        if mode != "all":
            return await ctx.send("❓ Usage: `!vcm kick all`")

        if not ctx.author.voice or not ctx.author.voice.channel:
            return await ctx.send("❌ You must be in a Voice Channel to use this command!")

        vc = ctx.author.voice.channel
        kicked_count = 0

        for member in vc.members:
            if member != ctx.author and not member.bot:
                try:
                    await member.edit(voice_channel=None, reason=f"VC Kick All by {ctx.author}")
                    kicked_count += 1
                except discord.Forbidden:
                    continue

        await ctx.send(f"💥 **Disconnected {kicked_count} members** from **{vc.name}**.")

async def setup(bot):
    await bot.add_cog(VCHelper(bot))
