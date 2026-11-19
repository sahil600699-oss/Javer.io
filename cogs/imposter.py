import asyncio
import random
import discord
from discord.ext import commands

WORD_PAIRS = [
    ("Hand", "Leg"), ("Pen", "Pencil"), ("Laptop", "Mobile"),
    ("Chair", "Sofa"), ("Door", "Window"), ("Shirt", "T-Shirt"),
    ("Shoes", "Socks"), ("Wallet", "Bag"), ("Book", "Notebook"),
    ("Clock", "Watch"), ("Key", "Lock"), ("Mirror", "Glass"),
    ("Bed", "Pillow"), ("Fan", "AC"), ("TV", "Monitor"),
    ("Earphones", "Headphones"), ("Charger", "Cable"), ("Camera", "Phone"),
    ("Comb", "Brush"), ("Soap", "Shampoo"), ("Towel", "Napkin"),
    ("Bottle", "Glass"), ("Plate", "Bowl"), ("Spoon", "Fork"),
    ("Bucket", "Mug"), ("Umbrella", "Raincoat"), ("Ring", "Chain"),
    ("Glasses", "Sunglasses"), ("Light", "Candle"), ("Battery", "Cell"),
    ("Tea", "Coffee"), ("Apple", "Mango"), ("Burger", "Pizza"),
    ("Samosa", "Kachori"), ("Momo", "Spring Roll"), ("Cake", "Pastry"),
    ("Ice Cream", "Kulfi"), ("Milk", "Curd"), ("Paneer", "Cheese"),
    ("Chai", "Green Tea"), ("Pepsi", "Coke"), ("Water", "Juice"),
    ("Roti", "Paratha"), ("Biryani", "Pulao"), ("Noodles", "Pasta"),
    ("Chocolate", "Candy"), ("Biscuit", "Cookie"), ("Gulab Jamun", "Rasgulla"),
    ("Banana", "Papaya"), ("Grapes", "Orange"), ("Potato", "Onion"),
    ("Tomato", "Cucumber"), ("Butter", "Ghee"), ("Popcorn", "Chips"),
    ("Sandwich", "Toast"), ("Dosa", "Idli"), ("Soup", "Stew"),
    ("Jalebi", "Imarti"), ("Omelette", "Boiled Egg"),
    ("Cat", "Dog"), ("Lion", "Tiger"), ("Sun", "Moon"),
    ("River", "Ocean"), ("Tree", "Plant"), ("Horse", "Donkey"),
    ("Cow", "Buffalo"), ("Crow", "Pigeon"), ("Eagle", "Hawk"),
    ("Snake", "Lizard"), ("Fish", "Shark"), ("Monkey", "Chimpanzee"),
    ("Bear", "Panda"), ("Wolf", "Fox"), ("Rain", "Storm"),
    ("Mountain", "Hill"), ("Rose", "Lotus"), ("Star", "Planet"),
    ("Fire", "Smoke"), ("Ice", "Snow"),
    ("Car", "Bike"), ("Bus", "Train"), ("Aeroplane", "Helicopter"),
    ("Ship", "Boat"), ("Scooter", "Bicycle"), ("Auto", "Taxi"),
    ("School", "College"), ("Hospital", "Clinic"), ("Hotel", "Restaurant"),
    ("Park", "Garden"), ("Mall", "Market"), ("Cinema", "Theatre"),
    ("Airport", "Railway Station"), ("Village", "City"), ("Road", "Bridge"),
    ("Football", "Cricket"), ("Badminton", "Tennis"), ("PUBG", "Free Fire"),
    ("YouTube", "Instagram"), ("WhatsApp", "Telegram"), ("GTA", "Cyberpunk"),
    ("Keyboard", "Mouse"), ("PS5", "Xbox"), ("Google", "Bing"),
    ("Spotify", "Wynk"), ("Netflix", "Prime"), ("Chess", "Ludo"),
    ("Valorant", "CSGO"), ("Instagram", "Snapchat"), ("Wi-Fi", "Bluetooth"),
]

MIN_PLAYERS = 3
MAX_PLAYERS = 10
TURN_SECONDS = 60
VOTE_SECONDS = 120
PURPLE = discord.Color.from_rgb(112, 72, 255)
DARK = discord.Color.from_rgb(31, 35, 56)
BLUE = discord.Color.from_rgb(50, 110, 255)
GREEN = discord.Color.from_rgb(46, 204, 113)
RED = discord.Color.from_rgb(235, 55, 75)
GOLD = discord.Color.from_rgb(255, 190, 55)


def clean_name(member):
    return discord.utils.escape_markdown(member.display_name)[:80]


def make_lobby_embeds(host, players, locked=False):
    embed = discord.Embed(
        title="✦ IMPOSTER  •  FIND THE IMPOSTER",
        description=("A social deduction game. One player has a different secret word.\n"
                     "The host is automatically added to the lobby."),
        color=PURPLE,
    )
    embed.set_author(name="IMPOSTER • PREMIUM GAME", icon_url=host.display_avatar.url)
    embed.set_thumbnail(url=host.display_avatar.url)
    embed.add_field(name="👑 HOST", value=f"{host.mention}\n**GAME CREATOR**", inline=True)
    embed.add_field(name="👥 PLAYERS", value=f"**{len(players)} / {MAX_PLAYERS}**", inline=True)
    embed.add_field(name="🎮 STATUS", value="🔒 Lobby Locked" if locked else "🟢 Lobby Open", inline=True)
    embed.add_field(name="📌 PLAYER LIMIT", value=f"Minimum **{MIN_PLAYERS}**  •  Maximum **{MAX_PLAYERS}**", inline=False)
    embed.add_field(name="JOINED PLAYERS", value="\n".join(f"{i}. {p.mention}" for i, p in enumerate(players, 1)) or "No players yet", inline=False)
    embed.set_footer(text="Only the host can start, cancel or kick players.")
    embeds = [embed]
    for player in players:
        if player.id == host.id:
            continue
        card = discord.Embed(description=f"**{clean_name(player)}**", color=DARK)
        card.set_thumbnail(url=player.display_avatar.url)
        card.set_author(name="PLAYER", icon_url=player.display_avatar.url)
        embeds.append(card)
    return embeds[:10]


class LobbyView(discord.ui.View):
    def __init__(self, cog, host):
        super().__init__(timeout=None)
        self.cog = cog
        self.host = host
        self.players = [host]
        self.message = None
        self.locked = False

    async def refresh(self):
        if self.message:
            await self.message.edit(embeds=make_lobby_embeds(self.host, self.players), view=self)

    @discord.ui.button(label="Join Game", emoji="📥", style=discord.ButtonStyle.success, custom_id="imposter:lobby:join")
    async def join(self, interaction, button):
        if self.locked:
            return await interaction.response.send_message("This lobby is locked.", ephemeral=True)
        if any(p.id == interaction.user.id for p in self.players):
            return await interaction.response.send_message("You are already in this lobby.", ephemeral=True)
        if len(self.players) >= MAX_PLAYERS:
            return await interaction.response.send_message("This lobby is full.", ephemeral=True)
        self.players.append(interaction.user)
        await self.refresh()
        await interaction.response.send_message("You joined the game lobby.", ephemeral=True)

    @discord.ui.button(label="Leave Game", emoji="🚪", style=discord.ButtonStyle.secondary, custom_id="imposter:lobby:leave")
    async def leave(self, interaction, button):
        if self.locked:
            return await interaction.response.send_message("This lobby is locked.", ephemeral=True)
        if interaction.user.id == self.host.id:
            return await interaction.response.send_message("The host cannot leave. Use Cancel Game instead.", ephemeral=True)
        player = next((p for p in self.players if p.id == interaction.user.id), None)
        if player is None:
            return await interaction.response.send_message("You are not in this lobby.", ephemeral=True)
        self.players.remove(player)
        await self.refresh()
        await interaction.response.send_message("You left the game lobby.", ephemeral=True)

    @discord.ui.button(label="Start Game", emoji="🚀", style=discord.ButtonStyle.primary, custom_id="imposter:lobby:start")
    async def start(self, interaction, button):
        if interaction.user.id != self.host.id:
            return await interaction.response.send_message("Only the host can start this game.", ephemeral=True)
        if len(self.players) < MIN_PLAYERS:
            return await interaction.response.send_message(f"At least {MIN_PLAYERS} players are required.", ephemeral=True)
        await interaction.response.defer(ephemeral=True)
        await self.cog.begin_game(interaction, self)

    @discord.ui.button(label="Kick Player", emoji="👢", style=discord.ButtonStyle.danger, custom_id="imposter:lobby:kick")
    async def kick(self, interaction, button):
        if interaction.user.id != self.host.id:
            return await interaction.response.send_message("Only the host can kick players.", ephemeral=True)
        choices = [p for p in self.players if p.id != self.host.id]
        if not choices:
            return await interaction.response.send_message("There are no players to kick.", ephemeral=True)
        await interaction.response.send_message("Select a player to remove.", view=KickPlayerView(self, choices), ephemeral=True)

    @discord.ui.button(label="Cancel Game", emoji="✖️", style=discord.ButtonStyle.danger, custom_id="imposter:lobby:cancel")
    async def cancel(self, interaction, button):
        if interaction.user.id != self.host.id:
            return await interaction.response.send_message("Only the host can cancel this game.", ephemeral=True)
        await interaction.response.defer(ephemeral=True)
        await self.cog.cancel_game(self.host.id)
        await interaction.followup.send("The game has been cancelled.", ephemeral=True)


class KickSelect(discord.ui.Select):
    def __init__(self, lobby, players):
        self.lobby = lobby
        options = [discord.SelectOption(label=clean_name(p)[:100], value=str(p.id)) for p in players]
        super().__init__(placeholder="Choose a player to kick", min_values=1, max_values=1, options=options)

    async def callback(self, interaction):
        if interaction.user.id != self.lobby.host.id:
            return await interaction.response.send_message("Only the host can use this control.", ephemeral=True)
        target_id = int(self.values[0])
        target = next((p for p in self.lobby.players if p.id == target_id), None)
        if target is None or target.id == self.lobby.host.id:
            return await interaction.response.send_message("That player is no longer available.", ephemeral=True)
        self.lobby.players.remove(target)
        await self.lobby.refresh()
        await interaction.response.send_message(f"Removed **{clean_name(target)}** from the lobby.", ephemeral=True)


class KickPlayerView(discord.ui.View):
    def __init__(self, lobby, players):
        super().__init__(timeout=30)
        self.add_item(KickSelect(lobby, players))


class TurnView(discord.ui.View):
    def __init__(self, host):
        super().__init__(timeout=TURN_SECONDS)
        self.host_id = host.id
        self.skipped = False

    @discord.ui.button(label="Skip Turn", emoji="⏭️", style=discord.ButtonStyle.primary)
    async def skip(self, interaction, button):
        if interaction.user.id != self.host_id:
            return await interaction.response.send_message("Only the host can skip the current turn.", ephemeral=True)
        self.skipped = True
        await interaction.response.send_message("The current turn has been skipped.", ephemeral=True)
        self.stop()


class VoteSelect(discord.ui.Select):
    def __init__(self, alive_players):
        options = [discord.SelectOption(label=clean_name(p)[:100], value=str(p.id), description="Cast or change your vote") for p in alive_players]
        super().__init__(placeholder="Select a player to vote for…", min_values=1, max_values=1, options=options)

    async def callback(self, interaction):
        view = self.view
        voter_id = interaction.user.id
        if voter_id not in view.voter_ids:
            return await interaction.response.send_message("You are not eligible to vote.", ephemeral=True)
        target_id = int(self.values[0])
        if target_id not in view.eligible_ids:
            return await interaction.response.send_message("That player cannot be voted for.", ephemeral=True)
        view.votes[voter_id] = target_id
        await interaction.response.send_message("Your vote has been recorded. You may change it before voting closes.", ephemeral=True)
        await view.refresh_counter()
        if len(view.votes) >= len(view.voter_ids):
            view.stop()


class MeetingView(discord.ui.View):
    def __init__(self, alive_players):
        super().__init__(timeout=VOTE_SECONDS)
        self.voter_ids = {p.id for p in alive_players}
        self.eligible_ids = {p.id for p in alive_players}
        self.votes = {}  # voter_id -> target_id; never shown publicly
        self.message = None
        self.add_item(VoteSelect(alive_players))

    async def refresh_counter(self):
        if self.message:
            embed = self.message.embeds[0]
            embed.set_field_at(1, name="📊 VOTES CAST", value=f"**{len(self.votes)}/{len(self.voter_ids)}** players have voted", inline=True)
            await self.message.edit(embed=embed, view=self)


def make_voting_roster(alive_players):
    embeds = []
    for player in alive_players:
        card = discord.Embed(title=clean_name(player), description="Eligible player", color=BLUE)
        card.set_thumbnail(url=player.display_avatar.url)
        card.set_author(name="EMERGENCY MEETING", icon_url=player.display_avatar.url)
        embeds.append(card)
    return embeds[:10]


class Imposter(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_games = {}  # host_id -> in-memory game state; no stats or persistence
        self._locks = {}

    def lock_for(self, host_id):
        return self._locks.setdefault(host_id, asyncio.Lock())

    async def safe_delete(self, message):
        try:
            await message.delete()
        except (discord.NotFound, discord.Forbidden, discord.HTTPException, AttributeError):
            pass

    async def cleanup_messages(self, game):
        for message in list(game.get("messages", [])):
            await self.safe_delete(message)
        game["messages"] = []

    async def track_send(self, channel, game, *, content=None, embed=None, embeds=None, view=None):
        kwargs = {"content": content, "view": view}
        if embeds is not None:
            kwargs["embeds"] = embeds
        elif embed is not None:
            kwargs["embed"] = embed
        message = await channel.send(**kwargs)
        game.setdefault("messages", []).append(message)
        return message

    @commands.hybrid_command(name="imposter")
    async def create_imposter(self, ctx, option: str = None):
        if (option or "").lower() != "create":
            return await ctx.send("Use `!imposter create` to open a new game lobby. Help: `!impohelp`.")
        if ctx.author.id in self.active_games:
            return await ctx.send("You already have an active Imposter game. Finish or cancel it first.")
        lobby = LobbyView(self, ctx.author)
        message = await ctx.send(embeds=make_lobby_embeds(ctx.author, lobby.players), view=lobby)
        lobby.message = message
        self.active_games[ctx.author.id] = {
            "host": ctx.author, "channel": ctx.channel, "lobby": lobby,
            "messages": [message], "status": "lobby"
        }

    async def begin_game(self, interaction, lobby):
        host_id = lobby.host.id
        async with self.lock_for(host_id):
            game = self.active_games.get(host_id)
            if not game or game.get("status") != "lobby":
                return await interaction.followup.send("This game is no longer available.", ephemeral=True)
            players = list(lobby.players)
            if not MIN_PLAYERS <= len(players) <= MAX_PLAYERS:
                return await interaction.followup.send(f"The game requires {MIN_PLAYERS}–{MAX_PLAYERS} players.", ephemeral=True)

            # Test every player's DM before assigning any secret word.
            dm_channels = {}
            failed = []
            probes = []
            for player in players:
                try:
                    dm = await player.create_dm()
                    probe = await dm.send("Imposter DM check. This temporary message will be deleted.")
                    probes.append(probe)
                    dm_channels[player.id] = dm
                except (discord.Forbidden, discord.HTTPException):
                    failed.append(player)
            for probe in probes:
                await self.safe_delete(probe)
            if failed:
                names = ", ".join(clean_name(p) for p in failed)
                return await interaction.followup.send(
                    "**GAME CANNOT START — DIRECT MESSAGES ARE CLOSED OR UNAVAILABLE.**\n"
                    f"Please ask these players to enable DMs from this server: **{names}**.\n"
                    "Everyone must open their DMs before the host can start the game.", ephemeral=True)

            lobby.locked = True
            for item in lobby.children:
                item.disabled = True
            try:
                await lobby.message.edit(embeds=make_lobby_embeds(lobby.host, players, locked=True), view=lobby)
            except discord.HTTPException:
                pass
            # The lobby message is intentionally removed as soon as the game begins.
            await self.safe_delete(lobby.message)
            game["messages"] = [m for m in game["messages"] if m.id != lobby.message.id]

            imposter = random.choice(players)
            innocent_word, imposter_word = random.choice(WORD_PAIRS)
            delivered = []
            try:
                for player in players:
                    word = imposter_word if player.id == imposter.id else innocent_word
                    secret_embed = discord.Embed(
                        title="🤫 YOUR SECRET WORD",
                        description=f"# **{discord.utils.escape_markdown(word)}**\n\nKeep this word private. Do not show or tell it to anyone.",
                        color=PURPLE,
                    )
                    secret_embed.set_footer(text="IMPOSTER • Private role message")
                    delivered.append(await dm_channels[player.id].send(embed=secret_embed))
            except (discord.Forbidden, discord.HTTPException):
                for sent in delivered:
                    await self.safe_delete(sent)
                await self.cleanup_messages(game)
                self.active_games.pop(host_id, None)
                return await interaction.followup.send(
                    "**GAME CANCELLED.** A player's DM became unavailable while secret words were being delivered. "
                    "No game has started. Please check everyone's DM settings and create a new lobby.", ephemeral=True)

            game.update({
                "players": players, "alive": players.copy(), "imposter": imposter,
                "innocent_word": innocent_word, "imposter_word": imposter_word,
                "eliminated": [], "status": "turns", "round": 1,
                "messages": [], "turn_view": None, "meeting_view": None,
            })
            await interaction.followup.send("All secret words have been delivered privately. The game is starting!", ephemeral=True)
            await self.run_description_cycle(host_id)

    async def run_description_cycle(self, host_id):
        game = self.active_games.get(host_id)
        if not game:
            return
        if len(game["alive"]) <= 2:
            return await self.finish_game(host_id, imposters_win=True)
        game["status"] = "turns"
        order = list(game["alive"])
        random.shuffle(order)
        game["turn_order"] = order
        host = game["host"]
        for index, player in enumerate(order, 1):
            if host_id not in self.active_games or game["status"] != "turns":
                return
            if player not in game["alive"]:
                continue
            embed = discord.Embed(
                title=f"🗣️ DESCRIPTION PHASE  •  ROUND {game['round']}",
                description=f"{player.mention}\n\n**It's your turn! Describe your word without saying it directly.**\n\n⏳ You have **60 seconds**. Your secret word was sent only to your Discord DMs.",
                color=PURPLE,
            )
            embed.set_thumbnail(url=player.display_avatar.url)
            embed.add_field(name="CURRENT PLAYER", value=player.mention, inline=True)
            embed.add_field(name="TURN", value=f"{index}/{len(order)}", inline=True)
            embed.add_field(name="TIME LIMIT", value="01:00", inline=True)
            embed.set_footer(text="The host can skip this turn. The secret word is never shown here.")
            view = TurnView(host)
            game["turn_view"] = view
            game["turn_player_id"] = player.id
            message = await self.track_send(game["channel"], game, embed=embed, view=view)
            await view.wait()
            game.pop("turn_view", None)
            game.pop("turn_player_id", None)
            try:
                await message.edit(view=None)
            except discord.HTTPException:
                pass
        if host_id in self.active_games and game["status"] == "turns":
            await self.run_meeting(host_id)

    @commands.hybrid_command(name="next")
    async def next_turn_cmd(self, ctx):
        game = self.active_games.get(ctx.author.id)
        if not game or game.get("status") != "turns":
            return await ctx.send("You do not have an active description turn to skip.")
        view = game.get("turn_view")
        if view is None:
            return await ctx.send("There is no active player turn right now.")
        view.skipped = True
        view.stop()
        await ctx.send("The host skipped the current player's turn.")

    async def run_meeting(self, host_id):
        game = self.active_games.get(host_id)
        if not game:
            return
        game["status"] = "meeting"
        alive = list(game["alive"])
        roster = make_voting_roster(alive)
        if roster:
            await self.track_send(game["channel"], game, embeds=roster)
        embed = discord.Embed(
            title="🚨 EMERGENCY MEETING",
            description=("Discuss who you believe is the Imposter, then cast your vote below.\n\n"
                         "**Votes are secret. You can change your vote until voting closes.**"),
            color=GOLD,
        )
        embed.add_field(name="👥 ALIVE PLAYERS", value="\n".join(p.mention for p in alive), inline=False)
        embed.add_field(name="📊 VOTES CAST", value=f"**0/{len(alive)}** players have voted", inline=True)
        embed.add_field(name="⏳ TIME LIMIT", value="02:00", inline=True)
        embed.set_footer(text="Only living players may vote. Vote choices are never displayed publicly.")
        view = MeetingView(alive)
        game["meeting_view"] = view
        message = await self.track_send(game["channel"], game, embed=embed, view=view)
        view.message = message
        await view.wait()
        game["meeting_view"] = None
        try:
            await message.edit(view=None)
        except discord.HTTPException:
            pass
        if host_id not in self.active_games:
            return

        # No votes or a tied highest vote means nobody is eliminated; restart descriptions.
        if not view.votes:
            await self.track_send(game["channel"], game, embed=discord.Embed(
                title="⏰ NO VOTES RECEIVED",
                description="No votes were cast before the meeting timed out. The description cycle will start again.",
                color=GOLD))
            game["round"] += 1
            return await self.run_description_cycle(host_id)

        counts = {}
        for target_id in view.votes.values():
            counts[target_id] = counts.get(target_id, 0) + 1
        highest = max(counts.values())
        leaders = [player_id for player_id, count in counts.items() if count == highest]
        if len(leaders) != 1:
            await self.track_send(game["channel"], game, embed=discord.Embed(
                title="⚖️ VOTE TIED",
                description="The highest vote count is tied. Nobody is eliminated. The description cycle will start again.",
                color=GOLD))
            game["round"] += 1
            return await self.run_description_cycle(host_id)

        eliminated = next((p for p in alive if p.id == leaders[0]), None)
        if eliminated is None:
            game["round"] += 1
            return await self.run_description_cycle(host_id)
        game["alive"] = [p for p in game["alive"] if p.id != eliminated.id]
        game["eliminated"].append(eliminated)
        is_imposter = eliminated.id == game["imposter"].id
        reveal = discord.Embed(
            title="🗳️ PLAYER ELIMINATED",
            description=f"{eliminated.mention} has been eliminated.\n\nTheir role was **{'THE IMPOSTER' if is_imposter else 'INNOCENT'}**.",
            color=RED if is_imposter else DARK,
        )
        reveal.set_thumbnail(url=eliminated.display_avatar.url)
        await self.track_send(game["channel"], game, embed=reveal)
        if is_imposter:
            return await self.finish_game(host_id, imposters_win=False)
        if len(game["alive"]) <= 2:
            return await self.finish_game(host_id, imposters_win=True)
        game["round"] += 1
        await self.run_description_cycle(host_id)

    async def finish_game(self, host_id, *, imposters_win):
        game = self.active_games.get(host_id)
        if not game:
            return
        for key in ("turn_view", "meeting_view"):
            view = game.get(key)
            if view:
                view.stop()
        await self.cleanup_messages(game)
        imposter = game["imposter"]
        if imposters_win:
            winners = [imposter]
            title = "🔴 IMPOSTER WINS!"
            description = f"{imposter.mention} outsmarted the crew and won the game!"
            color = RED
        else:
            winners = [p for p in game["players"] if p.id != imposter.id]
            title = "💜 INNOCENTS WIN!"
            description = f"The Imposter was caught! The Imposter was {imposter.mention}."
            color = PURPLE
        result = discord.Embed(title=title, description=description, color=color)
        result.add_field(name="🏆 WINNER" if len(winners) == 1 else "🏆 WINNING TEAM", value="\n".join(p.mention for p in winners), inline=False)
        result.add_field(name="🕵️ IMPOSTER", value=imposter.mention, inline=True)
        result.add_field(name="👥 PLAYERS", value=str(len(game["players"])), inline=True)
        result.set_thumbnail(url=winners[0].display_avatar.url if winners else imposter.display_avatar.url)
        result.set_footer(text="IMPOSTER • GAME OVER")
        result_embeds = [result]
        for winner in winners:
            card = discord.Embed(title=f"🏆 {clean_name(winner)}", description="Winner", color=color)
            card.set_thumbnail(url=winner.display_avatar.url)
            card.set_author(name="VICTOR", icon_url=winner.display_avatar.url)
            result_embeds.append(card)
        await game["channel"].send(embeds=result_embeds[:10])
        self.active_games.pop(host_id, None)

    async def cancel_game(self, host_id):
        game = self.active_games.pop(host_id, None)
        if not game:
            return
        for key in ("turn_view", "meeting_view"):
            view = game.get(key)
            if view:
                view.stop()
        await self.cleanup_messages(game)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        for host_id, game in list(self.active_games.items()):
            lobby = game.get("lobby")
            if game.get("status") == "lobby" and lobby:
                player = next((p for p in lobby.players if p.id == member.id), None)
                if player:
                    if member.id == host_id:
                        await self.cancel_game(host_id)
                    else:
                        lobby.players.remove(player)
                        await lobby.refresh()
                continue
            if game.get("status") not in {"turns", "meeting"}:
                continue
            if member.id == host_id:
                await self.cancel_game(host_id)
                continue
            player = next((p for p in game.get("players", []) if p.id == member.id), None)
            if player is None or player not in game.get("alive", []):
                continue
            game["alive"] = [p for p in game["alive"] if p.id != member.id]
            game["eliminated"].append(player)
            turn_view = game.get("turn_view")
            if turn_view and game.get("turn_player_id") == member.id:
                turn_view.stop()
            meeting = game.get("meeting_view")
            if meeting:
                meeting.voter_ids.discard(member.id)
                meeting.eligible_ids.discard(member.id)
                meeting.votes.pop(member.id, None)
                for voter_id, target_id in list(meeting.votes.items()):
                    if target_id == member.id:
                        meeting.votes.pop(voter_id, None)
                await meeting.refresh_counter()
                if len(meeting.votes) >= len(meeting.voter_ids):
                    meeting.stop()
            if member.id == game["imposter"].id:
                await self.finish_game(host_id, imposters_win=False)
            elif len(game["alive"]) <= 2:
                await self.finish_game(host_id, imposters_win=True)

    @commands.hybrid_command(name="impoend")
    async def end_imposter(self, ctx):
        game = self.active_games.get(ctx.author.id)
        if not game:
            return await ctx.send("You do not have an active Imposter game.")
        await self.cancel_game(ctx.author.id)
        await ctx.send("The game has been cancelled by the host.")

    @commands.hybrid_command(name="impohelp")
    async def help_imposter(self, ctx):
        embed = discord.Embed(title="🕵️ IMPOSTER • HOW TO PLAY", description="Find the player who received a different secret word.", color=PURPLE)
        embed.add_field(name="1 • JOIN", value=f"Join the lobby. The host joins automatically. Minimum {MIN_PLAYERS}, maximum {MAX_PLAYERS} players.", inline=False)
        embed.add_field(name="2 • SECRET WORD", value="Every player receives their word privately through Discord DM. DMs must be open before the game can start.", inline=False)
        embed.add_field(name="3 • DESCRIBE", value="Players are tagged one at a time. Each turn lasts up to 60 seconds. The host can skip a turn.", inline=False)
        embed.add_field(name="4 • VOTE", value="Vote privately. You may change your vote before voting closes. The player with the most votes is eliminated.", inline=False)
        embed.add_field(name="5 • TIE / NO VOTES", value="A tied vote or no votes means nobody is eliminated; the description cycle repeats.", inline=False)
        embed.add_field(name="COMMANDS", value="`!imposter create` • Create lobby\n`!next` • Host skips current turn\n`!impoend` • Cancel game\n`!impohelp` • Show rules", inline=False)
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Imposter(bot))
