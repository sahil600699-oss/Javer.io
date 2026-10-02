import discord
from discord.ext import commands
import asyncio

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Active spam tasks tracker: guild_id -> asyncio.Task
        self.active_spam_tasks = {}

    # ==========================================
    # 🔒 PERMISSION ERROR HANDLER
    # ==========================================
    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            perms = ", ".join(error.missing_permissions).replace("_", " ").title()
            embed = discord.Embed(
                title="⛔ Permission Denied!",
                description=f"You need **`{perms}`** permission to use this command.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
        elif isinstance(error, commands.BotMissingPermissions):
            perms = ", ".join(error.missing_permissions).replace("_", " ").title()
            await ctx.send(f"❌ Bot is missing required permission: **`{perms}`**")

    # ==========================================
    # 1. BAN, KICK & CLEAR COMMANDS
    # ==========================================
    @commands.command(name="kick")
    @commands.has_permissions(kick_members=True)
    async def kick_user(self, ctx, member: discord.Member, *, reason: str = "No reason provided"):
        if member == ctx.author:
            return await ctx.send("❌ You cannot kick yourself!")
        try:
            await member.kick(reason=reason)
            await ctx.send(f"👢 **{member.display_name}** has been kicked | Reason: {reason}")
        except Exception as e:
            await ctx.send(f"❌ Kick error: {e}")

    @commands.command(name="ban")
    @commands.has_permissions(ban_members=True)
    async def ban_user(self, ctx, member: discord.Member, *, reason: str = "No reason provided"):
        if member == ctx.author:
            return await ctx.send("❌ You cannot ban yourself!")
        try:
            await member.ban(reason=reason)
            await ctx.send(f"🔨 **{member.display_name}** has been banned | Reason: {reason}")
        except Exception as e:
            await ctx.send(f"❌ Ban error: {e}")

    @commands.command(name="clear", aliases=["purge"])
    @commands.has_permissions(manage_messages=True)
    async def clear_messages(self, ctx, amount: int):
        if amount <= 0:
            return await ctx.send("❌ Amount must be 1 or higher!")
        try:
            deleted = await ctx.channel.purge(limit=amount + 1)
            msg = await ctx.send(f"🧹 Cleared **{len(deleted)-1}** messages!")
            await asyncio.sleep(3)
            await msg.delete()
        except Exception as e:
            await ctx.send(f"❌ Clear error: {e}")

    # ==========================================
    # 2. CHANGE NICKNAME (!change nick @user [name])
    # ==========================================
    @commands.group(name="change", invoke_without_command=True)
    @commands.has_permissions(manage_nicknames=True)
    async def change_group(self, ctx):
        await ctx.send("❓ Invalid usage! Format: `!change nick @user [new_nickname]`")

    @change_group.command(name="nick")
    @commands.has_permissions(manage_nicknames=True)
    async def change_nickname(self, ctx, member: discord.Member, *, new_nick: str):
        try:
            old_nick = member.display_name
            await member.edit(nick=new_nick)
            await ctx.send(f"✅ Changed nickname for **{old_nick}** to **{new_nick}**!")
        except Exception as e:
            await ctx.send(f"❌ Nickname change error: {e}")

    # ==========================================
    # 3. MUTE & DEAFEN IN VC
    # ==========================================
    @commands.command(name="mute")
    @commands.has_permissions(mute_members=True)
    async def mute_vc(self, ctx, member: discord.Member):
        if not member.voice or not member.voice.channel:
            return await ctx.send(f"❌ {member.mention} is not in a Voice Channel!")
        try:
            is_muted = not member.voice.mute
            await member.edit(mute=is_muted)
            status = "Muted 🔕" if is_muted else "Unmuted 🔔"
            await ctx.send(f"✅ {member.mention} is now **{status}** in Voice!")
        except Exception as e:
            await ctx.send(f"❌ Mute action failed: {e}")

    @commands.command(name="def")
    @commands.has_permissions(deafen_members=True)
    async def deafen_vc(self, ctx, member: discord.Member):
        if not member.voice or not member.voice.channel:
            return await ctx.send(f"❌ {member.mention} is not in a Voice Channel!")
        try:
            is_deaf = not member.voice.deafen
            await member.edit(deafen=is_deaf)
            status = "Deafened 🔇" if is_deaf else "Undeafened 🔊"
            await ctx.send(f"✅ {member.mention} is now **{status}** in Voice!")
        except Exception as e:
            await ctx.send(f"❌ Deafen action failed: {e}")

    # ==========================================
    # 4. MOVE USER TO VC
    # ==========================================
    @commands.command(name="move")
    @commands.has_permissions(move_members=True)
    async def move_vc(self, ctx, member: discord.Member, *, vc_name: str):
        if not member.voice or not member.voice.channel:
            return await ctx.send(f"❌ {member.mention} is not in a Voice Channel!")

        target_vc = discord.utils.get(ctx.guild.voice_channels, name=vc_name)
        if not target_vc:
            return await ctx.send(f"❌ Voice Channel **'{vc_name}'** not found!")

        try:
            await member.move_to(target_vc)
            await ctx.send(f"🚚 Moved {member.mention} to **{target_vc.name}**!")
        except Exception as e:
            await ctx.send(f"❌ VC Move error: {e}")

    # ==========================================
    # 5. GIVE/REMOVE ROLE
    # ==========================================
    @commands.command(name="roleg")
    @commands.has_permissions(manage_roles=True)
    async def give_role(self, ctx, member: discord.Member, *, role_name: str):
        role = discord.utils.get(ctx.guild.roles, name=role_name)
        if not role:
            return await ctx.send(f"❌ Role **'{role_name}'** not found in this server!")

        try:
            if role in member.roles:
                await member.remove_roles(role)
                await ctx.send(f"➖ Removed **{role.name}** from {member.mention}.")
            else:
                await member.add_roles(role)
                await ctx.send(f"➕ Assigned **{role.name}** to {member.mention}!")
        except Exception as e:
            await ctx.send(f"❌ Role assignment error: {e}")

    # ==========================================
    # 6. FIXED SPAM & SPAMSTOP COMMANDS
    # ==========================================
    async def run_spam(self, ctx, amount: int, message_text: str):
        try:
            for _ in range(amount):
                await ctx.send(message_text)
                await asyncio.sleep(0.5)
        except asyncio.CancelledError:
            await ctx.send("🛑 Spam task stopped successfully.")
        finally:
            self.active_spam_tasks.pop(ctx.guild.id, None)

    @commands.command(name="spam")
    @commands.has_permissions(administrator=True)
    async def start_spam(self, ctx, amount: int, *, message_text: str):
        if ctx.guild.id in self.active_spam_tasks:
            return await ctx.send("⚠️ A spam process is already running in this server! Use `!spamstop` to end it.")

        if amount > 50:
            return await ctx.send("⚠️ For server safety, maximum spam limit per command is 50 messages.")

        await ctx.send(f"🚀 Starting spam task ({amount} messages)... Send `!spamstop` to cancel.")
        task = asyncio.create_task(self.run_spam(ctx, amount, message_text))
        self.active_spam_tasks[ctx.guild.id] = task

    @commands.command(name="spamstop")
    @commands.has_permissions(administrator=True)
    async def stop_spam(self, ctx):
        task = self.active_spam_tasks.get(ctx.guild.id)
        if task:
            task.cancel()
            await ctx.send("🛑 Active spam task has been cancelled.")
        else:
            await ctx.send("❓ No active spam process found in this server.")

    # ==========================================
    # 7. SERVER INFO
    # ==========================================
    @commands.command(name="serverinfo", aliases=["si"])
    async def server_info(self, ctx):
        guild = ctx.guild
        owner = guild.owner
        created_at = guild.created_at.strftime("%d %B %Y (%I:%M %p)")
        
        members_count = guild.member_count
        bots_count = sum(1 for m in guild.members if m.bot)
        humans_count = members_count - bots_count

        embed = discord.Embed(
            title=f"📊 Server Info — {guild.name}",
            color=discord.Color.gold()
        )
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        embed.add_field(name="👑 Server Owner", value=f"{owner.mention} (`{owner.id}`)", inline=False)
        embed.add_field(name="📅 Created On", value=created_at, inline=False)
        embed.add_field(name="👥 Members Count", value=f"• Total: **{members_count}**\n• Humans: **{humans_count}**\n• Bots: **{bots_count}**", inline=True)
        embed.add_field(name="🚀 Boost Status", value=f"• Boosts: **{guild.premium_subscription_count}**\n• Level: **Tier {guild.premium_tier}**", inline=True)
        embed.add_field(name="💬 Channels", value=f"• Text: **{len(guild.text_channels)}**\n• Voice: **{len(guild.voice_channels)}**", inline=True)
        
        embed.set_footer(text=f"Server ID: {guild.id}")
        await ctx.send(embed=embed)

    # ==========================================
    # 8. VANITY LINK LISTENER
    # ==========================================
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return

        if message.content.lower().strip() == "vanity":
            try:
                if message.guild.vanity_url_code:
                    return await message.channel.send(f"🔗 **Server Permanent Vanity Link:** https://discord.gg/{message.guild.vanity_url_code}")

                invites = await message.guild.invites()
                permanent_invite = None
                for inv in invites:
                    if inv.max_age == 0 and inv.max_uses == 0:
                        permanent_invite = inv
                        break

                if not permanent_invite:
                    permanent_invite = await message.channel.create_invite(max_age=0, max_uses=0, reason="Vanity Link Listener Triggered")

                await message.channel.send(f"🔗 **Server Invite Link:** {permanent_invite.url}")
            except Exception:
                await message.channel.send("❌ Missing permissions to generate invite or check vanity.")

async def setup(bot):
    await bot.add_cog(Moderation(bot))
            
