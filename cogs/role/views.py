import sqlite3
import discord

class MultiRoleSelectView(discord.ui.View):
    def __init__(self, target_user: discord.Member, all_roles: list, ctx):
        super().__init__(timeout=180)
        self.target_user = target_user
        self.all_roles = all_roles
        self.ctx = ctx
        self.selected_roles = set()
        self.current_page = 0
        self.page_size = 25

        self.update_components()

    def get_total_pages(self):
        return max(1, (len(self.all_roles) + self.page_size - 1) // self.page_size)

    def update_components(self):
        self.clear_items()

        start = self.current_page * self.page_size
        end = start + self.page_size
        page_roles = self.all_roles[start:end]

        options = []
        for role in page_roles:
            is_selected = role in self.selected_roles
            options.append(
                discord.SelectOption(
                    label=role.name[:100],
                    value=str(role.id),
                    description=f"ID: {role.id}",
                    emoji="✅" if is_selected else "🔘"
                )
            )

        select = discord.ui.Select(
            placeholder=f"Select roles (Page {self.current_page + 1}/{self.get_total_pages()})...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="role_select_menu"
        )
        select.callback = self.select_callback
        self.add_item(select)

        if len(self.all_roles) > self.page_size:
            prev_btn = discord.ui.Button(
                label="⬅️ Previous",
                style=discord.ButtonStyle.secondary,
                disabled=(self.current_page == 0)
            )
            prev_btn.callback = self.prev_page_callback
            self.add_item(prev_btn)

            next_btn = discord.ui.Button(
                label="Next ➡️",
                style=discord.ButtonStyle.secondary,
                disabled=(self.current_page >= self.get_total_pages() - 1)
            )
            next_btn.callback = self.next_page_callback
            self.add_item(next_btn)

        confirm_btn = discord.ui.Button(
            label="Confirm & Apply Roles",
            style=discord.ButtonStyle.green,
            emoji="⚙️",
            custom_id="confirm_roles"
        )
        confirm_btn.callback = self.confirm_callback
        self.add_item(confirm_btn)

    def build_embed(self):
        embed = discord.Embed(
            title="⚙️ Role Assignment Manager",
            description=f"Select roles for {self.target_user.mention} using the dropdown menu below.\nClick an already selected role to unselect it.",
            color=0x2B2D31
        )
        
        if self.selected_roles:
            roles_text = "\n".join([f"• {r.mention}" for r in self.selected_roles])
        else:
            roles_text = "*No roles selected yet.*"

        embed.add_field(
            name=f"📋 Selected Roles ({len(self.selected_roles)})",
            value=roles_text,
            inline=False
        )
        embed.set_footer(text=f"Total Available Roles: {len(self.all_roles)}")
        return embed

    async def select_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.ctx.author.id:
            return await interaction.response.send_message("❌ You cannot use this menu!", ephemeral=True)

        role_id = int(interaction.data["values"][0])
        role = interaction.guild.get_role(role_id)

        if not role:
            return await interaction.response.send_message("❌ Role not found!", ephemeral=True)

        if role >= interaction.user.top_role and interaction.user.id != interaction.guild.owner_id:
            return await interaction.response.send_message("❌ You cannot manage roles higher or equal to yours!", ephemeral=True)

        if role in self.selected_roles:
            self.selected_roles.remove(role)
        else:
            self.selected_roles.add(role)

        self.update_components()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    async def prev_page_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.ctx.author.id:
            return await interaction.response.send_message("❌ You cannot use this menu!", ephemeral=True)
        self.current_page -= 1
        self.update_components()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    async def next_page_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.ctx.author.id:
            return await interaction.response.send_message("❌ You cannot use this menu!", ephemeral=True)
        self.current_page += 1
        self.update_components()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    async def confirm_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.ctx.author.id:
            return await interaction.response.send_message("❌ You cannot use this menu!", ephemeral=True)

        if not self.selected_roles:
            return await interaction.response.send_message("❌ No roles selected to assign!", ephemeral=True)

        await interaction.response.defer()
        roles_to_add = list(self.selected_roles)
        try:
            await self.target_user.add_roles(*roles_to_add, reason=f"Managed by {interaction.user}")
            
            applied_text = "\n".join([f"• {r.mention}" for r in roles_to_add])
            success_embed = discord.Embed(
                title="✅ Roles Successfully Assigned",
                description=f"Applied the following roles to {self.target_user.mention}:\n\n{applied_text}",
                color=0x2B2D31
            )
            
            for child in self.children:
                child.disabled = True
                
            await interaction.message.edit(embed=success_embed, view=self)

        except discord.Forbidden:
            await interaction.followup.send("❌ Missing permissions to assign these roles! Check hierarchy.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Execution Error: {str(e)}", ephemeral=True)


class PlanAddRoleView(discord.ui.View):
    def __init__(self, plan_name: str, all_roles: list, ctx):
        super().__init__(timeout=180)
        self.plan_name = plan_name
        self.all_roles = all_roles
        self.ctx = ctx
        self.selected_roles = set()
        self.current_page = 0
        self.page_size = 25

        self.update_components()

    def get_total_pages(self):
        return max(1, (len(self.all_roles) + self.page_size - 1) // self.page_size)

    def update_components(self):
        self.clear_items()

        start = self.current_page * self.page_size
        end = start + self.page_size
        page_roles = self.all_roles[start:end]

        options = []
        for role in page_roles:
            is_selected = role in self.selected_roles
            options.append(
                discord.SelectOption(
                    label=role.name[:100],
                    value=str(role.id),
                    description=f"ID: {role.id}",
                    emoji="✅" if is_selected else "🔘"
                )
            )

        select = discord.ui.Select(
            placeholder=f"Select roles for plan '{self.plan_name}' (Page {self.current_page + 1}/{self.get_total_pages()})...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="plan_role_select"
        )
        select.callback = self.select_callback
        self.add_item(select)

        if len(self.all_roles) > self.page_size:
            prev_btn = discord.ui.Button(
                label="⬅️ Previous",
                style=discord.ButtonStyle.secondary,
                disabled=(self.current_page == 0)
            )
            prev_btn.callback = self.prev_page_callback
            self.add_item(prev_btn)

            next_btn = discord.ui.Button(
                label="Next ➡️",
                style=discord.ButtonStyle.secondary,
                disabled=(self.current_page >= self.get_total_pages() - 1)
            )
            next_btn.callback = self.next_page_callback
            self.add_item(next_btn)

        confirm_btn = discord.ui.Button(
            label="Confirm & Save to Plan",
            style=discord.ButtonStyle.green,
            emoji="💾",
            custom_id="confirm_plan_roles"
        )
        confirm_btn.callback = self.confirm_callback
        self.add_item(confirm_btn)

    def build_embed(self):
        embed = discord.Embed(
            title=f"📦 Add Roles to Plan: `{self.plan_name}`",
            description="Select roles from the dropdown menu below.\n*Clicking an already selected role will remove it.*",
            color=0x2B2D31
        )

        if self.selected_roles:
            roles_text = "\n".join([f"• {r.mention}" for r in self.selected_roles])
        else:
            roles_text = "*No roles selected yet.*"

        embed.add_field(
            name=f"📋 Selected Roles ({len(self.selected_roles)})",
            value=roles_text,
            inline=False
        )
        embed.set_footer(text=f"Total Available Roles: {len(self.all_roles)}")
        return embed

    async def select_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.ctx.author.id:
            return await interaction.response.send_message("❌ You cannot use this menu!", ephemeral=True)

        role_id = int(interaction.data["values"][0])
        role = interaction.guild.get_role(role_id)

        if not role:
            return await interaction.response.send_message("❌ Role not found!", ephemeral=True)

        if role in self.selected_roles:
            self.selected_roles.remove(role)
        else:
            self.selected_roles.add(role)

        self.update_components()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    async def prev_page_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.ctx.author.id:
            return await interaction.response.send_message("❌ You cannot use this menu!", ephemeral=True)
        self.current_page -= 1
        self.update_components()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    async def next_page_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.ctx.author.id:
            return await interaction.response.send_message("❌ You cannot use this menu!", ephemeral=True)
        self.current_page += 1
        self.update_components()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    async def confirm_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.ctx.author.id:
            return await interaction.response.send_message("❌ You cannot use this menu!", ephemeral=True)

        if not self.selected_roles:
            return await interaction.response.send_message("❌ Please select at least one role to add!", ephemeral=True)

        await interaction.response.defer()

        with sqlite3.connect("role_management.db") as conn:
            cursor = conn.cursor()
            added_count = 0
            for role in self.selected_roles:
                try:
                    cursor.execute(
                        "INSERT INTO role_presets (guild_id, preset_name, role_id) VALUES (?, ?, ?)",
                        (interaction.guild.id, self.plan_name.lower(), role.id)
                    )
                    added_count += 1
                except sqlite3.IntegrityError:
                    pass
            conn.commit()

        for item in self.children:
            item.disabled = True

        saved_text = "\n".join([f"• {r.mention}" for r in self.selected_roles])
        final_embed = discord.Embed(
            title=f"✅ Plan `{self.plan_name}` Updated",
            description=f"Successfully saved **{added_count}** role(s) to plan **{self.plan_name}**:\n\n{saved_text}",
            color=0x2B2D31
        )
        await interaction.message.edit(embed=final_embed, view=self)


class BaseRoleSelectView(discord.ui.View):
    def __init__(self, roles: list, callback_func, ctx):
        super().__init__(timeout=120)
        self.callback_func = callback_func
        self.ctx = ctx

        options = [
            discord.SelectOption(
                label=r.name[:100],
                value=str(r.id),
                description=f"ID: {r.id} | Members: {len(r.members)}",
                emoji="⚙️"
            ) for r in roles[:25]
        ]

        select = discord.ui.Select(
            placeholder="Choose a role from list...",
            min_values=1,
            max_values=1,
            options=options
        )
        select.callback = self.select_callback
        self.add_item(select)

    async def select_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.ctx.author.id:
            return await interaction.response.send_message("❌ You cannot use this menu!", ephemeral=True)

        role_id = int(interaction.data["values"][0])
        role = interaction.guild.get_role(role_id)
        if not role:
            return await interaction.response.send_message("❌ Role not found!", ephemeral=True)
        await self.callback_func(interaction, role)
                
