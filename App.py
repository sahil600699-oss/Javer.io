import os
import asyncio
import threading
from flask import Flask
import discord
from discord.ext import commands
from pymongo import MongoClient
from motor.motor_asyncio import AsyncIOMotorClient
import config

# --- Keep Alive Flask Server ---
app = Flask('')

@app.route('/')
def home():
    return 'Bot is live and active!', 200

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = threading.Thread(target=run_flask)
    t.daemon = True
    t.start()

keep_alive()
# -------------------------------

MONGO_URI = os.getenv('MONGO_URI', getattr(config, 'MONGO_URI', None))
db = None
async_db = None

if MONGO_URI:
    try:
        # Sync MongoClient for backup/recovery
        cluster = MongoClient(MONGO_URI)
        db = cluster['javer_database']
        
        # Async Motor Client for Async Cogs (Welcome, etc.)
        motor_client = AsyncIOMotorClient(MONGO_URI)
        async_db = motor_client['javer_database']
        
        print('[MongoDB] Successfully connected to javer_database!')

        storage_collections = [
            'welcome_setup', 'welcome', 'welcome_settings',
            'mod_logs', 'modlogs', 'logs',
            'msg_tracker', 'msgtracker', 'messages',
            'vc_tracker', 'vctracker', 'voice_time',
            'autosend', 'autoresponder', 'afk_users',
            'kingdom_data', 'roles_setup', 'rpg_players',
            'rpg_saved_cards', 'rpg_bans', 'premium_users'
        ]

        existing_dbs = cluster.list_database_names()
        for old_db_name in ['test', 'javer', 'bot_db', 'discord_bot', 'my_database']:
            if old_db_name in existing_dbs and old_db_name != 'javer_database':
                old_db = cluster[old_db_name]
                for coll in storage_collections:
                    if coll in old_db.list_collection_names():
                        docs = list(old_db[coll].find())
                        if docs:
                            for doc in docs:
                                db[coll].update_one({"_id": doc["_id"]}, {"$set": doc}, upsert=True)
                            print(f'[MongoDB Universal Recovery] Restored {len(docs)} records for `{coll}` from DB: `{old_db_name}`')
    except Exception as e:
        print(f'[MongoDB Connection Error]: {e}')
else:
    print('[MongoDB Warning] MONGO_URI variable missing in environment!')

# Enable Intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True  # Required for welcome system
intents.voice_states = True
intents.presences = False

PREFIXES = commands.when_mentioned_or('.', ',', '-', '?', '$', ';', '/', ':', "'", '!')

bot = commands.Bot(command_prefix=PREFIXES, intents=intents, help_command=None)
bot.db = db
bot.async_db = async_db  # Pass async database to cogs

@bot.event
async def on_ready():
    print('----------------------------------------')
    print(f'Bot Online: {bot.user} ({bot.user.id})')
    print('----------------------------------------')
    try:
        synced = await bot.tree.sync()
        print(f'Slash Commands Synced: {len(synced)}')
    except Exception as e:
        print(f'Slash Sync Error: {e}')

    await bot.change_presence(status=discord.Status.online, activity=None)

async def main():
    async with bot:
        cogs = [
            'cogs.help',
            'cogs.vchelper',
            'cogs.music',
            'cogs.moderation',
            'cogs.fungames',
            'cogs.utility',
            'cogs.vctracker',
            'cogs.gif',
            'cogs.msgtracker',
            'cogs.role',
            'cogs.kingdom',
            'cogs.antinuke',
            'cogs.welcome',
            'cogs.imposter',
            'cogs.modlogs',
            'cogs.xo',
            'cogs.autosend',
            'cogs.afk',
            'cogs.autoresponder',
            'cogs.premium',
            'cogs.card',
            'cogs.cgame.leaderboard'
        ]

        for cog in cogs:
            try:
                await bot.load_extension(cog)
                print(f'Loaded {cog}')
            except Exception as e:
                print(f'Error loading {cog}: {e}')

        token = os.getenv('BOT_TOKEN', getattr(config, 'BOT_TOKEN', None))
        if not token:
            print("❌ ERROR: BOT_TOKEN Environment variable is not set!")
            return
            
        await bot.start(token)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot shutdown gracefully.")
        
