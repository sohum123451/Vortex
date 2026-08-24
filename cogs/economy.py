import asyncio
import json
import random
import sqlite3
from datetime import datetime, timezone
import discord
from discord.ext import commands
from utils import DB_FILE, MAIN_COLOR, SUCCESS_COLOR, ERROR_COLOR, INFO_COLOR, WARN_COLOR

class BlackjackView(discord.ui.View):
    def __init__(self, author, bet, economy_cog):
        super().__init__(timeout=60)
        self.author = author
        self.bet = bet
        self.economy_cog = economy_cog
        self.deck = [2, 3, 4, 5, 6, 7, 8, 9, 10, 10, 10, 10, 11] * 4
        random.shuffle(self.deck)
        self.player_hand = [self.deck.pop(), self.deck.pop()]
        self.dealer_hand = [self.deck.pop(), self.deck.pop()]
        self.game_over = False

    def hand_val(self, hand):
        val = sum(hand)
        aces = hand.count(11)
        while val > 21 and aces:
            val -= 10
            aces -= 1
        return val

    def get_embed(self, finished=False):
        p_val = self.hand_val(self.player_hand)
        d_val = self.hand_val(self.dealer_hand)

        embed = discord.Embed(
            title="🃏 Blackjack Casino (21)",
            color=SUCCESS_COLOR if finished else INFO_COLOR,
        )
        embed.add_field(name=f"Your Hand ({p_val})", value="`" + ", ".join(map(str, self.player_hand)) + "`", inline=True)
        if finished:
            embed.add_field(name=f"Dealer Hand ({d_val})", value="`" + ", ".join(map(str, self.dealer_hand)) + "`", inline=True)
        else:
            embed.add_field(name="Dealer Hand", value=f"`{self.dealer_hand[0]}, ❓`", inline=True)
        embed.set_footer(text=f"Bet: {self.bet:,} coins")
        return embed

    @discord.ui.button(label="Hit", emoji="🃏", style=discord.ButtonStyle.primary)
    async def hit(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.author:
            return await interaction.response.send_message("❌ This is not your game.", ephemeral=True)
        if self.game_over:
            return

        self.player_hand.append(self.deck.pop())
        p_val = self.hand_val(self.player_hand)

        if p_val > 21:
            self.game_over = True
            self.economy_cog.update_wallet(str(self.author.id), -self.bet)
            embed = self.get_embed(finished=True)
            embed.description = f"💥 **Bust!** You went over 21 and lost **{self.bet:,} coins**."
            embed.color = ERROR_COLOR
            for item in self.children:
                item.disabled = True
            return await interaction.response.edit_message(embed=embed, view=self)

        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label="Stand", emoji="🛑", style=discord.ButtonStyle.secondary)
    async def stand(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.author:
            return await interaction.response.send_message("❌ This is not your game.", ephemeral=True)
        if self.game_over:
            return

        self.game_over = True
        while self.hand_val(self.dealer_hand) < 17:
            self.dealer_hand.append(self.deck.pop())

        p_val = self.hand_val(self.player_hand)
        d_val = self.hand_val(self.dealer_hand)

        embed = self.get_embed(finished=True)
        if d_val > 21 or p_val > d_val:
            win_amt = self.bet
            self.economy_cog.update_wallet(str(self.author.id), win_amt)
            embed.description = f"🎉 **You Win!** Dealer had {d_val}. You won **+{win_amt:,} coins**!"
            embed.color = SUCCESS_COLOR
        elif p_val < d_val:
            self.economy_cog.update_wallet(str(self.author.id), -self.bet)
            embed.description = f"😢 **Dealer Wins!** Dealer had {d_val}. You lost **-{self.bet:,} coins**."
            embed.color = ERROR_COLOR
        else:
            embed.description = "🤝 **Push!** It's a tie. Your coins have been returned."
            embed.color = WARN_COLOR

        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(embed=embed, view=self)

class Economy(commands.Cog):
    """Deep economy, jobs, mining, shop, inventory, and casino system."""

    def __init__(self, bot):
        self.bot = bot

    def get_account(self, user_id: str):
        with sqlite3.connect(DB_FILE) as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT balance, bank, daily_streak, last_daily, last_weekly, last_work, last_crime, inventory FROM economy WHERE user_id = ?",
                (user_id,),
            )
            row = cur.fetchone()
            if not row:
                cur.execute(
                    "INSERT INTO economy (user_id, balance, bank, daily_streak, inventory) VALUES (?, 0, 0, 0, '{}')",
                    (user_id,),
                )
                conn.commit()
                return 0, 0, 0, None, None, None, None, "{}"
            return (
                row[0],
                row[1],
                row[2] or 0,
                row[3],
                row[4],
                row[5],
                row[6],
                row[7] or "{}",
            )

    def update_wallet(self, user_id: str, amount: int):
        with sqlite3.connect(DB_FILE) as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO economy (user_id, balance, bank) VALUES (?, ?, 0)
                ON CONFLICT(user_id) DO UPDATE SET balance = balance + ?
                """,
                (user_id, amount, amount),
            )
            conn.commit()

    @commands.hybrid_command(name="balance", description="Check your or another member's coin balance")
    async def balance(self, ctx, member: discord.Member = None):
        target = member or ctx.author
        bal, bank, streak, _, _, _, _, _ = self.get_account(str(target.id))

        embed = discord.Embed(title=f"💰 {target.display_name}'s Financial Profile", color=WARN_COLOR)
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.add_field(name="💵 Wallet", value=f"`{bal:,}` coins", inline=True)
        embed.add_field(name="🏦 Bank", value=f"`{bank:,}` coins", inline=True)
        embed.add_field(name="📊 Net Worth", value=f"`{bal + bank:,}` coins", inline=True)
        embed.add_field(name="🔥 Daily Streak", value=f"`{streak}` days", inline=True)
        await ctx.reply(embed=embed)

    @commands.hybrid_command(name="daily", description="Claim daily allowance (streak bonuses up to +1000)")
    async def daily(self, ctx):
        uid = str(ctx.author.id)
        bal, bank, streak, last_daily, _, _, _, _ = self.get_account(uid)
        now = datetime.now(timezone.utc)

        if last_daily:
            try:
                last_dt = datetime.fromisoformat(last_daily)
                if last_dt.tzinfo is None:
                    last_dt = last_dt.replace(tzinfo=timezone.utc)
                elapsed = (now - last_dt).total_seconds()
            except Exception:
                elapsed = 999999

            if elapsed < 86400:
                remaining = 86400 - elapsed
                mins, secs = divmod(int(remaining), 60)
                hrs, mins = divmod(mins, 60)
                return await ctx.reply(f"⏳ **Daily already claimed!** Next claim in `{hrs}h {mins}m {secs}s`.")
            elif elapsed < 172800:
                streak += 1
            else:
                streak = 1
        else:
            streak = 1

        reward = 500 + min(streak * 50, 1000)
        with sqlite3.connect(DB_FILE) as conn:
            cur = conn.cursor()
            cur.execute(
                "UPDATE economy SET balance = balance + ?, daily_streak = ?, last_daily = ? WHERE user_id = ?",
                (reward, streak, now.isoformat(), uid),
            )
            conn.commit()

        await ctx.reply(f"💵 **Daily Allowance Claimed!** +**{reward:,} coins**! (🔥 Streak: `{streak}` days)")

    @commands.hybrid_command(name="weekly", description="Claim weekly reward bonus")
    async def weekly(self, ctx):
        uid = str(ctx.author.id)
        _, _, _, _, last_weekly, _, _, _ = self.get_account(uid)
        now = datetime.now(timezone.utc)

        if last_weekly:
            try:
                last_dt = datetime.fromisoformat(last_weekly)
                if last_dt.tzinfo is None:
                    last_dt = last_dt.replace(tzinfo=timezone.utc)
                elapsed = (now - last_dt).total_seconds()
            except Exception:
                elapsed = 999999

            if elapsed < 7 * 86400:
                remaining = (7 * 86400) - elapsed
                days, rem = divmod(int(remaining), 86400)
                hrs, mins = divmod(rem, 3600)
                return await ctx.reply(f"⏳ **Weekly already claimed!** Next claim in `{days}d {hrs}h`.")

        reward = 3500
        with sqlite3.connect(DB_FILE) as conn:
            cur = conn.cursor()
            cur.execute(
                "UPDATE economy SET balance = balance + ?, last_weekly = ? WHERE user_id = ?",
                (reward, now.isoformat(), uid),
            )
            conn.commit()

        await ctx.reply(f"🎁 **Weekly Bonus Claimed!** +**{reward:,} coins** added to your wallet!")

    @commands.hybrid_command(name="work", description="Work a job for coins (20m cooldown)")
    @commands.cooldown(1, 1200, commands.BucketType.user)
    async def work(self, ctx):
        earnings = random.randint(150, 450)
        jobs = [
            "fixed Discord bots", "deployed an AI service", "delivered high-priority packages",
            "moderated a 100k member server", "won an esports match", "wrote clean python code"
        ]
        self.update_wallet(str(ctx.author.id), earnings)
        await ctx.reply(f"💼 You {random.choice(jobs)} and earned **+{earnings:,} coins**!")

    @commands.hybrid_command(name="crime", description="Commit a high-risk crime for big payouts")
    @commands.cooldown(1, 3600, commands.BucketType.user)
    async def crime(self, ctx):
        success = random.choice([True, True, False])
        if success:
            payout = random.randint(600, 1500)
            self.update_wallet(str(ctx.author.id), payout)
            await ctx.reply(f"🥷 **Heist Succeeded!** You stole **+{payout:,} coins**!")
        else:
            fine = random.randint(200, 600)
            self.update_wallet(str(ctx.author.id), -fine)
            await ctx.reply(f"🚨 **Caught by Police!** Fined **-{fine:,} coins**!")

    @commands.command(name="slut", description="Hustle the streets for quick cash")
    @commands.cooldown(1, 1800, commands.BucketType.user)
    async def slut(self, ctx):
        success = random.choice([True, True, False])
        if success:
            earnings = random.randint(200, 700)
            self.update_wallet(str(ctx.author.id), earnings)
            await ctx.reply(f"💋 You hustled on the corner and made **+{earnings:,} coins**!")
        else:
            loss = random.randint(100, 300)
            self.update_wallet(str(ctx.author.id), -loss)
            await ctx.reply(f"🥀 You got mugged on the streets and lost **-{loss:,} coins**!")

    @commands.command(name="beg", description="Beg for coins")
    @commands.cooldown(1, 300, commands.BucketType.user)
    async def beg(self, ctx):
        if random.random() < 0.7:
            amt = random.randint(20, 100)
            self.update_wallet(str(ctx.author.id), amt)
            donors = ["Elon Musk", "MrBeast", "A kind stranger", "A generous grandma", "A rich bot"]
            await ctx.reply(f"🥺 **{random.choice(donors)}** took pity on you and gave you **+{amt} coins**!")
        else:
            await ctx.reply("😢 Nobody gave you any coins. Try again later!")

    @commands.command(name="fish", description="Go fishing for rare fish and treasures")
    @commands.cooldown(1, 300, commands.BucketType.user)
    async def fish(self, ctx):
        catches = [
            ("🐟 Common Fish", 50), ("🐠 Tropical Fish", 120), ("🐡 Pufferfish", 250),
            ("🦈 Great White Shark", 800), ("🥾 Old Boot", 5), ("💎 Sunken Treasure", 1500)
        ]
        weights = [45, 25, 15, 8, 5, 2]
        item, value = random.choices(catches, weights=weights, k=1)[0]
        self.update_wallet(str(ctx.author.id), value)
        await ctx.reply(f"🎣 You cast your line and caught a **{item}**! Sold for **+{value:,} coins**!")

    @commands.command(name="hunt", description="Go hunting in the forest for game")
    @commands.cooldown(1, 300, commands.BucketType.user)
    async def hunt(self, ctx):
        animals = [
            ("🐇 Rabbit", 60), ("🦆 Duck", 110), ("🦌 Deer", 300),
            ("🐗 Wild Boar", 450), ("🐻 Grizzly Bear", 900), ("🐉 Mythical Dragon", 3000)
        ]
        weights = [40, 30, 18, 8, 3, 1]
        item, value = random.choices(animals, weights=weights, k=1)[0]
        self.update_wallet(str(ctx.author.id), value)
        await ctx.reply(f"🏹 You tracked the forest and hunted a **{item}**! Sold for **+{value:,} coins**!")

    @commands.command(name="dig", description="Dig for buried ores and artifacts")
    @commands.cooldown(1, 300, commands.BucketType.user)
    async def dig(self, ctx):
        ores = [
            ("🪨 Gravel", 10), ("🪙 Copper Coin", 75), ("🥈 Silver Ingot", 200),
            ("🥇 Gold Nugget", 500), ("💎 Diamond", 1200), ("👑 Ancient Crown", 2500)
        ]
        weights = [35, 30, 20, 10, 4, 1]
        item, value = random.choices(ores, weights=weights, k=1)[0]
        self.update_wallet(str(ctx.author.id), value)
        await ctx.reply(f"⛏️ You dug into the ground and uncovered **{item}**! Sold for **+{value:,} coins**!")

    @commands.command(name="deposit", description="Deposit coins into your bank account")
    async def deposit(self, ctx, amount: str):
        bal, bank, _, _, _, _, _, _ = self.get_account(str(ctx.author.id))
        amt = bal if amount.lower() == "all" else int(amount) if amount.isdigit() else 0
        if amt <= 0:
            return await ctx.reply("❌ Invalid amount.")
        if amt > bal:
            return await ctx.reply("❌ You do not have that many coins in your wallet.")

        with sqlite3.connect(DB_FILE) as conn:
            cur = conn.cursor()
            cur.execute("UPDATE economy SET balance = balance - ?, bank = bank + ? WHERE user_id = ?", (amt, amt, str(ctx.author.id)))
            conn.commit()
        await ctx.reply(f"🏦 Deposited **{amt:,} coins** into your bank account.")

    @commands.command(name="withdraw", description="Withdraw coins from your bank")
    async def withdraw(self, ctx, amount: str):
        bal, bank, _, _, _, _, _, _ = self.get_account(str(ctx.author.id))
        amt = bank if amount.lower() == "all" else int(amount) if amount.isdigit() else 0
        if amt <= 0:
            return await ctx.reply("❌ Invalid amount.")
        if amt > bank:
            return await ctx.reply("❌ You do not have that many coins in your bank.")

        with sqlite3.connect(DB_FILE) as conn:
            cur = conn.cursor()
            cur.execute("UPDATE economy SET balance = balance + ?, bank = bank - ? WHERE user_id = ?", (amt, amt, str(ctx.author.id)))
            conn.commit()
        await ctx.reply(f"💵 Withdrew **{amt:,} coins** from your bank to your wallet.")

    @commands.command(name="rob", description="Attempt to rob wallet coins from a member")
    @commands.cooldown(1, 1800, commands.BucketType.user)
    async def rob(self, ctx, member: discord.Member):
        if member == ctx.author:
            return await ctx.reply("❌ You cannot rob yourself.")
        victim_bal, _, _, _, _, _, _, _ = self.get_account(str(member.id))
        if victim_bal < 100:
            return await ctx.reply(f"❌ {member.display_name} has too few wallet coins (min 100).")

        if random.random() < 0.5:
            stolen = random.randint(50, int(victim_bal * 0.4))
            with sqlite3.connect(DB_FILE) as conn:
                cur = conn.cursor()
                cur.execute("UPDATE economy SET balance = balance - ? WHERE user_id = ?", (stolen, str(member.id)))
                cur.execute("UPDATE economy SET balance = balance + ? WHERE user_id = ?", (stolen, str(ctx.author.id)))
                conn.commit()
            await ctx.reply(f"🥷 **Robbery Success!** Stole **{stolen:,} coins** from {member.mention}!")
        else:
            fine = random.randint(50, 250)
            self.update_wallet(str(ctx.author.id), -fine)
            await ctx.reply(f"🚨 **Caught!** The police caught you and fined you **-{fine:,} coins**!")

    @commands.command(name="pay", description="Transfer coins to another member")
    async def pay(self, ctx, member: discord.Member, amount: int):
        if member == ctx.author:
            return await ctx.reply("❌ You cannot pay yourself.")
        if amount <= 0:
            return await ctx.reply("❌ Amount must be greater than 0.")
        bal, _, _, _, _, _, _, _ = self.get_account(str(ctx.author.id))
        if bal < amount:
            return await ctx.reply("❌ You do not have enough coins in your wallet.")

        with sqlite3.connect(DB_FILE) as conn:
            cur = conn.cursor()
            cur.execute("UPDATE economy SET balance = balance - ? WHERE user_id = ?", (amount, str(ctx.author.id)))
            cur.execute(
                "INSERT INTO economy (user_id, balance, bank) VALUES (?, ?, 0) ON CONFLICT(user_id) DO UPDATE SET balance = balance + ?",
                (str(member.id), amount, amount),
            )
            conn.commit()
        await ctx.reply(f"💸 Sent **{amount:,} coins** to {member.mention}.")

    # Casino Games
    @commands.hybrid_command(name="blackjack", description="Play Blackjack 21 with interactive hit/stand buttons")
    async def blackjack(self, ctx, amount: int):
        if amount <= 0:
            return await ctx.reply("❌ Bet must be greater than 0.")
        bal, _, _, _, _, _, _, _ = self.get_account(str(ctx.author.id))
        if bal < amount:
            return await ctx.reply("❌ You do not have enough coins in your wallet.")

        view = BlackjackView(ctx.author, amount, self)
        await ctx.reply(embed=view.get_embed(), view=view)

    @commands.hybrid_command(name="slots", description="Play 3-reel casino slot machine: &slots <amount>")
    async def slots(self, ctx, amount: int):
        if amount <= 0:
            return await ctx.reply("❌ Bet must be positive.")
        bal, _, _, _, _, _, _, _ = self.get_account(str(ctx.author.id))
        if bal < amount:
            return await ctx.reply("❌ You do not have enough coins.")

        symbols = ["🍒", "🍋", "🍇", "🔔", "💎", "7️⃣"]
        weights = [30, 25, 20, 15, 7, 3]
        reel = random.choices(symbols, weights=weights, k=3)

        if reel[0] == reel[1] == reel[2]:
            mult = 10 if reel[0] == "7️⃣" else 7 if reel[0] == "💎" else 4 if reel[0] == "🔔" else 3
            winnings = amount * mult
            self.update_wallet(str(ctx.author.id), winnings)
            msg = f"🎉 **JACKPOT!** [ {reel[0]} | {reel[1]} | {reel[2]} ]\nWon **+{winnings:,} coins** ({mult}x)!"
        elif reel[0] == reel[1] or reel[1] == reel[2] or reel[0] == reel[2]:
            winnings = int(amount * 1.5)
            self.update_wallet(str(ctx.author.id), winnings - amount)
            msg = f"✨ **Pair!** [ {reel[0]} | {reel[1]} | {reel[2]} ]\nWon **+{winnings:,} coins** (1.5x)!"
        else:
            self.update_wallet(str(ctx.author.id), -amount)
            msg = f"😢 [ {reel[0]} | {reel[1]} | {reel[2]} ]\nNo match! Lost **-{amount:,} coins**."

        embed = discord.Embed(title="🎰 Casino Slots", description=msg, color=WARN_COLOR)
        await ctx.reply(embed=embed)

    @commands.command(name="gamble", description="Coinflip gamble: &gamble <amount> <heads/tails>")
    async def gamble(self, ctx, amount: int, choice: str):
        if amount <= 0:
            return await ctx.reply("❌ Bet must be greater than 0.")
        bal, _, _, _, _, _, _, _ = self.get_account(str(ctx.author.id))
        if bal < amount:
            return await ctx.reply("❌ You do not have enough coins in your wallet.")

        choice = choice.lower().strip()
        outcome = random.choice(["heads", "tails"])
        user_won = (choice.startswith("h") and outcome == "heads") or (choice.startswith("t") and outcome == "tails")

        if user_won:
            self.update_wallet(str(ctx.author.id), amount)
            await ctx.reply(f"🪙 Landed on **{outcome.upper()}**! 🎉 Won **+{amount:,} coins**!")
        else:
            self.update_wallet(str(ctx.author.id), -amount)
            await ctx.reply(f"🪙 Landed on **{outcome.upper()}**! 😢 Lost **-{amount:,} coins**.")

    @commands.command(name="roulette", description="Play casino roulette: &roulette <bet> <red/black/green/number>")
    async def roulette(self, ctx, amount: int, space: str):
        if amount <= 0:
            return await ctx.reply("❌ Bet must be positive.")
        bal, _, _, _, _, _, _, _ = self.get_account(str(ctx.author.id))
        if bal < amount:
            return await ctx.reply("❌ Insufficient coins.")

        num = random.randint(0, 36)
        color = "green" if num == 0 else "red" if num in [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36] else "black"
        sp = space.lower().strip()

        win = False
        mult = 0
        if sp in ["red", "black"] and sp == color:
            win = True
            mult = 2
        elif sp == "green" and color == "green":
            win = True
            mult = 14
        elif sp.isdigit() and int(sp) == num:
            win = True
            mult = 36

        if win:
            payout = amount * (mult - 1)
            self.update_wallet(str(ctx.author.id), payout)
            await ctx.reply(f"🎡 Landed on **{num} ({color.upper()})**! 🎉 You won **+{payout:,} coins** ({mult}x)!")
        else:
            self.update_wallet(str(ctx.author.id), -amount)
            await ctx.reply(f"🎡 Landed on **{num} ({color.upper()})**! 😢 You lost **-{amount:,} coins**.")

    @commands.hybrid_command(name="leaderboard", description="Top 10 richest server users")
    async def leaderboard(self, ctx):
        with sqlite3.connect(DB_FILE) as conn:
            cur = conn.cursor()
            cur.execute("SELECT user_id, (balance + bank) as total FROM economy ORDER BY total DESC LIMIT 10")
            rows = cur.fetchall()

        if not rows:
            return await ctx.reply("📊 No economy profiles found.")

        embed = discord.Embed(title="🏆 Server Wealth Leaderboard", color=WARN_COLOR)
        desc = []
        for rank, (uid, total) in enumerate(rows, start=1):
            user = self.bot.get_user(int(uid)) or f"User ({uid})"
            medal = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else f"**#{rank}**"
            desc.append(f"{medal} {user} — `{total:,}` coins")
        embed.description = "\n".join(desc)
        await ctx.reply(embed=embed)

    @commands.command(name="rob_bank", description="Attempt a high-stakes bank heist")
    @commands.cooldown(1, 7200, commands.BucketType.user)
    async def rob_bank(self, ctx):
        if random.random() < 0.35:
            payout = random.randint(3000, 10000)
            self.update_wallet(str(ctx.author.id), payout)
            await ctx.reply(f"🏦💥 **BANK HEIST SUCCESSFUL!** You bypassed laser security and escaped with **+{payout:,} coins**!")
        else:
            fine = random.randint(1000, 2500)
            self.update_wallet(str(ctx.author.id), -fine)
            await ctx.reply(f"🚨 **SWAT INTERCEPTED!** The bank alarm was tripped. You were fined **-{fine:,} coins**!")

    @commands.command(name="hack_atm", description="Hack an ATM machine for quick cash")
    @commands.cooldown(1, 1800, commands.BucketType.user)
    async def hack_atm(self, ctx):
        if random.random() < 0.6:
            payout = random.randint(400, 1200)
            self.update_wallet(str(ctx.author.id), payout)
            await ctx.reply(f"💻 **ATM Hacked!** Cash dispensed: **+{payout:,} coins**!")
        else:
            loss = random.randint(200, 500)
            self.update_wallet(str(ctx.author.id), -loss)
            await ctx.reply(f"🚨 **ATM Camera Tripped!** Security identified you. Lost **-{loss:,} coins**!")

    @commands.command(name="buy_mansion", description="Purchase a Luxury Villa & Mansion (100,000 coins)")
    async def buy_mansion(self, ctx):
        bal, _, _, _, _, _, _, _ = self.get_account(str(ctx.author.id))
        cost = 100000
        if bal < cost:
            return await ctx.reply(f"❌ You need `{cost:,} coins` to purchase a Luxury Villa.")
        self.update_wallet(str(ctx.author.id), -cost)
        await ctx.reply("🏰 **Mansion Purchased!** You are now the proud owner of a Beverly Hills Luxury Villa!")

    @commands.command(name="buy_yacht", description="Purchase a Mega Superyacht (250,000 coins)")
    async def buy_yacht(self, ctx):
        bal, _, _, _, _, _, _, _ = self.get_account(str(ctx.author.id))
        cost = 250000
        if bal < cost:
            return await ctx.reply(f"❌ You need `{cost:,} coins` to purchase a Superyacht.")
        self.update_wallet(str(ctx.author.id), -cost)
        await ctx.reply("🛥️ **Superyacht Purchased!** You now own a 200ft Monaco Ocean Superyacht!")

    @commands.command(name="buy_supercar", description="Purchase a Hypercar (50,000 coins)")
    async def buy_supercar(self, ctx):
        bal, _, _, _, _, _, _, _ = self.get_account(str(ctx.author.id))
        cost = 50000
        if bal < cost:
            return await ctx.reply(f"❌ You need `{cost:,} coins` for a Hypercar.")
        self.update_wallet(str(ctx.author.id), -cost)
        await ctx.reply("🏎️ **Bugatti Chiron Purchased!** Added to your luxury garage!")

    @commands.command(name="buy_island", description="Purchase a Private Tropical Island (1,000,000 coins)")
    async def buy_island(self, ctx):
        bal, _, _, _, _, _, _, _ = self.get_account(str(ctx.author.id))
        cost = 1000000
        if bal < cost:
            return await ctx.reply(f"❌ You need `{cost:,} coins` for a Private Island.")
        self.update_wallet(str(ctx.author.id), -cost)
        await ctx.reply("🏝️ **Private Island Purchased!** You now own an entire tropical paradise in the Caribbean!")

    @commands.command(name="open_business", description="Open a local business: &open_business <restaurant/tech/cafe>")
    async def open_business(self, ctx, business_type: str):
        btype = business_type.lower()
        cost = 15000
        bal, _, _, _, _, _, _, _ = self.get_account(str(ctx.author.id))
        if bal < cost:
            return await ctx.reply(f"❌ Starting a business requires `{cost:,} coins` startup capital.")
        self.update_wallet(str(ctx.author.id), -cost)
        await ctx.reply(f"🏢 **Business Founded!** You opened a **{business_type.title()}** company!")

    @commands.command(name="collect_revenue", description="Collect passive revenue from your businesses (Hourly)")
    @commands.cooldown(1, 3600, commands.BucketType.user)
    async def collect_revenue(self, ctx):
        revenue = random.randint(800, 2500)
        self.update_wallet(str(ctx.author.id), revenue)
        await ctx.reply(f"📈 **Revenue Collected!** Your commercial assets generated **+{revenue:,} coins** in net profits!")

    @commands.command(name="cups_game", description="Guess the cup hiding the coin (1, 2, or 3): &cups_game <1/2/3> <bet>")
    async def cups_game(self, ctx, cup_choice: int, bet: int):
        if bet <= 0:
            return await ctx.reply("❌ Invalid bet.")
        bal, _, _, _, _, _, _, _ = self.get_account(str(ctx.author.id))
        if bal < bet:
            return await ctx.reply("❌ Insufficient wallet balance.")
        winning_cup = random.randint(1, 3)
        if cup_choice == winning_cup:
            payout = bet * 2
            self.update_wallet(str(ctx.author.id), payout)
            await ctx.reply(f"🥤 **Ball was under cup {winning_cup}!** 🎉 You guessed correctly and won **+{payout:,} coins**!")
        else:
            self.update_wallet(str(ctx.author.id), -bet)
            await ctx.reply(f"🥤 **Ball was under cup {winning_cup}!** 😢 You chose cup {cup_choice} and lost **-{bet:,} coins**.")

async def setup(bot):
    await bot.add_cog(Economy(bot))
