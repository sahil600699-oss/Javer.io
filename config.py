import os

# Bot Token (Render Environment Variable se read karega)
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Bot Owner Configuration
OWNER_ID = 1302619411529732136

# Aapka Personal Lavalink Node
LAVALINK_HOST = os.getenv("LAVALINK_HOST", "in-1.visihost.in")
LAVALINK_PORT = int(os.getenv("LAVALINK_PORT", 3002))
LAVALINK_PASSWORD = os.getenv("LAVALINK_PASSWORD", "pvt@1211")
