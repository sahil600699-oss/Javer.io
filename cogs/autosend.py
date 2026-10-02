import discord
from discord.ext import commands

class AutoSend(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @property
    def db(self):
        return getattr(self.bot, "async_db", None)

    @property
    def tasks_col(self):
        return self.db["autosend_tasks"] if self.db is not None else None

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild or self.tasks_col is None:
            return

        # MongoDB se active task check karein
        task = await self.tasks_col.find_one({
            "guild_id": message.guild.id,
            "user_id": message.author.id
        })

        if task:
            try:
                await message.channel.send(f"{message.author.mention} {task['message']}")
            except Exception as e:
                print(f"AutoSend Error: {e}")

            new_amount = task["amount"] - 1

            if new_amount <= 0:
                await self.tasks_col.delete_one({
                    "guild_id": message.guild.id,
                    "user_id": message.author.id
                })
                await message.channel.send(f"✅ {message.author.mention} ke liye AutoSend process complete ho gaya hai!")
            else:
                await self.tasks_col.update_one(
                    {"guild_id": message.guild.id, "user_id": message.author.id},
                    {"$set": {"amount": new_amount}}
                )

    @commands.group(name="autosend", invoke_without_command=True)
    @commands.has_permissions(manage_messages=True)
    async def autosend_group(self, ctx, member: discord.Member = None, amount: int = None, *, custom_message: str = None):
        if self.tasks_col is None:
            return await ctx.send("❌ Database connection error!")

        if not member or not amount or not custom_message:
            await ctx.send("❓ Format: `!autosend @user [amount] [message]`\nHelp: `!autosend help`")
            return

        if amount <= 0:
            await ctx.send("❌ Amount positive number hona chahiye!")
            return

        await self.tasks_col.update_one(
            {"guild_id": ctx.guild.id, "user_id": member.id},
            {"$set": {
                "guild_id": ctx.guild.id,
                "user_id": member.id,
                "amount": amount,
                "message": custom_message
            }},
            upsert=True
        )

        embed = discord.Embed(
            title="🚀 AutoSend Activated!",
            description=f"**Target:** {member.mention}\n**Count:** `{amount}`\n**Message:** {custom_message}",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)

    @autosend_group.command(name="help")
    async def autosend_help(self, ctx):
        embed = discord.Embed(title="🤖 AutoSend Help", color=discord.Color.blue())
        embed.add_field(name="Set", value="`!autosend @user [amount] [message]`", inline=False)
        embed.add_field(name="Stop", value="`!autosendoff @user`", inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="autosendoff")
    @commands.has_permissions(manage_messages=True)
    async def autosend_off(self, ctx, member: discord.Member):
        if self.tasks_col is None:
            return await ctx.send("❌ Database connection error!")

        result = await self.tasks_col.delete_one({
            "guild_id": ctx.guild.id,
            "user_id": member.id
        })

        if result.deleted_count > 0:
            await ctx.send(f"🛑 **{member.display_name}** ke liye AutoSend turn off kar diya gaya hai.")
        else:
            await ctx.send(f"⚠️ **{member.display_name}** ke liye koi Active AutoSend nahi hai.")

async def setup(bot):
    await bot.add_cog(AutoSend(bot))
                              
