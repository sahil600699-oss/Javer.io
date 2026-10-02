import random

STARTER_POKEMON = [
    {"name": "Pikachu", "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/25.png", "hp": 100, "attack": 18, "defense": 8},
    {"name": "Charmander", "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/4.png", "hp": 90, "attack": 22, "defense": 6},
    {"name": "Squirtle", "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/7.png", "hp": 110, "attack": 15, "defense": 12},
    {"name": "Bulbasaur", "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/1.png", "hp": 105, "attack": 16, "defense": 10},
    {"name": "Eevee", "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/133.png", "hp": 95, "attack": 17, "defense": 9},
    {"name": "Lucario", "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/448.png", "hp": 120, "attack": 25, "defense": 11},
    {"name": "Gengar", "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/94.png", "hp": 100, "attack": 28, "defense": 7},
    {"name": "Mewtwo", "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/150.png", "hp": 130, "attack": 30, "defense": 15},
    {"name": "Charizard", "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/6.png", "hp": 125, "attack": 26, "defense": 12},
    {"name": "Snorlax", "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/143.png", "hp": 180, "attack": 20, "defense": 18}
]

def get_players_db(bot):
    return bot.db["rpg_players"] if hasattr(bot, 'db') and bot.db is not None else None

def get_owner_db(bot):
    return bot.db["rpg_saved_cards"] if hasattr(bot, 'db') and bot.db is not None else None

def get_bans_db(bot):
    return bot.db["rpg_bans"] if hasattr(bot, 'db') and bot.db is not None else None

def is_banned(bot, guild_id=None, user_id=None):
    bans_db = get_bans_db(bot)
    if bans_db is None:
        return False, None
    
    if guild_id and bans_db.find_one({"type": "server", "id": str(guild_id)}):
        return True, "🚫 Is server me character RPG game **Banned** hai!"
    if user_id and bans_db.find_one({"type": "user", "id": str(user_id)}):
        return True, "🚫 Aapko character RPG game se **Permanently Ban** kiya gaya hai!"
    
    return False, None

def get_or_create_player(bot, user):
    db = get_players_db(bot)
    if db is None:
        return None

    user_id = str(user.id)
    player = db.find_one({"user_id": user_id})

    if not player:
        starter = random.choice(STARTER_POKEMON)
        player = {
            "user_id": user_id,
            "name": f"{starter['name']} ({user.display_name})",
            "character_type": starter["name"],
            "image": starter["image"],
            "level": 1,
            "xp": 0,
            "max_xp": 100,
            "coins": 500,
            "hp": starter["hp"],
            "max_hp": starter["hp"],
            "attack": starter["attack"],
            "defense": starter["defense"],
            "wins": 0,
            "losses": 0,
            "autohunt_until": None,
            "buffs": {"attack": 0, "defense": 0, "double_xp": False}
        }
        db.insert_one(player)
    return player
  
