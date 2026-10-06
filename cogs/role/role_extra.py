import asyncio
import discord
from discord.ext import commands


# ============================================================
# EXTRA ROLE COMMANDS
# Works with the existing RoleManager / !role command group.
#
# This file does NOT create another !role group and does NOT
# replace the existing !role delete system.
# ============================================================


def _manageable_roles(guild: discord.Guild):
    """Return roles the bot can safely manage."""
    me = guild.me
    if me is None:
        return []

    return [
        role
        for role in guild.roles
        if not role.is_default()
        and not role.managed
        and role < me.top_role
    ]


def _role_icon_text(role: discord.Role) -> str:
    """
    Return a Discord-friendly representation of a role icon.

    Discord role icons can be either a custom image or a unicode emoji.
    """
    # Custom image role icon
    icon = getattr(role, "icon", None)
    if icon:
        return f"[🖼️ Icon]({icon.url})"

    # Unicode emoji role icon
    unicode_emoji = getattr(role, "unicode_emoji", None)
    if unicode_emoji:
        return unicode_emoji

    return "—"


# ============================================================
# !role create <role name>
# ============================================================

@commands.guild_only()
@commands.has_permissions(manage_roles=True)
async def role_create(ctx: commands.Context, *, role_name: str):
    role_name = role_name.strip()

    if not role_name:
        return await ctx.send("❌ Please provide a role name.")

    if len(role_name) > 100:
        return await ctx.send("❌ Role name cannot be longer than 100 characters.")

    me = ctx.guild.me
    if me is None:
        return await ctx.send("❌ I couldn't verify my bot role hierarchy.")

    if not me.guild_permissions.manage_roles:
        return await ctx.send("❌ I need the **Manage Roles** permission.")

    try:
        role = await ctx.guild.create_role(
            name=role_name,
            reason=f"Role created by {ctx.author} ({ctx.author.id})",
        )
    except discord.Forbidden:
        return await ctx.send(
            "❌ I don't have permission to create roles. "
            "Make sure **Manage Roles** is enabled and my bot role is high enough."
        )
    except discord.HTTPException:
        return await ctx.send("❌ Discord rejected the role creation request.")

    await ctx.send(f"✅ Role created {role.mention}")


# ============================================================
# Faster Role UI
# ============================================================

class RoleNameModal(discord.ui.Modal, title="Create Role"):
    role_name = discord.ui.TextInput(
        label="Role Name",
        placeholder="Enter the role name...",
        required=True,
        min_length=1,
        max_length=100,
    )

    def __init__(self, parent_view):
        super().__init__()
        self.parent_view = parent_view

    async def on_submit(self, interaction: discord.Interaction):
        self.parent_view.role_name = str(self.role_name.value).strip()

        if not self.parent_view.role_name:
            return await interaction.response.send_message(
                "❌ Role name cannot be empty.",
                ephemeral=True,
            )

        await interaction.response.edit_message(
            embed=self.parent_view.build_embed(),
            view=self.parent_view,
        )


class FasterRoleView(discord.ui.View):
    def __init__(self, ctx: commands.Context):
        super().__init__(timeout=600)
        self.ctx = ctx
        self.role_name = ""

    def build_embed(self):
        current_name = self.role_name if self.role_name else "*No role name entered yet.*"

        embed = discord.Embed(
            title="⚡ Faster Role Creator",
            description=(
                "Create roles quickly without running the command again.\n\n"
                f"**Role Name**\n`{current_name}`\n\n"
                "Use **Enter Name** to set the role name.\n"
                "Use **Confirm** to create the role.\n"
                "Use **Clear** to remove the current name."
            ),
            color=0x2B2D31,
        )
        embed.set_footer(text=f"Opened by {self.ctx.author}")
        return embed

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message(
                "❌ This role creator belongs to someone else.",
                ephemeral=True,
            )
            return False
        return True

    @discord.ui.button(
        label="Enter Name",
        style=discord.ButtonStyle.secondary,
        emoji="✏️",
        row=0,
    )
    async def enter_name(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        await interaction.response.send_modal(RoleNameModal(self))

    @discord.ui.button(
        label="Confirm",
        style=discord.ButtonStyle.success,
        emoji="✓",
        row=0,
    )
    async def confirm(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        if not self.role_name:
            return await interaction.response.send_message(
                "❌ Enter a role name first.",
                ephemeral=True,
            )

        guild = interaction.guild
        if guild is None:
            return await interaction.response.send_message(
                "❌ This can only be used inside a server.",
                ephemeral=True,
            )

        me = guild.me
        if me is None or not me.guild_permissions.manage_roles:
            return await interaction.response.send_message(
                "❌ I need the **Manage Roles** permission.",
                ephemeral=True,
            )

        role_name = self.role_name

        try:
            role = await guild.create_role(
                name=role_name,
                reason=f"Fast role created by {interaction.user} ({interaction.user.id})",
            )
        except discord.Forbidden:
            return await interaction.response.send_message(
                "❌ I don't have permission to create roles.",
                ephemeral=True,
            )
        except discord.HTTPException:
            return await interaction.response.send_message(
                "❌ Discord rejected the role creation request.",
                ephemeral=True,
            )

        # Reset the name immediately so the same panel can create
        # another role without running !role faster again.
        self.role_name = ""

        await interaction.response.edit_message(
            embed=self.build_embed(),
            view=self,
        )

        # Temporary confirmation message: 3 seconds.
        confirmation = await interaction.followup.send(
            f"Role created {role.name}",
            wait=True,
        )

        await asyncio.sleep(3)

        try:
            await confirmation.delete()
        except (discord.NotFound, discord.HTTPException):
            pass

    @discord.ui.button(
        label="Clear",
        style=discord.ButtonStyle.danger,
        emoji="×",
        row=0,
    )
    async def clear(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        self.role_name = ""

        await interaction.response.edit_message(
            embed=self.build_embed(),
            view=self,
        )

    @discord.ui.button(
        label="Close",
        style=discord.ButtonStyle.secondary,
        emoji="✕",
        row=1,
    )
    async def close(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        for child in self.children:
            child.disabled = True

        await interaction.response.edit_message(
            embed=discord.Embed(
                title="⚡ Faster Role Creator",
                description="Role creator closed.",
                color=0x2B2D31,
            ),
            view=self,
        )
        self.stop()


@commands.guild_only()
@commands.has_permissions(manage_roles=True)
async def role_faster(ctx: commands.Context):
    view = FasterRoleView(ctx)

    await ctx.send(
        embed=view.build_embed(),
        view=view,
    )


# ============================================================
# !role icon
# ============================================================

class RoleIconView(discord.ui.View):
    def __init__(self, ctx: commands.Context, roles):
        super().__init__(timeout=300)
        self.ctx = ctx
        self.roles = roles
        self.page = 0
        self.per_page = 20

    def build_embed(self):
        start = self.page * self.per_page
        current = self.roles[start:start + self.per_page]

        total_pages = max(
            1,
            (len(self.roles) + self.per_page - 1) // self.per_page,
        )

        embed = discord.Embed(
            title="◈ Server Role Icons",
            description="All manageable server roles and their current icons.",
            color=0x2B2D31,
        )

        if not current:
            embed.description = "No manageable roles found."
        else:
            lines = []
            for role in current:
                icon = getattr(role, "icon", None)
                unicode_emoji = getattr(role, "unicode_emoji", None)

                if icon:
                    icon_value = f"[🖼️]({icon.url})"
                elif unicode_emoji:
                    icon_value = unicode_emoji
                else:
                    icon_value = "—"

                lines.append(f"{icon_value}  **{role.name}**")

            embed.add_field(
                name=f"Roles • {start + 1}-{start + len(current)}",
                value="\n".join(lines),
                inline=False,
            )

        embed.set_footer(text=f"Page {self.page + 1}/{total_pages} • Total roles: {len(self.roles)}")

        self.previous.disabled = self.page <= 0
        self.next.disabled = self.page >= total_pages - 1

        return embed

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message(
                "❌ This role icon menu belongs to someone else.",
                ephemeral=True,
            )
            return False
        return True

    @discord.ui.button(
        label="Previous",
        style=discord.ButtonStyle.secondary,
        emoji="‹",
        row=0,
    )
    async def previous(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        if self.page > 0:
            self.page -= 1

        await interaction.response.edit_message(
            embed=self.build_embed(),
            view=self,
        )

    @discord.ui.button(
        label="Next",
        style=discord.ButtonStyle.secondary,
        emoji="›",
        row=0,
    )
    async def next(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        total_pages = max(
            1,
            (len(self.roles) + self.per_page - 1) // self.per_page,
        )

        if self.page < total_pages - 1:
            self.page += 1

        await interaction.response.edit_message(
            embed=self.build_embed(),
            view=self,
        )

    @discord.ui.button(
        label="Close",
        style=discord.ButtonStyle.danger,
        emoji="✕",
        row=0,
    )
    async def close(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        self.stop()
        await interaction.response.edit_message(view=None)


@commands.guild_only()
@commands.has_permissions(manage_roles=True)
async def role_icon(ctx: commands.Context):
    roles = _manageable_roles(ctx.guild)

    # Newest/highest roles first, while excluding @everyone,
    # managed integrations/bot roles, and roles above the bot.
    roles = list(reversed(roles))

    if not roles:
        return await ctx.send("❌ No manageable roles found.")

    view = RoleIconView(ctx, roles)
    await ctx.send(
        embed=view.build_embed(),
        view=view,
    )


# ============================================================
# Extension setup
# ============================================================

async def setup(bot):
    """
    Attach these commands to the EXISTING !role command group.

    Existing !role delete and all other role commands remain untouched.
    """
    role_group = bot.get_command("role")

    if role_group is None or not isinstance(role_group, commands.Group):
        raise RuntimeError(
            "Existing !role command group was not found. "
            "Load the existing RoleManager extension before role_extra."
        )

    commands_to_add = [
        commands.Command(
            role_create,
            name="create",
            help="Create a new server role.",
        ),
        commands.Command(
            role_faster,
            name="faster",
            help="Open the fast role creator.",
        ),
        commands.Command(
            role_icon,
            name="icon",
            help="Show server roles and their icons.",
        ),
    ]

    for command in commands_to_add:
        if role_group.get_command(command.name) is not None:
            raise RuntimeError(
                f"!role {command.name} already exists. "
                "Remove the duplicate command before loading role_extra."
            )
        role_group.add_command(command)


async def teardown(bot):
    """Remove only the commands added by this extension."""
    role_group = bot.get_command("role")
    if role_group is None:
        return

    for name in ("create", "faster", "icon"):
        command = role_group.get_command(name)
        if command is not None:
            role_group.remove_command(name)
