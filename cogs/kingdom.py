import asyncio
import random
import sqlite3
import time
from dataclasses import dataclass
from typing import Optional

import discord
from discord.ext import commands

DB_FILE = 'kingdom_wars.sqlite3'
PREP_TIME = 5 * 60
WAR_TIME = 20 * 60
HOUSE_HP = 200
NPC_CAP = 100
MIN_PLAYERS = 2
LUCKBOX_COST = 250

TIERS = ['Wood', 'Stone', 'Iron', 'Gold', 'Diamond']
WEAPONS = {'Wood': (12, 0), 'Stone': (20, 350), 'Iron': (30, 800), 'Gold': (42, 1500), 'Diamond': (58, 3000)}
ARMORS = {'Wood': (3, 0), 'Stone': (8, 300), 'Iron': (14, 700), 'Gold': (22, 1400), 'Diamond': (32, 2800)}
HOUSE = {1: (0, 0.00), 2: (600, .10), 3: (1200, .18), 4: (2200, .27), 5: (3500, .37), 6: (5000, .48), 7: (7000, .58), 8: (9500, .67), 9: (12500, .74), 10: (16000, .80)}


def fmt(n): return f'{n:,}'
def bar(v, m=200, n=14):
    x = round(max(0, min(v, m)) / m * n)
    return '█' * x + '░' * (n - x)
def pick(items):
    total = sum(x[-1] for x in items)
    r, cur = random.uniform(0, total), 0
    for x in items:
        cur += x[-1]
        if r <= cur: return x
    return items[-1]
def nxt(t):
    i = TIERS.index(t)
    return TIERS[i + 1] if i + 1 < len(TIERS) else None

@dataclass
class KP:
    uid: int
    name: str
    npc: bool = False
    coins: int = 500
    hp: int = HOUSE_HP
    house: int = 1
    weapon: str = 'Wood'
    armor: str = 'Wood'
    potions: int = 0
    loot: int = 0
    eliminated: bool = False
    last_mine: float = 0
    last_attack: float = 0

    def power(self):
        return WEAPONS[self.weapon][0] + ARMORS[self.armor][0] + self.house * 10 + self.hp // 10
    def alive(self): return not self.eliminated and self.hp > 0

class Match:
    def __init__(self, cog, guild, channel, host, name, password, npc_count=0):
        self.cog, self.guild, self.channel = cog, guild, channel
        self.host, self.name, self.password = host, name, password
        self.npc_count = npc_count
        self.players = {}
        self.message = None
        self.phase = 'lobby'
        self.prep_end = self.war_end = None
        self.finished = False
        self.lock = asyncio.Lock()
        self.timer_task = None
        self.npc_task = None

    def add_user(self, user):
        if user.id in self.players: return False
        self.players[user.id] = KP(user.id, user.display_name)
        return True

    def add_npcs(self, count):
        for i in range(1, count + 1):
            uid = -i
            self.players[uid] = KP(uid, f'NPC {i}', True, random.randint(400, 650))

    def get(self, uid): return self.players.get(uid)
    def alive(self): return [p for p in self.players.values() if p.alive()]
    def left(self):
        if self.phase == 'preparation' and self.prep_end: return max(0, int(self.prep_end - time.monotonic()))
        if self.phase == 'war' and self.war_end: return max(0, int(self.war_end - time.monotonic()))
        return 0
    def mention(self, p): return f'🤖 {p.name}' if p.npc else f'<@{p.uid}>'

    def lobby_embed(self):
        lines = []
        for i, p in enumerate(self.players.values(), 1):
            crown = ' 👑' if p.uid == self.host else ''
            lines.append(f'`{i:02}` {self.mention(p)}{crown}')
        e = discord.Embed(title='👑 KINGDOM WARS', description=f'**{self.name}**\n\n🔐 Password Protected\n👑 **Host:** <@{self.host}>\n👥 **Players:** {len(self.players)}\n⚔️ **Minimum to start:** 2', color=discord.Color.gold())
        e.add_field(name='👥 Players', value='\n'.join(lines) if lines else 'No players', inline=False)
        e.set_footer(text='Join, leave, or start the match. Only the host can start.')
        return e

    def embed(self, viewer=None):
        e = discord.Embed(title='🛡️ PREPARATION PHASE' if self.phase == 'preparation' else '⚔️ WAR PHASE', description='War is locked. Mine and upgrade.' if self.phase == 'preparation' else 'War is live! Attack other kingdoms.', color=discord.Color.blue() if self.phase == 'preparation' else discord.Color.red())
        e.add_field(name='⏱️ Time Remaining', value=f'**{self.left()//60:02}:{self.left()%60:02}**', inline=True)
        e.add_field(name='⚔️ Attacks', value='🔒 Locked' if self.phase == 'preparation' else '🟢 Unlocked', inline=True)
        e.add_field(name='👥 Alive', value=str(len(self.alive())), inline=True)
        if viewer:
            e.add_field(name=f'🏰 {viewer.name}', value=f'❤️ **{viewer.hp}/200** `{bar(viewer.hp)}`\n🛡️ Protection: **Lv.{viewer.house}**\n⚔️ Weapon: **{viewer.weapon}**\n🛡️ Armor: **{viewer.armor}**\n💰 Coins: **{fmt(viewer.coins)}**\n🧪 Potions: **{viewer.potions}**\n🎁 Loot: **{viewer.loot}**', inline=False)
        e.set_footer(text='!kingdom leave • !kingdom top')
        return e

    async def start(self):
        self.phase = 'preparation'; self.prep_end = time.monotonic() + PREP_TIME; self.war_end = self.prep_end + WAR_TIME
        self.timer_task = asyncio.create_task(self.timer())
        if self.npc_count: self.npc_task = asyncio.create_task(self.npcs())

    async def timer(self):
        try:
            while not self.finished:
                if self.phase == 'preparation' and time.monotonic() >= self.prep_end:
                    self.phase = 'war'
                    await self.cog.refresh(self)
                    await self.channel.send('🚨 **WAR PHASE HAS BEGUN!**\nAttacks are now unlocked.')
                elif self.phase == 'war' and time.monotonic() >= self.war_end:
                    await self.finish('time'); return
                await asyncio.sleep(5)
        except asyncio.CancelledError: pass
        except Exception as ex: print('[KINGDOM TIMER]', ex)

    def mine(self, p):
        now = time.monotonic()
        if now - p.last_mine < 8: return False, f'⏳ Mining cooldown: {max(1, int(8-(now-p.last_mine)))}s.'
        p.last_mine = now
        r = pick([('coins',35,90,55),('coins',70,160,25),('coins',120,250,10),('potion',1,1,7),('loot',1,1,3)])
        if r[0] == 'coins':
            n = random.randint(r[1], r[2]); p.coins += n; return True, f'💰 **+{fmt(n)} Coins**'
        if r[0] == 'potion': p.potions += 1; return True, '🧪 **+1 Recovery Potion**'
        p.loot += 1; return True, '🎁 **+1 Loot**'

    def luckbox(self, p):
        if p.coins < LUCKBOX_COST: return False, '❌ You need **250 Coins**.'
        p.coins -= LUCKBOX_COST
        r = pick([('coins',100,250,55),('potion',1,1,25),('coins',300,650,12),('gold',500,900,5),('diamond',1500,2000,2),('mega',3,3,1)])
        if r[0] == 'coins': n=random.randint(r[1],r[2]); p.coins+=n; return True,f'🎁 **Luck Box:** 💰 +{fmt(n)} Coins'
        if r[0]=='potion': p.potions+=1; return True,'🎁 **Luck Box:** 🧪 +1 Recovery Potion'
        if r[0]=='gold': p.coins+=r[1]; return True,'🎁 **RARE:** 🟨 Gold Cache'
        if r[0]=='diamond': p.coins+=r[1]; return True,'🎁 **EXTREMELY RARE:** 💎 Diamond Cache'
        p.potions += 3; return True, '🎁 **ULTRA RARE:** 🧪 +3 Recovery Potions'

    def upgrade(self, p, kind):
        if kind == 'weapon':
            n=nxt(p.weapon)
            if not n:return False,'⚔️ Your weapon is already Diamond.'
            cost=WEAPONS[n][1]; label=f'⚔️ Weapon upgraded to **{n}**.'
        elif kind == 'armor':
            n=nxt(p.armor)
            if not n:return False,'🛡️ Your armor is already Diamond.'
            cost=ARMORS[n][1]; label=f'🛡️ Armor upgraded to **{n}**.'
        else:
            n=p.house+1
            if n not in HOUSE:return False,'🏠 House Protection is already at maximum level.'
            cost=HOUSE[n][0]; label=f'🏠 House Protection upgraded to **Level {n}**.'
        if p.coins < cost:return False,f'❌ You need **{fmt(cost)} Coins**.'
        p.coins-=cost
        if kind=='weapon':p.weapon=n
        elif kind=='armor':p.armor=n
        else:p.house=n
        return True,label

    def recover(self,p,potion=False):
        if p.hp>=200:return False,'❤️ Your house is already at full health.'
        if potion:
            if p.potions<=0:return False,'❌ You do not have a Recovery Potion.'
            p.potions-=1; n=min(80,200-p.hp); p.hp+=n; return True,f'🧪 Recovery Potion used: **+{n} HP**.'
        if p.coins<100:return False,'❌ You need **100 Coins**.'
        p.coins-=100;n=min(50,200-p.hp);p.hp+=n;return True,f'❤️ House recovered by **{n} HP**.'

    async def attack(self, a_id, d_id):
        a,d=self.get(a_id),self.get(d_id)
        if not a or not d:return False,'❌ Player not found.'
        if not a.alive():return False,'❌ Your house is destroyed.'
        if not d.alive():return False,'❌ That house is already destroyed.'
        if self.phase!='war':return False,'🔒 Attacks are locked during the Preparation Phase.'
        now=time.monotonic()
        if now-a.last_attack<10:return False,f'⏳ Attack cooldown: {max(1,int(10-(now-a.last_attack)))}s.'
        a.last_attack=now
        raw=WEAPONS[a.weapon][0]+random.randint(0,max(2,ARMORS[a.armor][0]//3))
        reduction=HOUSE[d.house][1]; damage=max(1,round(raw*(1-reduction)))
        if random.random()<.08: damage=max(1,round(damage*1.5)); crit=True
        else: crit=False
        d.hp=max(0,d.hp-damage)
        if d.hp==0:
            d.eliminated=True
            await self.channel.send(f'🏚️ **{self.mention(d)}\'s house has been destroyed!**\n⚔️ Destroyed by {self.mention(a)}.')
            if len(self.alive())<=1: await self.finish('last',a if a.alive() else None)
        return True,f'{damage}{" 💥 CRITICAL HIT!" if crit else ""}'

    async def leave(self, uid):
        p=self.get(uid)
        if not p:return False,'❌ You are not in this game.'
        if self.phase=='lobby':
            del self.players[uid]
            if not self.players: await self.finish('empty'); return True,'🚪 You left. The empty lobby was removed.'
            if uid==self.host:
                humans=[x for x in self.players.values() if not x.npc]
                if humans:self.host=humans[0].uid
            await self.cog.refresh(self);return True,'🚪 You left the lobby.'
        del self.players[uid]
        alive=self.alive()
        if len(alive)==1: await self.finish('left',alive[0]);return True,'🚪 You left the game.'
        if not alive: await self.finish('empty');return True,'🚪 You left the game.'
        await self.cog.refresh(self);return True,'🚪 You left the game.'

    async def npcs(self):
        try:
            await asyncio.sleep(PREP_TIME)
            while not self.finished:
                for p in list(self.alive()):
                    if not p.npc: continue
                    if p.coins<1000 and random.random()<.65:self.mine(p);continue
                    for kind in ('weapon','armor','house'):
                        if random.random()<.3:
                            ok,_=self.upgrade(p,kind)
                            if ok:break
                    else:
                        targets=[x for x in self.alive() if x.uid!=p.uid]
                        if targets: await self.attack(p.uid,random.choice(targets).uid)
                await asyncio.sleep(8)
        except asyncio.CancelledError:pass
        except Exception as ex:print('[KINGDOM NPC]',ex)

    async def finish(self, reason='time', forced=None):
        if self.finished:return
        self.finished=True
        for t in (self.timer_task,self.npc_task):
            if t and not t.done():t.cancel()
        alive=self.alive()
        winner=forced
        if not winner and reason=='time': winner=max([p for p in self.players.values() if not p.eliminated],key=lambda p:(p.house,p.hp,p.power(),p.coins),default=None)
        if winner and not winner.npc:self.cog.add_win(self.guild,winner)
        e=discord.Embed(title='🏆 KINGDOM WARS — VICTORY' if winner else '🏁 KINGDOM WARS — GAME OVER',description=(f'👑 **{self.mention(winner)}** wins the match!' if winner else 'The match has ended.'),color=discord.Color.green() if winner else discord.Color.orange())
        e.add_field(name='📜 Result',value={'time':'⏱️ The 20-minute War Phase ended.','last':'⚔️ Only one kingdom remained.','left':'🚪 A player left and the remaining kingdom wins.','empty':'No players remained.'}.get(reason,'The match ended.'),inline=False)
        rows=sorted(self.players.values(),key=lambda p:(p.eliminated,-p.house,-p.hp,-p.power()))[:10]
        e.add_field(name='📊 Final Standings',value='\n'.join(f'**{i}.** {self.mention(p)} — 🏠 Lv.{p.house} • ⭐ {p.power()} Power' for i,p in enumerate(rows,1)) or 'No players',inline=False)
        e.set_footer(text='This match is temporary. Create a new game from !kingdom.')
        if self.message:
            try:await self.message.edit(embed=e,view=None)
            except discord.HTTPException:pass
        else:
            try:await self.channel.send(embed=e)
            except discord.HTTPException:pass
        self.cog.matches.pop(self.guild.id,None)

# --------------------------- Views ---------------------------

class MainView(discord.ui.View):
    def __init__(self,cog):super().__init__(timeout=180);self.cog=cog
    @discord.ui.button(label='Create Game',emoji='🏰',style=discord.ButtonStyle.success)
    async def create(self,i,b):await i.response.send_modal(CreateModal(self.cog))
    @discord.ui.button(label='Join Game',emoji='🔎',style=discord.ButtonStyle.primary)
    async def join(self,i,b):await self.cog.available(i)
    @discord.ui.button(label='NPC Game',emoji='🤖',style=discord.ButtonStyle.secondary)
    async def npc(self,i,b):await i.response.send_modal(NPCModal(self.cog))
    @discord.ui.button(label='Top 10',emoji='🏆',style=discord.ButtonStyle.secondary)
    async def top(self,i,b):await self.cog.top(i)

class CreateModal(discord.ui.Modal,title='Create Kingdom Wars'):
    name=discord.ui.TextInput(label='Game Name',placeholder='Shadow Kingdom',max_length=40)
    password=discord.ui.TextInput(label='Password',placeholder='Required',max_length=32)
    def __init__(self,cog):super().__init__();self.cog=cog
    async def on_submit(self,i):await self.cog.create(i,self.name.value.strip(),self.password.value)

class NPCModal(discord.ui.Modal,title='Create NPC Kingdom Wars'):
    count=discord.ui.TextInput(label='Number of NPCs',placeholder='Example: 5',max_length=3)
    name=discord.ui.TextInput(label='Game Name',placeholder='Solo Kingdom',max_length=40)
    def __init__(self,cog):super().__init__();self.cog=cog
    async def on_submit(self,i):
        try:n=int(self.count.value)
        except ValueError:await i.response.send_message('❌ NPC count must be a number.',ephemeral=True);return
        if n<1 or n>NPC_CAP:await i.response.send_message(f'❌ NPC count must be between 1 and {NPC_CAP}.',ephemeral=True);return
        await self.cog.create_npc(i,n,self.name.value.strip())

class PasswordModal(discord.ui.Modal,title='Enter Game Password'):
    password=discord.ui.TextInput(label='Password',max_length=32)
    def __init__(self,cog,match):super().__init__();self.cog=cog;self.match=match
    async def on_submit(self,i):
        if self.password.value!=self.match.password:await i.response.send_message('❌ Incorrect password.',ephemeral=True);return
        await self.cog.join(i,self.match)

class LobbyView(discord.ui.View):
    def __init__(self,cog,m):super().__init__(timeout=None);self.cog=cog;self.m=m
    @discord.ui.button(label='Join Game',emoji='➕',style=discord.ButtonStyle.success)
    async def join(self,i,b):
        if i.user.id in self.m.players:await i.response.send_message('ℹ️ You are already in this game.',ephemeral=True);return
        await i.response.send_modal(PasswordModal(self.cog,self.m))
    @discord.ui.button(label='Leave',emoji='🚪',style=discord.ButtonStyle.secondary)
    async def leave(self,i,b):
        ok,msg=await self.m.leave(i.user.id);await i.response.send_message(msg,ephemeral=True)
    @discord.ui.button(label='Start Game',emoji='▶️',style=discord.ButtonStyle.primary)
    async def start(self,i,b):
        if i.user.id!=self.m.host:await i.response.send_message('❌ Only the host can start this game.',ephemeral=True);return
        if len(self.m.players)<MIN_PLAYERS:await i.response.send_message('❌ At least 2 players are required to start.',ephemeral=True);return
        await i.response.defer();await self.m.start();await self.cog.refresh(self)

class GameView(discord.ui.View):
    def __init__(self,cog,m):super().__init__(timeout=None);self.cog=cog;self.m=m
    @discord.ui.button(label='Grind',emoji='⛏️',style=discord.ButtonStyle.primary)
    async def grind(self,i,b):await self.cog.grind(i,self.m)
    @discord.ui.button(label='Shop',emoji='🛒',style=discord.ButtonStyle.success)
    async def shop(self,i,b):await self.cog.shop(i,self.m)
    @discord.ui.button(label='Attack',emoji='⚔️',style=discord.ButtonStyle.danger)
    async def attack(self,i,b):await self.cog.targets(i,self.m)
    @discord.ui.button(label='House',emoji='🏠',style=discord.ButtonStyle.secondary)
    async def house(self,i,b):await self.cog.house(i,self.m)
    @discord.ui.button(label='Recovery',emoji='❤️',style=discord.ButtonStyle.secondary)
    async def recovery(self,i,b):await self.cog.recovery(i,self.m)
    @discord.ui.button(label='World',emoji='🗺️',style=discord.ButtonStyle.secondary)
    async def world(self,i,b):await self.cog.world(i,self.m)
    @discord.ui.button(label='Leave Game',emoji='🚪',style=discord.ButtonStyle.secondary,row=2)
    async def leave(self,i,b):ok,msg=await self.m.leave(i.user.id);await i.response.send_message(msg,ephemeral=True)

class SimpleView(discord.ui.View):
    def __init__(self,cog,m):super().__init__(timeout=120);self.cog=cog;self.m=m

class GrindView(SimpleView):
    @discord.ui.button(label='Mining',emoji='⛏️',style=discord.ButtonStyle.primary)
    async def mine(self,i,b):
        p=self.m.get(i.user.id)
        if not p or not p.alive():await i.response.send_message('❌ You cannot mine.',ephemeral=True);return
        ok,msg=self.m.mine(p);await i.response.send_message(msg if ok else '⏳ '+msg,ephemeral=True)
    @discord.ui.button(label='Luck Box',emoji='🎁',style=discord.ButtonStyle.success)
    async def luck(self,i,b):
        p=self.m.get(i.user.id)
        if not p or not p.alive():await i.response.send_message('❌ You cannot use this.',ephemeral=True);return
        ok,msg=self.m.luckbox(p);await i.response.send_message(msg,ephemeral=True)
    @discord.ui.button(label='Back',emoji='↩️',style=discord.ButtonStyle.secondary)
    async def back(self,i,b):await i.response.edit_message(embed=self.m.embed(self.m.get(i.user.id)),view=GameView(self.cog,self.m))

class ShopView(SimpleView):
    @discord.ui.button(label='Weapon',emoji='⚔️',style=discord.ButtonStyle.danger)
    async def weapon(self,i,b):await self.buy(i,'weapon')
    @discord.ui.button(label='Armor',emoji='🛡️',style=discord.ButtonStyle.primary)
    async def armor(self,i,b):await self.buy(i,'armor')
    @discord.ui.button(label='House Protection',emoji='🏠',style=discord.ButtonStyle.success)
    async def houseup(self,i,b):await self.buy(i,'house')
    async def buy(self,i,k):
        p=self.m.get(i.user.id)
        if not p:await i.response.send_message('❌ You are not in this game.',ephemeral=True);return
        ok,msg=self.m.upgrade(p,k);await i.response.send_message(msg+f'\n💰 Coins: **{fmt(p.coins)}**',ephemeral=True)
    @discord.ui.button(label='Back',emoji='↩️',style=discord.ButtonStyle.secondary,row=1)
    async def back(self,i,b):await i.response.edit_message(embed=self.m.embed(self.m.get(i.user.id)),view=GameView(self.cog,self.m))

class RecoveryView(SimpleView):
    @discord.ui.button(label='Recover with Coins',emoji='💰',style=discord.ButtonStyle.success)
    async def coins(self,i,b):
        p=self.m.get(i.user.id);ok,msg=self.m.recover(p) if p else (False,'❌ You are not in this game.');await i.response.send_message(msg,ephemeral=True)
    @discord.ui.button(label='Use Recovery Potion',emoji='🧪',style=discord.ButtonStyle.primary)
    async def potion(self,i,b):
        p=self.m.get(i.user.id);ok,msg=self.m.recover(p,True) if p else (False,'❌ You are not in this game.');await i.response.send_message(msg,ephemeral=True)
    @discord.ui.button(label='Back',emoji='↩️',style=discord.ButtonStyle.secondary,row=1)
    async def back(self,i,b):await i.response.edit_message(embed=self.m.embed(self.m.get(i.user.id)),view=GameView(self.cog,self.m))

class TargetSelect(discord.ui.Select):
    def __init__(self,cog,m):
        self.cog,self.m=cog,m
        opts=[discord.SelectOption(label=p.name[:100],value=str(p.uid),emoji='🏰') for p in m.alive()]
        super().__init__(placeholder='Choose a kingdom to attack',options=opts[:25])
    async def callback(self,i):
        async with self.m.lock:ok,msg=await self.m.attack(i.user.id,int(self.values[0]))
        await i.response.send_message(f'⚔️ Attack successful! **{msg} damage**.' if ok else msg,ephemeral=True)
        await self.cog.refresh(self.m)

class TargetView(SimpleView):
    def __init__(self,cog,m):super().__init__(cog,m);self.add_item(TargetSelect(cog,m))
    @discord.ui.button(label='Back',emoji='↩️',style=discord.ButtonStyle.secondary,row=1)
    async def back(self,i,b):await i.response.edit_message(embed=self.m.embed(self.m.get(i.user.id)),view=GameView(self.cog,self.m))

# --------------------------- Cog ---------------------------

class KingdomWars(commands.Cog):
    def __init__(self,bot):
        self.bot=bot;self.matches={}
        self.db=sqlite3.connect(DB_FILE)
        self.db.execute('CREATE TABLE IF NOT EXISTS kingdom_wins (guild_id INTEGER,user_id INTEGER,username TEXT,wins INTEGER DEFAULT 0,PRIMARY KEY(guild_id,user_id))');self.db.commit()
    def cog_unload(self):
        for m in self.matches.values():
            for t in (m.timer_task,m.npc_task):
                if t and not t.done():t.cancel()
        self.db.close()
    def add_win(self,guild,p):
        self.db.execute('INSERT INTO kingdom_wins VALUES (?,?,?,1) ON CONFLICT(guild_id,user_id) DO UPDATE SET username=excluded.username,wins=wins+1',(guild.id,p.uid,p.name));self.db.commit()
    def rows(self,gid):return self.db.execute('SELECT username,wins FROM kingdom_wins WHERE guild_id=? ORDER BY wins DESC,username LIMIT 10',(gid,)).fetchall()

    @commands.command(name='kingdom')
    @commands.cooldown(1,2,commands.BucketType.user)
    async def kingdom(self,ctx,action=None):
        action=action.lower() if action else None
        if action=='leave':
            m=self.matches.get(ctx.guild.id)
            if not m:await ctx.send('❌ There is no active Kingdom Wars match.');return
            ok,msg=await m.leave(ctx.author.id);await ctx.send(msg);return
        if action=='top':await self.send_top(ctx);return
        m=self.matches.get(ctx.guild.id)
        if m and not m.finished:
            await ctx.send(embed=m.lobby_embed() if m.phase=='lobby' else m.embed(m.get(ctx.author.id)),view=LobbyView(self,m) if m.phase=='lobby' else GameView(self,m));return
        e=discord.Embed(title='👑 KINGDOM WARS',description='Build your kingdom, mine Coins, upgrade your gear, and conquer other kingdoms.\n\n🏰 **Create Game**\n🔎 **Join Game**\n🤖 **NPC Game**\n🏆 **Top 10**',color=discord.Color.gold());e.add_field(name='⚔️ Match Rules',value='🛡️ 5 min Preparation\n⚔️ 20 min War\n❤️ House: 200 HP\n🏠 Higher Protection = less damage\n🚪 Players can leave anytime',inline=False);e.set_footer(text='All game UI is in English.')
        await ctx.send(embed=e,view=MainView(self))

    async def create(self,i,name,password):
        g=i.guild
        if g.id in self.matches and not self.matches[g.id].finished:await i.response.send_message('❌ This server already has an active match.',ephemeral=True);return
        m=Match(self,g,i.channel,i.user.id,name,password);m.add_user(i.user);self.matches[g.id]=m
        try:await i.response.send_message(embed=m.lobby_embed(),view=LobbyView(self,m));m.message=await i.original_response()
        except discord.HTTPException:self.matches.pop(g.id,None)
    async def create_npc(self,i,n,name):
        g=i.guild
        if g.id in self.matches and not self.matches[g.id].finished:await i.response.send_message('❌ This server already has an active match.',ephemeral=True);return
        m=Match(self,g,i.channel,i.user.id,name,'NPC',n);m.add_user(i.user);m.add_npcs(n);self.matches[g.id]=m
        try:await i.response.send_message(embed=m.lobby_embed(),view=LobbyView(self,m));m.message=await i.original_response()
        except discord.HTTPException:self.matches.pop(g.id,None)
    async def available(self,i):
        games=[m for m in self.matches.values() if not m.finished and m.phase=='lobby' and not m.npc_count]
        if not games:await i.response.send_message('🔎 **No available games.**\nCreate one with **Create Game**.',ephemeral=True);return
        e=discord.Embed(title='🔎 AVAILABLE KINGDOM GAMES',description='Select a game to enter its password.',color=discord.Color.blue());
        for m in games[:10]:e.add_field(name=f'🏰 {m.name}',value=f'👥 {len(m.players)} players\n👑 Host: <@{m.host}>\n🔐 Password Required',inline=True)
        v=discord.ui.View(timeout=120)
        sel=discord.ui.Select(placeholder='Select a game',options=[discord.SelectOption(label=m.name[:100],value=str(m.guild.id),emoji='🏰') for m in games[:25]])
        async def cb(x):await x.response.send_modal(PasswordModal(self,self.matches[int(sel.values[0])]))
        sel.callback=cb;v.add_item(sel);await i.response.send_message(embed=e,view=v,ephemeral=True)
    async def join(self,i,m):
        if m.phase!='lobby' or m.finished:await i.response.send_message('❌ This game is no longer accepting players.',ephemeral=True);return
        if i.user.id in m.players:await i.response.send_message('ℹ️ You are already in this game.',ephemeral=True);return
        m.add_user(i.user);await i.response.send_message(f'✅ You joined **{m.name}**.',ephemeral=True);await self.refresh(m)
    async def refresh(self,m):
        if not m.message or m.finished:return
        try:await m.message.edit(embed=m.lobby_embed() if m.phase=='lobby' else m.embed(m.get(m.host)),view=LobbyView(self,m) if m.phase=='lobby' else GameView(self,m))
        except discord.HTTPException:pass

    async def grind(self,i,m):
        p=m.get(i.user.id)
        if not p or not p.alive():await i.response.send_message('❌ You cannot use Grind.',ephemeral=True);return
        e=discord.Embed(title='⛏️ GRIND',description='Choose your activity.\n\n⛏️ **Mining** — click to earn Coins, Loot, or Recovery Potions.\n🎁 **Luck Box** — costs 250 Coins and can contain rare rewards.',color=discord.Color.dark_gold());e.add_field(name='💰 Coins',value=fmt(p.coins));e.add_field(name='🧪 Potions',value=str(p.potions));e.add_field(name='🎁 Loot',value=str(p.loot));await i.response.send_message(embed=e,view=GrindView(self,m),ephemeral=True)
    async def shop(self,i,m):
        p=m.get(i.user.id)
        if not p:await i.response.send_message('❌ You are not in this game.',ephemeral=True);return
        e=discord.Embed(title='🛒 KINGDOM SHOP',description=f'💰 Coins: **{fmt(p.coins)}**',color=discord.Color.green());e.add_field(name='⚔️ Weapon',value=f'Current: **{p.weapon}** → {nxt(p.weapon) or "MAX"}',inline=False);e.add_field(name='🛡️ Armor',value=f'Current: **{p.armor}** → {nxt(p.armor) or "MAX"}',inline=False);e.add_field(name='🏠 House Protection',value=f'Current: **Lv.{p.house}** → {"Lv."+str(p.house+1) if p.house<10 else "MAX"}',inline=False);await i.response.send_message(embed=e,view=ShopView(self,m),ephemeral=True)
    async def recovery(self,i,m):
        p=m.get(i.user.id);e=discord.Embed(title='❤️ HOUSE RECOVERY',description=f'House Health: **{p.hp}/200**\n\n💰 100 Coins → up to 50 HP\n🧪 1 Recovery Potion → up to 80 HP',color=discord.Color.green());await i.response.send_message(embed=e,view=RecoveryView(self,m),ephemeral=True)
    async def house(self,i,m):
        p=m.get(i.user.id);red=int(HOUSE[p.house][1]*100);e=discord.Embed(title='🏠 YOUR HOUSE',description=f'🏠 Protection Level: **{p.house}**\n❤️ Health: **{p.hp}/200** `{bar(p.hp)}`\n🛡️ Damage Reduction: **{red}%**\n⚔️ Weapon: **{p.weapon}**\n🛡️ Armor: **{p.armor}**\n⭐ Power: **{p.power()}**',color=discord.Color.blue());await i.response.send_message(embed=e,ephemeral=True)
    async def targets(self,i,m):
        p=m.get(i.user.id)
        if not p or not p.alive():await i.response.send_message('❌ You cannot attack.',ephemeral=True);return
        if m.phase!='war':await i.response.send_message('🔒 Attacks are locked during the Preparation Phase.',ephemeral=True);return
        targets=[x for x in m.alive() if x.uid!=p.uid]
        if not targets:await i.response.send_message('❌ No valid targets remain.',ephemeral=True);return
        e=discord.Embed(title='⚔️ CHOOSE A TARGET',description='Select a kingdom to attack.',color=discord.Color.red());await i.response.send_message(embed=e,view=TargetView(self,m),ephemeral=True)
    async def world(self,i,m):
        e=discord.Embed(title='🗺️ KINGDOM WORLD',description='All kingdoms in this match.',color=discord.Color.dark_green());rows=sorted(m.players.values(),key=lambda p:(p.eliminated,-p.power()));e.add_field(name='🏰 Kingdoms',value='\n'.join(f'{"💀" if p.eliminated else "🏰"} {m.mention(p)} — ❤️ {p.hp}/200 • 🏠 Lv.{p.house} • ⭐ {p.power()}' for p in rows)[:3900] or 'No kingdoms remain.',inline=False);await i.response.send_message(embed=e,ephemeral=True)
    async def top(self,i):
        rows=self.rows(i.guild.id);e=discord.Embed(title='🏆 KINGDOM WARS — TOP 10',description='Players with the most victories.',color=discord.Color.gold());e.add_field(name='👑 Champions',value='\n'.join(f'**{n}.** {name} — 🏆 **{wins} Wins**' for n,(name,wins) in enumerate(rows,1)) if rows else 'No wins recorded yet.',inline=False);await i.response.send_message(embed=e,ephemeral=True)
    async def send_top(self,ctx):
        rows=self.rows(ctx.guild.id);await ctx.send(embed=discord.Embed(title='🏆 KINGDOM WARS — TOP 10',description='\n'.join(f'**{n}.** {name} — 🏆 **{wins} Wins**' for n,(name,wins) in enumerate(rows,1)) or 'No wins recorded yet.',color=discord.Color.gold()))
    @kingdom.error
    async def err(self,ctx,error):
        if isinstance(error,commands.CommandOnCooldown):await ctx.send(f'⏳ Please wait {error.retry_after:.1f}s.')
        else:print('[KINGDOM ERROR]',type(error).__name__,error)

async def setup(bot):
    await bot.add_cog(KingdomWars(bot))
