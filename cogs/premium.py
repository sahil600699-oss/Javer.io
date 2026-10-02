import discord
from discord.ext import commands
import datetime
import config

# --- HELPER FUNCTIONS ---
def parse_duration(time_str: str):
    if time_str.lower() in ["perm", "permanent", "inf", "forever"]:
        return None
    unit = time_str[-1].lower()
    try:
        val = int(time_str[:-1])
    except ValueError:
        return -1
    now = datetime.datetime.utcnow()
    if unit == 'd':
        return now + datetime.timedelta(days=val)
    elif unit == 'm':
        return now + datetime.timedelta(days=val * 30)
    elif unit == 'y':
        return now + datetime.timedelta(days=val * 365)
    return -1

def is_owner_check(ctx):
    return ctx.author.id == getattr(config, "OWNER_ID", None)

# --- INTERACTIVE COMPONENTS ---

class CommandSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="🌟 All Commands (*)", value="*", description="Full access to ALL Premium commands"),
            discord.SelectOption(label="Spam Command", value="spam", description="Permission for Spam & Spamstop commands"),
            discord.SelectOption(label="Bot Customization", value="botprofile", description="Permission for !serverpfp, !servernick, !serverb"),
            discord.SelectOption(label="Mass Unban", value="massunban", description="Permission for Mass Unban command")
        ]
        super().__init__(placeholder="Permissions select karein...", min_values=1, max_values=len(options), options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        self.view.selected_cmds = self.values

class PlanCreateView(discord.ui.View):
    def __init__(self, cog, plan_name, owner_id):
        super().__init__(timeout=120)
        self.cog = cog
        self.plan_name = plan_name
        self.owner_id = owner_id
        self.selected_cmds = []
        self.add_item(CommandSelect())

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("❌ Access Denied!", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Confirm & Save Plan", style=discord.ButtonStyle.green)
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.selected_cmds:
            return await interaction.response.send_message("❌ Pehle permission select karein!", ephemeral=True)

        if self.cog.plans_col is None:
            return await interaction.response.send_message("❌ Database connection error!", ephemeral=True)

        cmds_str = ",".join(self.selected_cmds)
        
        await self.cog.plans_col.update_one(
            {"plan_name": self.plan_name},
            {"$set": {"plan_name": self.plan_name, "allowed_commands": cmds_str}},
            upsert=True
        )

        embed = discord.Embed(
            title="✅ Premium Plan Created!",
            description=f"Plan **`{self.plan_name}`** saved with permissions:\n`{cmds_str}`",
            color=discord.Color.green()
        )
        await interaction.response.edit_message(embed=embed, view=None)

# --- PREMIUM COG CLASS ---

class PremiumSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @property
    def db(self):
        return getattr(self.bot, "async_db", None)

    @property
    def plans_col(self):
        return self.db["premium_plans"] if self.db is not None else None

    @property
    def holders_col(self):
        return self.db["premium_holders"] if self.db is not None else None

    async def has_premium_access(self, user_id: int, guild_id: int, command_name: str) -> bool:
        if user_id == getattr(config, "OWNER_ID", None):
            return True

        if self.db is None:
            return False

        now = datetime.datetime.utcnow()

        cursor = self.plans_col.find({})
        async for plan in cursor:
            plan_name = plan.get("plan_name")
            cmds_str = plan.get("allowed_commands", "")
            allowed_cmds = [c.strip().lower() for c in cmds_str.split(",")]

            if command_name.lower() in allowed_cmds or "*" in allowed_cmds:
                query = {
                    "plan_name": plan_name,
                    "$or": [
                        {"target_type": "user", "target_id": user_id},
                        {"target_type": "server", "guild_id": guild_id},
                        {"target_type": "su", "target_id": user_id, "guild_id": guild_id}
                    ]
                }
                holders_cursor = self.holders_col.find(query)
                async for holder in holders_cursor:
                    exp_dt = holder.get("expires_at")
                    if exp_dt is None:
                        return True
                    if isinstance(exp_dt, str):
                        exp_dt = datetime.datetime.fromisoformat(exp_dt)
                    if exp_dt > now:
                        return True

        return False

    async def cog_check(self, ctx):
        if not is_owner_check(ctx):
            await ctx.send("❌ **Access Denied!** Ye command sirf Bot Owner run kar sakta hai.")
            return False
        return True

    # 1. CREATE PLAN VIA UI
    @commands.command(name="pcreate", aliases=["pp"])
    async def pcreate(self, ctx, plan_name: str = None):
        if not plan_name:
            return await ctx.send("❌ Usage: `!pcreate <plan_name>`")
        
        view = PlanCreateView(self, plan_name.lower(), ctx.author.id)
        embed = discord.Embed(
            title=f"🔨 Creating Premium Plan: {plan_name}",
            description="Dropdown menu se permissions select karein (Multi-select enabled ya `*` select karein) aur Confirm click karein.",
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed, view=view)

    # 2. ADD COMMAND TO PLAN DIRECTLY VIA TEXT COMMAND
    @commands.command(name="pcommand")
    async def pcommand(self, ctx, plan_name: str = None, command_name: str = None):
        if self.plans_col is None:
            return await ctx.send("❌ Database connection error!")

        if not plan_name or not command_name:
            return await ctx.send("❌ Usage: `!pcommand <plan_name> <command_permission>`\nExample: `!pcommand diamond botprofile`")

        plan = plan_name.lower()
        cmd = command_name.lower()

        row = await self.plans_col.find_one({"plan_name": plan})

        if row:
            existing_cmds = [c.strip() for c in row.get("allowed_commands", "").split(",") if c.strip()]
            if cmd not in existing_cmds:
                existing_cmds.append(cmd)
            new_cmds_str = ",".join(existing_cmds)
            await self.plans_col.update_one({"plan_name": plan}, {"$set": {"allowed_commands": new_cmds_str}})
            msg = f"✅ Plan **`{plan}`** me **`{cmd}`** command permission add kar di gayi!\nExisting Permissions: `{new_cmds_str}`"
        else:
            await self.plans_col.insert_one({"plan_name": plan, "allowed_commands": cmd})
            msg = f"✅ Naya Plan **`{plan}`** banaya gaya aur usme **`{cmd}`** permission add kar di gayi!"

        await ctx.send(msg)

    # 3. GIVE PREMIUM ACCESS
    @commands.group(name="pgive", invoke_without_command=True)
    async def pgive(self, ctx):
        await ctx.send("❌ Usage:\n• `!pgive user @user <time> <plan>`\n• `!pgive server <plan> [time]`\n• `!pgive su @user <plan> [time]`")

    @pgive.command(name="user")
    async def pgive_user(self, ctx, member: discord.Member = None, time_str: str = None, plan_name: str = None):
        if self.holders_col is None:
            return await ctx.send("❌ Database connection error!")

        if not member or not time_str or not plan_name:
            return await ctx.send("❌ Usage: `!pgive user @user <time> <plan_name>`")
        
        exp_dt = parse_duration(time_str)
        if exp_dt == -1:
            return await ctx.send("❌ Invalid Time Format! (Use: `1d`, `1m`, `1y`, or `perm`)")

        await self.holders_col.insert_one({
            "target_type": "user",
            "target_id": member.id,
            "plan_name": plan_name.lower(),
            "expires_at": exp_dt
        })

        await ctx.send(f"✅ **{member.display_name}** ko Global Premium **`{plan_name}`** de diya gaya hai.")

    @pgive.command(name="server")
    async def pgive_server(self, ctx, plan_name: str = None, time_str: str = "perm"):
        if self.holders_col is None:
            return await ctx.send("❌ Database connection error!")

        if not plan_name:
            return await ctx.send("❌ Usage: `!pgive server <plan_name> [time]`")

        exp_dt = parse_duration(time_str)
        await self.holders_col.insert_one({
            "target_type": "server",
            "guild_id": ctx.guild.id,
            "plan_name": plan_name.lower(),
            "expires_at": exp_dt
        })

        await ctx.send(f"🎉 Server **{ctx.guild.name}** ko Premium **`{plan_name}`** de diya gaya hai!")

    @pgive.command(name="su")
    async def pgive_su(self, ctx, member: discord.Member = None, plan_name: str = None, time_str: str = "perm"):
        if self.holders_col is None:
            return await ctx.send("❌ Database connection error!")

        if not member or not plan_name:
            return await ctx.send("❌ Usage: `!pgive su @user <plan_name> [time]`")

        exp_dt = parse_duration(time_str)
        await self.holders_col.insert_one({
            "target_type": "su",
            "target_id": member.id,
            "guild_id": ctx.guild.id,
            "plan_name": plan_name.lower(),
            "expires_at": exp_dt
        })

        await ctx.send(f"✅ **{member.display_name}** ko Single-Server Premium **`{plan_name}`** de diya gaya.")

    # 4. LIST PLANS
    @commands.command(name="plist")
    async def plist(self, ctx):
        if self.plans_col is None:
            return await ctx.send("❌ Database connection error!")

        cursor = self.plans_col.find({})
        rows = await cursor.to_list(length=None)

        if not rows:
            return await ctx.send("📑 Koi Premium Plan nahi hai!")

        embed = discord.Embed(title="📜 Premium Plans List", color=discord.Color.purple())
        for item in rows:
            name = item.get("plan_name", "")
            cmds = item.get("allowed_commands", "")
            embed.add_field(name=f"🔹 {name.upper()}", value=f"**Permissions:** `{cmds}`", inline=False)
        await ctx.send(embed=embed)

    # 5. FULL PREMIUM HELP COMMAND
    @commands.command(name="phelp")
    async def phelp(self, ctx):
        embed = discord.Embed(
            title="👑 Premium System Management Help",
            description="Bot Owner Premium commands aur unka exact usage details niche diye gaye hain:",
            color=discord.Color.gold()
        )
        embed.add_field(
            name="🔨 `!pcreate <plan_name>`",
            value="Dropdown UI se plan create karta hai aur permissions assign karta hai.\n*Supports All Commands (`*`) or multiple selections.*",
            inline=False
        )
        embed.add_field(
            name="➕ `!pcommand <plan_name> <perm>`",
            value="Direct command se kisi plan me extra permission add karta hai.\n*Example:* `!pcommand diamond botprofile` or `!pcommand diamond *`",
            inline=False
        )
        embed.add_field(
            name="🎁 `!pgive user @user <time> <plan>`",
            value="Kisi specific User ko poore Bot ke har server ke liye Global Premium deta hai.\n*Time Format:* `1d`, `1m`, `1y`, `perm`",
            inline=False
        )
        embed.add_field(
            name="🏰 `!pgive server <plan> [time]`",
            value="Jis Server me command run hoga, us poore server ke sabhi members ko premium feature ka access de deta hai.",
            inline=False
        )
        embed.add_field(
            name="👤 `!pgive su @user <plan> [time]`",
            value="Single User (SU) ko SIRF specific server me access deta hai.",
            inline=False
        )
        embed.add_field(
            name="📜 `!plist`",
            value="Database me majood saare Premium Plans aur unki Command Permissions ki list dikhata hai.",
            inline=False
        )
        embed.add_field(
            name="🔑 Available Permission Keys",
            value="• `spam` : For !spam & !spamstop\n• `botprofile` : For !serverpfp, !servernick, !serverb\n• `*` : All commands access",
            inline=False
        )
        embed.set_footer(text="Bot Owner Only Commands", icon_url=self.bot.user.display_avatar.url)
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(PremiumSystem(bot))
        
