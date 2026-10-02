import discord
from discord.ext import commands
import random

class FunGames(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        # Last sent items (Duplicate repeat se bachne ke liye)
        self.last_roast = None
        self.last_flirt = None
        self.last_motivation = None

        self.roasts = [
            "Tumhe dekh kar lagta hai ki god ne tum par thoda kam dhyan diya tha! 😂",
            "You bring everyone so much joy... when you leave the room.",
            "Shakal acchi nahi hai to kam se kam baat to acchi kar liya karo! 💀",
            "I'd agree with you, but then we'd both be wrong.",
            "Aapka dimaag recharge karwa do, lagta hai validity khatam ho gayi hai.",
            "Itna attitude kis baat ka hai? Google par bhi search karoge to apni aukaat nahi milegi! 🔥",
            "Tumhari dimaag ki batti jalne se pehle hi fuse ho jaati hai! 💡",
            "Aapki baatein sunkar mera dimaag uninstall hone laga hai.",
            "If genius was a crime, you'd be the most innocent person on earth. 😇",
            "Tumse zyada speed me to BSNL ka network chalta hai!",
            "You're not stupid; you just have bad luck when thinking.",
            "Aapki akal par taala laga hai ya chabi kho gayi hai? 🗝️",
            "Agar bewakoofi ki koi trophy hoti, toh tum bina competition ke jeet jaate!",
            "I'm not saying I hate you, but I'd disconnect your Wi-Fi if I had the chance.",
            "Aapka dimaag 404 error dikha raha hai.",
            "Someday you'll go far... and I hope you stay there.",
            "Tumhe samajhne ke liye alag se course karna padega lagta hai.",
            "Mirror me dekh kar ye mat socha karo ki tum special ho, wo sirf glass ka kamaal hai! 🪞",
            "Your secrets are always safe with me. I never even listen when you tell me.",
            "Aapki baatein sunke lagta hai ki mute button sabse accha invention tha.",
            "Aap utne hi smart hain jitna ek bina recharge wala SIM card! 📲",
            "Don't worry, everyone makes mistakes. Your parents, for example.",
            "Tumse baat karke lagta hai ki time travel exist karta hai... past me chale jaata hoon!",
            "Aapka IQ level dekh kar to calculator bhi hang ho jaye. 🧮",
            "I’d slap you, but that would be animal abuse.",
            "Aapka talent chhupa hua hai... aur chhupa hi rahe toh sabke liye accha hai!",
            "You have an entire lifetime to be an idiot, why not take a day off today?",
            "Aapki baat me utna hi dum hai jitna Lay's ke packet me chips! 🥔",
            "If I had a face like yours, I'd sue my parents.",
            "Aapka dimaag bilkul naya hai, kabhi use hi nahi kiya gaya!"
        ]

        self.flirts = [
            "Are you a campfire? Because you're hot and I want s'more. 😉",
            "Kya aap Google ho? Kyunki jo bhi mujhe chahiye wo sab aap me mil jata hai! ❤️",
            "Do you have a map? I keep getting lost in your eyes.",
            "Kya aap doctor ho? Kyunki mera dil aapko dekh kar fast dhadak raha hai! 💓",
            "Aap par koi tax lagna chahiye, kyunki itna pyara hona illegal hona chahiye! ✨",
            "Is your name Wi-Fi? Because I'm feeling a real connection. 📶",
            "Kya aap camera ho? Kyunki jab bhi main aapko dekhta hoon, smile kar deta hoon! 📸",
            "Are you a magician? Because whenever I look at you, everyone else disappears. 🎩",
            "Kya aapke paas extra dil hai? Kyunki mera toh aapne chura liya! 💘",
            "Do you believe in love at first sight, or should I walk by again?",
            "Aap itne khoobsurat ho ki Bluetooth se bhi attachment bhejne ka mann karta hai!",
            "Are you French? Because Eiffel for you. 🗼",
            "Kya aap bijli ka taar ho? Kyunki aapko dekh kar jhatka lagta hai! ⚡",
            "If you were a transformer, you'd be Optimus Fine. 😉",
            "Aapka naam kya GPS hai? Kyunki aapke bina main bhatak jaata hoon.",
            "Is it hot in here, or is it just you?",
            "Kya aap painter ho? Kyunki aapne meri zindagi me rang bhar diye hain! 🎨",
            "Do you have a Band-Aid? Because I just scraped my knee falling for you.",
            "Aapki smile kitni costly hai? Kyunki ye toh ameer se ameer bande ko bhi loot le!",
            "If loving you was a job, I’d be the most dedicated employee.",
            "Kya aap sun ho? Kyunki aapke aane se mera din bright ho jaata hai! ☀️",
            "Are you a time traveler? Because I see you in my future.",
            "Aapki aankhon me koi nasha hai kya? Kyunki dekhte hi hosh ud jaate hain! 💫",
            "Is your dad a boxer? Because you’re a total knockout!",
            "Kya aap Bluetooth ho? Kyunki main aapse pair hone ke liye ready hoon.",
            "Do you like Star Wars? Because Yoda one for me! 🌌",
            "Aap mere sapnon ke password ho, jise main kabhi bhoolna nahi chahta.",
            "Are you made of copper and tellurium? Because you're CuTe! 🧪",
            "Aapko dekh kar lagta hai ki baaki duniya ko pause kar doon.",
            "Is your name Google? Because you have everything I’ve been searching for."
        ]

        self.motivations = [
            "🌟 **Safar kitna bhi mushkil ho, pehla kadam uthana hi sabse badi jeet hoti hai. Aage badhte raho!**",
            "💪 **You are stronger than you think. Keep pushing forward!**",
            "🔥 **Khudi ko kar buland itna ki har taqdeer se pehle, Khuda bande se khud pooche bata teri meza kya hai!**",
            "🚀 **The only limit to your realization of tomorrow will be your doubts of today.**",
            "🌈 **Haar tab nahi hoti jab aap gir jaate hain, haar tab hoti hai jab aap uthne se inkaar kar dete hain.**",
            "✨ **Dream big, work hard, stay focused, and surround yourself with good people.**",
            "🏆 **Zindagi me safalta paani hai toh mehnath par vishwas karo, kismat ki aazmaish toh juaye me hoti hai.**",
            "Don't count the days, make the days count. 📅",
            "🦁 **Aap wo sher ho jo apni kismat khud likhta hai. Kabhi peeche mat hatna!**",
            "Believe you can and you're halfway there. 🎯",
            "🎯 **Kaamyabi unhi ko milti hai jinke sapno me jaan hoti hai, pankho se kuch nahi hota hauslo se udaan hoti hai!**",
            "Hard work beats talent when talent doesn't work hard. ⚡",
            "💡 **Waqt badalta hai, phir badlega, aapka daur aayega!**",
            "Your speed doesn't matter, forward is forward. 🐢➡️🐇",
            "👑 **Girte hain shahswar hi maidaan-e-jung me, wo tifl kya gire jo ghutno ke bal chale.**",
            "Difficult roads often lead to beautiful destinations. 🏔️",
            "⚡ **Agar mehnat aadat ban jaye, toh kamyabi muqaddar ban jaati hai.**",
            "Push yourself, because no one else is going to do it for you.",
            "🌱 **Har chota badlaaw badi kaamyabi ka hissa hota hai.**",
            "Success is not final, failure is not fatal: It is the courage to continue that counts. 🏁"
        ]

    def get_unique_choice(self, lst, last_item):
        choice = random.choice(lst)
        # Agar same item repeat ho raha hai toh dubara select karega
        if len(lst) > 1 and choice == last_item:
            choices = [item for item in lst if item != last_item]
            choice = random.choice(choices)
        return choice

    @commands.command(name="roast")
    async def roast_cmd(self, ctx, member: discord.Member = None):
        target = member.mention if member else ctx.author.mention
        roast_text = self.get_unique_choice(self.roasts, self.last_roast)
        self.last_roast = roast_text
        await ctx.send(f"🔥 {target}, {roast_text}")

    @commands.command(name="flirt")
    async def flirt_cmd(self, ctx, member: discord.Member = None):
        target = member.mention if member else "everyone"
        flirt_text = self.get_unique_choice(self.flirts, self.last_flirt)
        self.last_flirt = flirt_text
        await ctx.send(f"😉 {target}, {flirt_text}")

    @commands.command(name="motivation")
    async def motivation_cmd(self, ctx, member: discord.Member = None):
        target = member.mention if member else ctx.author.mention
        motivation_text = self.get_unique_choice(self.motivations, self.last_motivation)
        self.last_motivation = motivation_text
        
        embed = discord.Embed(
            title="💡 Motivational Quote",
            description=f"{target}\n\n{motivation_text}",
            color=discord.Color.gold()
        )
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(FunGames(bot))
