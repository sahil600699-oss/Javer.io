import asyncio
import sqlite3
import discord
from discord.ext import commands

from .views import BaseRoleSelectView, MultiRoleSelectView, PlanAddRoleView
from .db import init_db, is_owner_or_bot_owner, get_assignable_roles


class _FasterRoleModal(discord.ui.Modal, title="Create Role"):
    role_name = discord.ui.TextInput(
        label="Role Name",
        placeholder="Enter role name...",
        required=True,
        min_length=1,
        max_length=100,
    )

    def __init__(self, view):
        super().__init__()
        self.view_ref = view

    async def on_submit(self, interaction: discord.Interaction):
        name = str(self.role_name.value).strip()
        if not name:
            return await interaction.response.send_message(
                "❌ Role name cannot be empty.", ephemeral=True
            )

        self.view_ref.role_name = name
        await interaction.response.edit_message(
            embed=self.view_ref.build_embed(), view=self.view_ref
        )


class _FasterRoleView(discord.ui.View):
    def __init__(self, ctx):
        super().__init__(timeout=600)
        self.ctx = ctx
        self.role_name = ""

    def build_embed(self):
        current = self.role_name if self.role_name else "*No role name entered yet.*"
        embed = discord.Embed(
            title="⚡ Faster Role Creator",
            description=(
                "Create multiple roles quickly from one panel.\n\n"
                f"**Role Name**\n`{current}`\n\n"
                "Click **Enter Name** to enter a role name, then **Confirm** to create it.\n"
                "After creation, the name is cleared automatically so you can create another role."
            ),
            color=0x2B2D31,
        )
        embed.set_footer(text=f"Opened by {self.ctx.author}")
        return embed

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message(
                "❌ This role creator belongs to someone else.", ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="Enter Name", style=discord.ButtonStyle.secondary, emoji="✏️")
    async def enter_name(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(_FasterRoleModal(self))

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.success, emoji="✓")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.role_name:
            return await interaction.response.send_message(
                "❌ Enter a role name first.", ephemeral=True
            )

        guild = interaction.guild
        me = guild.me if guild else None
        if guild is None or me is None:
            return await interaction.response.send_message(
                "❌ This can only be used inside a server.", ephemeral=True
            )
        if not me.guild_permissions.manage_roles:
            return await interaction.response.send_message(
                "❌ I need the **Manage Roles** permission.", ephemeral=True
            )

        name = self.role_name
        try:
            role = await guild.create_role(
                name=name,
                reason=f"Fast role created by {interaction.user} ({interaction.user.id})",
            )
        except discord.Forbidden:
            return await interaction.response.send_message(
                "❌ I don't have permission to create roles.", ephemeral=True
            )
        except discord.HTTPException:
            return await interaction.response.send_message(
                "❌ Discord rejected the role creation request.", ephemeral=True
            )

        self.role_name = ""
        await interaction.response.edit_message(
            embed=self.build_embed(), view=self
        )

        confirmation = await interaction.followup.send(
            f"Role created {role.name}", wait=True
        )
        await asyncio.sleep(3)
        try:
            await confirmation.delete()
        except (discord.NotFound, discord.HTTPException):
            pass

    @discord.ui.button(label="Clear", style=discord.ButtonStyle.danger, emoji="×")
    async def clear(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.role_name = ""
        await interaction.response.edit_message(
            embed=self.build_embed(), view=self
        )

    @discord.ui.button(label="Close", style=discord.ButtonStyle.secondary, emoji="✕", row=1)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(view=self)
        self.stop()


class _RoleIconView(discord.ui.View):
    def __init__(self, ctx, roles):
        super().__init__(timeout=300)
        self.ctx = ctx
        self.roles = roles
        self.page = 0
        self.per_page = 20

    def build_embed(self):
        start = self.page * self.per_page
        current = self.roles[start:start + self.per_page]
        pages = max(1, (len(self.roles) + self.per_page - 1) // self.per_page)

        lines = []
        for role in current:
            icon = getattr(role, "icon", None)
            unicode_emoji = getattr(role, "unicode_emoji", None)
            if icon:
                icon_text = f"[🖼️]({icon.url})"
            elif unicode_emoji:
                icon_text = unicode_emoji
            else:
                icon_text = "—"
            lines.append(f"{icon_text}  **{role.name}**")

        embed = discord.Embed(
            title="◈ Server Role Icons",
            description="Roles and their configured role icons.",
            color=0x2B2D31,
        )
        embed.add_field(
            name=f"Roles • {start + 1}-{start + len(current)}" if current else "Roles",
            value="\n".join(lines) if lines else "No manageable roles found.",
            inline=False,
        )
        embed.set_footer(text=f"Page {self.page + 1}/{pages} • Total: {len(self.roles)}")
        self.previous.disabled = self.page <= 0
        self.next.disabled = self.page >= pages - 1
        return embed

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message(
                "❌ This role icon menu belongs to someone else.", ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.secondary, emoji="‹")
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page > 0:
            self.page -= 1
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.secondary, emoji="›")
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        pages = max(1, (len(self.roles) + self.per_page - 1) // self.per_page)
        if self.page < pages - 1:
            self.page += 1
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    @discord.ui.button(label="Close", style=discord.ButtonStyle.danger, emoji="✕")
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.stop()
        await interaction.response.edit_message(view=None)

class RoleManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        init_db()

    @commands.group(name="role", invoke_without_command=True)
    @commands.has_permissions(manage_roles=True)
    async def role_group(self, ctx):
        await ctx.invoke(self.role_help)

    @role_group.command(name="help")
    @commands.has_permissions(manage_roles=True)
    async def role_help(self, ctx):
        embed = discord.Embed(
            title="⚙️ Role Management System",
            description="Interactive menu-driven role operations for your server.",
            color=0x2B2D31
        )
        embed.add_field(
            name="👤 Member Actions",
            value=(
                "• `!role menu @user` - Open role selector UI\n"
                "• `!role add @user` - Add a role via dropdown\n"
                "• `!role remove @user` - Remove a role via dropdown\n"
                "• `!role perms` - Inspect role permissions\n"
                "• `!role members` - List members with specific role\n"
                "• `!role delete` - Delete a role from server\n"
                "• `!role create <name>` - Create a new server role\n"
                "• `!role faster` - Open the fast role creator\n"
                "• `!role icon` - Show roles and their icons"
            ),
            inline=False
        )
        embed.add_field(
            name="📦 Role Plan System (Owner Only)",
            value=(
                "• `!role plan create <name>` - Create a role plan\n"
                "• `!role plan add <name>` - Add roles to plan with multi-page UI\n"
                "• `!role plan details <name>` - Show roles & current holders of plan\n"
                "• `!role plan list` - List all saved plans\n"
                "• `!role plan delete <name>` - Delete a plan\n"
                "• `!role paste @user <plan_name>` - Apply plan roles to user"
            ),
            inline=False
        )
        embed.add_field(
            name="⚡ Mass Actions & Auto-Roles",
            value=(
                "• `!role all / humans / bots` - Assign role to targeted group\n"
                "• `!role removeall` - Strip role from everyone\n"
                "• `!role autorole human / bot` - Configure auto-roles"
            ),
            inline=False
        )
        await ctx.send(embed=embed)

    @role_group.command(name="menu")
    @commands.has_permissions(manage_roles=True)
    async def role_menu(self, ctx, member: discord.Member):
        roles = get_assignable_roles(ctx.guild)
        if not roles:
            return await ctx.send("❌ No assignable roles found!")

        view = MultiRoleSelectView(target_user=member, all_roles=roles, ctx=ctx)
        await ctx.send(embed=view.build_embed(), view=view)

    @role_group.command(name="add")
    @commands.has_permissions(manage_roles=True)
    async def role_add(self, ctx, member: discord.Member):
        roles = get_assignable_roles(ctx.guild)
        if not roles:
            return await ctx.send("❌ No assignable roles found!")

        async def callback(interaction: discord.Interaction, role: discord.Role):
            await interaction.response.defer(ephemeral=True)
            await member.add_roles(role)
            await interaction.followup.send(f"✅ Added {role.mention} to {member.mention}", ephemeral=True)

        view = BaseRoleSelectView(roles, callback, ctx=ctx)
        await ctx.send(f"Select role to add for **{member.display_name}**:", view=view)

    @role_group.command(name="remove")
    @commands.has_permissions(manage_roles=True)
    async def role_remove(self, ctx, member: discord.Member):
        user_roles = [r for r in member.roles if not r.is_default() and not r.managed]
        if not user_roles:
            return await ctx.send("❌ User has no custom roles to remove.")

        async def callback(interaction: discord.Interaction, role: discord.Role):
            await interaction.response.defer(ephemeral=True)
            await member.remove_roles(role)
            await interaction.followup.send(f"🔻 Removed {role.mention} from {member.mention}", ephemeral=True)

        view = BaseRoleSelectView(user_roles, callback, ctx=ctx)
        await ctx.send(f"Select role to remove from **{member.display_name}**:", view=view)

    @role_group.command(name="perms")
    @commands.has_permissions(manage_roles=True)
    async def role_perms(self, ctx):
        roles = get_assignable_roles(ctx.guild)
        if not roles:
            return await ctx.send("❌ No roles available!")

        async def callback(interaction: discord.Interaction, role: discord.Role):
            await interaction.response.defer()
            perms = [f"`{perm.replace('_', ' ').title()}`" for perm, val in role.permissions if val]
            perms_text = ", ".join(perms) if perms else "No special permissions."
            embed = discord.Embed(title=f"🔒 Permissions: {role.name}", description=perms_text, color=0x2B2D31)
            embed.add_field(name="Total Active Permissions", value=f"**{len(perms)}**")
            await ctx.send(embed=embed)

        view = BaseRoleSelectView(roles, callback, ctx=ctx)
        await ctx.send("Select role to inspect permissions:", view=view)

    @role_group.command(name="members")
    @commands.has_permissions(manage_roles=True)
    async def role_members(self, ctx):
        roles = get_assignable_roles(ctx.guild)
        if not roles:
            return await ctx.send("❌ No roles available!")

        async def callback(interaction: discord.Interaction, role: discord.Role):
            await interaction.response.defer()
            members = role.members
            if not members:
                return await ctx.send(f"❌ No members currently hold {role.mention}.")

            member_list = "\n".join([f"• {m.mention} (`{m.id}`)" for m in members[:20]])
            embed = discord.Embed(
                title=f"👥 Members with {role.name}",
                description=member_list,
                color=0x2B2D31
            )
            embed.set_footer(text=f"Total: {len(members)} members")
            await ctx.send(embed=embed)

        view = BaseRoleSelectView(roles, callback, ctx=ctx)
        await ctx.send("Select role to view members:", view=view)

    @role_group.command(name="delete")
    @commands.has_permissions(manage_roles=True)
    async def role_delete(self, ctx):
        roles = get_assignable_roles(ctx.guild)
        if not roles:
            return await ctx.send("❌ No roles available!")

        async def callback(interaction: discord.Interaction, role: discord.Role):
            await interaction.response.defer()
            name = role.name
            await role.delete(reason=f"Deleted by {ctx.author}")
            await ctx.send(f"❌ Role **{name}** deleted successfully.")

        view = BaseRoleSelectView(roles, callback, ctx=ctx)
        await ctx.send("Select role to DELETE:", view=view)

    @role_group.command(name="create")
    @commands.has_permissions(manage_roles=True)
    async def role_create(self, ctx, *, role_name: str):
        role_name = role_name.strip()
        if not role_name:
            return await ctx.send("❌ Please provide a role name.")
        if len(role_name) > 100:
            return await ctx.send("❌ Role name cannot be longer than 100 characters.")

        me = ctx.guild.me
        if me is None or not me.guild_permissions.manage_roles:
            return await ctx.send("❌ I need the **Manage Roles** permission.")

        try:
            role = await ctx.guild.create_role(
                name=role_name,
                reason=f"Role created by {ctx.author} ({ctx.author.id})",
            )
        except discord.Forbidden:
            return await ctx.send("❌ I don't have permission to create roles.")
        except discord.HTTPException:
            return await ctx.send("❌ Discord rejected the role creation request.")

        await ctx.send(f"✅ Role created {role.mention}")

    @role_group.command(name="faster")
    @commands.has_permissions(manage_roles=True)
    async def role_faster(self, ctx):
        view = _FasterRoleView(ctx)
        await ctx.send(embed=view.build_embed(), view=view)

    @role_group.command(name="icon")
    @commands.has_permissions(manage_roles=True)
    async def role_icon(self, ctx):
        me = ctx.guild.me
        if me is None:
            return await ctx.send("❌ I couldn't verify my bot role hierarchy.")

        roles = [
            role for role in ctx.guild.roles
            if not role.is_default()
            and not role.managed
            and role < me.top_role
        ]
        roles.reverse()

        if not roles:
            return await ctx.send("❌ No manageable roles found.")

        view = _RoleIconView(ctx, roles)
        await ctx.send(embed=view.build_embed(), view=view)

    @role_group.group(name="plan", invoke_without_command=True)
    async def plan_group(self, ctx):
        await ctx.send("Usage: `!role plan create <name>`, `!role plan add <name>`, `!role plan details <name>`, `!role plan list`, `!role plan delete <name>`")

    @plan_group.command(name="create")
    async def plan_create(self, ctx, name: str):
        if not is_owner_or_bot_owner(ctx):
            return await ctx.send("❌ Server owner permission required!")
        await ctx.send(f"✅ Role Plan **{name.lower()}** created! Use `!role plan add {name.lower()}` to select roles.")

    @plan_group.command(name="add")
    async def plan_add(self, ctx, name: str):
        if not is_owner_or_bot_owner(ctx):
            return await ctx.send("❌ Server owner permission required!")

        roles = get_assignable_roles(ctx.guild)
        if not roles:
            return await ctx.send("❌ No assignable roles found!")

        view = PlanAddRoleView(plan_name=name, all_roles=roles, ctx=ctx)
        await ctx.send(embed=view.build_embed(), view=view)

    @plan_group.command(name="details")
    async def plan_details(self, ctx, name: str):
        with sqlite3.connect("role_management.db") as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT role_id FROM role_presets WHERE guild_id = ? AND preset_name = ?", (ctx.guild.id, name.lower()))
            rows = cursor.fetchall()

        if not rows:
            return await ctx.send(f"❌ Plan `{name.lower()}` not found!")

        plan_roles = [role for (r_id,) in rows if (role := ctx.guild.get_role(r_id))]
        if not plan_roles:
            return await ctx.send(f"❌ No active roles found in plan `{name.lower()}`.")

        plan_role_set = set(plan_roles)
        members_with_plan = [
            member for member in ctx.guild.members 
            if plan_role_set.issubset(set(member.roles))
        ]

        roles_text = "\n".join([f"• {r.mention}" for r in plan_roles])
        
        if members_with_plan:
            members_text = "\n".join([f"• {m.mention} (`{m.id}`)" for m in members_with_plan[:20]])
            if len(members_with_plan) > 20:
                members_text += f"\n*...and {len(members_with_plan) - 20} more*"
        else:
            members_text = "*No member currently holds all roles of this plan.*"

        embed = discord.Embed(
            title=f"📋 Plan Details: {name.lower()}",
            color=0x2B2D31
        )
        embed.add_field(name="⚙️ Roles Included", value=roles_text, inline=False)
        embed.add_field(name=f"👥 Members With Plan ({len(members_with_plan)})", value=members_text, inline=False)
        
        await ctx.send(embed=embed)

    @plan_group.command(name="list")
    async def plan_list(self, ctx):
        with sqlite3.connect("role_management.db") as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT preset_name, role_id FROM role_presets WHERE guild_id = ?", (ctx.guild.id,))
            rows = cursor.fetchall()

        if not rows:
            return await ctx.send("❌ No role plans saved.")

        plans = {}
        for p_name, r_id in rows:
            role = ctx.guild.get_role(r_id)
            mention = role.mention if role else "`Deleted Role`"
            plans.setdefault(p_name, []).append(mention)

        embed = discord.Embed(title="📦 Saved Role Plans", color=0x2B2D31)
        for p_name, roles in plans.items():
            embed.add_field(name=f"🔹 Plan: {p_name}", value=", ".join(roles), inline=False)
        await ctx.send(embed=embed)

    @plan_group.command(name="delete")
    async def plan_delete(self, ctx, name: str):
        if not is_owner_or_bot_owner(ctx):
            return await ctx.send("❌ Server owner permission required!")

        with sqlite3.connect("role_management.db") as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM role_presets WHERE guild_id = ? AND preset_name = ?", (ctx.guild.id, name.lower()))
            conn.commit()
        await ctx.send(f"🗑️ Plan **{name.lower()}** deleted.")

    @role_group.command(name="paste")
    async def role_paste(self, ctx, member: discord.Member, name: str):
        if not is_owner_or_bot_owner(ctx):
            return await ctx.send("❌ Server owner permission required!")

        with sqlite3.connect("role_management.db") as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT role_id FROM role_presets WHERE guild_id = ? AND preset_name = ?", (ctx.guild.id, name.lower()))
            rows = cursor.fetchall()

        if not rows:
            return await ctx.send(f"❌ Plan `{name.lower()}` not found!")

        roles_to_add = [role for (r_id,) in rows if (role := ctx.guild.get_role(r_id))]
        if not roles_to_add:
            return await ctx.send("❌ No valid roles found in plan.")

        msg = await ctx.send(f"⏳ Applying plan **{name.lower()}**...")
        await member.add_roles(*roles_to_add)

        role_mentions = ", ".join([r.mention for r in roles_to_add])
        embed = discord.Embed(
            title="⚙️ Plan Applied",
            description=f"Applied plan **{name.lower()}** to {member.mention}:\n\n{role_mentions}",
            color=0x2B2D31
        )
        await msg.edit(content=None, embed=embed)

    @role_group.command(name="all")
    @commands.has_permissions(administrator=True)
    async def role_all(self, ctx):
        roles = get_assignable_roles(ctx.guild)
        if not roles:
            return await ctx.send("❌ No roles available!")

        async def callback(interaction: discord.Interaction, role: discord.Role):
            await interaction.response.defer()
            msg = await ctx.send(f"⏳ Adding {role.mention} to all members...")
            for m in ctx.guild.members:
                if role not in m.roles:
                    try:
                        await m.add_roles(role)
                    except Exception:
                        pass
            await msg.edit(content=f"✅ Added {role.mention} to all members!")

        view = BaseRoleSelectView(roles, callback, ctx=ctx)
        await ctx.send("Select role to assign to ALL members:", view=view)

    @role_group.command(name="humans")
    @commands.has_permissions(administrator=True)
    async def role_humans(self, ctx):
        roles = get_assignable_roles(ctx.guild)
        if not roles:
            return await ctx.send("❌ No roles available!")

        async def callback(interaction: discord.Interaction, role: discord.Role):
            await interaction.response.defer()
            msg = await ctx.send(f"⏳ Adding {role.mention} to human members...")
            for m in ctx.guild.members:
                if not m.bot and role not in m.roles:
                    try:
                        await m.add_roles(role)
                    except Exception:
                        pass
            await msg.edit(content=f"✅ Added {role.mention} to all human members!")

        view = BaseRoleSelectView(roles, callback, ctx=ctx)
        await ctx.send("Select role to assign to HUMANS:", view=view)

    @role_group.command(name="bots")
    @commands.has_permissions(administrator=True)
    async def role_bots(self, ctx):
        roles = get_assignable_roles(ctx.guild)
        if not roles:
            return await ctx.send("❌ No roles available!")

        async def callback(interaction: discord.Interaction, role: discord.Role):
            await interaction.response.defer()
            msg = await ctx.send(f"⏳ Adding {role.mention} to bots...")
            for m in ctx.guild.members:
                if m.bot and role not in m.roles:
                    try:
                        await m.add_roles(role)
                    except Exception:
                        pass
            await msg.edit(content=f"🤖 Added {role.mention} to all bot accounts!")

        view = BaseRoleSelectView(roles, callback, ctx=ctx)
        await ctx.send("Select role to assign to BOTS:", view=view)

    @role_group.command(name="removeall")
    @commands.has_permissions(administrator=True)
    async def role_removeall(self, ctx):
        roles = get_assignable_roles(ctx.guild)
        if not roles:
            return await ctx.send("❌ No roles available!")

        async def callback(interaction: discord.Interaction, role: discord.Role):
            await interaction.response.defer()
            msg = await ctx.send(f"⏳ Removing {role.mention} from all members...")
            for m in ctx.guild.members:
                if role in m.roles:
                    try:
                        await m.remove_roles(role)
                    except Exception:
                        pass
            await msg.edit(content=f"🔻 Stripped {role.mention} from all members!")

        view = BaseRoleSelectView(roles, callback, ctx=ctx)
        await ctx.send("Select role to REMOVE from everyone:", view=view)

    @role_group.group(name="autorole", invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def autorole_group(self, ctx):
        await ctx.send("Usage: `!role autorole human` or `!role autorole bot`")

    @autorole_group.command(name="human")
    @commands.has_permissions(administrator=True)
    async def autorole_human(self, ctx):
        roles = get_assignable_roles(ctx.guild)
        if not roles:
            return await ctx.send("❌ No roles available!")

        async def callback(interaction: discord.Interaction, role: discord.Role):
            await interaction.response.defer(ephemeral=True)
            with sqlite3.connect("role_management.db") as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO autoroles (guild_id, human_role_id) VALUES (?, ?) ON CONFLICT(guild_id) DO UPDATE SET human_role_id = excluded.human_role_id",
                    (ctx.guild.id, role.id)
                )
                conn.commit()
            await interaction.followup.send(f"✅ Human auto-role configured: {role.mention}", ephemeral=True)

        view = BaseRoleSelectView(roles, callback, ctx=ctx)
        await ctx.send("Select Human Auto-Role:", view=view)

    @autorole_group.command(name="bot")
    @commands.has_permissions(administrator=True)
    async def autorole_bot(self, ctx):
        roles = get_assignable_roles(ctx.guild)
        if not roles:
            return await ctx.send("❌ No roles available!")

        async def callback(interaction: discord.Interaction, role: discord.Role):
            await interaction.response.defer(ephemeral=True)
            with sqlite3.connect("role_management.db") as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO autoroles (guild_id, bot_role_id) VALUES (?, ?) ON CONFLICT(guild_id) DO UPDATE SET bot_role_id = excluded.bot_role_id",
                    (ctx.guild.id, role.id)
                )
                conn.commit()
            await interaction.followup.send(f"🤖 Bot auto-role configured: {role.mention}", ephemeral=True)

        view = BaseRoleSelectView(roles, callback, ctx=ctx)
        await ctx.send("Select Bot Auto-Role:", view=view)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        with sqlite3.connect("role_management.db") as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT human_role_id, bot_role_id FROM autoroles WHERE guild_id = ?", (member.guild.id,))
            data = cursor.fetchone()

        if data:
            human_id, bot_id = data
            if member.bot and bot_id:
                if r := member.guild.get_role(bot_id):
                    await member.add_roles(r)
            elif not member.bot and human_id:
                if r := member.guild.get_role(human_id):
                    await member.add_roles(r)


async def setup(bot):
    await bot.add_cog(RoleManager(bot))
        
