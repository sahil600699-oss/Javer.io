import discord
from discord.ext import commands
import random
import asyncio

WORD_PAIRS = [
    # --- Everyday Items & Objects ---
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

    # --- Food, Drinks & Snacks ---
    ("Tea", "Coffee"), ("Apple", "Mango"), ("Burger", "Pizza"),
    ("Samosa", "Kachori"), ("Momo", "Spring Roll"), ("Cake", "Pastry"),
    ("Ice Cream", "Kulfi"), ("Milk", "Curd"), ("Paneer", "Cheese"),
    ("Chai", "Green Tea"), ("Pepsi", "Coke"), ("Water", "Juice"),
    ("Roti", "Paratha"), ("Biryani", "Pulao"), ("Noodles", "Pasta"),
    ("Chocolate", "Candy"), ("Biscuit", "Cookie"), ("Gulab Jamun", "Rasgulla"),
    ("Banana", "Papaya"), ("Grapes", "Orange"), ("Potato", "Onion"),
    ("Tomato", "Cucumber"), ("Butter", "Ghee"),
    ("Popcorn", "Chips"), ("Sandwich", "Toast"), ("Dosa", "Idli"),
    ("Soup", "Stew"), ("Jalebi", "Imarti"), ("Omelette", "Boiled Egg"),

    # --- Animals, Birds & Nature ---
    ("Cat", "Dog"), ("Lion", "Tiger"), ("Sun", "Moon"),
    ("River", "Ocean"), ("Tree", "Plant"), ("Horse", "Donkey"),
    ("Cow", "Buffalo"), ("Crow", "Pigeon"), ("Eagle", "Hawk"),
    ("Snake", "Lizard"), ("Fish", "Shark"), ("Monkey", "Chimpanzee"),
    ("Bear", "Panda"), ("Wolf", "Fox"), ("Rain", "Storm"),
    ("Mountain", "Hill"), ("Rose", "Lotus"), ("Star", "Planet"),
    ("Fire", "Smoke"), ("Ice", "Snow"),

    # --- Vehicles & Places ---
    ("Car", "Bike"), ("Bus", "Train"), ("Aeroplane", "Helicopter"),
    ("Ship", "Boat"), ("Scooter", "Bicycle"), ("Auto", "Taxi"),
    ("School", "College"), ("Hospital", "Clinic"), ("Hotel", "Restaurant"),
    ("Park", "Garden"), ("Mall", "Market"), ("Cinema", "Theatre"),
    ("Airport", "Railway Station"), ("Village", "City"), ("Road", "Bridge"),

    # --- Gaming, Tech & Sports ---
    ("Football", "Cricket"), ("Badminton", "Tennis"), ("PUBG", "Free Fire"),
    ("YouTube", "Instagram"), ("WhatsApp", "Telegram"), ("GTA", "Cyberpunk"),
    ("Keyboard", "Mouse"), ("PS5", "Xbox"), ("Google", "Bing"),
    ("Spotify", "Wynk"), ("Netflix", "Prime"), ("Chess", "Ludo"),
    ("Valorant", "CSGO"), ("Instagram", "Snapchat"), ("Wi-Fi", "Bluetooth")
]

class JoinView(discord.ui.View):
    def __init__(self, host, cog):
        super().__init__(timeout=None)
        self.host = host
        self.cog = cog
        self.players = [host]

    @discord.ui.button(label="📥 Join Game", style=discord.ButtonStyle.green, custom_id="join_imposter")
    async def join_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user in self.players:
            await interaction.response.send_message("❌ Aap pehle se hi game me hain!", ephemeral=True)
            return
        self.players.append(interaction.user)
        embed = interaction.message.embeds[0]
        player_list = "\n".join([f"• {p.mention}" for p in self.players])
        embed.set_field_at(0, name=f"👥 Players Joined ({len(self.players)}):", value=player_list, inline=False)
        await interaction.message.edit(embed=embed)
        await interaction.response.send_message("✅ Aap game me join ho gaye!", ephemeral=True)

    @discord.ui.button(label="🚀 Start Game", style=discord.ButtonStyle.blurple, custom_id="start_imposter")
    async def start_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.host:
            await interaction.response.send_message("❌ Sirf Game Creator hi start kar sakta hai!", ephemeral=True)
            return
        if len(self.players) < 3:
            await interaction.response.send_message("❌ Kam se kam 3 players chahiye!", ephemeral=True)
            return
        await interaction.response.send_message("🎮 Game shuru ho raha hai...", ephemeral=True)
        self.stop()
        await self.cog.start_game_logic(interaction.channel, self.host, self.players)


class ResumeView(discord.ui.View):
    def __init__(self, host, cog, channel):
        super().__init__(timeout=60)
        self.host = host
        self.cog = cog
        self.channel = channel

    @discord.ui.button(label="▶️ Resume Unfinished Game", style=discord.ButtonStyle.green)
    async def resume_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.host:
            await interaction.response.send_message("❌ Sirf Host hi resume kar sakta hai!", ephemeral=True)
            return
        await interaction.response.send_message("🔄 Game wapas se continue kiya ja raha hai...", ephemeral=True)
        self.stop()
        await self.cog.resume_game_logic(self.channel, self.host)

    @discord.ui.button(label="🆕 Delete Old & Create New", style=discord.ButtonStyle.red)
    async def new_game_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.host:
            await interaction.response.send_message("❌ Sirf Host hi naya game bana sakta hai!", ephemeral=True)
            return
        await interaction.response.send_message("🗑️ Purana game cancel karke naya room banaya ja raha hai...", ephemeral=True)
        self.stop()
        if self.host.id in self.cog.active_games:
            del self.cog.active_games[self.host.id]
        await self.cog.create_new_room(self.channel, self.host)


class NextTurnView(discord.ui.View):
    def __init__(self, host, cog, channel):
        super().__init__(timeout=None)
        self.host = host
        self.cog = cog
        self.channel = channel

    @discord.ui.button(label="➡️ Next Player", style=discord.ButtonStyle.primary, custom_id="next_player_turn")
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.host:
            await interaction.response.send_message("❌ Sirf Host hi 'Next' daba sakta hai!", ephemeral=True)
            return
        await interaction.response.defer()
        await self.cog.process_next_turn(self.channel, self.host)


class VoteDropdown(discord.ui.Select):
    def __init__(self, players):
        options = [discord.SelectOption(label=p.display_name, value=str(p.id)) for p in players]
        super().__init__(placeholder="Kisko vote karein?", options=options)

    async def callback(self, interaction: discord.Interaction):
        view: MeetingView = self.view
        if interaction.user not in view.voters_needed:
            await interaction.response.send_message("❌ Aap vote nahi kar sakte!", ephemeral=True)
            return
        if interaction.user.id in view.votes_cast:
            await interaction.response.send_message("❌ Aapne pehle hi vote de diya hai!", ephemeral=True)
            return
        voted_id = int(self.values[0])
        view.votes[voted_id] = view.votes.get(voted_id, 0) + 1
        view.votes_cast.add(interaction.user.id)
        await interaction.response.send_message("✅ Vote register ho gaya!", ephemeral=True)
        if len(view.votes_cast) >= len(view.voters_needed):
            view.stop()


class MeetingView(discord.ui.View):
    def __init__(self, alive_players):
        super().__init__(timeout=540) # 9 Minutes
        self.alive_players = alive_players
        self.voters_needed = list(alive_players)
        self.votes = {}
        self.votes_cast = set()
        self.add_item(VoteDropdown(alive_players))


class Imposter(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Structure: host_id -> game_data
        self.active_games = {}

    async def auto_cleanup(self, host_id):
        """Automatically delete abandoned games after 1 Hour (3600 seconds)"""
        await asyncio.sleep(3600)
        if host_id in self.active_games:
            del self.active_games[host_id]

    @commands.command(name="imposter")
    async def create_imposter(self, ctx, option: str = None):
        if option != "create":
            await ctx.send("❓ Use: `!imposter create` (Help: `!impohelp`)")
            return

        host = ctx.author

        # Check if Host already has an unfinished/abandoned game
        if host.id in self.active_games:
            view = ResumeView(host, self, ctx.channel)
            embed = discord.Embed(
                title="⚠️ Unfinished Game Found!",
                description=f"{host.mention}, aapka ek game pehle se adhoora pada hua hai.\n\nKya aap use **Resume** karna chahte hain ya **Naya Game** shuru karna chahte hain?",
                color=discord.Color.orange()
            )
            await ctx.send(embed=embed, view=view)
            return

        await self.create_new_room(ctx.channel, host)

    async def create_new_room(self, channel, host):
        view = JoinView(host, self)
        embed = discord.Embed(
            title="🎮 Imposter Game Room",
            description=f"Host: {host.mention}\nClick **📥 Join** to play!",
            color=discord.Color.gold()
        )
        embed.add_field(name=f"👥 Players ({len(view.players)}):", value=f"• {host.mention}", inline=False)
        msg = await channel.send(embed=embed, view=view)
        
        self.active_games[host.id] = {
            "host": host,
            "join_msg": msg,
            "channel_id": channel.id,
            "status": "lobby"
        }
        # Start 1-hour auto cleanup timer
        asyncio.create_task(self.auto_cleanup(host.id))

    @commands.command(name="next")
    async def next_turn_cmd(self, ctx):
        host = ctx.author
        game = self.active_games.get(host.id)
        if not game:
            await ctx.send("❌ Aapka koi active game nahi chal raha hai.")
            return
        if game["status"] != "turns":
            await ctx.send("❌ Abhi turn phase nahi chal raha hai.")
            return

        await ctx.send(f"⏩ Host {host.mention} ne `!next` command use kiya...")
        await self.process_next_turn(ctx.channel, host)

    @commands.command(name="impoend")
    async def end_imposter(self, ctx):
        host = ctx.author
        game = self.active_games.get(host.id)
        if not game:
            await ctx.send("❌ Aapka koi active game chal nahi raha hai jise end kiya jaye.")
            return

        del self.active_games[host.id]
        await ctx.send(f"🛑 Game {host.mention} dwara band kar diya gaya.")

    @commands.command(name="impohelp")
    async def help_imposter(self, ctx):
        embed = discord.Embed(
            title="🕵️ Imposter Game Guide & Rules",
            description="**Kaise Khelte Hain (How to Play):**",
            color=discord.Color.purple()
        )
        embed.add_field(
            name="1️⃣ Game Join & Role Assignment",
            value="• `!imposter create` se har koi apna room bana sakta hai.\n• Sabhi players ko DMs me Secret Word milega.\n• Role secret rahega!",
            inline=False
        )
        embed.add_field(
            name="2️⃣ Turn Phase (Description)",
            value="• Ek-ek karke sabhi players apne word ko describe karenge.\n• Host **➡️ Next** button ya `!next` se turn aage badhayega.",
            inline=False
        )
        embed.add_field(
            name="3️⃣ Voting Phase (9 Mins)",
            value="• Turn khatam hone par Voting start hogi.\n• Highest voted player eliminate hoga.\n• Adhoore games 1 hour me auto-delete ho jate hain!",
            inline=False
        )
        embed.add_field(
            name="📜 Commands",
            value="• `!imposter create` — Game room create karne ke liye.\n• `!next` — Next turn ke liye.\n• `!impoend` — Game end karne ke liye.\n• `!impohelp` — Guide dekhne ke liye.",
            inline=False
        )
        await ctx.send(embed=embed)

    async def start_game_logic(self, channel, host, players):
        imposter = random.choice(players)
        innocent_word, imposter_word = random.choice(WORD_PAIRS)
        
        dm_failed = []
        for player in players:
            word = imposter_word if player == imposter else innocent_word
            try:
                await player.send(f"🤫 **Aapka Secret Word hai:** **{word}**\n\nIsse describe karein lekin exact word mat bolna!")
            except:
                dm_failed.append(player.mention)

        if dm_failed:
            await channel.send(f"📩 **Sabhi players ko DMs bhej diye gaye hain!**\n⚠️ Alert: {', '.join(dm_failed)} ke DMs closed hain!")
        else:
            await channel.send("📩 **Sabhi players ko DMs me Secret Word bhej diya gaya hai!**")

        turn_order = players.copy()
        random.shuffle(turn_order)
        
        if turn_order[0] == imposter and len(turn_order) > 1:
            turn_order[0], turn_order[-1] = turn_order[-1], turn_order[0]

        self.active_games[host.id].update({
            "imposter": imposter,
            "alive": players.copy(),
            "turn_order": turn_order,
            "current_turn": 0,
            "status": "turns"
        })
        
        await channel.send(f"🚨 **Game Start (Host: {host.mention})!** Turn-by-turn description start karte hain.")
        await self.process_next_turn(channel, host)

    async def resume_game_logic(self, channel, host):
        game = self.active_games.get(host.id)
        if not game: return
        status = game.get("status")

        if status == "turns":
            await channel.send(f"🔄 **Game Resumed!** Current turn se continue kar rahe hain...")
            await self.process_next_turn(channel, host)
        elif status == "meeting":
            await channel.send(f"🔄 **Game Resumed!** Voting phase se continue kar rahe hain...")
            await self.start_meeting(channel, host)
        else:
            await channel.send("⚠️ Game lobby state me tha. Naya game room banaya ja raha hai...")
            await self.create_new_room(channel, host)

    async def process_next_turn(self, channel, host):
        game = self.active_games.get(host.id)
        if not game or game["status"] != "turns": return
        idx = game["current_turn"]
        if idx < len(game["turn_order"]):
            player = game["turn_order"][idx]
            game["current_turn"] += 1
            view = NextTurnView(host, self, channel)
            await channel.send(f"🗣️ **Turn {idx + 1}/{len(game['turn_order'])} (Host: {host.display_name}):** {player.mention} - Describe your word!", view=view)
        else:
            await channel.send("✅ Sabki turn ho gayi! Ab **Voting Phase** shuru ho raha hai (9 minutes).")
            await self.start_meeting(channel, host)

    async def start_meeting(self, channel, host):
        game = self.active_games.get(host.id)
        if not game: return
        game["status"] = "meeting"
        view = MeetingView(game["alive"])
        await channel.send(f"🔔 **EMERGENCY MEETING (Host: {host.display_name})!** Imposter ko vote karein.", view=view)
        await view.wait()
        
        if not view.votes:
            await channel.send("⏰ Time over! Kisi ne vote nahi kiya. Next round shuru karte hain...")
            await self.continue_game(channel, host)
            return

        ejected_id = max(view.votes, key=view.votes.get)
        ejected_player = discord.utils.get(game["alive"], id=ejected_id)
        
        if ejected_player in game["alive"]:
            game["alive"].remove(ejected_player)

        if ejected_player == game["imposter"]:
            await channel.send(f"🎉 **Victory!** {ejected_player.mention} Imposter tha! Innocents ne game jeet liya!")
            del self.active_games[host.id]
            return

        await channel.send(f"💀 **{ejected_player.mention}** eliminate ho gaya, par wo Imposter nahi tha!")
        
        if len(game["alive"]) <= 2:
            await channel.send(f"🗡️ **Imposter Wins!** Only 2 players left. **{game['imposter'].mention}** (Imposter) bach gaya aur jeet gaya!")
            del self.active_games[host.id]
        else:
            await channel.send("🔄 **Nayi Round!** Zinda bando ke sath cycle wapas shuru ho rahi hai...")
            await self.continue_game(channel, host)

    async def continue_game(self, channel, host):
        game = self.active_games.get(host.id)
        if not game: return
        
        game["status"] = "turns"
        game["current_turn"] = 0
        
        new_order = game["alive"].copy()
        random.shuffle(new_order)
        
        if new_order[0] == game["imposter"] and len(new_order) > 1:
            new_order[0], new_order[-1] = new_order[-1], new_order[0]
            
        game["turn_order"] = new_order
        await self.process_next_turn(channel, host)

async def setup(bot):
    await bot.add_cog(Imposter(bot))
