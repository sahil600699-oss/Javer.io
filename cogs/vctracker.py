import discord
from discord.ext import commands
from datetime import datetime, timedelta, timezone

# India (IST) calendar helpers. MongoDB collection/setup is unchanged.
IST = timezone(timedelta(hours=5, minutes=30))

def ist_day_start_utc():
    now = datetime.now(IST)
    start = datetime(now.year, now.month, now.day, tzinfo=IST)
    return start.astimezone(timezone.utc)

def ist_week_start_utc():
    now = datetime.now(IST)
    start_date = (now - timedelta(days=now.weekday())).date()
    start = datetime(start_date.year, start_date.month, start_date.day, tzinfo=IST)
    return start.astimezone(timezone.utc)

# --- INTERACTIVE DROPDOWN MENU ---
class VcCommandSelect(discord.ui.Select):
    def __init__(self, bot, target_user=None):
        self.bot = bot
        self.target_user = target_user
        options = [
            discord.SelectOption(label="24h Top VC Members", value="vc_top", description="Pichle 24 hours ke top 20 VC active members", emoji="🎙️"),
            discord.SelectOption(label="Weekly Top VC Members", value="vcw_top", description="Pichle 7 days ke top VC active members", emoji="👑"),
            discord.SelectOption(label="User 24h VC Stats", value="vc_user", description="Selected user ki 24h channel breakdown", emoji="📊"),
            discord.SelectOption(label="User Weekly VC Combined", value="vcw_user", description="User ke 24h + 7 Days total VC stats", emoji="📈"),
            discord.SelectOption(label="VC Tracker Help Guide", value="vc_help", description="All VC tracking commands info", emoji="❓")
        ]
        super().__init__(placeholder="⚡ Select VC Command to Execute...", min_values=1, max_values=1, options=options, row=1)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        cog = self.bot.get_cog("VcTracker")
        if not cog:
            await interaction.followup.send("❌ Error: VcTracker Cog active nahi hai!", ephemeral=True)
            return

        user = self.target_user or interaction.user
        val = self.values[0]

        if val == "vc_top":
            embed, view = await cog.get_vc_top_data(interaction.guild, interaction.user)
            await interaction.followup.send(embed=embed, view=view)
        elif val == "vcw_top":
            embed, view = await cog.get_vcw_top_data(interaction.guild, interaction.user)
            await interaction.followup.send(embed=embed, view=view)
        elif val == "vc_user":
            embed, view = await cog.get_vc_user_data(interaction.guild, user)
            await interaction.followup.send(embed=embed, view=view)
        elif val == "vcw_user":
            embed, view = await cog.get_vcw_user_data(interaction.guild, user)
            await interaction.followup.send(embed=embed, view=view)
        elif val == "vc_help":
            embed, view = await cog.get_vc_help_data(interaction.user)
            await interaction.followup.send(embed=embed, view=view)


# --- PAGINATION & DROPDOWN COMBINED VIEW ---
class VcTopPaginationView(discord.ui.View):
    def __init__(self, bot, author, rows, guild, format_func):
        super().__init__(timeout=180)
        self.bot = bot
        self.author = author
        self.rows = rows
        self.guild = guild
        self.format_func = format_func
        self.current_page = 1
        
        self.add_item(VcCommandSelect(bot))
        self.update_buttons()

    def update_buttons(self):
        self.prev_btn.disabled = (self.current_page == 1)
        self.next_btn.disabled = (self.current_page == 2 or len(self.rows) <= 10)

    def create_embed(self):
        embed = discord.Embed(
            title="🎙️ Top 20 Voice Active Members (Today (IST))",
            description="*(Aaj (India time) ke top voice active users)*\n",
            color=discord.Color.red()
        )

        if self.current_page == 1:
            page_rows = self.rows[:10]
            start_rank = 1
            rank_title = "📍 Rank 1 - 10"
        else:
            page_rows = self.rows[10:20]
            start_rank = 11
            rank_title = "📍 Rank 11 - 20"

        lines = []
        for idx, item in enumerate(page_rows, start_rank):
            user_id = item["_id"]
            total_sec = item["total_duration"]
            member = self.guild.get_member(user_id)
            name = member.display_name if member else f"User `{user_id}`"
            formatted_time = self.format_func(total_sec)
            lines.append(f"**{idx}.** `{name[:15]}`: **{formatted_time}**")

        page_text = "\n".join(lines) if lines else "No Data"
        embed.add_field(name=rank_title, value=page_text, inline=False)
        embed.set_footer(text=f"Page {self.current_page}/2 • Requested by {self.author.display_name}", icon_url=self.author.display_avatar.url)

        return embed

    @discord.ui.button(label="◀️ Prev", style=discord.ButtonStyle.primary, row=0)
    async def prev_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author.id:
            return await interaction.response.send_message("❌ Yeh action aapke liye nahi hai!", ephemeral=True)
        
        self.current_page = 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.create_embed(), view=self)

    @discord.ui.button(label="Next ▶️", style=discord.ButtonStyle.primary, row=0)
    async def next_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author.id:
            return await interaction.response.send_message("❌ Yeh action aapke liye nahi hai!", ephemeral=True)
        
        self.current_page = 2
        self.update_buttons()
        await interaction.response.edit_message(embed=self.create_embed(), view=self)


class VcDropdownView(discord.ui.View):
    def __init__(self, bot, author, target_user=None):
        super().__init__(timeout=180)
        self.add_item(VcCommandSelect(bot, target_user))


# --- MAIN COG CLASS ---
class VcTracker(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_sessions = {}

    @property
    def collection(self):
        # Universal MongoDB collection instance fetch
        if self.bot.db is not None:
            return self.bot.db['vc_logs']
        return None

    def format_seconds(self, seconds):
        seconds = int(seconds or 0)
        minutes, sec = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        if hours > 0:
            return f"{hours}h {minutes}m"
        elif minutes > 0:
            return f"{minutes}m {sec}s"
        return f"{sec}s"

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.bot or self.collection is None:
            return

        now = datetime.now(timezone.utc)

        # VC Join
        if before.channel is None and after.channel is not None:
            self.active_sessions[member.id] = (after.channel.id, now)

        # VC Leave
        elif before.channel is not None and after.channel is None:
            session = self.active_sessions.pop(member.id, None)
            if session:
                ch_id, join_time = session
                if now > join_time:
                    self._save_session_chunks(member, ch_id, join_time, now)

        # Channel Switch
        elif before.channel is not None and after.channel is not None and before.channel.id != after.channel.id:
            session = self.active_sessions.pop(member.id, None)
            if session:
                ch_id, join_time = session
                if now > join_time:
                    self._save_session_chunks(member, ch_id, join_time, now)
            self.active_sessions[member.id] = (after.channel.id, now)

    def _save_session_chunks(self, member, channel_id, join_time, end_time):
        # Split a session at every IST midnight so daily stats reset correctly.
        cursor = join_time
        while cursor < end_time:
            local = cursor.astimezone(IST)
            next_day = datetime(
                local.year, local.month, local.day, tzinfo=IST
            ) + timedelta(days=1)
            boundary = next_day.astimezone(timezone.utc)
            chunk_end = min(end_time, boundary)
            seconds = int((chunk_end - cursor).total_seconds())

            if seconds > 0:
                self.collection.insert_one({
                    "guild_id": member.guild.id,
                    "channel_id": channel_id,
                    "user_id": member.id,
                    "duration_seconds": seconds,
                    "timestamp": chunk_end
                })

            cursor = chunk_end

    def _add_live_time(self, rows, guild, period_start):
        # Count a member's current VC session immediately, without waiting for leave.
        totals = {item["_id"]: item["total_duration"] for item in rows}
        now = datetime.now(timezone.utc)

        for user_id, (_, join_time) in self.active_sessions.items():
            member = guild.get_member(user_id)
            if member is None or member.guild.id != guild.id:
                continue

            start = max(join_time, period_start)
            if now > start:
                totals[user_id] = totals.get(user_id, 0) + int(
                    (now - start).total_seconds()
                )

        result = [
            {"_id": uid, "total_duration": total}
            for uid, total in totals.items()
            if total > 0
        ]
        result.sort(key=lambda x: x["total_duration"], reverse=True)
        return result

    async def get_vc_top_data(self, guild, author):
        if self.collection is None:
            return discord.Embed(title="Error", description="Database connection error!"), None

        time_24h_ago = ist_day_start_utc()
        
        pipeline = [
            {"$match": {"guild_id": guild.id, "timestamp": {"$gte": time_24h_ago}}},
            {"$group": {"_id": "$user_id", "total_duration": {"$sum": "$duration_seconds"}}},
            {"$sort": {"total_duration": -1}},
            {"$limit": 20}
        ]
        rows = list(self.collection.aggregate(pipeline))
        rows = self._add_live_time(rows, guild, time_24h_ago)

        if not rows:
            embed = discord.Embed(
                title="🎙️ Top 20 Voice Active Members (Today (IST))",
                description="⚠️ Aaj (India time) me koi Voice Activity record nahi mila.",
                color=discord.Color.red()
            )
            return embed, VcDropdownView(self.bot, author)

        view = VcTopPaginationView(self.bot, author, rows, guild, self.format_seconds)
        embed = view.create_embed()
        return embed, view

    async def get_vcw_top_data(self, guild, author):
        if self.collection is None:
            return discord.Embed(title="Error", description="Database connection error!"), None

        time_7d_ago = ist_week_start_utc()
        
        pipeline = [
            {"$match": {"guild_id": guild.id, "timestamp": {"$gte": time_7d_ago}}},
            {"$group": {"_id": "$user_id", "total_duration": {"$sum": "$duration_seconds"}}},
            {"$sort": {"total_duration": -1}},
            {"$limit": 10}
        ]
        rows = list(self.collection.aggregate(pipeline))
        rows = self._add_live_time(rows, guild, time_7d_ago)

        embed = discord.Embed(title="👑 Top VC Active Members (Current Week / IST)", color=discord.Color.red())

        if not rows:
            embed.description = "⚠️ Is week koi Voice activity record nahi mila."
        else:
            description_lines = []
            for idx, item in enumerate(rows, 1):
                user_id = item["_id"]
                total_sec = item["total_duration"]
                member = guild.get_member(user_id)
                name = member.mention if member else f"User `{user_id}`"
                formatted_time = self.format_seconds(total_sec)
                description_lines.append(f"**#{idx}** {name} — ⏱️ **{formatted_time}**")
            embed.description = "\n".join(description_lines)

        embed.set_footer(text=f"Requested by {author.display_name}", icon_url=author.display_avatar.url)
        return embed, VcDropdownView(self.bot, author)

    async def get_vc_user_data(self, guild, target_user):
        if self.collection is None:
            return discord.Embed(title="Error", description="Database connection error!"), None

        time_24h_ago = ist_day_start_utc()
        
        pipeline = [
            {"$match": {"guild_id": guild.id, "user_id": target_user.id, "timestamp": {"$gte": time_24h_ago}}},
            {"$group": {"_id": "$channel_id", "total_sec": {"$sum": "$duration_seconds"}}},
            {"$sort": {"total_sec": -1}}
        ]
        rows = list(self.collection.aggregate(pipeline))

        # Current VC session is counted live, even before the user leaves.
        session = self.active_sessions.get(target_user.id)
        if session and target_user.guild.id == guild.id:
            ch_id, join_time = session
            now = datetime.now(timezone.utc)
            start = max(join_time, time_24h_ago)
            if now > start:
                live_seconds = int((now - start).total_seconds())
                found = False
                for item in rows:
                    if item["_id"] == ch_id:
                        item["total_sec"] += live_seconds
                        found = True
                        break
                if not found:
                    rows.append({"_id": ch_id, "total_sec": live_seconds})

        rows.sort(key=lambda x: x["total_sec"], reverse=True)

        embed = discord.Embed(
            title=f"📊 Today (IST) VC Activity Breakdown — {target_user.display_name}",
            color=discord.Color.red()
        )
        embed.set_thumbnail(url=target_user.display_avatar.url)

        total_24h_sec = sum(item["total_sec"] for item in rows)
        
        if not rows:
            embed.description = "⚠️ Aaj (India time) me is user ne VC use nahi kiya hai."
        else:
            channel_breakdown = []
            for item in rows:
                ch_id = item["_id"]
                total_sec = item["total_sec"]
                ch = guild.get_channel(ch_id)
                ch_name = ch.mention if ch else f"#deleted-vc"
                channel_breakdown.append(f"• {ch_name}: **{self.format_seconds(total_sec)}**")

            embed.description = "**Voice Channel Breakdown:**\n" + "\n".join(channel_breakdown)

        embed.add_field(name="⏱️ Total 24h VC Time", value=f"**{self.format_seconds(total_24h_sec)}**", inline=False)
        embed.set_footer(text=f"User ID: {target_user.id}")

        return embed, VcDropdownView(self.bot, target_user, target_user)

    async def get_vcw_user_data(self, guild, target_user):
        if self.collection is None:
            return discord.Embed(title="Error", description="Database connection error!"), None

        now = datetime.now(timezone.utc)
        time_24h_ago = now - timedelta(hours=24)
        time_7d_ago = now - timedelta(days=7)

        # 24h Total
        pipeline_24h = [
            {"$match": {"guild_id": guild.id, "user_id": target_user.id, "timestamp": {"$gte": time_24h_ago}}},
            {"$group": {"_id": None, "total": {"$sum": "$duration_seconds"}}}
        ]
        res_24h = list(self.collection.aggregate(pipeline_24h))
        sec_24h = res_24h[0]["total"] if res_24h else 0

        # 7d Total
        pipeline_7d = [
            {"$match": {"guild_id": guild.id, "user_id": target_user.id, "timestamp": {"$gte": time_7d_ago}}},
            {"$group": {"_id": None, "total": {"$sum": "$duration_seconds"}}}
        ]
        res_7d = list(self.collection.aggregate(pipeline_7d))
        sec_7d = res_7d[0]["total"] if res_7d else 0

        # Count the current session immediately in both periods.
        session = self.active_sessions.get(target_user.id)
        if session and target_user.guild.id == guild.id:
            _, join_time = session
            now = datetime.now(timezone.utc)
            day_start = ist_day_start_utc()
            week_start = ist_week_start_utc()

            live_day = max(0, int((now - max(join_time, day_start)).total_seconds()))
            live_week = max(0, int((now - max(join_time, week_start)).total_seconds()))

            sec_24h += live_day
            sec_7d += live_week

        embed = discord.Embed(
            title=f"📈 Overview VC Stats — {target_user.display_name}",
            color=discord.Color.red()
        )
        embed.set_thumbnail(url=target_user.display_avatar.url)
        embed.add_field(name="⏰ Today (IST)", value=f"**{self.format_seconds(sec_24h)}**", inline=True)
        embed.add_field(name="📅 Current Week (IST)", value=f"**{self.format_seconds(sec_7d)}**", inline=True)
        embed.set_footer(text=f"User ID: {target_user.id}")

        return embed, VcDropdownView(self.bot, target_user, target_user)

    async def get_vc_help_data(self, author):
        embed = discord.Embed(
            title="❓ Voice Tracking System — Commands Guide",
            description="Commands typing se ya neeche diye gaye dropdown menu se directly run karein:",
            color=discord.Color.red()
        )
        embed.add_field(name="🔹 !vc top", value="Aaj (India time) ke Top 20 Active VC Members (Page 1: 1-10 | Page 2: 11-20).", inline=False)
        embed.add_field(name="🔹 !vc @user", value="Targeted member ki 24h Channel-wise VC Time breakdown.", inline=False)
        embed.add_field(name="🔹 !vcw top", value="Current Week (IST) (Weekly) ke Top VC Users ki Leaderboard.", inline=False)
        embed.add_field(name="🔹 !vcw @user", value="Member ka 24h aur Current Week (IST) total VC time summary.", inline=False)
        embed.add_field(name="🔹 !vc help", value="Ye VC Help Menu display karega.", inline=False)
        
        embed.set_footer(text="⚡ Select commands from the dropdown menu below!")
        return embed, VcDropdownView(self.bot, author)

    @commands.group(name="vc", invoke_without_command=True)
    async def vc_group(self, ctx, member: discord.Member = None):
        target = member or ctx.author
        embed, view = await self.get_vc_user_data(ctx.guild, target)
        await ctx.send(embed=embed, view=view)

    @vc_group.command(name="top")
    async def vc_top(self, ctx):
        embed, view = await self.get_vc_top_data(ctx.guild, ctx.author)
        await ctx.send(embed=embed, view=view)

    @vc_group.command(name="help")
    async def vc_help_cmd(self, ctx):
        embed, view = await self.get_vc_help_data(ctx.author)
        await ctx.send(embed=embed, view=view)

    @commands.group(name="vcw", invoke_without_command=True)
    async def vcw_group(self, ctx, member: discord.Member = None):
        target = member or ctx.author
        embed, view = await self.get_vcw_user_data(ctx.guild, target)
        await ctx.send(embed=embed, view=view)

    @vcw_group.command(name="top")
    async def vcw_top(self, ctx):
        embed, view = await self.get_vcw_top_data(ctx.guild, ctx.author)
        await ctx.send(embed=embed, view=view)


async def setup(bot):
    await bot.add_cog(VcTracker(bot))
            
