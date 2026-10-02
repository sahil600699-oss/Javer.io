import discord
from discord.ext import commands
import aiohttp
import asyncio

class Utility(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Helper: Fetch image bytes safely
    async def get_image_bytes(self, ctx, url: str = None):
        if ctx.message.attachments:
            url = ctx.message.attachments[0].url
        
        if not url:
            return None

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        return await resp.read()
        except Exception as e:
            print(f"Image fetch error: {e}")
        return None

    # ==========================================
    # USER AVATAR COMMAND (!av / !avatar / !pfp)
    # ==========================================
    @commands.command(name="av", aliases=["avatar", "pfp"])
    async def user_avatar(self, ctx, member: discord.Member = None):
        user = member or ctx.author
        avatar_url = user.display_avatar.url

        embed = discord.Embed(
            title=f"📸 {user.display_name}'s Avatar",
            color=discord.Color.blue()
        )
        embed.set_image(url=avatar_url)
        embed.add_field(name="🔗 Direct Link", value=f"[Download Avatar]({avatar_url})")
        await ctx.send(embed=embed)

    # ==========================================
    # USER BANNER COMMAND (!banner)
    # ==========================================
    @commands.command(name="banner")
    async def user_banner(self, ctx, member: discord.Member = None):
        target = member or ctx.author
        
        try:
            # User object fetch mandatory to load profile banner
            user = await self.bot.fetch_user(target.id)

            if not user.banner:
                return await ctx.send(f"❌ **{user.display_name}** ke paas koi profile banner nahi hai!")

            banner_url = user.banner.url
            embed = discord.Embed(
                title=f"🖼️ {user.display_name}'s Banner",
                color=discord.Color.purple()
            )
            embed.set_image(url=banner_url)
            embed.add_field(name="🔗 Direct Link", value=f"[Download Banner]({banner_url})")
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"❌ Error fetching banner: {e}")

    # ==========================================
    # 1. BOT SERVER AVATAR CHANGE (!serverpfp)
    # ==========================================
    @commands.command(name="serverpfp")
    async def server_pfp(self, ctx, url: str = None):
        if not ctx.author.guild_permissions.administrator:
            return await ctx.send("⛔ Is command ko use karne ke liye `Administrator` permission chahiye!")

        img_bytes = await self.get_image_bytes(ctx, url)
        if not img_bytes:
            return await ctx.send("❌ Image attach karein ya direct image link dein!")

        try:
            # Note: Global bot avatar update
            await self.bot.user.edit(avatar=img_bytes)
            await ctx.send("✅ **Bot ka Profile Picture (Avatar) change kar diya gaya hai!**")
        except Exception as e:
            await ctx.send(f"❌ Error: {e}")

    # ==========================================
    # 2. BOT SERVER NICKNAME CHANGE (!servernick)
    # ==========================================
    @commands.command(name="servernick")
    @commands.has_permissions(manage_nicknames=True)
    async def server_nick(self, ctx, *, new_nick: str = None):
        if not new_nick:
            return await ctx.send("❌ Usage: `!servernick <new_name>`")

        try:
            await ctx.guild.me.edit(nick=new_nick)
            await ctx.send(f"✅ **Is Server me Bot ka Nickname badal kar `{new_nick}` kar diya gaya!**")
        except Exception as e:
            await ctx.send(f"❌ Error: {e}")

    # ==========================================
    # 3. BOT BANNER CHANGE (!serverb / !serverbanner)
    # ==========================================
    @commands.command(name="serverb", aliases=["serverbanner"])
    async def server_banner(self, ctx, url: str = None):
        if not ctx.author.guild_permissions.administrator:
            return await ctx.send("⛔ Is command ko use karne ke liye `Administrator` permission chahiye!")

        img_bytes = await self.get_image_bytes(ctx, url)
        if not img_bytes:
            return await ctx.send("❌ Banner Image attach karein ya link dein!")

        try:
            await self.bot.user.edit(banner=img_bytes)
            await ctx.send("🖼️ **Bot ka Banner successfully update kar diya gaya hai!**")
        except Exception as e:
            await ctx.send(f"❌ Error: {e}")

async def setup(bot):
    await bot.add_cog(Utility(bot))
        
