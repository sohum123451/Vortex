import asyncio
import random
import sqlite3
from datetime import datetime, timezone
import discord
from discord.ext import commands
from utils import DB_FILE, MAIN_COLOR, SUCCESS_COLOR, ERROR_COLOR, WARN_COLOR, INFO_COLOR

RPG_CLASSES = {
    "Warrior": {"hp": 140, "attack": 22, "defense": 16, "emoji": "⚔️", "desc": "High HP & sturdy armor defense."},
    "Mage": {"hp": 90, "attack": 32, "defense": 8, "emoji": "🧙", "desc": "Extreme magical burst damage with low defense."},
    "Rogue": {"hp": 110, "attack": 26, "defense": 12, "emoji": "🗡️", "desc": "High agility, critical strike chance, and swift dodges."},
    "Paladin": {"hp": 160, "attack": 18, "defense": 22, "emoji": "🛡️", "desc": "Unyielding holy tank with self-healing aura."},
    "Necromancer": {"hp": 105, "attack": 28, "defense": 10, "emoji": "💀", "desc": "Drains life essence and summons undead minions."},
}

MONSTERS = [
    {"name": "Goblin Scout", "hp": 45, "atk": 10, "xp": 25, "coins": 30, "floor": 1},
    {"name": "Forest Wolf", "hp": 60, "atk": 14, "xp": 40, "coins": 50, "floor": 1},
    {"name": "Skeleton Warrior", "hp": 85, "atk": 18, "xp": 65, "coins": 80, "floor": 2},
    {"name": "Cave Troll", "hp": 130, "atk": 25, "xp": 110, "coins": 140, "floor": 2},
    {"name": "Dark Sorcerer", "hp": 160, "atk": 35, "xp": 180, "coins": 220, "floor": 3},
    {"name": "Shadow Dragon", "hp": 300, "atk": 50, "xp": 400, "coins": 600, "floor": 4},
]

BOSSES = [
    {"name": "Infernal Dragon Lord", "hp": 800, "atk": 70, "xp": 1200, "coins": 2000},
    {"name": "Lich King of the Abyss", "hp": 1000, "atk": 85, "xp": 1800, "coins": 3000},
    {"name": "Abyssal Titan", "hp": 1500, "atk": 110, "xp": 3000, "coins": 5000},
]

SHOP_ITEMS = {
    "Iron Broadsword": {"type": "weapon", "power": 15, "cost": 250, "emoji": "🗡️"},
    "Obsidian Greatsword": {"type": "weapon", "power": 35, "cost": 800, "emoji": "⚔️"},
    "Excalibur": {"type": "weapon", "power": 65, "cost": 2500, "emoji": "✨"},
    "Chainmail Armor": {"type": "armor", "power": 15, "cost": 250, "emoji": "🛡️"},
    "Dragonscale Plate": {"type": "armor", "power": 40, "cost": 1000, "emoji": "🐉"},
    "Aegis Shield": {"type": "armor", "power": 70, "cost": 3000, "emoji": "🛡️"},
    "Health Potion": {"type": "potion", "power": 60, "cost": 60, "emoji": "🧪"},
    "Mega Health Elixir": {"type": "potion", "power": 150, "cost": 150, "emoji": "🍷"},
}

PETS = {
    "Baby Dragon": {"atk_bonus": 15, "hp_bonus": 30, "cost": 1200, "emoji": "🐲"},
    "Spirit Wolf": {"atk_bonus": 10, "hp_bonus": 20, "cost": 600, "emoji": "🐺"},
    "Phoenix Chick": {"atk_bonus": 20, "hp_bonus": 40, "cost": 2000, "emoji": "🦅"},
    "Cyber Hound": {"atk_bonus": 25, "hp_bonus": 50, "cost": 3500, "emoji": "🐕"},
}

class RPGAdventure(commands.Cog):
    """Deep interactive text RPG with dungeons, bosses, crafting, pets, and PvP duels."""

    def __init__(self, bot):
        self.bot = bot

    def get_player(self, user_id: str):
        with sqlite3.connect(DB_FILE) as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT class_type, level, xp, hp, max_hp, attack, defense, coins,
                       equipped_weapon, equipped_armor, pet, dungeon_floor
                FROM rpg_players WHERE user_id = ?
                """,
                (user_id,),
            )
            row = cur.fetchone()
            if not row:
                cur.execute(
                    """
                    INSERT INTO rpg_players (user_id, class_type, level, xp, hp, max_hp, attack, defense, coins)
                    VALUES (?, 'Warrior', 1, 0, 140, 140, 22, 16, 150)
                    """,
                    (user_id,),
                )
                conn.commit()
                return "Warrior", 1, 0, 140, 140, 22, 16, 150, "Wooden Sword", "Cloth Tunic", "None", 1
            return row

    def update_player(self, user_id: str, **kwargs):
        allowed = {"class_type", "level", "xp", "hp", "max_hp", "attack", "defense", "coins", "equipped_weapon", "equipped_armor", "pet", "dungeon_floor"}
        with sqlite3.connect(DB_FILE) as conn:
            cur = conn.cursor()
            sets = []
            vals = []
            for k, v in kwargs.items():
                if k in allowed:
                    sets.append(f"{k} = ?")
                    vals.append(v)
            if not sets:
                return
            vals.append(user_id)
            query = f"UPDATE rpg_players SET {', '.join(sets)} WHERE user_id = ?"
            cur.execute(query, vals)
            conn.commit()

    @commands.hybrid_command(name="rpg_profile", description="View your RPG hero stats, equipment, and level")
    async def rpg_profile(self, ctx, member: discord.Member = None):
        target = member or ctx.author
        cls, lvl, xp, hp, max_hp, atk, df, coins, weapon, armor, pet, floor = self.get_player(str(target.id))
        next_xp = lvl * 100

        embed = discord.Embed(
            title=f"⚔️ Hero Profile: {target.display_name}",
            description=f"**Class:** `{cls}` • **Level:** `{lvl}`\n**XP:** `{xp}/{next_xp}` • **Dungeon Floor:** `{floor}`",
            color=MAIN_COLOR,
            timestamp=datetime.now(timezone.utc),
        )
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.add_field(name="❤️ Health", value=f"`{hp}/{max_hp}` HP", inline=True)
        embed.add_field(name="⚔️ Attack Power", value=f"`{atk}` ATK", inline=True)
        embed.add_field(name="🛡️ Defense", value=f"`{df}` DEF", inline=True)
        embed.add_field(name="🪙 Gold Coins", value=f"`{coins:,}` Gold", inline=True)
        embed.add_field(name="🗡️ Weapon", value=f"`{weapon}`", inline=True)
        embed.add_field(name="🦺 Armor", value=f"`{armor}`", inline=True)
        embed.add_field(name="🐾 Companion Pet", value=f"`{pet}`", inline=True)
        await ctx.reply(embed=embed)

    @commands.command(name="chooseclass", description="Choose your RPG class: &chooseclass <Warrior/Mage/Rogue/Paladin/Necromancer>")
    async def chooseclass(self, ctx, class_name: str):
        cname = class_name.title()
        if cname not in RPG_CLASSES:
            avail = ", ".join(RPG_CLASSES.keys())
            return await ctx.reply(f"❌ Invalid class! Available classes: `{avail}`")
        info = RPG_CLASSES[cname]
        self.update_player(
            str(ctx.author.id),
            class_type=cname,
            hp=info["hp"],
            max_hp=info["hp"],
            attack=info["attack"],
            defense=info["defense"],
        )
        await ctx.reply(f"{info['emoji']} **Class Chosen:** You are now a **{cname}**!\n*{info['desc']}*")

    @commands.command(name="classes", description="List all RPG classes and combat attributes")
    async def classes(self, ctx):
        embed = discord.Embed(title="🛡️ Vortex RPG Classes", color=INFO_COLOR)
        for name, data in RPG_CLASSES.items():
            embed.add_field(
                name=f"{data['emoji']} {name}",
                value=f"**HP:** `{data['hp']}` | **ATK:** `{data['attack']}` | **DEF:** `{data['defense']}`\n*{data['desc']}*",
                inline=False,
            )
        await ctx.reply(embed=embed)

    @commands.hybrid_command(name="hunt_monster", description="Hunt wild monsters in the wilderness for Gold & XP")
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def hunt_monster(self, ctx):
        uid = str(ctx.author.id)
        cls, lvl, xp, hp, max_hp, atk, df, coins, weapon, armor, pet, floor = self.get_player(uid)
        if hp <= 0:
            return await ctx.reply("💀 You are defeated! Use `&heal_hero` to restore your health before fighting.")

        eligible = [m for m in MONSTERS if m["floor"] <= floor]
        monster = random.choice(eligible)
        m_hp = monster["hp"]
        m_atk = monster["atk"]

        # Player attacks
        p_dmg = max(5, atk + random.randint(-4, 6))
        m_hp -= p_dmg
        m_dmg = max(1, m_atk - (df // 2) + random.randint(-2, 3))
        new_hp = max(0, hp - m_dmg)

        if m_hp <= 0:
            won_xp = monster["xp"]
            won_coins = monster["coins"]
            new_xp = xp + won_xp
            new_lvl = lvl
            next_xp = lvl * 100
            lvl_up_str = ""
            if new_xp >= next_xp:
                new_lvl += 1
                new_xp -= next_xp
                max_hp += 20
                atk += 5
                df += 3
                new_hp = max_hp
                lvl_up_str = f"\n🎉 **LEVEL UP!** You reached **Level {new_lvl}**! (+20 Max HP, +5 ATK, +3 DEF)"

            self.update_player(
                uid,
                hp=new_hp,
                xp=new_xp,
                level=new_lvl,
                max_hp=max_hp,
                attack=atk,
                defense=df,
                coins=coins + won_coins,
            )
            embed = discord.Embed(
                title=f"⚔️ Wilderness Hunt: {monster['name']} Defeated!",
                description=f"💥 You struck for **{p_dmg} DMG** and vanquished the **{monster['name']}**!\n"
                            f"🎁 **Loot:** `+{won_coins} Gold` • `+{won_xp} XP`\n"
                            f"❤️ **Remaining HP:** `{new_hp}/{max_hp}`{lvl_up_str}",
                color=SUCCESS_COLOR,
            )
            await ctx.reply(embed=embed)
        else:
            self.update_player(uid, hp=new_hp)
            embed = discord.Embed(
                title=f"⚔️ Wilderness Hunt: {monster['name']}",
                description=f"💥 You dealt **{p_dmg} DMG**.\n"
                            f"🩸 The monster retaliated for **{m_dmg} DMG**!\n"
                            f"❤️ **Your HP:** `{new_hp}/{max_hp}` | **Monster HP:** `{m_hp}`",
                color=WARN_COLOR,
            )
            await ctx.reply(embed=embed)

    @commands.command(name="dungeon", description="Explore deep dungeon floors for rare loot")
    @commands.cooldown(1, 120, commands.BucketType.user)
    async def dungeon(self, ctx):
        uid = str(ctx.author.id)
        cls, lvl, xp, hp, max_hp, atk, df, coins, weapon, armor, pet, floor = self.get_player(uid)
        if hp < 40:
            return await ctx.reply("❌ You are too wounded for the dungeon! Use `&heal_hero` first.")

        p_dmg = atk * 2 + random.randint(5, 15)
        floor_dmg = max(10, floor * 15 - df)
        new_hp = max(0, hp - floor_dmg)
        loot_gold = floor * 180 + random.randint(50, 150)
        loot_xp = floor * 120 + random.randint(30, 80)
        new_floor = floor + 1 if random.random() < 0.6 else floor

        self.update_player(uid, hp=new_hp, coins=coins + loot_gold, xp=xp + loot_xp, dungeon_floor=new_floor)
        embed = discord.Embed(
            title=f"🏰 Dungeon Expedition — Floor {floor}",
            description=f"🗡️ You delved deep into the abyss, defeating dungeon guardians!\n"
                        f"🩸 Sustained **{floor_dmg} DMG** (Current HP: `{new_hp}/{max_hp}`)\n"
                        f"💰 **Dungeon Loot:** `+{loot_gold:,} Gold` • `+{loot_xp} XP`\n"
                        f"🚪 **Highest Floor Cleared:** Floor `{new_floor}`",
            color=INFO_COLOR,
        )
        await ctx.reply(embed=embed)

    @commands.command(name="boss_raid", description="Join server boss raid for legendary rewards")
    @commands.cooldown(1, 600, commands.BucketType.user)
    async def boss_raid(self, ctx):
        uid = str(ctx.author.id)
        cls, lvl, xp, hp, max_hp, atk, df, coins, weapon, armor, pet, floor = self.get_player(uid)
        boss = random.choice(BOSSES)

        success = (atk + df) > (boss["atk"] // 2) or random.random() < 0.4
        if success:
            reward_gold = boss["coins"]
            reward_xp = boss["xp"]
            self.update_player(uid, coins=coins + reward_gold, xp=xp + reward_xp)
            embed = discord.Embed(
                title=f"👑 Epic Boss Raid: {boss['name']} Vanquished!",
                description=f"⚔️ With mighty courage, you slayed the **{boss['name']}**!\n"
                            f"🏆 **Legendary Bounty:** `+{reward_gold:,} Gold` • `+{reward_xp:,} XP`",
                color=SUCCESS_COLOR,
            )
            await ctx.reply(embed=embed)
        else:
            self.update_player(uid, hp=max(1, hp // 4))
            embed = discord.Embed(
                title=f"💀 Boss Raid Failed: {boss['name']}",
                description=f"💥 The **{boss['name']}** unleashed its devastating wrath! You barely escaped with your life.",
                color=ERROR_COLOR,
            )
            await ctx.reply(embed=embed)

    @commands.command(name="pvp_duel", description="Challenge another member to a turn-based RPG duel")
    async def pvp_duel(self, ctx, member: discord.Member):
        if member == ctx.author or member.bot:
            return await ctx.reply("❌ Invalid opponent.")
        p1 = self.get_player(str(ctx.author.id))
        p2 = self.get_player(str(member.id))

        p1_power = p1[5] + p1[6] + random.randint(1, 20)
        p2_power = p2[5] + p2[6] + random.randint(1, 20)

        winner = ctx.author if p1_power >= p2_power else member
        loser = member if winner == ctx.author else ctx.author
        wager = 100

        self.update_player(str(winner.id), coins=self.get_player(str(winner.id))[7] + wager)
        self.update_player(str(loser.id), coins=max(0, self.get_player(str(loser.id))[7] - wager))

        embed = discord.Embed(
            title=f"⚔️ PvP Arena: {ctx.author.display_name} vs {member.display_name}",
            description=f"🏆 **{winner.mention}** won the duel and claimed **+{wager} Gold** from {loser.mention}!",
            color=WARN_COLOR,
        )
        await ctx.reply(embed=embed)

    @commands.command(name="rpg_shop", description="Browse weapons, armor, and potions in the RPG shop")
    async def rpg_shop(self, ctx):
        embed = discord.Embed(title="🛒 Vortex RPG Armory & Shop", color=MAIN_COLOR)
        for name, d in SHOP_ITEMS.items():
            embed.add_field(
                name=f"{d['emoji']} {name}",
                value=f"**Type:** `{d['type'].title()}` | **Power:** `+{d['power']}`\n💰 **Price:** `{d['cost']:,} Gold`\n*Buy: `&buy_gear {name}`*",
                inline=False,
            )
        await ctx.reply(embed=embed)

    @commands.command(name="buy_gear", description="Purchase equipment from shop: &buy_gear <item_name>")
    async def buy_gear(self, ctx, *, item_name: str):
        target_item = None
        for k in SHOP_ITEMS:
            if k.lower() == item_name.strip().lower():
                target_item = k
                break
        if not target_item:
            return await ctx.reply("❌ Item not found in shop. Type `&rpg_shop` to view available gear.")

        info = SHOP_ITEMS[target_item]
        uid = str(ctx.author.id)
        cls, lvl, xp, hp, max_hp, atk, df, coins, weapon, armor, pet, floor = self.get_player(uid)

        if coins < info["cost"]:
            return await ctx.reply(f"❌ You need `{info['cost']:,} Gold`, but only have `{coins:,} Gold`.")

        new_coins = coins - info["cost"]
        if info["type"] == "weapon":
            self.update_player(uid, coins=new_coins, equipped_weapon=target_item, attack=atk + info["power"])
            await ctx.reply(f"🗡️ Equipped **{target_item}**! (Attack +{info['power']})")
        elif info["type"] == "armor":
            self.update_player(uid, coins=new_coins, equipped_armor=target_item, defense=df + info["power"], max_hp=max_hp + 30)
            await ctx.reply(f"🛡️ Equipped **{target_item}**! (Defense +{info['power']}, Max HP +30)")
        elif info["type"] == "potion":
            new_hp = min(max_hp, hp + info["power"])
            self.update_player(uid, coins=new_coins, hp=new_hp)
            await ctx.reply(f"🧪 Drank **{target_item}**! Restored **+{info['power']} HP** (Current: `{new_hp}/{max_hp}`).")

    @commands.command(name="heal_hero", description="Restore your hero's health at the town healer")
    async def heal_hero(self, ctx):
        uid = str(ctx.author.id)
        _, _, _, hp, max_hp, _, _, coins, _, _, _, _ = self.get_player(uid)
        cost = 30
        if coins < cost:
            return await ctx.reply("❌ You need at least 30 Gold to visit the town healer.")
        self.update_player(uid, hp=max_hp, coins=coins - cost)
        await ctx.reply(f"✨ **Healed!** Restored to full **{max_hp}/{max_hp} HP** for `{cost} Gold`.")

    @commands.command(name="pet_shop", description="Adopt magical companion pets: &pet_shop")
    async def pet_shop(self, ctx):
        embed = discord.Embed(title="🐾 Vortex Magical Pet Sanctuary", color=INFO_COLOR)
        for name, d in PETS.items():
            embed.add_field(
                name=f"{d['emoji']} {name}",
                value=f"**Buffs:** `+{d['atk_bonus']} ATK`, `+{d['hp_bonus']} HP`\n💰 **Cost:** `{d['cost']:,} Gold`\n*Adopt: `&adopt_pet {name}`*",
                inline=False,
            )
        await ctx.reply(embed=embed)

    @commands.command(name="adopt_pet", description="Adopt a companion pet: &adopt_pet <pet_name>")
    async def adopt_pet(self, ctx, *, pet_name: str):
        target_pet = None
        for k in PETS:
            if k.lower() == pet_name.strip().lower():
                target_pet = k
                break
        if not target_pet:
            return await ctx.reply("❌ Pet not found. Type `&pet_shop` to view available companions.")

        p_info = PETS[target_pet]
        uid = str(ctx.author.id)
        cls, lvl, xp, hp, max_hp, atk, df, coins, weapon, armor, pet, floor = self.get_player(uid)

        if coins < p_info["cost"]:
            return await ctx.reply(f"❌ You need `{p_info['cost']:,} Gold`.")

        self.update_player(
            uid,
            coins=coins - p_info["cost"],
            pet=target_pet,
            attack=atk + p_info["atk_bonus"],
            max_hp=max_hp + p_info["hp_bonus"],
            hp=hp + p_info["hp_bonus"],
        )
        await ctx.reply(f"{p_info['emoji']} **Adopted {target_pet}!** Granted `+{p_info['atk_bonus']} ATK` and `+{p_info['hp_bonus']} Max HP`.")

    @commands.command(name="cast_fireball", description="Cast an explosive Fireball spell")
    async def cast_fireball(self, ctx):
        dmg = random.randint(35, 75)
        await ctx.reply(f"🔥 **FIREBALL!** You channeled arcane magic and blasted for **{dmg} Fire DMG**!")

    @commands.command(name="cast_blizzard", description="Cast a freezing Blizzard spell")
    async def cast_blizzard(self, ctx):
        dmg = random.randint(30, 65)
        await ctx.reply(f"❄️ **BLIZZARD!** Freezing winds dealt **{dmg} Frost DMG** and slowed enemies!")

    @commands.command(name="cast_thunder", description="Cast a devastating Thunderstorm spell")
    async def cast_thunder(self, ctx):
        dmg = random.randint(40, 90)
        await ctx.reply(f"⚡ **THUNDERSTORM!** Lightning struck the battlefield for **{dmg} Shock DMG**!")

    @commands.command(name="cast_holylight", description="Cast a holy healing radiance spell")
    async def cast_holylight(self, ctx):
        heal = random.randint(30, 60)
        await ctx.reply(f"✨ **HOLY RADIANCE!** Divine light enveloped you and restored **+{heal} HP**!")

    @commands.command(name="cast_shadowbolt", description="Cast dark necromancy Shadowbolt")
    async def cast_shadowbolt(self, ctx):
        dmg = random.randint(45, 80)
        await ctx.reply(f"💀 **SHADOWBOLT!** Dark essence drained the foe for **{dmg} Shadow DMG**!")

    @commands.command(name="meditate", description="Meditate to regain spiritual energy and XP")
    @commands.cooldown(1, 300, commands.BucketType.user)
    async def meditate(self, ctx):
        xp_gain = random.randint(30, 70)
        uid = str(ctx.author.id)
        cls, lvl, xp, hp, max_hp, atk, df, coins, weapon, armor, pet, floor = self.get_player(uid)
        self.update_player(uid, xp=xp + xp_gain)
        await ctx.reply(f"🧘 **Meditation Complete:** Found inner peace and gained **+{xp_gain} XP**!")

    @commands.command(name="quest_daily", description="Complete daily adventurer guild quest")
    @commands.cooldown(1, 86400, commands.BucketType.user)
    async def quest_daily(self, ctx):
        reward_gold = random.randint(200, 500)
        reward_xp = random.randint(150, 300)
        uid = str(ctx.author.id)
        cls, lvl, xp, hp, max_hp, atk, df, coins, weapon, armor, pet, floor = self.get_player(uid)
        self.update_player(uid, coins=coins + reward_gold, xp=xp + reward_xp)
        quests = [
            "Escorted a merchant caravan through the bandit pass",
            "Cleared giant spiders from the village granary",
            "Collected rare sunburst herbs from the mountaintop",
        ]
        await ctx.reply(f"📜 **Guild Quest Complete!** *{random.choice(quests)}*\n🎁 **Reward:** `+{reward_gold} Gold` • `+{reward_xp} XP`")

async def setup(bot):
    await bot.add_cog(RPGAdventure(bot))
