import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timezone

# SC Permission Manager for discord.py 2.x
# Uses bot.async_db["sc_permission_manager"] for persistent VIEW role and audit-channel settings.
# No permission snapshots, backups, or Undo history are stored.

RED = discord.Color.red()
DARK = discord.Color.from_rgb(24, 25, 28)
DANGEROUS = {
    "administrator", "manage_guild", "manage_roles", "manage_channels",
    "manage_webhooks", "ban_members", "kick_members", "mention_everyone",
    "manage_messages"
}

def pretty_permission(name):
    return name.replace("_", " ").title()

def perm_value(perms, name):
    value = getattr(perms, name, None)
    return "ON" if value is True else "OFF" if value is False else "N/A"

def base_embed(title, description=None):
    e = discord.Embed(title=f"🔴 {title}", description=description, color=RED,
                      timestamp=datetime.now(timezone.utc))
    e.set_footer(text="SC Permission Manager • Secure • Javer.io")
    return e

class SCView(discord.ui.View):
    def __init__(self, cog, owner_id, guild_id, *, timeout=180):
        super().__init__(timeout=timeout)
        self.cog = cog
        self.owner_id = owner_id
        self.guild_id = guild_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not interaction.guild or interaction.guild.id != self.guild_id:
            await interaction.response.send_message("🔒 This panel belongs to another server.", ephemeral=True)
            return False
        access = await self.cog.access_level(interaction.user, interaction.guild)
        if access == "none":
            await interaction.response.send_message("🔒 You are not authorized to use SC.", ephemeral=True)
            return False
        # Panels are private to the person who opened them, except the configured view-role can view.
        if interaction.user.id != self.owner_id and access != "owner":
            await interaction.response.send_message("🔒 Open your own SC panel first.", ephemeral=True)
            return False
        return True

class TargetTypeSelect(discord.ui.Select):
    def __init__(self, parent_view, options, placeholder):
        self.parent_view = parent_view
        super().__init__(placeholder=placeholder, min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        self.parent_view.selection = self.values[0]
        await interaction.response.edit_message(
            embed=base_embed("Selection Ready", f"Selected: **{self.values[0]}**\nPress **Continue** to view results."),
            view=self.parent_view
        )

class PermissionSearchView(SCView):
    def __init__(self, cog, ctx, owner_id):
        super().__init__(cog, owner_id, ctx.guild.id)
        self.ctx = ctx
        self.permission = None
        self.target_type = None
        perms = [p for p in discord.Permissions.VALID_FLAGS if p not in ("use_application_commands",)]
        self.add_item(PermissionSelect(self, perms))
        self.add_item(TargetTypeSelect(self, [
            discord.SelectOption(label="Roles", value="roles", emoji="🛡️"),
            discord.SelectOption(label="Text Channels", value="text", emoji="💬"),
            discord.SelectOption(label="Voice Channels", value="voice", emoji="🔊"),
        ], "Choose target type"))

    @discord.ui.button(label="Continue", style=discord.ButtonStyle.danger, row=2)
    async def continue_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.permission or not self.target_type:
            return await interaction.response.send_message("Select a permission and target type first.", ephemeral=True)
        guild = interaction.guild
        lines = []
        if self.target_type == "roles":
            for role in sorted(guild.roles, key=lambda r: r.position, reverse=True):
                if role.is_default():
                    continue
                if self.permission == "administrator":
                    enabled = role.permissions.administrator
                else:
                    enabled = getattr(role.permissions, self.permission, False)
                if enabled:
                    lines.append(f"• {role.mention} (`{role.id}`)")
        else:
            channels = [c for c in guild.channels if
                        (self.target_type == "text" and isinstance(c, (discord.TextChannel, discord.ForumChannel, discord.Thread))) or
                        (self.target_type == "voice" and isinstance(c, (discord.VoiceChannel, discord.StageChannel)))]
            for channel in channels:
                # Channel overrides are explicit allow/deny. Inherited/effective permissions are not guessed.
                if self.permission == "administrator":
                    continue
                everyone = channel.overwrites_for(guild.default_role)
                allowed = getattr(everyone, self.permission, None)
                role_allows = any(getattr(channel.overwrites_for(r), self.permission, None) is True for r in guild.roles)
                if allowed is True or role_allows:
                    lines.append(f"• {channel.mention} (`{channel.id}`)")
        e = base_embed(f"Permission Search • {pretty_permission(self.permission)}",
                       f"**Target:** {self.target_type.title()}\n**Matches:** {len(lines)}")
        e.description += "\n\n" + ("\n".join(lines[:35]) if lines else "No explicit matching permissions found.")
        if len(lines) > 35:
            e.set_footer(text=f"Showing 35 of {len(lines)} matches • SC Permission Manager")
        await interaction.response.edit_message(embed=e, view=None)

class PermissionSelect(discord.ui.Select):
    def __init__(self, parent_view, permissions):
        self.parent_view = parent_view
        # Discord select limit is 25 options; provide common permissions first.
        common = ["administrator", "manage_guild", "manage_roles", "manage_channels", "view_channel",
                  "send_messages", "read_message_history", "connect", "speak", "mute_members",
                  "deafen_members", "move_members", "manage_messages", "mention_everyone",
                  "kick_members", "ban_members", "manage_webhooks", "attach_files", "embed_links",
                  "use_application_commands", "create_instant_invite", "add_reactions", "stream",
                  "send_messages_in_threads", "manage_threads"]
        opts = []
        for p in common[:25]:
            if p in permissions:
                opts.append(discord.SelectOption(label=pretty_permission(p), value=p,
                                                 description="⚠️ Powerful permission" if p in DANGEROUS else None))
        super().__init__(placeholder="Choose a permission", min_values=1, max_values=1, options=opts)

    async def callback(self, interaction: discord.Interaction):
        self.parent_view.permission = self.values[0]
        await interaction.response.send_message(
            f"Selected permission: **{pretty_permission(self.values[0])}**", ephemeral=True
        )

class SCManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @property
    def settings(self):
        db = getattr(self.bot, "async_db", None)
        return db["sc_permission_manager"] if db is not None else None

    async def get_settings(self, guild_id):
        if self.settings is None:
            return {}
        return await self.settings.find_one({"guild_id": guild_id}) or {}

    async def access_level(self, member, guild):
        if not isinstance(member, discord.Member):
            return "none"
        if member.id == guild.owner_id:
            return "owner"
        data = await self.get_settings(guild.id)
        view_role_id = data.get("view_role_id")
        if view_role_id and any(r.id == int(view_role_id) for r in member.roles):
            return "view"
        return "none"

    async def require_access(self, ctx, *, edit=False):
        if not ctx.guild or not isinstance(ctx.author, discord.Member):
            await ctx.send(embed=base_embed("Server Only", "SC commands can only be used inside a server."))
            return False
        level = await self.access_level(ctx.author, ctx.guild)
        if level == "owner":
            return True
        if level == "view" and not edit:
            return True
        msg = "Only the server owner can edit settings." if level == "view" else "You are not authorized to use SC."
        await ctx.send(embed=base_embed("Access Denied", msg))
        return False

    async def interaction_can_edit(self, interaction):
        return await self.access_level(interaction.user, interaction.guild) == "owner"

    @commands.hybrid_group(name="sc", invoke_without_command=True, description="SC Permission Manager")
    async def sc(self, ctx):
        await ctx.send(embed=base_embed("SC Permission Manager", "Use `sc help` to see available commands."))

    @sc.command(name="help", description="Show SC commands")
    async def sc_help(self, ctx):
        if not await self.require_access(ctx):
            return
        e = base_embed("Command Guide")
        e.description = (
            "`/sc channel <channel>` — View channel permissions\n"
            "`/sc role <role>` — View role permissions\n"
            "`/sc find` — Browse channels, roles, and members\n"
            "`/sc permission` — Search for a permission\n"
            "`/sc check <member or role>` — Inspect a member or role\n"
            "`/sc info` — Server permission overview\n"
            "`/sc view <role>` — Set read-only role (owner only)\n"
            "`/sc audit <channel>` — Set permission audit channel (owner only)\n"
            "`/sc help` — Show this guide"
        )
        await ctx.send(embed=e)

    @sc.command(name="info", description="Show server permission overview")
    async def sc_info(self, ctx):
        if not await self.require_access(ctx):
            return
        g = ctx.guild
        admin_roles = [r.mention for r in g.roles if not r.is_default() and r.permissions.administrator]
        manage_roles = [r.mention for r in g.roles if not r.is_default() and r.permissions.manage_roles]
        manage_channels = [r.mention for r in g.roles if not r.is_default() and r.permissions.manage_channels]
        e = base_embed(f"{g.name} • Permission Overview")
        e.add_field(name="📊 Server inventory", value=f"Roles: **{len(g.roles)-1}**\nText channels: **{sum(isinstance(c, discord.TextChannel) for c in g.channels)}**\nVoice channels: **{sum(isinstance(c, (discord.VoiceChannel, discord.StageChannel)) for c in g.channels)}**", inline=False)
        e.add_field(name="⚠️ Administrator roles", value=", ".join(admin_roles[:15]) or "None", inline=False)
        e.add_field(name="🛡️ Manage Roles", value=", ".join(manage_roles[:15]) or "None", inline=False)
        e.add_field(name="🧰 Manage Channels", value=", ".join(manage_channels[:15]) or "None", inline=False)
        await ctx.send(embed=e)

    @sc.command(name="check", description="Check a member or role")
    async def sc_check(self, ctx, target: discord.Member | discord.Role):
        if not await self.require_access(ctx):
            return
        e = base_embed("Permission Check")
        if isinstance(target, discord.Member):
            e.description = f"**Member:** {target.mention}\n**ID:** `{target.id}`\n**Joined:** {discord.utils.format_dt(target.joined_at, 'R') if target.joined_at else 'Unknown'}"
            e.add_field(name="🏷️ Roles", value=", ".join(r.mention for r in reversed(target.roles) if not r.is_default()) or "No roles", inline=False)
            perms = target.guild_permissions
            enabled = [pretty_permission(n) for n, v in perms if v]
            e.add_field(name="🔑 Effective server permissions", value=", ".join(enabled[:45]) or "No permissions", inline=False)
        else:
            e.description = f"**Role:** {target.mention}\n**ID:** `{target.id}`\n**Position:** `{target.position}`\n**Members:** `{len(target.members)}`"
            enabled = [pretty_permission(n) for n, v in target.permissions if v]
            e.add_field(name="🔑 Enabled role permissions", value=", ".join(enabled[:45]) or "No permissions", inline=False)
        await ctx.send(embed=e)

    @sc.command(name="role", description="View a role's permissions")
    async def sc_role(self, ctx, role: discord.Role):
        if not await self.require_access(ctx):
            return
        e = base_embed(f"Role Details • {role.name}")
        e.description = f"{role.mention}\n**ID:** `{role.id}` • **Position:** `{role.position}` • **Members:** `{len(role.members)}`"
        enabled = [pretty_permission(n) for n, v in role.permissions if v]
        e.add_field(name="✅ Enabled permissions", value=", ".join(enabled[:45]) or "None", inline=False)
        dangerous = [pretty_permission(n) for n, v in role.permissions if v and n in DANGEROUS]
        e.add_field(name="⚠️ Dangerous permissions", value=", ".join(dangerous) or "None", inline=False)
        if await self.access_level(ctx.author, ctx.guild) == "owner":
            await ctx.send(embed=e, view=RoleEditView(self, role, ctx.author.id))
        else:
            await ctx.send(embed=e)

    @sc.command(name="channel", description="View a channel's permissions")
    async def sc_channel(self, ctx, channel: discord.abc.GuildChannel):
        if not await self.require_access(ctx):
            return
        e = base_embed(f"Channel Details • {channel.name}")
        e.description = f"{channel.mention}\n**ID:** `{channel.id}`\n**Type:** `{channel.type}`\n**Category:** {channel.category.mention if getattr(channel, 'category', None) else 'None'}"
        rows = []
        for target, overwrite in channel.overwrites.items():
            allow, deny = overwrite.pair()
            a = [pretty_permission(n) for n, v in allow if v]
            d = [pretty_permission(n) for n, v in deny if v]
            rows.append(f"**{target.mention}**\n🟢 Allow: {', '.join(a[:10]) or 'None'}\n🔴 Deny: {', '.join(d[:10]) or 'None'}")
        e.add_field(name="🔐 Permission Overrides", value="\n\n".join(rows[:8]) or "No explicit overwrites.", inline=False)
        if await self.access_level(ctx.author, ctx.guild) == "owner":
            await ctx.send(embed=e, view=ChannelEditView(self, channel, ctx.author.id))
        else:
            await ctx.send(embed=e)

    @sc.command(name="view", description="Set a role that can view SC details without editing")
    async def sc_view(self, ctx, role: discord.Role):
        if not ctx.guild or ctx.author.id != ctx.guild.owner_id:
            return await ctx.send(embed=base_embed("Access Denied", "Only the server owner can set the SC read-only role."))
        if self.settings is None:
            return await ctx.send(embed=base_embed("Database Error", "MongoDB async database is not available."))
        await self.settings.update_one({"guild_id": ctx.guild.id}, {"$set": {"view_role_id": role.id}}, upsert=True)
        e = base_embed("Read-Only Role Updated", f"{role.mention} members can view SC details but cannot edit permissions.")
        e.add_field(name="🔒 Access level", value="Read-only")
        await ctx.send(embed=e)

    @sc.command(name="audit", description="Set the channel for permission change logs")
    async def sc_audit(self, ctx, channel: discord.TextChannel):
        if not ctx.guild or ctx.author.id != ctx.guild.owner_id:
            return await ctx.send(embed=base_embed("Access Denied", "Only the server owner can configure SC audit logging."))
        if self.settings is None:
            return await ctx.send(embed=base_embed("Database Error", "MongoDB async database is not available."))
        await self.settings.update_one({"guild_id": ctx.guild.id}, {"$set": {"audit_channel_id": channel.id}}, upsert=True)
        await ctx.send(embed=base_embed("Audit Channel Configured", f"Permission change logs will be sent to {channel.mention}.\n\nNote: Discord Audit Log access is required to identify the actor."))

    @sc.command(name="permission", description="Search roles/channels with a permission enabled")
    async def sc_permission(self, ctx):
        if not await self.require_access(ctx):
            return
        view = PermissionSearchView(self, ctx, ctx.author.id)
        e = base_embed("Permission Search", "Select a permission and target type, then press **Continue**.")
        await ctx.send(embed=e, view=view)

    @sc.command(name="find", description="Browse server roles and channels")
    async def sc_find(self, ctx):
        if not await self.require_access(ctx):
            return
        view = FindView(self, ctx, ctx.author.id)
        await ctx.send(embed=base_embed("Find a Target", "Choose Text Channels, Voice Channels, Roles, or Members. Use **Next** to browse and **Confirm** to inspect."), view=view)

    @commands.Cog.listener()
    async def on_guild_role_update(self, before, after):
        await self._audit_permission_change(after.guild, "Role permissions changed", before, after)

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before, after):
        if before.overwrites != after.overwrites:
            await self._audit_permission_change(after.guild, "Channel permission overrides changed", before, after)

    async def _audit_permission_change(self, guild, title, before, after):
        if self.settings is None:
            return
        try:
            data = await self.get_settings(guild.id)
            channel = guild.get_channel(int(data.get("audit_channel_id", 0)))
            if not isinstance(channel, discord.TextChannel):
                return
            if isinstance(before, discord.Role):
                old = dict(before.permissions)
                new = dict(after.permissions)
                changed = [(n, old.get(n), new.get(n)) for n in old if old.get(n) != new.get(n)]
                lines = [f"• **{pretty_permission(n)}:** `{a}` → `{b}`" for n, a, b in changed]
                e = base_embed(title, f"**Role:** {after.mention}\n**ID:** `{after.id}`\n" + ("\n".join(lines[:25]) or "No permission flag differences detected."))
            else:
                # Discord overwrites can differ by target; show each target's changed allow/deny flags.
                old_map, new_map = before.overwrites, after.overwrites
                lines = []
                targets = set(old_map) | set(new_map)
                for target in targets:
                    o = old_map.get(target, discord.PermissionOverwrite())
                    n = new_map.get(target, discord.PermissionOverwrite())
                    for perm in discord.Permissions.VALID_FLAGS:
                        ov, nv = getattr(o, perm, None), getattr(n, perm, None)
                        if ov != nv:
                            lines.append(f"• {target.mention} — **{pretty_permission(perm)}:** `{ov}` → `{nv}`")
                e = base_embed(title, f"**Channel:** {after.mention}\n**ID:** `{after.id}`\n" + ("\n".join(lines[:25]) or "Overwrite changes detected."))
            e.add_field(name="Actor", value="Unknown (not reliably available from this event)", inline=False)
            await channel.send(embed=e)
        except Exception as exc:
            print(f"[SC Audit] Failed to send audit event: {type(exc).__name__}: {exc}")

EDITABLE_ROLE_PERMS = [
    "administrator", "manage_guild", "manage_roles", "manage_channels",
    "manage_webhooks", "manage_messages", "manage_threads", "kick_members",
    "ban_members", "moderate_members", "mention_everyone", "view_channel",
    "send_messages", "read_message_history", "embed_links", "attach_files",
    "add_reactions", "create_instant_invite", "connect", "speak",
    "mute_members", "deafen_members", "move_members", "stream",
    "send_messages_in_threads"
]

class PermissionPicker(discord.ui.Select):
    def __init__(self, parent, *, channel_mode=False):
        self.parent = parent
        options = []
        for name in EDITABLE_ROLE_PERMS[:25]:
            options.append(discord.SelectOption(
                label=pretty_permission(name),
                value=name,
                description="Dangerous permission — confirmation required" if name in DANGEROUS else None
            ))
        super().__init__(placeholder="Choose a permission to edit", min_values=1, max_values=1, options=options, row=1 if channel_mode else 0)

    async def callback(self, interaction: discord.Interaction):
        self.parent.permission_name = self.values[0]
        await interaction.response.edit_message(
            embed=base_embed("Permission Selected",
                             f"Selected: **{pretty_permission(self.values[0])}**\n"
                             "Choose an action below. Dangerous changes require confirmation."),
            view=self.parent
        )

class RoleEditView(SCView):
    def __init__(self, cog, role, owner_id):
        super().__init__(cog, owner_id, role.guild.id)
        self.role = role
        self.permission_name = None
        self.add_item(PermissionPicker(self))

    async def change_permission(self, interaction, value):
        if not await self.cog.interaction_can_edit(interaction):
            return await interaction.response.send_message("🔒 Only the server owner can edit SC permissions.", ephemeral=True)
        if not self.permission_name:
            return await interaction.response.send_message("Select a permission first.", ephemeral=True)
        if self.role.is_default():
            return await interaction.response.send_message("The @everyone role cannot be edited from this panel.", ephemeral=True)
        if self.role >= interaction.guild.me.top_role:
            return await interaction.response.send_message("The bot's highest role must be above the target role.", ephemeral=True)
        if self.permission_name in DANGEROUS:
            view = ConfirmRoleChangeView(self.cog, self.role, self.permission_name, value, interaction.user.id)
            return await interaction.response.send_message(
                embed=base_embed("⚠️ Confirm Dangerous Permission",
                    f"Role: {self.role.mention}\nPermission: **{pretty_permission(self.permission_name)}**\n"
                    f"New value: **{'ON' if value else 'OFF'}**\n\nConfirm this change?"),
                view=view, ephemeral=True
            )
        await interaction.response.defer(ephemeral=True)
        await self._apply(interaction, value)

    async def _apply(self, interaction, value):
        try:
            permissions = self.role.permissions
            setattr(permissions, self.permission_name, value)
            await self.role.edit(permissions=permissions, reason=f"SC Permission Manager by {interaction.user} ({interaction.user.id})")
            await interaction.followup.send(
                embed=base_embed("Role Permission Updated",
                    f"Role: {self.role.mention}\nPermission: **{pretty_permission(self.permission_name)}**\n"
                    f"New value: **{'ON' if value else 'OFF'}**"),
                ephemeral=True
            )
        except discord.Forbidden:
            await interaction.followup.send(embed=base_embed("Missing Permission", "Bot cannot edit this role. Check Manage Roles and role hierarchy."), ephemeral=True)
        except discord.HTTPException as exc:
            await interaction.followup.send(embed=base_embed("Edit Failed", f"Discord rejected the change: `{exc}`"), ephemeral=True)

    @discord.ui.button(label="Turn ON", style=discord.ButtonStyle.success, row=1)
    async def turn_on(self, interaction, button):
        await self.change_permission(interaction, True)

    @discord.ui.button(label="Turn OFF", style=discord.ButtonStyle.danger, row=1)
    async def turn_off(self, interaction, button):
        await self.change_permission(interaction, False)

class ConfirmRoleChangeView(discord.ui.View):
    def __init__(self, cog, role, permission_name, value, owner_id):
        super().__init__(timeout=60)
        self.cog, self.role, self.permission_name, self.value, self.owner_id = cog, role, permission_name, value, owner_id

    async def interaction_check(self, interaction):
        if not interaction.guild or interaction.user.id != self.owner_id or not await self.cog.interaction_can_edit(interaction):
            await interaction.response.send_message("🔒 Only the server owner who started this confirmation can approve it.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Confirm Change", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction, button):
        try:
            if self.role.is_default() or self.role >= interaction.guild.me.top_role:
                return await interaction.response.send_message("Role hierarchy prevents this edit.", ephemeral=True)
            perms = self.role.permissions
            setattr(perms, self.permission_name, self.value)
            await self.role.edit(permissions=perms, reason=f"SC confirmed change by {interaction.user} ({interaction.user.id})")
            await interaction.response.edit_message(
                embed=base_embed("Permission Updated", f"{self.role.mention}\n**{pretty_permission(self.permission_name)}** → **{'ON' if self.value else 'OFF'}**"),
                view=None
            )
        except discord.HTTPException as exc:
            await interaction.response.send_message(f"Edit failed: `{exc}`", ephemeral=True)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction, button):
        await interaction.response.edit_message(embed=base_embed("Change Cancelled", "No permission was changed."), view=None)

class ChannelTargetSelect(discord.ui.Select):
    def __init__(self, parent, channel):
        self.parent = parent
        self.channel = channel
        targets = [channel.guild.default_role]
        targets += [r for r in sorted(channel.guild.roles, key=lambda x: x.position, reverse=True) if not r.is_default()][:24]
        options = [discord.SelectOption(label="@everyone", value=f"r:{channel.guild.id}")]
        options += [discord.SelectOption(label=r.name[:100], value=f"r:{r.id}") for r in targets[1:]]
        remaining = max(0, 25-len(options))
        members = list(channel.guild.members)[:remaining]
        options += [discord.SelectOption(label=f"Member: {m.display_name}"[:100], value=f"m:{m.id}") for m in members]
        super().__init__(placeholder="Select role/member override target", min_values=1, max_values=1, options=options[:25], row=0)

    async def callback(self, interaction):
        raw = self.values[0]
        kind, ident = raw.split(":", 1)
        self.parent.target = self.channel.guild.get_role(int(ident)) if kind == "r" else self.channel.guild.get_member(int(ident))
        await interaction.response.edit_message(
            embed=base_embed("Override Target Selected", f"Target: {self.parent.target.mention}\nNow select a permission and choose Allow, Deny, or Inherit."),
            view=self.parent
        )

class ChannelEditView(SCView):
    def __init__(self, cog, channel, owner_id):
        super().__init__(cog, owner_id, channel.guild.id)
        self.channel = channel
        self.target = None
        self.permission_name = None
        self.add_item(ChannelTargetSelect(self, channel))
        self.add_item(PermissionPicker(self, channel_mode=True))

    async def apply_override(self, interaction, value):
        if not await self.cog.interaction_can_edit(interaction):
            return await interaction.response.send_message("🔒 Only the server owner can edit SC permissions.", ephemeral=True)
        if not self.target or not self.permission_name:
            return await interaction.response.send_message("Select both an override target and a permission first.", ephemeral=True)
        if self.permission_name == "administrator":
            return await interaction.response.send_message("Administrator is a role permission, not a channel override.", ephemeral=True)
        if not interaction.guild.me.guild_permissions.manage_roles:
            return await interaction.response.send_message("Bot needs Manage Roles to edit channel permission overrides.", ephemeral=True)
        if isinstance(self.target, discord.Role) and not self.target.is_default() and self.target >= interaction.guild.me.top_role:
            return await interaction.response.send_message("Bot's highest role must be above the selected role.", ephemeral=True)
        if self.permission_name in DANGEROUS:
            return await interaction.response.send_message(
                embed=base_embed("⚠️ Confirm Channel Permission",
                    f"Channel: {self.channel.mention}\nTarget: {self.target.mention}\n"
                    f"Permission: **{pretty_permission(self.permission_name)}**\n"
                    f"New value: **{value if value is not None else 'INHERIT'}**"),
                view=ConfirmChannelChangeView(self.cog, self.channel, self.target, self.permission_name, value, interaction.user.id),
                ephemeral=True
            )
        await interaction.response.defer(ephemeral=True)
        await self._apply(interaction, value)

    async def _apply(self, interaction, value):
        try:
            overwrite = self.channel.overwrites_for(self.target)
            setattr(overwrite, self.permission_name, value)
            await self.channel.set_permissions(self.target, overwrite=overwrite,
                reason=f"SC Permission Manager by {interaction.user} ({interaction.user.id})")
            shown = "INHERIT" if value is None else ("ALLOW" if value else "DENY")
            await interaction.followup.send(embed=base_embed("Channel Permission Updated",
                f"Channel: {self.channel.mention}\nTarget: {self.target.mention}\n"
                f"Permission: **{pretty_permission(self.permission_name)}**\nNew value: **{shown}**"), ephemeral=True)
        except discord.Forbidden:
            await interaction.followup.send(embed=base_embed("Missing Permission", "Bot needs Manage Roles and must be allowed to edit this channel."), ephemeral=True)
        except discord.HTTPException as exc:
            await interaction.followup.send(embed=base_embed("Edit Failed", f"Discord rejected the change: `{exc}`"), ephemeral=True)

    @discord.ui.button(label="Allow", style=discord.ButtonStyle.success, row=2)
    async def allow_button(self, interaction, button):
        await self.apply_override(interaction, True)

    @discord.ui.button(label="Deny", style=discord.ButtonStyle.danger, row=2)
    async def deny_button(self, interaction, button):
        await self.apply_override(interaction, False)

    @discord.ui.button(label="Inherit", style=discord.ButtonStyle.secondary, row=2)
    async def inherit_button(self, interaction, button):
        await self.apply_override(interaction, None)

class ConfirmChannelChangeView(discord.ui.View):
    def __init__(self, cog, channel, target, permission_name, value, owner_id):
        super().__init__(timeout=60)
        self.cog, self.channel, self.target = cog, channel, target
        self.permission_name, self.value, self.owner_id = permission_name, value, owner_id

    async def interaction_check(self, interaction):
        if not interaction.guild or interaction.user.id != self.owner_id or not await self.cog.interaction_can_edit(interaction):
            await interaction.response.send_message("🔒 Only the server owner who started this confirmation can approve it.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Confirm Change", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction, button):
        try:
            overwrite = self.channel.overwrites_for(self.target)
            setattr(overwrite, self.permission_name, self.value)
            await self.channel.set_permissions(self.target, overwrite=overwrite,
                reason=f"SC confirmed change by {interaction.user} ({interaction.user.id})")
            val = "INHERIT" if self.value is None else ("ALLOW" if self.value else "DENY")
            await interaction.response.edit_message(embed=base_embed("Channel Permission Updated",
                f"{self.channel.mention}\n{self.target.mention}\n**{pretty_permission(self.permission_name)}** → **{val}**"), view=None)
        except discord.HTTPException as exc:
            await interaction.response.send_message(f"Edit failed: `{exc}`", ephemeral=True)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction, button):
        await interaction.response.edit_message(embed=base_embed("Change Cancelled", "No permission was changed."), view=None)

class FindView(SCView):
    def __init__(self, cog, ctx, owner_id):
        super().__init__(cog, owner_id, ctx.guild.id)
        self.ctx = ctx
        self.kind = "text"
        self.index = 0
        self.targets = []
        self._reload()
        options = [
            discord.SelectOption(label="Text Channels", value="text", emoji="💬", default=True),
            discord.SelectOption(label="Voice Channels", value="voice", emoji="🔊"),
            discord.SelectOption(label="Roles", value="roles", emoji="🛡️"),
            discord.SelectOption(label="Members", value="members", emoji="👤")
        ]
        self.add_item(FindTypeSelect(self, options))

    def _reload(self):
        g = self.ctx.guild
        if self.kind == "text":
            self.targets = [c for c in g.channels if isinstance(c, (discord.TextChannel, discord.ForumChannel))]
        elif self.kind == "voice":
            self.targets = [c for c in g.channels if isinstance(c, (discord.VoiceChannel, discord.StageChannel))]
        elif self.kind == "roles":
            self.targets = sorted([r for r in g.roles if not r.is_default()], key=lambda r: r.position, reverse=True)
        else:
            # Requires the Members intent/cache to be enabled for a complete member list.
            self.targets = sorted(list(g.members), key=lambda m: m.display_name.casefold())
        self.index = min(self.index, max(0, len(self.targets)-1))

    def embed(self):
        self._reload()
        if not self.targets:
            return base_embed("Find a Target", "No items found.")
        target = self.targets[self.index]
        if isinstance(target, discord.Member):
            item = target.mention
            name = f"{target.display_name} (@{target.name})"
            extra = f"\n**Roles:** {', '.join(r.name for r in reversed(target.roles) if not r.is_default()) or 'None'}"
        else:
            item = target.mention
            name = target.name
            extra = f"\n**Position:** {target.position}" if isinstance(target, discord.Role) else f"\n**Channel type:** {target.type}"
        e = base_embed("Find a Target", f"**Type:** {self.kind.title()}\n**Item:** {item}\n**Name:** {name}\n**ID:** `{target.id}`\n**Result:** {self.index+1}/{len(self.targets)}{extra}")
        return e

    @discord.ui.button(label="◀ Previous", style=discord.ButtonStyle.secondary, row=1)
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.index = max(0, self.index - 1)
        await interaction.response.edit_message(embed=self.embed(), view=self)

    @discord.ui.button(label="Next ▶", style=discord.ButtonStyle.secondary, row=1)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.index = min(max(0, len(self.targets)-1), self.index + 1)
        await interaction.response.edit_message(embed=self.embed(), view=self)

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.danger, row=1)
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.targets:
            return await interaction.response.send_message("No target available.", ephemeral=True)
        target = self.targets[self.index]
        await interaction.response.defer()
        if isinstance(target, discord.Role):
            await interaction.followup.send(embed=base_embed(f"Role • {target.name}", f"ID: `{target.id}`\nPosition: `{target.position}`\nPermissions: {', '.join(pretty_permission(n) for n,v in target.permissions if v) or 'None'}"), view=RoleEditView(self.cog, target, interaction.user.id) if await self.cog.interaction_can_edit(interaction) else None)
        elif isinstance(target, discord.Member):
            enabled = [pretty_permission(n) for n, value in target.guild_permissions if value]
            e = base_embed(f"Member • {target.display_name}", f"{target.mention}\n**Username:** {target}\n**ID:** `{target.id}`\n**Joined:** {discord.utils.format_dt(target.joined_at, 'R') if target.joined_at else 'Unknown'}")
            e.add_field(name="Roles", value=', '.join(r.mention for r in reversed(target.roles) if not r.is_default()) or 'None', inline=False)
            e.add_field(name="Effective server permissions", value=', '.join(enabled[:40]) or 'None', inline=False)
            await interaction.followup.send(embed=e)
        else:
            rows = []
            for t, o in target.overwrites.items():
                allow, deny = o.pair()
                rows.append(f"**{t.mention}** — Allow: {', '.join(pretty_permission(n) for n,v in allow if v) or 'None'}; Deny: {', '.join(pretty_permission(n) for n,v in deny if v) or 'None'}")
            await interaction.followup.send(embed=base_embed(f"Channel • {target.name}", "\n".join(rows[:10]) or "No explicit permission overrides."), view=ChannelEditView(self.cog, target, interaction.user.id) if await self.cog.interaction_can_edit(interaction) else None)

class FindTypeSelect(discord.ui.Select):
    def __init__(self, parent_view, options):
        self.parent_view = parent_view
        super().__init__(placeholder="Choose what to browse", min_values=1, max_values=1, options=options, row=0)

    async def callback(self, interaction: discord.Interaction):
        self.parent_view.kind = self.values[0]
        self.parent_view.index = 0
        self.parent_view._reload()
        await interaction.response.edit_message(embed=self.parent_view.embed(), view=self.parent_view)

async def setup(bot):
    await bot.add_cog(SCManager(bot))
