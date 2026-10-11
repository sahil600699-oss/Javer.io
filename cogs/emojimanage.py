"""Emoji/sticker manager for discord.py 2.4+.

Load extension as ``cogs.emojimanage``. No database or persistent storage.
Only server Administrators and the configured bot owner can run these commands.
The bot itself must have Manage Expressions permission in the target guild.
"""
from __future__ import annotations

import io
import re
from urllib.parse import urlparse

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

try:
    import config
except ImportError:
    config = None

_OWNER_VALUE = (getattr(config, "OWNER_ID", None) or getattr(config, "BOT_OWNER_ID", None)) if config else None
try:
    BOT_OWNER_ID = int(_OWNER_VALUE or 0)
except (TypeError, ValueError):
    BOT_OWNER_ID = 0

CUSTOM_EMOJI_RE = re.compile(r"<(?P<animated>a?):(?P<name>[A-Za-z0-9_]{2,32}):(?P<id>\d{15,22})>")
VALID_NAME_RE = re.compile(r"^[A-Za-z0-9_]{2,32}$")
MAX_DOWNLOAD_BYTES = 8 * 1024 * 1024
IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".apng")


class EmojiManage(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def allowed(self, ctx: commands.Context) -> bool:
        if ctx.guild is None:
            await ctx.send("❌ Ye command sirf server ke andar use ho sakti hai.")
            return False
        author = ctx.author
        is_owner = bool(BOT_OWNER_ID and author.id == BOT_OWNER_ID)
        is_admin = isinstance(author, discord.Member) and author.guild_permissions.administrator
        if not (is_owner or is_admin):
            await ctx.send("❌ Aapke paas permission nahi hai. Sirf server Administrator ya bot owner ye command use kar sakte hain.")
            return False
        return True

    async def can_manage_expressions(self, ctx: commands.Context) -> bool:
        me = ctx.guild.me if ctx.guild else None
        if me is None or not me.guild_permissions.manage_emojis_and_stickers:
            await ctx.send("❌ Bot ko is server mein **Manage Expressions** permission nahi hai. Bot ke role ko ye permission do.")
            return False
        return True

    async def download_url(self, url: str) -> bytes:
        timeout = aiohttp.ClientTimeout(total=20)
        headers = {"User-Agent": "DiscordEmojiManager/1.0"}
        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
            async with session.get(url, allow_redirects=True) as response:
                if response.status != 200:
                    raise ValueError(f"Image download nahi hui (HTTP {response.status}).")
                content_type = (response.headers.get("Content-Type") or "").lower()
                if not (content_type.startswith("image/") or "octet-stream" in content_type):
                    raise ValueError("Diya gaya link image file nahi lag raha.")
                if response.content_length is not None and response.content_length > MAX_DOWNLOAD_BYTES:
                    raise ValueError("Image 8 MB se chhoti honi chahiye.")
                data = await response.read()
        if not data:
            raise ValueError("Image file khaali hai.")
        if len(data) > MAX_DOWNLOAD_BYTES:
            raise ValueError("Image 8 MB se chhoti honi chahiye.")
        return data

    async def attachment_bytes(self, attachment: discord.Attachment) -> tuple[bytes, str]:
        if attachment.size and attachment.size > MAX_DOWNLOAD_BYTES:
            raise ValueError("Image 8 MB se chhoti honi chahiye.")
        filename = attachment.filename or "image.png"
        if not filename.lower().endswith(IMAGE_EXTENSIONS):
            raise ValueError("PNG, JPG, JPEG, GIF, WEBP ya APNG image use karo.")
        data = await attachment.read(use_cached=True)
        if not data:
            raise ValueError("Attachment khaali hai ya read nahi ho saka.")
        if len(data) > MAX_DOWNLOAD_BYTES:
            raise ValueError("Image 8 MB se chhoti honi chahiye.")
        return data, filename

    async def get_image(self, ctx: commands.Context, attachment: discord.Attachment | None = None,
                        target: discord.Message | None = None, emoji_text: str | None = None) -> tuple[bytes | None, str | None]:
        if attachment is not None:
            return await self.attachment_bytes(attachment)

        # For prefix commands, use an image attached to the command message first.
        current = getattr(ctx, "message", None)
        for message in (current, target):
            if message:
                for item in getattr(message, "attachments", []):
                    ctype = (item.content_type or "").lower()
                    if ctype.startswith("image/") or item.filename.lower().endswith(IMAGE_EXTENSIONS):
                        return await self.attachment_bytes(item)

        source_text = emoji_text or (target.content if target else "")
        match = CUSTOM_EMOJI_RE.search(source_text or "")
        if match:
            ext = "gif" if match.group("animated") else "png"
            url = f"https://cdn.discordapp.com/emojis/{match.group('id')}.{ext}?quality=lossless"
            return await self.download_url(url), f"{match.group('name')}.{ext}"

        if target:
            stickers = getattr(target, "stickers", []) or []
            if stickers:
                url = str(getattr(stickers[0], "url", "") or "")
                if url:
                    path = urlparse(url).path
                    ext = path.rsplit(".", 1)[-1].lower() if "." in path else "png"
                    if ext not in {"png", "apng", "gif", "webp"}:
                        ext = "png"
                    return await self.download_url(url), f"{stickers[0].name}.{ext}"
        return None, None

    async def replied_message(self, ctx: commands.Context, message_id: str | None = None) -> discord.Message | None:
        if message_id:
            try:
                return await ctx.channel.fetch_message(int(message_id))
            except (ValueError, discord.NotFound, discord.Forbidden, discord.HTTPException):
                return None
        reference = getattr(getattr(ctx, "message", None), "reference", None)
        if not reference or not reference.message_id:
            return None
        resolved = getattr(reference, "resolved", None)
        if isinstance(resolved, discord.Message):
            return resolved
        try:
            return await ctx.channel.fetch_message(reference.message_id)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            return None

    async def create_emoji(self, ctx: commands.Context, name: str, data: bytes) -> discord.Emoji:
        if not VALID_NAME_RE.fullmatch(name or ""):
            raise ValueError("Emoji name 2–32 characters ka ho; sirf letters, numbers aur underscore use karo.")
        return await ctx.guild.create_custom_emoji(name=name, image=data, reason=f"Added by {ctx.author} ({ctx.author.id})")

    async def create_sticker(self, ctx: commands.Context, name: str, emoji: str, description: str,
                             data: bytes, filename: str) -> discord.GuildSticker:
        if not VALID_NAME_RE.fullmatch(name or ""):
            raise ValueError("Sticker name 2–32 characters ka ho; sirf letters, numbers aur underscore use karo.")
        if not emoji or len(emoji) > 100:
            raise ValueError("Sticker ke liye associated emoji do, example: 🤣")
        if not description.strip():
            description = f"{name} sticker"
        if len(description) > 100:
            raise ValueError("Sticker description 100 characters se chhoti honi chahiye.")
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "png"
        if ext not in {"png", "apng", "gif", "webp", "json"}:
            ext = "png"
        file = discord.File(io.BytesIO(data), filename=f"{name}.{ext}")
        return await ctx.guild.create_sticker(name=name, description=description, emoji=emoji,
                                               file=file, reason=f"Added by {ctx.author} ({ctx.author.id})")

    async def show_ej_help(self, ctx: commands.Context):
        await ctx.send(
            "😀 **Emoji Manager**\n"
            "`!ej add <name> <custom_emoji>` — custom emoji copy karo; command ke saath image attach bhi kar sakte ho.\n"
            "`!ej save <name>` — emoji/image wale message par reply karke bhejo.\n"
            "`!ej delete <name>` — server ka emoji delete karo.\n"
            "Slash: `/ej add`, `/ej save`, `/ej delete`, `/ej help`.\n"
            "Note: Unicode emoji (🤣) ko custom server emoji file ki tarah upload nahi kar sakte."
        )

    async def show_sticker_help(self, ctx: commands.Context):
        await ctx.send(
            "🎨 **Sticker Manager**\n"
            "`!sticker add <name> <emoji> <description>` — image command ke saath attach karo; description ko quotes mein likho agar spaces hain.\n"
            "`!sticker save <name> <emoji> <description>` — image/sticker wale message par reply karo.\n"
            "`!sticker delete <name>` — server ka sticker delete karo.\n"
            "Slash: `/sticker add`, `/sticker save`, `/sticker delete`, `/sticker help`."
        )

    @commands.hybrid_group(name="ej", invoke_without_command=True, description="Emoji manager commands")
    async def ej(self, ctx: commands.Context):
        await self.show_ej_help(ctx)

    @ej.command(name="help", description="Show emoji manager help")
    async def ej_help(self, ctx: commands.Context):
        await self.show_ej_help(ctx)

    @ej.command(name="add", description="Add a custom emoji to this server")
    async def ej_add(self, ctx: commands.Context, name: str, emoji: str | None = None,
                     image: discord.Attachment | None = None):
        if not await self.allowed(ctx) or not await self.can_manage_expressions(ctx):
            return
        try:
            data, _ = await self.get_image(ctx, attachment=image, emoji_text=emoji)
            if not data:
                await ctx.send("❌ Custom emoji do ya image attach karo. Example: `!ej add Hahaha <:name:123456789012345678>`")
                return
            created = await self.create_emoji(ctx, name, data)
            await ctx.send(f"✅ Emoji add ho gaya: {created} (`{created.name}`).")
        except ValueError as exc:
            await ctx.send(f"❌ {exc}")
        except (discord.Forbidden, discord.HTTPException) as exc:
            await ctx.send(f"❌ Discord emoji add nahi kar saka: {exc}")
        except (aiohttp.ClientError, TimeoutError) as exc:
            await ctx.send(f"❌ Emoji image download nahi hui: {exc}")

    @ej.command(name="save", description="Save an emoji or image from a replied message")
    async def ej_save(self, ctx: commands.Context, name: str, message_id: str | None = None,
                      image: discord.Attachment | None = None):
        if not await self.allowed(ctx) or not await self.can_manage_expressions(ctx):
            return
        target = await self.replied_message(ctx, message_id)
        try:
            data, _ = await self.get_image(ctx, attachment=image, target=target)
            if not data:
                await ctx.send("❌ Prefix mein emoji/image wale message par reply karo. Slash command mein `message_id` ya `image` do.")
                return
            created = await self.create_emoji(ctx, name, data)
            await ctx.send(f"✅ Emoji save ho gaya: {created} (`{created.name}`).")
        except ValueError as exc:
            await ctx.send(f"❌ {exc}")
        except (discord.Forbidden, discord.HTTPException) as exc:
            await ctx.send(f"❌ Discord emoji save nahi kar saka: {exc}")
        except (aiohttp.ClientError, TimeoutError) as exc:
            await ctx.send(f"❌ Emoji image download nahi hui: {exc}")

    @ej.command(name="delete", description="Delete a server emoji by name")
    async def ej_delete(self, ctx: commands.Context, name: str):
        if not await self.allowed(ctx) or not await self.can_manage_expressions(ctx):
            return
        emoji = discord.utils.get(ctx.guild.emojis, name=name.strip(":"))
        if emoji is None:
            await ctx.send(f"❌ `{name}` naam ka emoji nahi mila. `!ej help` dekho.")
            return
        try:
            await emoji.delete(reason=f"Deleted by {ctx.author} ({ctx.author.id})")
            await ctx.send(f"🗑️ Emoji **{name}** delete ho gaya.")
        except (discord.Forbidden, discord.HTTPException) as exc:
            await ctx.send(f"❌ Emoji delete nahi hua: {exc}")

    @commands.hybrid_group(name="sticker", invoke_without_command=True, description="Sticker manager commands")
    async def sticker(self, ctx: commands.Context):
        await self.show_sticker_help(ctx)

    @sticker.command(name="help", description="Show sticker manager help")
    async def sticker_help(self, ctx: commands.Context):
        await self.show_sticker_help(ctx)

    @sticker.command(name="add", description="Create a server sticker from an attached image")
    async def sticker_add(self, ctx: commands.Context, name: str, emoji: str,
                          description: str = "Sticker", image: discord.Attachment | None = None):
        if not await self.allowed(ctx) or not await self.can_manage_expressions(ctx):
            return
        try:
            data, filename = await self.get_image(ctx, attachment=image)
            if not data:
                await ctx.send("❌ Image attach karo. Example: `!sticker add Hahaha 🤣 Funny` (description ek word; slash mein image option use karo).")
                return
            created = await self.create_sticker(ctx, name, emoji, description, data, filename or "image.png")
            await ctx.send(f"✅ Sticker add ho gaya: **{created.name}**.")
        except ValueError as exc:
            await ctx.send(f"❌ {exc}")
        except (discord.Forbidden, discord.HTTPException) as exc:
            await ctx.send(f"❌ Discord sticker add nahi kar saka: {exc}")
        except (aiohttp.ClientError, TimeoutError) as exc:
            await ctx.send(f"❌ Sticker image download nahi hui: {exc}")

    @sticker.command(name="save", description="Save an image or sticker from a replied message")
    async def sticker_save(self, ctx: commands.Context, name: str, emoji: str,
                           description: str = "Sticker", message_id: str | None = None,
                           image: discord.Attachment | None = None):
        if not await self.allowed(ctx) or not await self.can_manage_expressions(ctx):
            return
        target = await self.replied_message(ctx, message_id)
        try:
            data, filename = await self.get_image(ctx, attachment=image, target=target)
            if not data:
                await ctx.send("❌ Prefix mein image/sticker wale message par reply karo. Slash mein `message_id` ya `image` do.")
                return
            created = await self.create_sticker(ctx, name, emoji, description, data, filename or "image.png")
            await ctx.send(f"✅ Sticker save ho gaya: **{created.name}**.")
        except ValueError as exc:
            await ctx.send(f"❌ {exc}")
        except (discord.Forbidden, discord.HTTPException) as exc:
            await ctx.send(f"❌ Discord sticker save nahi kar saka: {exc}")
        except (aiohttp.ClientError, TimeoutError) as exc:
            await ctx.send(f"❌ Sticker image download nahi hui: {exc}")

    @sticker.command(name="delete", description="Delete a server sticker by name")
    async def sticker_delete(self, ctx: commands.Context, name: str):
        if not await self.allowed(ctx) or not await self.can_manage_expressions(ctx):
            return
        sticker = discord.utils.get(ctx.guild.stickers, name=name)
        if sticker is None:
            await ctx.send(f"❌ `{name}` naam ka sticker nahi mila. `!sticker help` dekho.")
            return
        try:
            await sticker.delete(reason=f"Deleted by {ctx.author} ({ctx.author.id})")
            await ctx.send(f"🗑️ Sticker **{name}** delete ho gaya.")
        except (discord.Forbidden, discord.HTTPException) as exc:
            await ctx.send(f"❌ Sticker delete nahi hua: {exc}")

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        # CommandNotFound is a bot-level event, so cog_command_error alone cannot catch it.
        if not isinstance(error, commands.CommandNotFound):
            return
        content = (getattr(getattr(ctx, "message", None), "content", "") or "").lower().strip()
        prefixes = ("!", ".", ",", "-", "?", "$", ";", "/", ":", "'")
        for prefix in prefixes:
            if content.startswith(prefix + "ej"):
                await self.show_ej_help(ctx)
                return
            if content.startswith(prefix + "sticker"):
                await self.show_sticker_help(ctx)
                return

    async def cog_command_error(self, ctx: commands.Context, error: commands.CommandError):
        error = getattr(error, "original", error)
        if isinstance(error, commands.CommandNotFound):
            content = (getattr(getattr(ctx, "message", None), "content", "") or "").lower()
            if content.startswith(("!ej", ".ej", ",ej", "-ej", "?ej", "$ej", ";ej", ":ej", "'ej")):
                await self.show_ej_help(ctx)
            elif "sticker" in content:
                await self.show_sticker_help(ctx)
            return
        if isinstance(error, (commands.MissingRequiredArgument, commands.BadArgument, commands.TooManyArguments)):
            cmd = ctx.command.qualified_name if ctx.command else "ej"
            root = "sticker" if cmd.startswith("sticker") else "ej"
            await ctx.send(f"❌ Command format galat hai. Sahi format: `!{cmd}`. Help: `!{root} help`.")
            return
        if isinstance(error, commands.NoPrivateMessage):
            await ctx.send("❌ Ye command sirf server ke andar use ho sakti hai.")
            return
        print(f"[EmojiManage] Prefix command error: {type(error).__name__}: {error}")
        await ctx.send("❌ Command chal nahi saki. `!ej help` ya `!sticker help` se sahi format dekho.")

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        original = getattr(error, "original", error)
        message = "❌ Slash command chal nahi saki. Command ke options check karke dobara try karo."
        if isinstance(original, app_commands.MissingPermissions):
            message = "❌ Aapke paas permission nahi hai. Sirf server Administrator ya bot owner ye command use kar sakte hain."
        elif isinstance(original, app_commands.TransformerError):
            message = "❌ Option ka format galat hai. `/ej help` ya `/sticker help` dekho."
        print(f"[EmojiManage] Slash command error: {type(original).__name__}: {original}")
        try:
            if interaction.response.is_done():
                await interaction.followup.send(message, ephemeral=True)
            else:
                await interaction.response.send_message(message, ephemeral=True)
        except discord.HTTPException:
            pass


async def setup(bot: commands.Bot):
    await bot.add_cog(EmojiManage(bot))
