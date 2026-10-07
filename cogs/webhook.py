import discord
from discord import app_commands
from discord.ext import commands


class Webhook(commands.Cog):
    """Send a webhook-style embed through the bot account."""

    webhook_group = app_commands.Group(
        name="webhook",
        description="Send webhook-style embeds",
    )

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @webhook_group.command(name="send", description="Send an embed to a channel")
    @app_commands.describe(
        text="Text to display in the embed",
        channel="Channel where the embed will be sent",
        imageurl="Direct URL of an image (optional)",
    )
    @app_commands.checks.has_permissions(manage_webhooks=True)
    async def send_embed(
        self,
        interaction: discord.Interaction,
        text: str,
        channel: discord.TextChannel,
        imageurl: str | None = None,
    ):
        if interaction.guild is None:
            await interaction.response.send_message(
                "This command can only be used in a server.", ephemeral=True
            )
            return

        if len(text) > 4096:
            await interaction.response.send_message(
                "Embed text must be 4096 characters or fewer.", ephemeral=True
            )
            return

        if imageurl:
            if not imageurl.startswith(("https://", "http://")):
                await interaction.response.send_message(
                    "Image URL must start with `https://` or `http://`.",
                    ephemeral=True,
                )
                return

        bot_member = interaction.guild.me
        if bot_member is None:
            await interaction.response.send_message(
                "I couldn't verify my permissions in this server.", ephemeral=True
            )
            return

        permissions = channel.permissions_for(bot_member)
        if not permissions.view_channel or not permissions.send_messages or not permissions.embed_links:
            await interaction.response.send_message(
                f"I need **View Channel**, **Send Messages**, and **Embed Links** in {channel.mention}.",
                ephemeral=True,
            )
            return

        embed = discord.Embed(description=text, color=discord.Color.blurple())
        if imageurl:
            embed.set_image(url=imageurl)

        try:
            await channel.send(embed=embed)
        except discord.Forbidden:
            await interaction.response.send_message(
                f"Discord denied permission to send an embed in {channel.mention}.",
                ephemeral=True,
            )
            return
        except discord.HTTPException:
            await interaction.response.send_message(
                "Discord couldn't send that embed. Check the image URL and try again.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            f"Embed sent to {channel.mention}.", ephemeral=True
        )

    async def cog_app_command_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ):
        if isinstance(error, app_commands.MissingPermissions):
            message = "You need the **Manage Webhooks** permission to use this command."
        else:
            message = "An error occurred while running `/webhook send`."

        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Webhook(bot))
