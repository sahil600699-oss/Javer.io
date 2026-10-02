import asyncio
import random

import discord
from discord.ext import commands


GAME_TIMEOUT = 600  # 10 minutes
GAME_END_DELAY = 3


class XOGame:
    def __init__(
        self,
        cog,
        channel,
        player_x,
        player_o=None,
        vs_bot=False
    ):
        self.cog = cog
        self.channel = channel

        self.player_x = player_x
        self.player_o = player_o
        self.vs_bot = vs_bot

        self.board = [" "] * 9
        self.turn = "X"

        self.message = None
        self.finished = False

        # Prevent two button clicks at exactly the same time.
        self.lock = asyncio.Lock()

    # ========================================================
    # PLAYER HELPERS
    # ========================================================

    def get_player(self, symbol):
        if symbol == "X":
            return self.player_x

        return self.player_o

    def get_symbol(self, user_id):
        if self.player_x and user_id == self.player_x.id:
            return "X"

        if (
            not self.vs_bot
            and self.player_o
            and user_id == self.player_o.id
        ):
            return "O"

        return None

    def is_player(self, user_id):
        if self.player_x and user_id == self.player_x.id:
            return True

        if (
            not self.vs_bot
            and self.player_o
            and user_id == self.player_o.id
        ):
            return True

        return False

    # ========================================================
    # WIN / DRAW
    # ========================================================

    def get_result(self):
        winning_lines = (
            (0, 1, 2),
            (3, 4, 5),
            (6, 7, 8),
            (0, 3, 6),
            (1, 4, 7),
            (2, 5, 8),
            (0, 4, 8),
            (2, 4, 6),
        )

        for a, b, c in winning_lines:
            if (
                self.board[a] != " "
                and self.board[a] == self.board[b]
                and self.board[b] == self.board[c]
            ):
                return self.board[a]

        if " " not in self.board:
            return "DRAW"

        return None

    # ========================================================
    # BOARD
    # ========================================================

    def board_text(self):
        cells = []

        for value in self.board:
            if value == "X":
                cells.append("❌")
            elif value == "O":
                cells.append("⭕")
            else:
                cells.append(" ")

        return (
            f"{cells[0] or '1'} │ {cells[1] or '2'} │ {cells[2] or '3'}\n"
            "───┼───┼───\n"
            f"{cells[3] or '4'} │ {cells[4] or '5'} │ {cells[5] or '6'}\n"
            "───┼───┼───\n"
            f"{cells[6] or '7'} │ {cells[7] or '8'} │ {cells[8] or '9'}"
        )

    # ========================================================
    # EMBED
    # ========================================================

    def create_embed(self, status=None):
        embed = discord.Embed(
            title="🎮 Tic-Tac-Toe",
            color=discord.Color.blurple()
        )

        embed.description = (
            f"```text\n"
            f"{self.board_text()}\n"
            f"```"
        )

        # ----------------------------
        # Custom status
        # ----------------------------

        if status == "ended":
            embed.add_field(
                name="🛑 Game Ended",
                value="Game manually end kar di gayi.",
                inline=False
            )

        elif status == "expired":
            embed.add_field(
                name="⏰ Game Expired",
                value="10 minutes complete ho gaye. Game khatam ho gayi.",
                inline=False
            )

        else:
            result = self.get_result()

            if result == "X":
                embed.add_field(
                    name="🏆 Winner",
                    value=f"❌ {self.player_x.mention}",
                    inline=False
                )

            elif result == "O":
                if self.vs_bot:
                    winner = "🤖 Bot"
                else:
                    winner = self.player_o.mention

                embed.add_field(
                    name="🏆 Winner",
                    value=f"⭕ {winner}",
                    inline=False
                )

            elif result == "DRAW":
                embed.add_field(
                    name="🤝 Result",
                    value="Game Draw ho gaya!",
                    inline=False
                )

            else:
                current_player = self.get_player(self.turn)

                if self.turn == "O" and self.vs_bot:
                    turn_text = "🤖 **Bot ki turn hai...**"
                else:
                    symbol = "❌" if self.turn == "X" else "⭕"
                    turn_text = (
                        f"{current_player.mention} ki turn hai "
                        f"**{symbol}**"
                    )

                embed.add_field(
                    name="🎯 Current Turn",
                    value=turn_text,
                    inline=False
                )

        # ----------------------------
        # Players
        # ----------------------------

        if self.vs_bot:
            players = (
                f"❌ {self.player_x.mention}\n"
                f"⭕ 🤖 Bot"
            )
        else:
            players = (
                f"❌ {self.player_x.mention}\n"
                f"⭕ {self.player_o.mention}"
            )

        embed.add_field(
            name="👥 Players",
            value=players,
            inline=False
        )

        embed.set_footer(
            text="⏱️ Game limit: 10 minutes • !xo end to end the game"
        )

        return embed

    # ========================================================
    # USER MOVE
    # ========================================================

    async def make_move(self, interaction, position):
        async with self.lock:

            if self.finished:
                await interaction.response.send_message(
                    "❌ Ye game already khatam ho chuki hai.",
                    ephemeral=True
                )
                return

            # --------------------------------------------
            # Only actual players can play
            # --------------------------------------------

            symbol = self.get_symbol(interaction.user.id)

            if symbol is None:
                await interaction.response.send_message(
                    "❌ Tum is game ke player nahi ho.",
                    ephemeral=True
                )
                return

            # --------------------------------------------
            # Turn check
            # --------------------------------------------

            if symbol != self.turn:
                await interaction.response.send_message(
                    "⏳ Abhi tumhari turn nahi hai.",
                    ephemeral=True
                )
                return

            # --------------------------------------------
            # Position check
            # --------------------------------------------

            if self.board[position] != " ":
                await interaction.response.send_message(
                    "❌ Ye box already filled hai.",
                    ephemeral=True
                )
                return

            # --------------------------------------------
            # Make move
            # --------------------------------------------

            self.board[position] = symbol

            result = self.get_result()

            # --------------------------------------------
            # Win / Draw
            # --------------------------------------------

            if result:
                self.finished = True
                self.cog.remove_game(self.channel.id)

                await interaction.response.edit_message(
                    embed=self.create_embed(),
                    view=None
                )

                return

            # --------------------------------------------
            # Change turn
            # --------------------------------------------

            self.turn = "O" if self.turn == "X" else "X"

            new_view = XOView(self)

            await interaction.response.edit_message(
                embed=self.create_embed(),
                view=new_view
            )

        # Bot turn outside lock
        if (
            self.vs_bot
            and self.turn == "O"
            and not self.finished
        ):
            await asyncio.sleep(0.7)
            await self.bot_move()

    # ========================================================
    # BOT MOVE
    # ========================================================

    async def bot_move(self):
        async with self.lock:

            if self.finished:
                return

            if self.turn != "O":
                return

            move = self.find_best_move()

            if move is None:
                return

            self.board[move] = "O"

            result = self.get_result()

            if result:
                self.finished = True
                self.cog.remove_game(self.channel.id)

                try:
                    await self.message.edit(
                        embed=self.create_embed(),
                        view=None
                    )
                except (
                    discord.NotFound,
                    discord.HTTPException
                ):
                    pass

                return

            self.turn = "X"

            new_view = XOView(self)

            try:
                await self.message.edit(
                    embed=self.create_embed(),
                    view=new_view
                )
            except (
                discord.NotFound,
                discord.HTTPException
            ):
                pass

    # ========================================================
    # BOT AI
    # ========================================================

    def find_best_move(self):
        empty = [
            i
            for i, value in enumerate(self.board)
            if value == " "
        ]

        if not empty:
            return None

        # 1. Bot can win
        for move in empty:
            self.board[move] = "O"

            if self.get_result() == "O":
                self.board[move] = " "
                return move

            self.board[move] = " "

        # 2. Block player
        for move in empty:
            self.board[move] = "X"

            if self.get_result() == "X":
                self.board[move] = " "
                return move

            self.board[move] = " "

        # 3. Center
        if self.board[4] == " ":
            return 4

        # 4. Corners
        corners = [0, 2, 6, 8]

        available_corners = [
            move
            for move in corners
            if self.board[move] == " "
        ]

        if available_corners:
            return random.choice(available_corners)

        # 5. Any remaining move
        return random.choice(empty)

    # ========================================================
    # END GAME
    # ========================================================

    async def end_game(self, status="ended"):
        if self.finished and status != "expired":
            return

        self.finished = True
        self.cog.remove_game(self.channel.id)

        if self.message is None:
            return

        try:
            await self.message.edit(
                embed=self.create_embed(status=status),
                view=None
            )

        except discord.NotFound:
            return

        except discord.HTTPException:
            return

        # Delete after a short delay
        await asyncio.sleep(GAME_END_DELAY)

        try:
            await self.message.delete()
        except (
            discord.NotFound,
            discord.HTTPException
        ):
            pass


# ============================================================
# BUTTON
# ============================================================

class XOButton(discord.ui.Button):

    def __init__(self, game, position):
        super().__init__(
            label=str(position + 1),
            style=discord.ButtonStyle.secondary,
            row=position // 3
        )

        self.game = game
        self.position = position

    async def callback(self, interaction):
        await self.game.make_move(
            interaction,
            self.position
        )


# ============================================================
# VIEW
# ============================================================

class XOView(discord.ui.View):

    def __init__(self, game):
        # Discord persistent button view
        super().__init__(timeout=None)

        for position in range(9):

            button = XOButton(
                game,
                position
            )

            value = game.board[position]

            if value == "X":
                button.label = "❌"
                button.style = discord.ButtonStyle.danger

            elif value == "O":
                button.label = "⭕"
                button.style = discord.ButtonStyle.success

            self.add_item(button)


# ============================================================
# COG
# ============================================================

class XO(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

        # channel_id -> XOGame
        self.games = {}

    # ========================================================
    # !xo / ?xo / .xo / $xo
    # ========================================================

    @commands.command(name="xo")
    @commands.cooldown(
        1,
        2,
        commands.BucketType.user
    )
    async def xo(self, ctx, opponent=None):

        # ----------------------------------------------------
        # !xo end
        # ----------------------------------------------------

        if opponent is not None and opponent.lower() == "end":

            game = self.games.get(ctx.channel.id)

            if game is None or game.finished:
                await ctx.send(
                    "❌ Is channel mein koi active XO game nahi hai."
                )
                return

            # Only players can end the game.
            if not game.is_player(ctx.author.id):
                await ctx.send(
                    "❌ Sirf XO game ke players mein se koi "
                    "ek game end kar sakta hai."
                )
                return

            await game.end_game(status="ended")
            return

        # ----------------------------------------------------
        # Existing game
        # ----------------------------------------------------

        existing_game = self.games.get(ctx.channel.id)

        if existing_game and not existing_game.finished:
            await ctx.send(
                "❌ Is channel mein already ek XO game chal rahi hai.\n"
                "Game khatam karne ke liye `!xo end` use karo."
            )
            return

        # Remove stale game
        if existing_game:
            self.remove_game(ctx.channel.id)

        # ----------------------------------------------------
        # No argument
        # ----------------------------------------------------

        if opponent is None:
            await ctx.send(
                "🎮 **Tic-Tac-Toe / XO**\n\n"
                "`!xo bot` → Bot ke saath khelo\n"
                "`!xo @user` → Kisi user ke saath khelo\n"
                "`!xo end` → Current game end karo"
            )
            return

        # ----------------------------------------------------
        # BOT GAME
        # ----------------------------------------------------

        if opponent.lower() == "bot":

            game = XOGame(
                cog=self,
                channel=ctx.channel,
                player_x=ctx.author,
                player_o=self.bot.user,
                vs_bot=True
            )

            try:
                message = await ctx.send(
                    embed=game.create_embed(),
                    view=XOView(game)
                )

            except discord.HTTPException as error:

                # IMPORTANT:
                # Game active list mein tab tak nahi jayegi
                # jab tak message successfully send na ho.
                self.remove_game(ctx.channel.id)

                try:
                    await ctx.send(
                        "❌ XO game start nahi ho saki.\n"
                        f"Discord error: `{error}`"
                    )
                except discord.HTTPException:
                    pass

                return

            # Message successfully created.
            game.message = message

            # Now mark the game as active.
            self.games[ctx.channel.id] = game

            # Start 10-minute timer.
            asyncio.create_task(
                self.timeout_game(game)
            )

            return

        # ----------------------------------------------------
        # USER GAME
        # ----------------------------------------------------

        if not ctx.message.mentions:
            await ctx.send(
                "❌ Kisi user ko mention karo.\n\n"
                "Example:\n"
                "`!xo @User`"
            )
            return

        opponent_user = ctx.message.mentions[0]

        # Self game
        if opponent_user.id == ctx.author.id:
            await ctx.send(
                "❌ Tum khud ke saath XO nahi khel sakte."
            )
            return

        # Bot mention
        if opponent_user.bot:
            await ctx.send(
                "❌ Bot ke saath khelne ke liye:\n"
                "`!xo bot`"
            )
            return

        game = XOGame(
            cog=self,
            channel=ctx.channel,
            player_x=ctx.author,
            player_o=opponent_user,
            vs_bot=False
        )

        try:
            message = await ctx.send(
                embed=game.create_embed(),
                view=XOView(game)
            )

        except discord.HTTPException as error:

            self.remove_game(ctx.channel.id)

            try:
                await ctx.send(
                    "❌ XO game start nahi ho saki.\n"
                    f"Discord error: `{error}`"
                )
            except discord.HTTPException:
                pass

            return

        # Message successfully created.
        game.message = message

        # Now mark game active.
        self.games[ctx.channel.id] = game

        # Start 10-minute timer.
        asyncio.create_task(
            self.timeout_game(game)
        )

    # ========================================================
    # 10 MINUTE TIMEOUT
    # ========================================================

    async def timeout_game(self, game):

        await asyncio.sleep(GAME_TIMEOUT)

        if game.finished:
            return

        await game.end_game(
            status="expired"
        )

    # ========================================================
    # REMOVE GAME
    # ========================================================

    def remove_game(self, channel_id):
        self.games.pop(
            channel_id,
            None
        )

    # ========================================================
    # COMMAND ERROR HANDLER
    # ========================================================

    @xo.error
    async def xo_error(self, ctx, error):

        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(
                f"⏳ Thoda wait karo. Dubara try karo "
                f"`{error.retry_after:.1f}s` baad."
            )
            return

        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(
                "❌ Use: `!xo bot` ya `!xo @User`"
            )
            return

        if isinstance(error, commands.BadArgument):
            await ctx.send(
                "❌ Invalid argument. Use: `!xo bot` ya `!xo @User`"
            )
            return

        print(
            f"[XO ERROR] {type(error).__name__}: {error}"
        )

        try:
            await ctx.send(
                "❌ XO command mein unexpected error aa gaya. "
                "Console mein error check karo."
            )
        except discord.HTTPException:
            pass


# ============================================================
# SETUP
# ============================================================

async def setup(bot):
    await bot.add_cog(XO(bot))
