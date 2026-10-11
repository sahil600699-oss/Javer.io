import asyncio
import io
import re
from datetime import datetime, timezone
from urllib.parse import urlparse

import aiohttp
import discord
from discord.ext import commands

try:
    import config
    BOT_OWNER_ID = int(getattr(config, "OWNER_ID", 0) or 0)
except (ImportError, TypeError, ValueError):
    BOT_OWNER_ID = 0


CUSTOM_EMOJI_RE = re.compile(r"<(?P<animated>a?):(?P<name>[A-Za-z0-9_]{2,32}):(?P<id>\d{15,22})>")
VALID_NAME_RE = re.compile(r"^[A-Za-z0-9_]{2,32}$")
MAX_DOWNLOAD_BYTES = 8 * 1024 * 1024


class EmojiManage(commands.Cog):
    """Manage server emojis and stickers with prefix and slash commands."""

    def __init__(self, bot):
        self.bot = bot

    @property
    def log_col(self):
        database = getattr(self.bot, "async_db", None)
        return database["emoji_manager_logs"] if database is not None else None

    async def log_action(self, guild, user, action, asset_type, name, asset_id=None, status="success", details=None):
        collection = self.log_col
        if collection is None or guild is None:
            return
        try:
            await collection.insert_one({
                "guild_id": guild.id,
                "user_id": user.id if user else None,
                "action": action,
                "asset_type": asset_type,
                "name": name,
                "asset_id": asset_id,
                "status": status,
                "details": details,
                "created_at": datetime.now(timezone.utc),
            })
        except Exception as exc:
            print(f"[EmojiManage] Mongo log error: {exc}")

    async def ensure_manage(self, ctx):
        """Only server Administrators or configured bot owner can run commands.

        The bot itself must still have Manage Expressions in the target server;
        Discord does not allow a bot to bypass its own server permissions.
        """
        if not ctx.guild:
            await ctx.send("❌ This command can only be used in a server.")
            return False

        is_bot_owner = BOT_OWNER_ID != 0 and ctx.author.id == BOT_OWNER_ID
        member = ctx.author
        is_admin = isinstance(member, discord.Member) and member.guild_permissions.administrator
        if not (is_bot_owner or is_admin):
            await ctx.send("❌ Only server **Administrators** or the **bot owner** can use Emoji/Sticker Manager.")
            return False

        me = ctx.guild.me
        if me is None or not me.guild_permissions.manage_emojis_and_stickers:
            await ctx.send("❌ I need **Manage Expressions** permission in this server to add/delete emojis or stickers.")
            return False
        return True

    async def replied_message(self, ctx, message_id=None):
        if message_id:
            try:
                return await ctx.channel.fetch_message(int(message_id))
            except (ValueError, discord.HTTPException, discord.NotFound, discord.Forbidden):
                return None
        message = getattr(ctx, "message", None)
        reference = getattr(message, "reference", None)
        if not reference:
            return None
        resolved = getattr(reference, "resolved", None)
        if isinstance(resolved, discord.Message):
            return resolved
        if reference.message_id:
            try:
                return await ctx.channel.fetch_message(reference.message_id)
            except (discord.HTTPException, discord.NotFound, discord.Forbidden):
                return None
        return None

    async def get_image_bytes(self, ctx, target_message=None):
        # Prefer an image attached to the command message, then to the replied-to message.
        candidates = []
        message = getattr(ctx, "message", None)
        if message and getattr(message, "attachments", None):
            candidates.extend(message.attachments)
        if target_message and getattr(target_message, "attachments", None):
            candidates.extend(target_message.attachments)

        for attachment in candidates:
            content_type = (attachment.content_type or "").lower()
            filename = attachment.filename or "upload.png"
            if content_type.startswith("image/") or filename.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".webp", ".apng")):
                try:
                    data = await attachment.read()
                    if data:
                        return data, filename
                except discord.HTTPException:
                    continue

        # If a custom emoji is present in the replied-to message, download its CDN asset.
        if target_message:
            match = CUSTOM_EMOJI_RE.search(target_message.content or "")
            if match:
                ext = "gif" if match.group("animated") else "png"
                url = f"https://cdn.discordapp.com/emojis/{match.group('id')}.{ext}?quality=lossless"
                try:
                    return await self.download_url(url), f"{match.group('name')}.{ext}"
                except Exception:
                    pass

            # A custom sticker in a replied-to message can be copied if Discord exposes its asset URL.
            stickers = getattr(target_message, "stickers", None)
            if stickers:
                sticker = stickers[0]
                try:
                    fetched = await sticker.fetch()
                    url = str(getattr(fetched, "url", "") or getattr(sticker, "url", ""))
                    if url:
                        ext = os_path_extension(url) or "png"
                        return await self.download_url(url), f"{getattr(sticker, 'name', 'sticker')}.{ext}"
                except Exception:
                    pass
        return None, None

    async def download_url(self, url):
        timeout = aiohttp.ClientTimeout(total=15)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as response:
                if response.status != 200:
                    raise ValueError(f"Download failed (HTTP {response.status}).")
                length = response.content_length
                if length and length > MAX_DOWNLOAD_BYTES:
                    raise ValueError("File is too large.")
                data = await response.read()
                if len(data) > MAX_DOWNLOAD_BYTES:
                    raise ValueError("File is too large (8 MB maximum).")
                return data

    async def resolve_emoji_image(self, ctx, emoji_text=None, target_message=None):
        if emoji_text:
            match = CUSTOM_EMOJI_RE.fullmatch(emoji_text.strip())
            if match:
                ext = "gif" if match.group("animated") else "png"
                url = f"https://cdn.discordapp.com/emojis/{match.group('id')}.{ext}?quality=lossless"
                data = await self.download_url(url)
                return data, f"{match.group('name')}.{ext}"
            # Unicode emoji are not image uploads and cannot be made into custom server emojis.
        return await self.get_image_bytes(ctx, target_message)

    async def create_emoji(self, ctx, name, data, filename):
        if not VALID_NAME_RE.fullmatch(name):
            raise ValueError("Name must be 2–32 characters and use only letters, numbers, or underscores.")
        if len(data) > MAX_DOWNLOAD_BYTES:
            raise ValueError("Image is too large (8 MB maximum).")
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "png"
        if ext not in {"png", "jpg", "jpeg", "gif", "webp"}:
            ext = "png"
        file = discord.File(io.BytesIO(data), filename=f"{name}.{ext}")
        return await ctx.guild.create_custom_emoji(name=name, image=data, reason=f"Added by {ctx.author} ({ctx.author.id})")

    async def create_sticker(self, ctx, name, emoji, description, data, filename):
        if not VALID_NAME_RE.fullmatch(name):
            raise ValueError("Name must be 2–32 characters and use only letters, numbers, or underscores.")
        if not emoji or len(emoji) > 100:
            raise ValueError("Please provide an associated emoji, e.g. 🤣.")
        description = (description or "").strip() or f"{name} sticker"
        description = description[:100]
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "png"
        if ext not in {"png", "apng", "json", "gif"}:
            ext = "png"
        upload = discord.File(io.BytesIO(data), filename=f"{name}.{ext}")
        return await ctx.guild.create_sticker(
            name=name,
            description=description,
            emoji=emoji,
            file=upload,
            reason=f"Added by {ctx.author} ({ctx.author.id})",
        )

    @commands.hybrid_group(name="ej", invoke_without_command=True, description="Manage server emojis")
    @commands.guild_only()
    async def ej_group(self, ctx):
        await ctx.send(
            "😀 **Emoji Manager**\n"
            "`!ej add <name> <custom emoji>` or attach an image\n"
            "`!ej save <name>` — reply to a custom emoji/image message\n"
            "`!ej delete [name]` — reply to a custom emoji or enter its name\n"
            "Slash commands: `/ej add`, `/ej save`, `/ej delete`."
        )

    @ej_group.command(name="add", description="Add a custom emoji or attached image to this server")
    async def ej_add(self, ctx, name: str, emoji: str = None, image: discord.Attachment = None):
        if not await self.ensure_manage(ctx):
            return
        try:
            if image is not None:
                data, filename = await image.read(), image.filename
            else:
                data, filename = await self.resolve_emoji_image(ctx, emoji)
            if not data:
                if emoji and not CUSTOM_EMOJI_RE.fullmatch(emoji.strip()):
                    return await ctx.send("❌ Unicode emojis (like 😭) cannot be uploaded as server custom emojis. Use a custom Discord emoji or attach an image.")
                return await ctx.send("❌ Attach an image, or provide a custom Discord emoji such as `<:name:id>`.")
            created = await self.create_emoji(ctx, name, data, filename)
            await self.log_action(ctx.guild, ctx.author, "add", "emoji", created.name, created.id)
            await ctx.send(f"✅ Added emoji {created} as **`{created.name}`**.")
        except discord.HTTPException as exc:
            await self.log_action(ctx.guild, ctx.author, "add", "emoji", name, status="failed", details=str(exc)[:500])
            await ctx.send(f"❌ Discord couldn't add that emoji: {exc}")
        except (ValueError, aiohttp.ClientError) as exc:
            await ctx.send(f"❌ {exc}")

    @ej_group.command(name="save", description="Save an emoji or image from a replied-to message")
    async def ej_save(self, ctx, name: str, message_id: str = None, image: discord.Attachment = None):
        if not await self.ensure_manage(ctx):
            return
        target = await self.replied_message(ctx, message_id)
        if image is None and target is None and not (getattr(getattr(ctx, "message", None), "attachments", None)):
            return await ctx.send("❌ Reply to a message containing a custom emoji/image. For slash, provide its message ID or attach an image.")
        try:
            if image is not None:
                data, filename = await image.read(), image.filename
            else:
                data, filename = await self.resolve_emoji_image(ctx, target_message=target)
            if not data:
                return await ctx.send("❌ I couldn't find a custom emoji or image in that message. Unicode emojis can't be uploaded as custom emojis.")
            created = await self.create_emoji(ctx, name, data, filename)
            await self.log_action(ctx.guild, ctx.author, "save", "emoji", created.name, created.id, details=f"source_message_id={target.id}" if target else None)
            await ctx.send(f"✅ Saved emoji {created} as **`{created.name}`**.")
        except discord.HTTPException as exc:
            await self.log_action(ctx.guild, ctx.author, "save", "emoji", name, status="failed", details=str(exc)[:500])
            await ctx.send(f"❌ Discord couldn't save that emoji: {exc}")
        except (ValueError, aiohttp.ClientError) as exc:
            await ctx.send(f"❌ {exc}")

    @ej_group.command(name="delete", description="Delete a server emoji by replying to it or entering its name")
    async def ej_delete(self, ctx, name: str = None, message_id: str = None):
        if not await self.ensure_manage(ctx):
            return
        target = await self.replied_message(ctx, message_id)
        emoji_id = None
        if target:
            match = CUSTOM_EMOJI_RE.search(target.content or "")
            if match:
                emoji_id = int(match.group("id"))
        emoji_obj = discord.utils.get(ctx.guild.emojis, id=emoji_id) if emoji_id else None
        if emoji_obj is None and name:
            emoji_obj = discord.utils.get(ctx.guild.emojis, name=name)
        if emoji_obj is None:
            return await ctx.send("❌ Reply to a message containing this server's custom emoji, or use `!ej delete <emoji_name>`.")
        try:
            emoji_name, emoji_id = emoji_obj.name, emoji_obj.id
            await emoji_obj.delete(reason=f"Deleted by {ctx.author} ({ctx.author.id})")
            await self.log_action(ctx.guild, ctx.author, "delete", "emoji", emoji_name, emoji_id)
            await ctx.send(f"🗑️ Deleted emoji **`{emoji_name}`**.")
        except discord.HTTPException as exc:
            await self.log_action(ctx.guild, ctx.author, "delete", "emoji", emoji_obj.name, emoji_obj.id, status="failed", details=str(exc)[:500])
            await ctx.send(f"❌ Couldn't delete that emoji: {exc}")

    @commands.hybrid_group(name="sticker", invoke_without_command=True, description="Manage server stickers")
    @commands.guild_only()
    async def sticker_group(self, ctx):
        await ctx.send(
            "🎨 **Sticker Manager**\n"
            "`!sticker add <name> <emoji> <description>` — attach an image to the command\n"
            "`!sticker save <name> <emoji> <description>` — reply to a sticker/image message\n"
            "`!sticker delete [name]` — reply to a sticker or enter its name\n"
            "Slash commands: `/sticker add`, `/sticker save`, `/sticker delete`."
        )

    @sticker_group.command(name="add", description="Turn an attached image into a server sticker")
    async def sticker_add(self, ctx, name: str, emoji: str, image: discord.Attachment = None, *, description: str = ""):
        if not await self.ensure_manage(ctx):
            return
        if image is not None:
            data, filename = await image.read(), image.filename
        else:
            data, filename = await self.get_image_bytes(ctx)
        if not data:
            return await ctx.send("❌ Attach the image to the same message as the command. Example: `!sticker add Hahaha 🤣 Funny reaction`")
        try:
            created = await self.create_sticker(ctx, name, emoji, description, data, filename)
            await self.log_action(ctx.guild, ctx.author, "add", "sticker", created.name, created.id)
            await ctx.send(f"✅ Added sticker **`{created.name}`** {created}")
        except discord.HTTPException as exc:
            await self.log_action(ctx.guild, ctx.author, "add", "sticker", name, status="failed", details=str(exc)[:500])
            await ctx.send(f"❌ Discord couldn't add that sticker: {exc}")
        except ValueError as exc:
            await ctx.send(f"❌ {exc}")

    @sticker_group.command(name="save", description="Save a sticker or image from a replied-to message")
    async def sticker_save(self, ctx, name: str, emoji: str, message_id: str = None, image: discord.Attachment = None, *, description: str = ""):
        if not await self.ensure_manage(ctx):
            return
        target = await self.replied_message(ctx, message_id)
        if image is not None:
            data, filename = await image.read(), image.filename
        elif target is not None:
            data, filename = await self.get_image_bytes(ctx, target)
        else:
            return await ctx.send("❌ Reply to a message containing the image/sticker. For slash, provide its message ID or attach an image.")
        if not data:
            return await ctx.send("❌ I couldn't download an image from that message. Unicode emoji alone can't be converted into a sticker.")
        try:
            created = await self.create_sticker(ctx, name, emoji, description, data, filename)
            await self.log_action(ctx.guild, ctx.author, "save", "sticker", created.name, created.id, details=f"source_message_id={target.id}")
            await ctx.send(f"✅ Saved sticker **`{created.name}`** {created}")
        except discord.HTTPException as exc:
            await self.log_action(ctx.guild, ctx.author, "save", "sticker", name, status="failed", details=str(exc)[:500])
            await ctx.send(f"❌ Discord couldn't save that sticker: {exc}")
        except ValueError as exc:
            await ctx.send(f"❌ {exc}")

    @sticker_group.command(name="delete", description="Delete a server sticker by replying to it or entering its name")
    async def sticker_delete(self, ctx, name: str = None, message_id: str = None):
        if not await self.ensure_manage(ctx):
            return
        target = await self.replied_message(ctx, message_id)
        sticker_obj = None
        if target and getattr(target, "stickers", None):
            sticker_id = target.stickers[0].id
            sticker_obj = discord.utils.get(ctx.guild.stickers, id=sticker_id)
        if sticker_obj is None and name:
            sticker_obj = discord.utils.get(ctx.guild.stickers, name=name)
        if sticker_obj is None:
            return await ctx.send("❌ Reply to a message containing this server's sticker, or use `!sticker delete <sticker_name>`.")
        try:
            sticker_name, sticker_id = sticker_obj.name, sticker_obj.id
            await sticker_obj.delete(reason=f"Deleted by {ctx.author} ({ctx.author.id})")
            await self.log_action(ctx.guild, ctx.author, "delete", "sticker", sticker_name, sticker_id)
            await ctx.send(f"🗑️ Deleted sticker **`{sticker_name}`**.")
        except discord.HTTPException as exc:
            await self.log_action(ctx.guild, ctx.author, "delete", "sticker", sticker_obj.name, sticker_obj.id, status="failed", details=str(exc)[:500])
            await ctx.send(f"❌ Couldn't delete that sticker: {exc}")


def os_path_extension(url):
    path = urlparse(url).path
    return path.rsplit(".", 1)[-1].lower() if "." in path else "png"


async def setup(bot):
    await bot.add_cog(EmojiManage(bot))
