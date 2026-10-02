import discord
from discord.ext import commands

try:
    from config import OWNER_ID
except ImportError:
    OWNER_ID = None


class AutoResponder(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @property
    def db(self):
        return getattr(self.bot, "async_db", None)

    @property
    def responses_col(self):
        return self.db["auto_responses"] if self.db is not None else None

    @property
    def reactions_col(self):
        return self.db["auto_reactions"] if self.db is not None else None

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild or self.db is None:
            return

        msg_content = message.content.lower().strip()

        # Check Auto Reaction
        rec_row = await self.reactions_col.find_one({
            "guild_id": message.guild.id,
            "trigger_text": msg_content
        })
        if rec_row and "emoji" in rec_row:
            try:
                await message.add_reaction(rec_row["emoji"])
            except Exception:
                pass

        # Check Auto Response
        res_row = await self.responses_col.find_one({
            "guild_id": message.guild.id,
            "trigger_text": msg_content
        })
        if res_row and "response_text" in res_row:
            try:
                await message.channel.send(res_row["response_text"])
            except Exception:
                pass

    @commands.group(name="autoresponse", aliases=["autoadd"], invoke_without_command=True)
    async def auto_response_group(self, ctx, *, content: str = None):
        if self.responses_col is None:
            return await ctx.send("❌ Database connection error!")

        if content is None:
            embed = discord.Embed(
                title="🤖 AutoResponder & Reaction Help System",
                description="Server ke liye custom auto-replies aur reactions set karein.",
                color=discord.Color.blue()
            )
            embed.add_field(
                name="💬 Auto Response Set Karein",
                value="`!autoresponse trigger | reply text`\n*Example:* `!autoresponse hi | Hello! Kaise ho?`",
                inline=False
            )
            embed.add_field(
                name="🎭 Auto Reaction Set Karein",
                value="`!autorec <emoji> <trigger text>`\n*Example:* `!autorec ❤️ thanks`",
                inline=False
            )
            embed.add_field(
                name="🗑️ Delete Commands",
                value="`!autodel <trigger>` - Auto-Response remove karein.\n`!autorecdel <trigger>` - Auto-Reaction remove karein.",
                inline=False
            )
            embed.add_field(
                name="📋 All Triggers List",
                value="`!autolist` - Saare active auto-responses aur reactions dikhaega.",
                inline=False
            )
            embed.set_footer(text=f"Requested by {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
            return await ctx.send(embed=embed)

        if "|" not in content:
            return await ctx.send("❌ Usage: `!autoresponse trigger | response`")
        
        trigger, response = [item.strip() for item in content.split("|", 1)]
        
        await self.responses_col.update_one(
            {"guild_id": ctx.guild.id, "trigger_text": trigger.lower()},
            {"$set": {"guild_id": ctx.guild.id, "trigger_text": trigger.lower(), "response_text": response}},
            upsert=True
        )
        await ctx.send(f"✅ Set Auto-Response for `{trigger}`")

    @commands.command(name="autorec", aliases=["autoreaction"])
    async def auto_reaction(self, ctx, emoji: str = None, *, trigger: str = None):
        if self.reactions_col is None:
            return await ctx.send("❌ Database connection error!")

        if not emoji or not trigger:
            return await ctx.send("❌ Usage: `!autorec <emoji> <trigger text>`\n*Example:* `!autorec ❤️ thanks`")

        await self.reactions_col.update_one(
            {"guild_id": ctx.guild.id, "trigger_text": trigger.lower()},
            {"$set": {"guild_id": ctx.guild.id, "trigger_text": trigger.lower(), "emoji": emoji}},
            upsert=True
        )

        await ctx.send(f"Confirm {emoji} {trigger}")

    @commands.command(name="autorecdel")
    async def auto_rec_del(self, ctx, *, trigger: str = None):
        if self.reactions_col is None:
            return await ctx.send("❌ Database connection error!")

        if not trigger:
            return await ctx.send("❌ Usage: `!autorecdel <trigger>`")

        trig_lower = trigger.lower().strip()
        result = await self.reactions_col.delete_one({"guild_id": ctx.guild.id, "trigger_text": trig_lower})

        if result.deleted_count > 0:
            await ctx.send(f"🗑️ Auto-Reaction trigger `{trigger}` delete kar diya gaya!")
        else:
            await ctx.send(f"⚠️ `{trigger}` naam ka koi Auto-Reaction nahi mila.")

    @commands.command(name="autodel")
    async def auto_del(self, ctx, *, trigger: str = None):
        if self.responses_col is None or self.reactions_col is None:
            return await ctx.send("❌ Database connection error!")

        if not trigger:
            return await ctx.send("❌ Usage: `!autodel <trigger>`")

        trig_lower = trigger.lower().strip()
        res_del = await self.responses_col.delete_one({"guild_id": ctx.guild.id, "trigger_text": trig_lower})
        rec_del = await self.reactions_col.delete_one({"guild_id": ctx.guild.id, "trigger_text": trig_lower})

        if res_del.deleted_count > 0 or rec_del.deleted_count > 0:
            await ctx.send(f"🗑️ Trigger `{trigger}` successfully delete kar diya gaya!")
        else:
            await ctx.send(f"⚠️ `{trigger}` naam ka koi trigger nahi mila.")

    @commands.command(name="autolist")
    async def auto_list(self, ctx):
        if self.responses_col is None or self.reactions_col is None:
            return await ctx.send("❌ Database connection error!")

        responses = await self.responses_col.find({"guild_id": ctx.guild.id}).to_list(length=None)
        reactions = await self.reactions_col.find({"guild_id": ctx.guild.id}).to_list(length=None)

        if not responses and not reactions:
            return await ctx.send("📑 Is server me koi Auto-Response ya Reaction set nahi hai!")

        embed = discord.Embed(title=f"📜 Active Auto-Triggers — {ctx.guild.name}", color=discord.Color.gold())

        if responses:
            res_text = "\n".join([f"• `{r['trigger_text']}` ➔ {r['response_text']}" for r in responses])
            embed.add_field(name="💬 Auto Responses (!autoadd / !autoresponse)", value=res_text[:1024], inline=False)

        if reactions:
            rec_text = "\n".join([f"• `{r['trigger_text']}` ➔ {r['emoji']}" for r in reactions])
            embed.add_field(name="🎭 Auto Reactions (!autorec)", value=rec_text[:1024], inline=False)

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(AutoResponder(bot))
    
