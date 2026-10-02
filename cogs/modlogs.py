import discord
from discord.ext import commands
from datetime import datetime

class LogTypeSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Message Logs", value="message_logs", emoji="💬"),
            discord.SelectOption(label="Mod Action Logs", value="mod_action_logs", emoji="🛡️"),
            discord.SelectOption(label="Member Logs", value="member_logs", emoji="👥"),
            discord.SelectOption(label="VC Logs", value="vc_logs", emoji="🔊"),
            discord.SelectOption(label="Invite Logs", value="invite_logs", emoji="✉️"),
            discord.SelectOption(label="Role Logs", value="role_logs", emoji="🏷️")
        ]
        super().__init__(placeholder="1️⃣ Select Log Type...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        self.view.selected_log_type = self.values[0]
        await interaction.response.send_message(f"✅ Selected Log Type: **{self.values[0]}**", ephemeral=True)

class ChannelSelectMenu(discord.ui.ChannelSelect):
    def __init__(self):
        super().__init__(placeholder="2️⃣ Select Channel...", channel_types=[discord.ChannelType.text], min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        self.view.selected_channel = self.values[0]
        await interaction.response.send_message(f"✅ Selected Channel: {self.values[0].mention}", ephemeral=True)

class SetupInteractiveView(discord.ui.View):
    def __init__(self, cog, author):
        super().__init__(timeout=120)
        self.cog = cog
        self.author = author
        self.selected_log_type = None
        self.selected_channel = None
        self.add_item(LogTypeSelect())
        self.add_item(ChannelSelectMenu())

    @discord.ui.button(label="✅ Save & Setup", style=discord.ButtonStyle.green, row=2)
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.author:
            return await interaction.response.send_message("❌ Not allowed!", ephemeral=True)
        if not self.selected_log_type or not self.selected_channel:
            return await interaction.response.send_message("⚠️ Select Log Type & Channel first!", ephemeral=True)

        if self.cog.modlog_col is None:
            return await interaction.response.send_message("❌ Database connection error!", ephemeral=True)

        await self.cog.modlog_col.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": {f"logs.{self.selected_log_type}": self.selected_channel.id}},
            upsert=True
        )

        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(content=f"🎉 **{self.selected_log_type}** set to {self.selected_channel.mention}!", view=self)

class ModLogs(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.invites_cache = {}

    @property
    def modlog_col(self):
        if hasattr(self.bot, 'async_db') and self.bot.async_db is not None:
            return self.bot.async_db["modlogs"]
        return None

    async def get_log_channel(self, guild, log_type):
        if self.modlog_col is None or not guild:
            return None
        data = await self.modlog_col.find_one({"guild_id": guild.id})
        if data and "logs" in data and log_type in data["logs"]:
            channel_id = data["logs"][log_type]
            return guild.get_channel(int(channel_id))
        return None

    # --- INVITE CACHE SYSTEM ---
    @commands.Cog.listener()
    async def on_ready(self):
        for guild in self.bot.guilds:
            try:
                self.invites_cache[guild.id] = await guild.invites()
            except Exception:
                pass

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        try:
            self.invites_cache[guild.id] = await guild.invites()
        except Exception:
            pass

    @commands.group(name="log", invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def log_group(self, ctx):
        await ctx.send("Use `!log setup` to configure logging channels.")

    @log_group.command(name="setup")
    @commands.has_permissions(administrator=True)
    async def log_interactive_setup(self, ctx):
        view = SetupInteractiveView(self, ctx.author)
        await ctx.send("⚙️ Select Log Options below:", view=view)

    # --- 1. MESSAGE LOGS ---
    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if message.author.bot or not message.guild:
            return
        log_ch = await self.get_log_channel(message.guild, "message_logs")
        if log_ch:
            embed = discord.Embed(title="🗑️ Message Deleted", color=discord.Color.red(), timestamp=datetime.utcnow())
            embed.add_field(name="Author", value=message.author.mention, inline=True)
            embed.add_field(name="Channel", value=message.channel.mention, inline=True)
            embed.add_field(name="Content", value=message.content or "Attachment / Embed", inline=False)
            await log_ch.send(embed=embed)

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if before.author.bot or not before.guild or before.content == after.content:
            return
        log_ch = await self.get_log_channel(before.guild, "message_logs")
        if log_ch:
            embed = discord.Embed(title="✏️ Message Edited", color=discord.Color.orange(), timestamp=datetime.utcnow())
            embed.add_field(name="Author", value=before.author.mention, inline=True)
            embed.add_field(name="Channel", value=before.channel.mention, inline=True)
            embed.add_field(name="Before", value=before.content or "None", inline=False)
            embed.add_field(name="After", value=after.content or "None", inline=False)
            await log_ch.send(embed=embed)

    # --- 2. VC LOGS ---
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.bot or not member.guild:
            return
        log_ch = await self.get_log_channel(member.guild, "vc_logs")
        if not log_ch:
            return

        embed = discord.Embed(timestamp=datetime.utcnow())
        if before.channel is None and after.channel is not None:
            embed.title = "🔊 Joined Voice Channel"
            embed.color = discord.Color.green()
            embed.description = f"{member.mention} joined **{after.channel.name}**"
            await log_ch.send(embed=embed)
        elif before.channel is not None and after.channel is None:
            embed.title = "🔇 Left Voice Channel"
            embed.color = discord.Color.red()
            embed.description = f"{member.mention} left **{before.channel.name}**"
            await log_ch.send(embed=embed)
        elif before.channel is not None and after.channel is not None and before.channel.id != after.channel.id:
            embed.title = "🔀 Switched Voice Channel"
            embed.color = discord.Color.blue()
            embed.description = f"{member.mention} moved from **{before.channel.name}** to **{after.channel.name}**"
            await log_ch.send(embed=embed)

    # --- 3. INVITE LOGS & MEMBER LOGS ---
    @commands.Cog.listener()
    async def on_member_join(self, member):
        guild = member.guild
        
        # Member Join Log
        log_ch = await self.get_log_channel(guild, "member_logs")
        if log_ch:
            embed = discord.Embed(title="📥 Member Joined", color=discord.Color.green(), timestamp=datetime.utcnow())
            embed.add_field(name="User", value=f"{member.mention} ({member.name})")
            embed.add_field(name="Account Created", value=member.created_at.strftime("%Y-%m-%d %H:%M:%S UTC"))
            embed.set_thumbnail(url=member.display_avatar.url)
            await log_ch.send(embed=embed)

        # Invite Log
        inv_ch = await self.get_log_channel(guild, "invite_logs")
        if inv_ch:
            inviter = None
            used_invite = None
            try:
                new_invites = await guild.invites()
                old_invites = self.invites_cache.get(guild.id, [])
                for inv in new_invites:
                    for old_inv in old_invites:
                        if inv.code == old_inv.code and inv.uses > old_inv.uses:
                            inviter = inv.inviter
                            used_invite = inv
                            break
                self.invites_cache[guild.id] = new_invites
            except Exception:
                pass

            embed_inv = discord.Embed(title="✉️ Invite Tracking", color=discord.Color.blue(), timestamp=datetime.utcnow())
            embed_inv.add_field(name="Joined Member", value=f"{member.mention} (`{member.id}`)")
            if inviter and used_invite:
                embed_inv.add_field(name="Invited By", value=f"{inviter.mention} (`{inviter.name}`)")
                embed_inv.add_field(name="Invite Code / Uses", value=f"`{used_invite.code}` ({used_invite.uses} uses)")
            else:
                embed_inv.add_field(name="Invited By", value="Unknown / Vanity URL / Bot")
            await inv_ch.send(embed=embed_inv)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        log_ch = await self.get_log_channel(member.guild, "member_logs")
        if log_ch:
            embed = discord.Embed(title="📤 Member Left", color=discord.Color.red(), timestamp=datetime.utcnow())
            embed.add_field(name="User", value=f"{member.name} ({member.id})")
            embed.set_thumbnail(url=member.display_avatar.url)
            await log_ch.send(embed=embed)

    # --- 4. MOD ACTION LOGS ---
    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        log_ch = await self.get_log_channel(guild, "mod_action_logs")
        if not log_ch:
            return
        async for entry in guild.audit_logs(action=discord.AuditLogAction.ban, limit=1):
            if entry.target.id == user.id:
                embed = discord.Embed(title="🔨 Member Banned", color=discord.Color.dark_red(), timestamp=datetime.utcnow())
                embed.add_field(name="Target", value=f"{user.mention} (`{user.id}`)")
                embed.add_field(name="Moderator", value=entry.user.mention)
                embed.add_field(name="Reason", value=entry.reason or "No reason provided", inline=False)
                await log_ch.send(embed=embed)
                break

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        log_ch = await self.get_log_channel(before.guild, "mod_action_logs")
        role_ch = await self.get_log_channel(before.guild, "role_logs")

        # Timeout / Mute Detector
        if log_ch and before.timed_out_until != after.timed_out_until:
            async for entry in before.guild.audit_logs(action=discord.AuditLogAction.member_update, limit=1):
                if entry.target.id == after.id:
                    embed = discord.Embed(timestamp=datetime.utcnow())
                    if after.timed_out_until:
                        embed.title = "⏳ Member Timed Out"
                        embed.color = discord.Color.orange()
                        embed.add_field(name="Target", value=after.mention)
                        embed.add_field(name="Moderator", value=entry.user.mention)
                        embed.add_field(name="Until", value=after.timed_out_until.strftime("%Y-%m-%d %H:%M:%S UTC"))
                        embed.add_field(name="Reason", value=entry.reason or "None", inline=False)
                    else:
                        embed.title = "🔊 Timeout Removed"
                        embed.color = discord.Color.green()
                        embed.add_field(name="Target", value=after.mention)
                        embed.add_field(name="Moderator", value=entry.user.mention)
                    await log_ch.send(embed=embed)
                    break

        # Role Given / Removed to Member
        if role_ch and before.roles != after.roles:
            async for entry in before.guild.audit_logs(action=discord.AuditLogAction.member_role_update, limit=1):
                if entry.target.id == after.id:
                    added_roles = [r.mention for r in after.roles if r not in before.roles]
                    removed_roles = [r.mention for r in before.roles if r not in after.roles]
                    
                    embed = discord.Embed(title="👤 Member Roles Updated", color=discord.Color.blue(), timestamp=datetime.utcnow())
                    embed.add_field(name="Target", value=after.mention)
                    embed.add_field(name="Moderator", value=entry.user.mention)
                    if added_roles:
                        embed.add_field(name="Added Roles", value=", ".join(added_roles), inline=False)
                    if removed_roles:
                        embed.add_field(name="Removed Roles", value=", ".join(removed_roles), inline=False)
                    await role_ch.send(embed=embed)
                    break

    # --- 5. ROLE LOGS (CREATE, DELETE, UPDATE) ---
    @commands.Cog.listener()
    async def on_guild_role_create(self, role):
        log_ch = await self.get_log_channel(role.guild, "role_logs")
        if log_ch:
            async for entry in role.guild.audit_logs(action=discord.AuditLogAction.role_create, limit=1):
                embed = discord.Embed(title="🟢 Role Created", color=discord.Color.green(), timestamp=datetime.utcnow())
                embed.add_field(name="Role Name", value=role.name)
                embed.add_field(name="Created By", value=entry.user.mention)
                await log_ch.send(embed=embed)
                break

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role):
        log_ch = await self.get_log_channel(role.guild, "role_logs")
        if log_ch:
            async for entry in role.guild.audit_logs(action=discord.AuditLogAction.role_delete, limit=1):
                embed = discord.Embed(title="🔴 Role Deleted", color=discord.Color.red(), timestamp=datetime.utcnow())
                embed.add_field(name="Role Name", value=role.name)
                embed.add_field(name="Deleted By", value=entry.user.mention)
                await log_ch.send(embed=embed)
                break

    @commands.Cog.listener()
    async def on_guild_role_update(self, before, after):
        log_ch = await self.get_log_channel(before.guild, "role_logs")
        if log_ch and before.name != after.name:
            async for entry in before.guild.audit_logs(action=discord.AuditLogAction.role_update, limit=1):
                embed = discord.Embed(title="✏️ Role Renamed", color=discord.Color.gold(), timestamp=datetime.utcnow())
                embed.add_field(name="Before", value=before.name)
                embed.add_field(name="After", value=after.name)
                embed.add_field(name="Updated By", value=entry.user.mention)
                await log_ch.send(embed=embed)
                break

async def setup(bot):
    await bot.add_cog(ModLogs(bot))
            
