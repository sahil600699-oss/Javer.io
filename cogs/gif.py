import discord
from discord.ext import commands
import random

class GifCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        # Duplicate repeat na ho uske liye last sent items track karna
        self.last_slap = None
        self.last_kiss = None
        self.last_hug = None
        self.last_punch = None
        self.last_boss = None

        self.slap_gifs = [
            "https://media2.giphy.com/media/v1.Y2lkPTZjMDliOTUydzlkdTd4dWV2bnFkNzJ1ZmwwN2hwa3BrejJiejE3dHdvcDF5ZXplbCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/rl5FEIQ15m57r5PkOA/giphy.gif",
            "https://media3.giphy.com/media/v1.Y2lkPTZjMDliOTUya3NwOTNuMTY3MmoxN3k3NHl0YmRlMjN5aXhpMjhhaGJ5NXZ5NWlyaCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/WvzGVdiVRNq8qtWPKu/giphy.gif",
            "https://media1.giphy.com/media/v1.Y2lkPTZjMDliOTUycm11NHhraGYydHk5cW92NnRwY2w4ZGFmYXFiYWt2a2lmcG8xOWpuZCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/6Fad0loHc6Cbe/giphy.gif",
            "https://media1.giphy.com/media/v1.Y2lkPTZjMDliOTUyb3NjNGg3NTk2ZmxicGdodno3aTk3MXcxMXYxazkxa3oyemd5dGJtMiZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/3XlEk2RxPS1m8/giphy.gif",
            "https://media2.giphy.com/media/v1.Y2lkPTZjMDliOTUyaTV3YTV0bjc1MmpmeGtnYnd4NGZhdHZ1NHFrZW9vam9ueWJmdjA3ZiZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/k32fZJ2JtmzBF1GkOG/giphy.gif",
            "https://media0.giphy.com/media/v1.Y2lkPTZjMDliOTUydjFzaGg0cHN3MDd1czVmbDFrOGZiOTA0eGswaWNqbXRid3dpdWJlZyZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/xUNd9HZq1itMkiK652/giphy.gif",
            "https://media1.giphy.com/media/v1.Y2lkPTZjMDliOTUycWU1a2xya2l0cWlvNXp0OWdycm9tMWpxM3NhdWQ3Z2l5bmFianBxcyZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/tX29X2Dx3sAXS/giphy.gif",
            "https://media1.giphy.com/media/v1.Y2lkPTZjMDliOTUydnV1ODY0eDNzMjVzMzRscHR4OGxlcnFmZWR6MnF2bmU2YjEycWM4dSZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/VVqtPmHqcBsE2SNPgt/giphy.gif",
            "https://media3.giphy.com/media/v1.Y2lkPTZjMDliOTUyZnR2cnloZXp4cmEwd2Uwemx4d2xxdXQ4bDNsaTUyd3p6OXNkOHQ0cCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/Wy6tit6VeXBraTQNhC/giphy.gif",
            "https://media2.giphy.com/media/v1.Y2lkPTZjMDliOTUydGcweDlteDJ1cXlsMXVheWtjOXljbjhkb2lpYnF3YzU1dWJqdmg4byZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/jauNHUg3yB9ZmDtzOv/giphy.gif"
        ]

        self.kiss_gifs = [
            "https://media3.giphy.com/media/v1.Y2lkPTZjMDliOTUyYjFvNHY5YWczZnF2ZXJiajNrcmY5d2FrcGx3bTNmNjZ3M2VyY3N2YSZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/W1hd3uXRIbddu/giphy.gif",
            "https://media2.giphy.com/media/v1.Y2lkPTZjMDliOTUyc2doNjNiYjJvaTUwdTFraWQ0djB0ZGdqM281dXZia2F4Z3FoMHl2YyZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/TD9S6MSGZFg6hR8Om0/giphy.gif",
            "https://media3.giphy.com/media/v1.Y2lkPTZjMDliOTUybmJieWtyYmYxajF0b2N4ZGMxY2gwODRzMmh2dWhsZzB3ZTV2dmxoNiZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/xR5cPyPoL5HVXSphqA/giphy.gif",
            "https://media0.giphy.com/media/v1.Y2lkPTZjMDliOTUyZDA2ajJiazJnZzRpN2FianF0YjQ4bnJ0M2ZubGhpZzdpM2I4MWR3bSZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/Au0qyvUbkRNyDYbdZl/giphy.gif",
            "https://media1.giphy.com/media/v1.Y2lkPTZjMDliOTUyNGZiYWI4aXUwbm51M3R5enByNDRnYzQyb2ludjNqem11YTU4dG5ocyZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/nmv0fzqIg10s1CB0W2/giphy.gif",
            "https://media4.giphy.com/media/v1.Y2lkPTZjMDliOTUyMWUxMXEyMjY2azFiOG41aTIyaGlpaG9vM2l4M3BxNnNxYzd4YWMxdSZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/jQEPreIHMrrS2BZvNN/giphy.gif",
            "https://media2.giphy.com/media/v1.Y2lkPTZjMDliOTUyaDdmOXZqdm1jd3A1NHJ4ZW00NDgzbXEzenk0djJ0ZTdqdTF5dGhwOCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/MQVpBqASxSlFu/giphy.gif",
            "https://media4.giphy.com/media/v1.Y2lkPTZjMDliOTUyNzJlbmFsM3Z6YXNmY3pjbndnNHd1dXZoNWd1Mm8wbHd5Z3VydG4zYiZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/zkppEMFvRX5FC/giphy.gif",
            "https://media4.giphy.com/media/v1.Y2lkPTZjMDliOTUyaHJ0NG9vdDA1bXA1MTZkMDV1bDMxM2EzbWZvYWZnOGcyejVya2R1NCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/KmeIYo9IGBoGY/giphy.gif"
        ]

        self.hug_gifs = [
            "https://media0.giphy.com/media/v1.Y2lkPTZjMDliOTUycm9ndWR0eWVwM25saHN6YXR0dm91NWhsZ2IzcGd5a3d4YjIxaXBrZyZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/2A75Y6NodD38I/giphy.gif",
            "https://media4.giphy.com/media/v1.Y2lkPTZjMDliOTUyN21vNWozZXE3OHczeTlpdDF6NXBkMGgxenkzc3pwYWFibzExYWU4ciZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/KG5oq4vesf9r8JbBEN/giphy.gif",
            "https://media2.giphy.com/media/v1.Y2lkPTZjMDliOTUyZnFiZGR4ejYyNDRmcHNzN3h4NXJmNXozM3BmeWZueTUwbHE2M2o4bSZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/ABjJcFelbuanC/giphy.gif",
            "https://media3.giphy.com/media/v1.Y2lkPTZjMDliOTUyZDN2am1wbHU0cWM5MW1rZ3ltMmYxM2RzZW56a2ExazIzcHp6aWRxMSZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/svXXBgduBsJ1u/giphy.gif",
            "https://media4.giphy.com/media/v1.Y2lkPTZjMDliOTUybHNncjZvbmUxYnFucDZnb3p6NjQ3ZGd2aWVzazQyZzdiN3djaTQ3OCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/yziFo5qYAOgY8/giphy.gif",
            "https://media4.giphy.com/media/v1.Y2lkPTZjMDliOTUyMXlibmlhYXc3ZTZzZnZ5NGt2dDk0NndlaTU1am8xcmZlaXkwdzhjMiZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/sjGQDBUbJr8G1uRiE9/giphy.gif",
            "https://media0.giphy.com/media/v1.Y2lkPTZjMDliOTUyeWV6MGNvdW4wZGZwcGZsb3h5MGViOHBjbzZodXRmZHpxNG00ZWh3MiZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/LIqFOpO9Qh0uA/giphy.gif",
            "https://media1.giphy.com/media/v1.Y2lkPTZjMDliOTUyamlkdw41ZGc0b2xzcXcydjYwcmx3djg0Nzc1MWl6ZG5hbjQ3ZmFyYSZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/wSY4wcrHnB0CA/giphy.gif",
            "https://media1.giphy.com/media/v1.Y2lkPTZjMDliOTUycWx3b3lnMTV5dnVyNGo3eTlrb3ozdW8yZDNzNWhpc3E4eTdvNThvdyZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/l2QDM9Jnim1YVILXa/giphy.gif"
        ]

        self.punch_gifs = [
            "https://media3.giphy.com/media/v1.Y2lkPTZjMDliOTUyZG5ldG5zaHNpY2pkNzA2aDJ5OTRwZTRzY2M5ZHZxejd4NnNveTBkbiZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/NuiEoMDbstN0J2KAiH/giphy.gif",
            "https://media4.giphy.com/media/v1.Y2lkPTZjMDliOTUyZ281OTd5cGhzdG16YXY5OWhncmdobjRzMno1YzY0ZTRza241bTl0bCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/OpvUphysvKumQ/giphy.gif",
            "https://media.giphy.com/media/YN7DcBA6rgI9opx0aj/giphy.gif",
            "https://media.giphy.com/media/3OcUO1YEErcUo/giphy.gif",
            "https://media.giphy.com/media/SzC42gUrhHopW/giphy.gif"
        ]

        self.boss_gifs = [
            "https://media.giphy.com/media/Qm6rAHUN4X1INCzz6T/giphy.gif",
            "https://media.giphy.com/media/hF9zeIpc8RbMPp1neu/giphy.gif"
        ]

    def get_clean_name(self, user):
        if not user:
            return "Someone"
        name = getattr(user, 'global_name', None) or getattr(user, 'display_name', None) or getattr(user, 'name', None)
        if not name or str(name).strip().lower() == "null":
            name = getattr(user, 'name', "Someone")
        return name

    def get_unique_gif(self, gif_list, last_gif):
        choice = random.choice(gif_list)
        if len(gif_list) > 1 and choice == last_gif:
            choices = [g for g in gif_list if g != last_gif]
            choice = random.choice(choices)
        return choice

    @commands.command(name="slap")
    async def slap_cmd(self, ctx, member: discord.Member = None):
        target = member or ctx.author
        author_name = self.get_clean_name(ctx.author)
        target_name = self.get_clean_name(target)

        text = f"🖐️ **{author_name}** slapped **themselves**!" if target.id == ctx.author.id else f"🖐️ **{author_name}** slapped **{target_name}** hard!"

        gif = self.get_unique_gif(self.slap_gifs, self.last_slap)
        self.last_slap = gif

        embed = discord.Embed(description=text, color=discord.Color.orange())
        embed.set_image(url=gif)
        await ctx.send(embed=embed)

    @commands.command(name="kiss")
    async def kiss_cmd(self, ctx, member: discord.Member = None):
        target = member or ctx.author
        author_name = self.get_clean_name(ctx.author)
        target_name = self.get_clean_name(target)

        text = f"💋 **{author_name}** kissed **themselves**!" if target.id == ctx.author.id else f"💋 **{author_name}** kissed **{target_name}**!"

        gif = self.get_unique_gif(self.kiss_gifs, self.last_kiss)
        self.last_kiss = gif

        embed = discord.Embed(description=text, color=discord.Color.magenta())
        embed.set_image(url=gif)
        await ctx.send(embed=embed)

    @commands.command(name="hug")
    async def hug_cmd(self, ctx, member: discord.Member = None):
        target = member or ctx.author
        author_name = self.get_clean_name(ctx.author)
        target_name = self.get_clean_name(target)

        text = f"🤗 **{author_name}** gave **themselves** a warm hug!" if target.id == ctx.author.id else f"🤗 **{author_name}** gave **{target_name}** a big hug!"

        gif = self.get_unique_gif(self.hug_gifs, self.last_hug)
        self.last_hug = gif

        embed = discord.Embed(description=text, color=discord.Color.teal())
        embed.set_image(url=gif)
        await ctx.send(embed=embed)

    @commands.command(name="punch")
    async def punch_cmd(self, ctx, member: discord.Member = None):
        target = member or ctx.author
        author_name = self.get_clean_name(ctx.author)
        target_name = self.get_clean_name(target)

        text = f"🥊 **{author_name}** punched **themselves**!" if target.id == ctx.author.id else f"🥊 **{author_name}** punched **{target_name}**!"

        gif = self.get_unique_gif(self.punch_gifs, self.last_punch)
        self.last_punch = gif

        embed = discord.Embed(description=text, color=discord.Color.red())
        embed.set_image(url=gif)
        await ctx.send(embed=embed)

    @commands.command(name="boss", aliases=["Boss"])
    async def boss_cmd(self, ctx, member: discord.Member = None):
        target = member or ctx.author
        author_name = self.get_clean_name(ctx.author)
        target_name = self.get_clean_name(target)

        text = f"😎 **{author_name}** is showing off their **Boss** entry!" if target.id == ctx.author.id else f"😎 **{author_name}** flexed their **Boss** attitude on **{target_name}**!"

        gif = self.get_unique_gif(self.boss_gifs, self.last_boss)
        self.last_boss = gif

        embed = discord.Embed(description=text, color=discord.Color.gold())
        embed.set_image(url=gif)
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(GifCommands(bot))
