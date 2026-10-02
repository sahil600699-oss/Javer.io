import discord
from discord.ext import commands

RED = discord.Color.red()


PAGES = [
    ("HELP CENTER", "**Welcome to the Help Center.**\n\nUse **Back** and **Next** to browse pages, or use the **Select a page** menu to open a section directly.\n\n**Sections**\n2. Moderation\n3. Protection\n4. Logging\n5. Voice\n6. Music\n7. Roles\n8. Welcome & Automation\n9. Utility\n10. Fun & Games\n11. Community Game\n12. Imposter\n13. Premium"),
    ("MODERATION", "**Member Moderation**\n`!kick @user [reason]` — Kick a member.\n`!ban @user [reason]` — Ban a member.\n`!clear <amount>` / `!purge <amount>` — Delete messages.\n`!change nick @user <name>` — Change a member nickname.\n`!mute @user` — Voice mute a member.\n`!def @user` — Voice deafen a member.\n`!move @user <channel>` — Move a member to another voice channel.\n`!roleg @user <role>` — Give a role to a member.\n`!serverinfo` / `!si` — View server information."),
    ("PROTECTION", "**Anti-Nuke Protection**\n`!antinuke` / `!nuke` — Open the protection system.\n`!antinuke spam` — Configure spam protection.\n`!antinuke spamdel` — Remove spam protection.\n`!antinuke url action` — Configure URL protection.\n`!antinuke urldel` — Remove URL protection.\n`!antinuke ban` — Configure ban protection.\n`!antinuke bandel` — Remove ban protection.\n`!antinuke app` — Configure application/bot protection.\n`!antinuke whitelist` / `!nuke wl` — Manage whitelist protection.\n`!antinuke unwhitelist` / `!nuke unwl` — Remove a whitelist entry.\n`!whitelistuser` — View whitelisted users.\n`!antinuke logs` — Set the protection log channel.\n`!antinuke logsdel` — Remove the protection log channel.\n`!antinuke list` — View protection configuration.\n`!antinuke resetall` — Reset protection settings."),
    ("LOGGING", "**Server Activity Logs**\n`!log` — Open the logging system.\n`!log setup` — Configure server logging.\n\nThe logging system records supported activity such as message deletion/editing, voice activity, member joins/leaves, bans and role changes.\n\n**Message Tracking**\n`!msg` — Open message tracking.\n`!msg top` — View the message activity leaderboard.\n`!msg help` — View message tracker help.\n`!msgw` — Open weekly message tracking.\n`!msgw top` — View the weekly message leaderboard."),
    ("VOICE", "**Voice Tools**\n`!vcall` — Configure voice-call permissions.\n`!pull` — Pull a member into your current voice channel.\n`!vcm` — Open voice mass-control tools.\n`!vcm help` / `!vcm h` — Voice mass-control help.\n`!vcm drag` — Drag members between voice channels.\n`!vcm mute` — Mass voice mute controls.\n`!vcm unmute` — Mass voice unmute controls.\n`!vcm def` / `!vcm deaf` — Mass deafen controls.\n`!vcm undef` / `!vcm undeaf` — Remove mass deafen.\n`!vcm kick` — Disconnect members from voice.\n\n**Voice Tracking**\n`!vc` — Open voice tracking.\n`!vc top` — View voice activity leaderboard.\n`!vc help` — View voice tracker help.\n`!vcw` — Open weekly voice tracking.\n`!vcw top` — View the weekly voice leaderboard."),
    ("MUSIC", "**Music Player**\n`!play <song or URL>` / `!p <song or URL>` — Play music.\n`!join` — Join your voice channel.\n`!leave` — Leave the voice channel.\n`!stop` — Stop playback.\n`!queue` — View the music queue.\n`!vol <amount>` — Change music volume.\n\n*The additional Music commands above are documented here for the planned music system.*"),
    ("ROLES", "**Role Management**\n`!role` — Open role management.\n`!role help` — Role command help.\n`!role menu` — Open the role menu.\n`!role add` — Add a role.\n`!role remove` — Remove a role.\n`!role perms` — Manage role permissions.\n`!role members` — View role members.\n`!role delete` — Delete a role.\n`!role paste` — Paste saved role configuration.\n`!role all` — Manage roles for all members.\n`!role humans` — Manage roles for human members.\n`!role bots` — Manage roles for bots.\n`!role removeall` — Remove managed roles.\n\n**Role Plans**\n`!role plan create` • `!role plan add` • `!role plan details` • `!role plan list` • `!role plan delete`\n\n**Autorole**\n`!role autorole human` — Configure human autorole.\n`!role autorole bot` — Configure bot autorole."),
    ("WELCOME & AUTOMATION", "**Welcome**\n`!welcome` — Open welcome settings.\n`!welcome setup` — Configure welcome messages.\n`!welcome msg` — Set the welcome message.\n`!welcome image` — Configure the welcome image.\n`!welcome reset` — Reset welcome settings.\n`!welcome test` — Test the welcome system.\n\n**Autoresponder**\n`!autoresponse` / `!autoadd` — Open autoresponder controls.\n`!autorec` / `!autoreaction` — Configure automatic reactions.\n`!autorecdel` — Delete an automatic reaction.\n`!autodel` — Delete an autoresponder.\n`!autolist` — List autoresponders.\n\n**Autosend**\n`!autosend` — Open autosend controls.\n`!autosend help` — Show autosend help.\n`!autosendoff` — Disable autosend.\n\n**AFK**\n`!afk [message]` — Set an AFK status."),
    ("UTILITY", "**Profile & Server Utilities**\n`!av` / `!avatar` / `!pfp` — View a user's avatar.\n`!banner [@user]` — View a user's banner.\n`!serverpfp` — Change the bot's server profile picture (Premium).\n`!servernick <name>` — Change the bot nickname.\n`!serverb` / `!serverbanner` — Manage the server banner."),
    ("FUN & GAMES", "**Fun Commands**\n`!roast @user` — Send a playful roast.\n`!flirt @user` — Send a playful flirt message.\n`!motivation` — Get a motivational message.\n\n**GIF Actions**\n`!slap @user` • `!kiss @user` • `!hug @user` • `!punch @user` • `!boss @user`\n\n**Games**\n`!xo @user` — Start an XO game.\n`!kingdom` — Open the Kingdom game."),
    ("COMMUNITY GAME", "**Community RPG**\n`!c` — Open the Community Game.\n`!c profile` / `!c p` — View your profile.\n`!c lvl` / `!c l` — View your level.\n`!c edit` / `!c e` — Open profile editing.\n`!c edit name` / `!c edit n` — Change your name.\n`!c edit image` / `!c edit i` — Change your profile image.\n`!c hunt` / `!c h` — Hunt for rewards.\n`!c huntauto` / `!c ha` — Automatic hunting.\n`!c team create` — Create a team.\n`!c team room` — Open the team room.\n`!c raid spawn` — Spawn a raid.\n`!c raid start` — Start a raid.\n`!c shop` — Open the shop.\n`!c buy` — Buy an item.\n`!c top` / `!c t` — View the leaderboard.\n`!c battle all` / `!c battle a` — View battle targets.`"),
    ("IMPOSTER", "**Imposter Game**\n`!imposter` — Start an Imposter game.\n`!next` — Move to the next turn.\n`!impoend` — End the current game.\n`!impohelp` — View Imposter game help."),
    ("PREMIUM", "**Premium Information**\n\nPremium is required for a **custom bot server PFP**.\n\nTo get Premium, **join the support server using the link in the bot's profile bio.**\n\nThe support server contains Premium information, plans and purchase details.")
]


class HelpSelect(discord.ui.Select):
    def __init__(self, help_view):
        self.help_view = help_view
        options = [
            discord.SelectOption(label=f"{i + 1}. {title}", value=str(i), description=f"Open the {title} page")
            for i, (title, _) in enumerate(PAGES)
        ]
        super().__init__(placeholder="Select a page...", min_values=1, max_values=1, options=options, row=1)

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.help_view.ctx.author.id:
            return await interaction.response.send_message("This help menu belongs to the user who opened it.", ephemeral=True)
        self.help_view.current_page = int(self.values[0])
        self.help_view.update_buttons()
        await interaction.response.edit_message(embed=self.help_view.get_embed(), view=self.help_view)


class HelpView(discord.ui.View):
    def __init__(self, ctx):
        super().__init__(timeout=180)
        self.ctx = ctx
        self.current_page = 0
        self.total_pages = len(PAGES)
        self.back_button = discord.ui.Button(label="Back", style=discord.ButtonStyle.secondary, row=2)
        self.next_button = discord.ui.Button(label="Next", style=discord.ButtonStyle.secondary, row=2)
        self.back_button.callback = self.go_back
        self.next_button.callback = self.go_next
        self.add_item(HelpSelect(self))
        self.add_item(self.back_button)
        self.add_item(self.next_button)
        self.update_buttons()

    def update_buttons(self):
        self.back_button.disabled = self.current_page == 0
        self.next_button.disabled = self.current_page == self.total_pages - 1

    async def go_back(self, interaction: discord.Interaction):
        if interaction.user.id != self.ctx.author.id:
            return await interaction.response.send_message("This help menu belongs to the user who opened it.", ephemeral=True)
        self.current_page = max(0, self.current_page - 1)
        self.update_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    async def go_next(self, interaction: discord.Interaction):
        if interaction.user.id != self.ctx.author.id:
            return await interaction.response.send_message("This help menu belongs to the user who opened it.", ephemeral=True)
        self.current_page = min(self.total_pages - 1, self.current_page + 1)
        self.update_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    def get_embed(self):
        title, description = PAGES[self.current_page]
        embed = discord.Embed(title=title, description=description, color=RED)
        embed.set_footer(text=f"Page {self.current_page + 1}/{self.total_pages} • Requested by {self.ctx.author.display_name}")
        return embed


class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="help")
    async def help_command(self, ctx):
        """Open the professional help center."""
        view = HelpView(ctx)
        await ctx.send(embed=view.get_embed(), view=view)


async def setup(bot):
    await bot.add_cog(Help(bot))
