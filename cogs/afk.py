import discord
from discord.ext import commands
import sqlite3
from datetime import datetime

DB_NAME = "afk_system.db"


def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """CREATE TABLE IF NOT EXISTS afk_users (
                guild_id INTEGER,
                user_id INTEGER,
                reason TEXT,
                afk_since DATETIME,
                PRIMARY KEY (guild_id, user_id)
            )"""
        )
        conn.commit()


init_db()


class AFK(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return

        # Ignore the AFK command itself for ANY configured prefix.
        # This prevents ?afk, -afk, !afk, etc. from triggering
        # the "Welcome back" message immediately.
        ctx = await self.bot.get_context(message)
        if ctx.command and ctx.command.name == "afk":
            return

        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()

            # Check if the message author is currently AFK.
            cursor.execute(
                "SELECT reason FROM afk_users WHERE guild_id = ? AND user_id = ?",
                (message.guild.id, message.author.id),
            )

            if cursor.fetchone():
                cursor.execute(
                    "DELETE FROM afk_users WHERE guild_id = ? AND user_id = ?",
                    (message.guild.id, message.author.id),
                )
                conn.commit()

                await message.channel.send(
                    f"👋 Welcome back {message.author.mention}! AFK Removed."
                )

            # Check whether the message mentions any AFK users.
            if message.mentions:
                for member in message.mentions:
                    cursor.execute(
                        "SELECT reason FROM afk_users WHERE guild_id = ? AND user_id = ?",
                        (message.guild.id, member.id),
                    )
                    row = cursor.fetchone()

                    if row:
                        await message.channel.send(
                            f"⚠️ **{member.display_name}** is AFK: {row[0]}"
                        )
                        break

    @commands.hybrid_command(name="afk")
    async def afk_cmd(self, ctx, *, reason: str = "AFK"):
        current_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO afk_users VALUES (?, ?, ?, ?)",
                (ctx.guild.id, ctx.author.id, reason, current_time),
            )
            conn.commit()

        await ctx.send(
            f"💤 {ctx.author.mention} is now AFK: {reason}"
        )


async def setup(bot):
    await bot.add_cog(AFK(bot))
