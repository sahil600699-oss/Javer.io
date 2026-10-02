import sqlite3

BOT_OWNER_ID = 1302619411529732136

def init_db():
    with sqlite3.connect("role_management.db") as conn:
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS autoroles (
                guild_id INTEGER PRIMARY KEY,
                human_role_id INTEGER DEFAULT NULL,
                bot_role_id INTEGER DEFAULT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS role_presets (
                guild_id INTEGER,
                preset_name TEXT,
                role_id INTEGER,
                PRIMARY KEY (guild_id, preset_name, role_id)
            )
        """)
        conn.commit()

def is_owner_or_bot_owner(ctx):
    return (ctx.author.id == ctx.guild.owner_id) or (ctx.author.id == BOT_OWNER_ID)

def get_assignable_roles(guild):
    valid_roles = []
    for r in guild.roles:
        if not r.is_default() and not r.managed and r < guild.me.top_role:
            valid_roles.append(r)
    return valid_roles
    
