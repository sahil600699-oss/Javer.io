import discord
from discord.ext import commands
from .database import get_players_db, get_or_create_player, is_banned
from .raid import RaidMixin

SHOP_ITEMS = {
    "1": {"name": "❤️ HP Potion", "cost": 300, "desc": "Instant Full Health Recovery"},
    "2": {"name": "⚔️ Attack Elixir", "cost": 750, "desc": "+25 Attack Boost"},
    "3": {"name": "🛡️ Iron Shield", "cost": 900, "desc": "+15 Defense Boost"},
    "4": {"name": "🌟 2x EXP Scroll", "cost": 1500, "desc": "Double EXP for next Hunt"}
}

class ShopMixin(RaidMixin):
    @RaidMixin.c_main.command(name="shop")
    async def c_shop(self, ctx):
        banned, msg = is_banned(self.bot, ctx.guild.id, ctx.author.id)
        if banned: return await ctx.send(msg)

        embed = discord.Embed(title="🛒 RPG ITEM SHOP", color=0xF1C40F)
        for key, item in SHOP_ITEMS.items():
            embed.add_field(name=f"`[{key}]` {item['name']} — 🪙 {item['cost']} Coins", value=item['desc'], inline=False)
        embed.set_footer(text="Use '!c buy <id>' to purchase an item.")
        await ctx.send(embed=embed)

    @RaidMixin.c_main.command(name="buy")
    async def c_buy(self, ctx, item_id: str):
        banned, msg = is_banned(self.bot, ctx.guild.id, ctx.author.id)
        if banned: return await ctx.send(msg)

        if item_id not in SHOP_ITEMS:
            return await ctx.send("❌ Invalid Item ID! Check `!c shop`.")

        item = SHOP_ITEMS[item_id]
        p = get_or_create_player(self.bot, ctx.author)
        db = get_players_db(self.bot)

        if p.get("coins", 0) < item["cost"]:
            return await ctx.send(f"❌ Coins kam hain! Cost: `{item['cost']}` Coins.")

        p["coins"] -= item["cost"]
        if item_id == "1": p["hp"] = p["max_hp"]
        elif item_id == "2": p["buffs"]["attack"] = p["buffs"].get("attack", 0) + 25
        elif item_id == "3": p["buffs"]["defense"] = p["buffs"].get("defense", 0) + 15
        elif item_id == "4": p["buffs"]["double_xp"] = True

        db.update_one({"user_id": str(ctx.author.id)}, {"$set": p})
        await ctx.send(f"✅ Successfully purchased **{item['name']}**!")
      
