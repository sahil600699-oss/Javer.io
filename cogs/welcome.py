import discord
from discord.ext import commands

class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @property
    def welcome_col(self):
        db = getattr(self.bot, "async_db", None)
        return db["welcome_settings"] if db is not None else None

    async def get_settings(self, guild_id):
        col = self.welcome_col
        if col is None:
            return None
        return await col.find_one({"guild_id": guild_id})

    async def send_welcome(self, member, data):
        channel_id = data.get("channel_id")
        if not channel_id:
            print(f"[WELCOME] No channel configured: {member.guild.id}")
            return False
        try:
            channel = member.guild.get_channel(int(channel_id))
            if channel is None:
                channel = await self.bot.fetch_channel(int(channel_id))
        except Exception as e:
            print(f"[WELCOME] Channel error: {type(e).__name__}: {e}")
            return False
        if not isinstance(channel, discord.TextChannel):
            print("[WELCOME] Saved channel is not a text channel.")
            return False

        raw_desc = data.get("description") or "Welcome {user} to **{server}**!\nTotal Members: #{count}"
        description = (str(raw_desc)
            .replace("{user}", member.mention)
            .replace("{server}", member.guild.name)
            .replace("{count}", str(member.guild.member_count))
            .replace("{username}", member.display_name)
            .replace("{userid}", str(member.id)))

        embed = discord.Embed(
            title=data.get("title") or "✦ WELCOME ✦",
            description=description,
            color=discord.Color.blue())
        embed.set_thumbnail(url=member.display_avatar.url)
        if data.get("image_url"):
            embed.set_image(url=str(data["image_url"]))

        try:
            await channel.send(
                content=member.mention,
                embed=embed,
                allowed_mentions=discord.AllowedMentions(users=True, roles=False, everyone=False))
            print(f"[WELCOME] Sent welcome for {member} in #{channel.name}")
            return True
        except Exception as e:
            print(f"[WELCOME] Send error: {type(e).__name__}: {e}")
            return False

    @commands.hybrid_group(name="welcome", description="Configure the server welcome system.", invoke_without_command=True)
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def welcome(self, ctx):
        embed = discord.Embed(
            title="👋 Welcome System",
            description=(
                "`!welcome setup #channel` / `/welcome setup`\n"
                "`!welcome msg <text>` - Custom message\n"
                "`!welcome image <url>` - Welcome image\n"
                "`!welcome test` - Send a test\n"
                "`!welcome reset` - Remove settings"),
            color=discord.Color.blue())
        await ctx.send(embed=embed)

    @welcome.command(name="setup", description="Set the welcome channel.")
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def setup_cmd(self, ctx, channel: discord.TextChannel):
        col = self.welcome_col
        if col is None:
            return await ctx.send("❌ MongoDB connection is not available.")
        await col.update_one(
            {"guild_id": ctx.guild.id},
            {"$set": {"guild_id": ctx.guild.id, "channel_id": channel.id, "enabled": True}},
            upsert=True)
        await ctx.send(f"✅ Welcome channel set to {channel.mention}")

    @welcome.command(name="msg", description="Set the custom welcome message.")
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def set_msg(self, ctx, *, message: str):
        col = self.welcome_col
        if col is None:
            return await ctx.send("❌ MongoDB connection is not available.")
        await col.update_one(
            {"guild_id": ctx.guild.id},
            {"$set": {"description": message, "guild_id": ctx.guild.id}},
            upsert=True)
        await ctx.send(f"✅ Welcome message saved:\n> {message}")

    @welcome.command(name="image", description="Set a welcome image URL.")
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def set_image(self, ctx, url: str):
        col = self.welcome_col
        if col is None:
            return await ctx.send("❌ MongoDB connection is not available.")
        await col.update_one(
            {"guild_id": ctx.guild.id},
            {"$set": {"image_url": url, "guild_id": ctx.guild.id}},
            upsert=True)
        await ctx.send("✅ Welcome image URL saved.")

    @welcome.command(name="test", description="Send a welcome test.")
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def test_cmd(self, ctx):
        data = await self.get_settings(ctx.guild.id)
        if not data or not data.get("channel_id"):
            return await ctx.send("❌ Use `!welcome setup #channel` first.")
        ok = await self.send_welcome(ctx.author, data)
        await ctx.send("✅ Test welcome message sent." if ok else "❌ Could not send welcome. Check `[WELCOME]` logs.")

    @welcome.command(name="reset", description="Remove welcome settings.")
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def reset_welcome(self, ctx):
        col = self.welcome_col
        if col is None:
            return await ctx.send("❌ MongoDB connection is not available.")
        result = await col.delete_one({"guild_id": ctx.guild.id})
        await ctx.send("🗑️ Welcome settings removed." if result.deleted_count else "⚠️ No welcome settings were saved.")

    @commands.Cog.listener()
    async def on_member_join(self, member):
        print(f"[WELCOME] MEMBER JOIN: {member} ({member.id}) -> {member.guild.name} ({member.guild.id})")
        try:
            data = await self.get_settings(member.guild.id)
            if not data:
                print(f"[WELCOME] No settings for guild {member.guild.id}")
                return
            if data.get("enabled") is False:
                print(f"[WELCOME] Disabled for guild {member.guild.id}")
                return
            await self.send_welcome(member, data)
        except Exception as e:
            print(f"[WELCOME] Join handler error: {type(e).__name__}: {e}")

async def setup(bot):
    await bot.add_cog(Welcome(bot))
    print("[WELCOME] Welcome cog loaded successfully.")
