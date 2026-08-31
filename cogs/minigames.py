import asyncio
import random
import re
from datetime import datetime, timezone
import discord
from discord.ext import commands
from utils import MAIN_COLOR, INFO_COLOR, SUCCESS_COLOR, WARN_COLOR, ERROR_COLOR, generate_ai

DARES_FALLBACK = [
    "Send 'I have a secret confession to make...' to the most active person in chat and don't reply for 2 minutes.",
    "Change your server nickname to 'Certified NPC' for the next 1 hour.",
    "Sing the chorus of your favorite song in voice chat or send a voice message singing it.",
    "Send the 5th image in your camera roll / gallery with zero explanation.",
    "Type a message in chat using only emojis that describes your day and let others guess.",
    "Talk in pirate speak ('Ahoy matey!') for the next 5 messages.",
    "Compliment your biggest rival or someone you rarely talk to in the server with 3 genuine sentences.",
]

TRUTHS_FALLBACK = [
    "What is the most embarrassing Discord server you have ever joined?",
    "If you had to delete all your messages with one person in this server forever, who would it be?",
    "What is something you lied about on the internet that everyone believed?",
    "Who in this server would survive the longest in a zombie apocalypse, and who dies first?",
    "What is your biggest guilty pleasure gaming habit or song?",
    "What is the cringiest message you have sent in DMs late at night?",
    "If you could trade lives with anyone in this server for 24 hours, who would it be?",
]

# =============================================================================
# 🕹️ TIC TAC TOE
# =============================================================================

class TicTacToeButton(discord.ui.Button):
    def __init__(self, x: int, y: int):
        super().__init__(style=discord.ButtonStyle.secondary, label="\u200b", row=y)
        self.x = x
        self.y = y

    async def callback(self, interaction: discord.Interaction):
        view: TicTacToeView = self.view
        if interaction.user != view.current_player:
            return await interaction.response.send_message("❌ It's not your turn!", ephemeral=True)

        if view.board[self.y][self.x] != 0:
            return await interaction.response.send_message("❌ Cell already occupied!", ephemeral=True)

        if view.current_player == view.player_x:
            self.style = discord.ButtonStyle.danger
            self.label = "X"
            self.disabled = True
            view.board[self.y][self.x] = 1
            view.current_player = view.player_o
        else:
            self.style = discord.ButtonStyle.primary
            self.label = "O"
            self.disabled = True
            view.board[self.y][self.x] = 2
            view.current_player = view.player_x

        winner = view.check_winner()
        if winner:
            for child in view.children:
                child.disabled = True
            if winner == 1:
                msg = f"🎉 **{view.player_x.mention} (X) Won!**"
            elif winner == 2:
                msg = f"🎉 **{view.player_o.mention} (O) Won!**"
            else:
                msg = "🤝 **It's a Tie!**"
            return await interaction.response.edit_message(content=msg, view=view)

        await interaction.response.edit_message(content=f"🎮 Turn: {view.current_player.mention}", view=view)

class TicTacToeView(discord.ui.View):
    def __init__(self, player_x: discord.Member, player_o: discord.Member):
        super().__init__(timeout=120)
        self.player_x = player_x
        self.player_o = player_o
        self.current_player = player_x
        self.board = [[0, 0, 0], [0, 0, 0], [0, 0, 0]]
        for y in range(3):
            for x in range(3):
                self.add_item(TicTacToeButton(x, y))

    def check_winner(self):
        for i in range(3):
            if self.board[i][0] == self.board[i][1] == self.board[i][2] != 0:
                return self.board[i][0]
            if self.board[0][i] == self.board[1][i] == self.board[2][i] != 0:
                return self.board[0][i]
        if self.board[0][0] == self.board[1][1] == self.board[2][2] != 0:
            return self.board[0][0]
        if self.board[0][2] == self.board[1][1] == self.board[2][0] != 0:
            return self.board[0][2]
        if all(cell != 0 for row in self.board for cell in row):
            return 3
        return None

# =============================================================================
# 🗳️ WOULD YOU RATHER INTERACTIVE VIEW
# =============================================================================

class WYRView(discord.ui.View):
    def __init__(self, opt1: str, opt2: str):
        super().__init__(timeout=180)
        self.opt1 = opt1
        self.opt2 = opt2
        self.votes1 = set()
        self.votes2 = set()

    @discord.ui.button(label="Option A", style=discord.ButtonStyle.primary, emoji="🅰️")
    async def vote_a(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.votes1.add(interaction.user.id)
        self.votes2.discard(interaction.user.id)
        await self.update_embed(interaction)

    @discord.ui.button(label="Option B", style=discord.ButtonStyle.success, emoji="🅱️")
    async def vote_b(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.votes2.add(interaction.user.id)
        self.votes1.discard(interaction.user.id)
        await self.update_embed(interaction)

    async def update_embed(self, interaction: discord.Interaction):
        total = len(self.votes1) + len(self.votes2)
        pct1 = int((len(self.votes1) / total) * 100) if total else 0
        pct2 = int((len(self.votes2) / total) * 100) if total else 0
        
        embed = discord.Embed(
            title="🤔 AI-Generated Dilemma: Would You Rather?",
            color=0x9B59B6,
            timestamp=datetime.now(timezone.utc),
        )
        embed.add_field(name="🅰️ Option A", value=f"**{self.opt1}**\n📊 **{len(self.votes1)} votes** (`{pct1}%`)", inline=False)
        embed.add_field(name="🅱️ Option B", value=f"**{self.opt2}**\n📊 **{len(self.votes2)} votes** (`{pct2}%`)", inline=False)
        embed.set_footer(text=f"Total Votes: {total} • Powered by Google Gemini AI")
        await interaction.response.edit_message(embed=embed, view=self)

# =============================================================================
# 🎮 MINIGAMES COG
# =============================================================================

class Minigames(commands.Cog):
    """AI-integrated multiplayer games, dynamic Truth or Dare, interactive Dilemmas, and Tarot readings."""

    def __init__(self, bot):
        self.bot = bot
        self.tod_games = {}
        self.antakshari_games = {}

    @commands.hybrid_command(name="tictactoe", aliases=["ttt"], description="Play 2-player Tic-Tac-Toe: &ttt @user")
    async def tictactoe(self, ctx, opponent: discord.Member):
        if opponent == ctx.author or opponent.bot:
            return await ctx.reply("❌ Choose a valid fellow server member.")
        view = TicTacToeView(player_x=ctx.author, player_o=opponent)
        await ctx.reply(f"🎮 **Tic-Tac-Toe Started!** {ctx.author.mention} (❌) vs {opponent.mention} (⭕)\nTurn: {ctx.author.mention}", view=view)

    @commands.hybrid_command(name="rps", description="Play Rock, Paper, Scissors: &rps <rock/paper/scissors>")
    async def rps(self, ctx, choice: str):
        c = choice.lower().strip()
        moves = ["rock", "paper", "scissors"]
        if c not in moves:
            return await ctx.reply("❌ Choose `rock`, `paper`, or `scissors`.")
        bot_m = random.choice(moves)
        if c == bot_m:
            res = "🤝 **It's a Tie!**"
            color = WARN_COLOR
        elif (c == "rock" and bot_m == "scissors") or (c == "paper" and bot_m == "rock") or (c == "scissors" and bot_m == "paper"):
            res = "🎉 **You Win!**"
            color = SUCCESS_COLOR
        else:
            res = "😢 **Bot Wins!**"
            color = ERROR_COLOR

        embed = discord.Embed(title="✊ Rock, Paper, Scissors", description=f"You chose: **{c.title()}**\nBot chose: **{bot_m.title()}**\n\n{res}", color=color)
        await ctx.reply(embed=embed)

    @commands.hybrid_command(name="guess", description="Play secret number guessing game (1 to 100)")
    async def guess(self, ctx):
        secret = random.randint(1, 100)
        await ctx.reply("🔢 I've picked a secret number between **1 and 100**. You have **5 attempts**! Type your guesses in chat.")

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content.isdigit()

        for attempt in range(1, 6):
            try:
                msg = await self.bot.wait_for("message", check=check, timeout=25.0)
                val = int(msg.content)
                if val == secret:
                    return await ctx.reply(f"🎉 **BINGO!** You guessed `{secret}` on attempt **{attempt}/5**! 🏆")
                elif val < secret:
                    await ctx.reply(f"🔼 **Higher!** ({5 - attempt} attempts remaining)")
                else:
                    await ctx.reply(f"🔽 **Lower!** ({5 - attempt} attempts remaining)")
            except asyncio.TimeoutError:
                return await ctx.reply(f"⏱️ **Time's up!** The secret number was `{secret}`.")
        await ctx.reply(f"💀 **Game Over!** Out of attempts. The secret number was `{secret}`.")

    # =========================================================================
    # 🧠 AI-POWERED TRUTH OR DARE & DILEMMAS
    # =========================================================================

    @commands.hybrid_command(name="truth", aliases=["ai_truth"], description="Generate a spicy, unique AI-powered Truth question")
    async def truth_standalone(self, ctx):
        """Generate a fresh, hilarious, and thought-provoking Truth question with Gemini AI."""
        await ctx.defer()
        prompt = "Generate a single hilarious, spicy, or engaging Truth question for a Discord game of Truth or Dare. Make it creative, thought-provoking, and fun. Return ONLY the question sentence."
        try:
            res = await generate_ai(prompt, system_instruction="You are a witty, hilarious party game master.")
            q = res.strip().strip('"')
        except Exception:
            q = random.choice(TRUTHS_FALLBACK)

        embed = discord.Embed(
            title="🔮 AI Truth Question",
            description=f"**\"{q}\"**",
            color=INFO_COLOR,
            timestamp=datetime.now(timezone.utc),
        )
        embed.set_footer(text=f"Requested by {ctx.author.display_name} • Powered by Gemini AI")
        await ctx.reply(embed=embed)

    @commands.hybrid_command(name="dare", aliases=["ai_dare"], description="Generate a spicy, funny AI-powered Dare challenge")
    async def dare_standalone(self, ctx):
        """Generate a fresh, hilarious, and creative Dare challenge with Gemini AI."""
        await ctx.defer()
        prompt = "Generate a single funny, creative, and safe-for-Discord Dare challenge for a party game (e.g. funny text to send, status change, voice note, joke). Return ONLY the dare sentence."
        try:
            res = await generate_ai(prompt, system_instruction="You are a witty, hilarious party game master.")
            d = res.strip().strip('"')
        except Exception:
            d = random.choice(DARES_FALLBACK)

        embed = discord.Embed(
            title="🔥 AI Dare Challenge",
            description=f"**\"{d}\"**",
            color=ERROR_COLOR,
            timestamp=datetime.now(timezone.utc),
        )
        embed.set_footer(text=f"Requested by {ctx.author.display_name} • Powered by Gemini AI")
        await ctx.reply(embed=embed)

    @commands.hybrid_command(name="wyr", aliases=["wouldyourather", "dilemma"], description="Generate an AI-powered Would You Rather dilemma with interactive voting buttons")
    async def would_you_rather(self, ctx):
        """Generates a dynamic 2-choice dilemma with live reaction buttons."""
        await ctx.defer()
        prompt = "Generate a creative, hilarious, and difficult 'Would you rather' dilemma. Output format: Exactly two lines:\nA: [Option A text]\nB: [Option B text]"
        try:
            res = await generate_ai(prompt, system_instruction="You are a creative dilemma architect.")
            lines = [line.strip() for line in res.splitlines() if line.strip()]
            opt1 = lines[0].replace("A:", "").replace("Option A:", "").strip()
            opt2 = lines[1].replace("B:", "").replace("Option B:", "").strip()
        except Exception:
            opt1 = "Have the ability to speak every language in the universe fluently"
            opt2 = "Have the ability to talk to all animals and mythical creatures"

        view = WYRView(opt1, opt2)
        embed = discord.Embed(
            title="🤔 AI-Generated Dilemma: Would You Rather?",
            color=0x9B59B6,
            timestamp=datetime.now(timezone.utc),
        )
        embed.add_field(name="🅰️ Option A", value=f"**{opt1}**", inline=False)
        embed.add_field(name="🅱️ Option B", value=f"**{opt2}**", inline=False)
        embed.set_footer(text=f"Click a button below to cast your vote! • Powered by Gemini AI")
        await ctx.reply(embed=embed, view=view)

    # Truth or Dare Room
    @commands.command(name="tod", description="Create an AI-powered multiplayer Truth or Dare lobby")
    async def tod(self, ctx):
        if ctx.channel.id in self.tod_games:
            return await ctx.reply("❌ A game is already running in this channel. Type `&endtod` to conclude.")
        self.tod_games[ctx.channel.id] = {
            "host": ctx.author,
            "players": [ctx.author],
            "started": False,
            "current_player_index": 0,
        }
        embed = discord.Embed(
            title="🎲 AI-Powered Truth or Dare Room Created!",
            description=(
                f"**Host:** {ctx.author.mention}\n\n"
                "**How to play:**\n"
                "• Type `&join` to enter the lobby\n"
                "• Host types `&start` to begin\n"
                "• Host types `&next` for subsequent turns\n"
                "• Host types `&endtod` to finish\n\n"
                "✨ *Truths and Dares are dynamically generated with Google Gemini AI for infinite fresh content!*"
            ),
            color=MAIN_COLOR,
        )
        await ctx.reply(embed=embed)

    @commands.command(name="join", description="Join an open Truth or Dare lobby")
    async def join(self, ctx):
        game = self.tod_games.get(ctx.channel.id)
        if not game or game["started"]:
            return await ctx.reply("❌ No joinable lobby in this channel.")
        if ctx.author in game["players"]:
            return await ctx.reply("❌ You have already joined.")
        game["players"].append(ctx.author)
        await ctx.reply(f"✅ {ctx.author.display_name} joined the game! (**{len(game['players'])} players**)")

    @commands.command(name="start", description="Host starts the Truth or Dare game")
    async def start(self, ctx):
        game = self.tod_games.get(ctx.channel.id)
        if not game or ctx.author != game["host"]:
            return await ctx.reply("❌ Only the host can start the game.")
        if len(game["players"]) < 2:
            return await ctx.reply("❌ You need at least 2 players to start.")
        game["started"] = True
        random.shuffle(game["players"])
        await ctx.reply("🚀 Player turn order randomized! Starting now...")
        await self.next_tod_turn(ctx)

    @commands.command(name="next", description="Move to the next player in Truth or Dare")
    async def next_cmd(self, ctx):
        game = self.tod_games.get(ctx.channel.id)
        if not game or not game["started"] or ctx.author != game["host"]:
            return await ctx.reply("❌ Only the game host can advance turns.")
        game["current_player_index"] = (game["current_player_index"] + 1) % len(game["players"])
        await self.next_tod_turn(ctx)

    async def next_tod_turn(self, ctx):
        game = self.tod_games[ctx.channel.id]
        player = game["players"][game["current_player_index"]]
        choice = random.choice(["Truth", "Dare"])

        prompt = f"Generate a single creative, spicy, and hilarious {choice} for a multiplayer party game on Discord. Output ONLY the {choice} text."
        try:
            ai_q = await generate_ai(prompt, system_instruction="You are an energetic party host.")
            question = ai_q.strip().strip('"')
        except Exception:
            question = random.choice(TRUTHS_FALLBACK if choice == "Truth" else DARES_FALLBACK)

        embed = discord.Embed(
            title=f"🎲 {player.display_name}'s Turn",
            description=f"✨ **AI Question:**\n**{question}**",
            color=WARN_COLOR if choice == "Truth" else ERROR_COLOR,
            timestamp=datetime.now(timezone.utc),
        )
        embed.add_field(name="Category", value=f"🎭 **{choice}**", inline=True)
        embed.add_field(name="Turn Order", value=f"👤 Player `{game['current_player_index'] + 1}/{len(game['players'])}`", inline=True)
        embed.set_footer(text="Host: Type &next for next turn • Type &endtod to finish")
        await ctx.send(content=player.mention, embed=embed)

    @commands.command(name="endtod", description="End Truth or Dare session")
    async def endtod(self, ctx):
        if ctx.channel.id in self.tod_games:
            del self.tod_games[ctx.channel.id]
            await ctx.reply("🛑 Truth or Dare game concluded.")

    # Antakshari
    @commands.command(name="antakshari", description="Start word/song chain game")
    async def antakshari(self, ctx):
        if ctx.channel.id in self.antakshari_games:
            return await ctx.reply("❌ Game already running. Type `&endakshari`.")
        self.antakshari_games[ctx.channel.id] = {
            "expected_letter": None,
            "used_words": set(),
            "last_player": None,
        }
        embed = discord.Embed(
            title="🎤 Antakshari Word Chain Started!",
            description="Rules:\n1. Next word must start with the **last letter** of previous.\n2. No repeats.\n3. Cannot play twice consecutively.",
            color=discord.Color.purple(),
        )
        await ctx.reply(embed=embed)

    @commands.command(name="endakshari", description="End Antakshari game")
    async def endakshari(self, ctx):
        if ctx.channel.id not in self.antakshari_games:
            return await ctx.reply("❌ No game running in this channel.")
        rounds = len(self.antakshari_games[ctx.channel.id]["used_words"])
        del self.antakshari_games[ctx.channel.id]
        await ctx.reply(f"🛑 Antakshari ended! Played **{rounds}** words.")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or message.content.startswith(("&", "/")):
            return
        game = self.antakshari_games.get(message.channel.id)
        if not game:
            return

        text = message.content.strip().lower()
        alpha_text = re.sub(r"[^a-z]", "", text)
        if not alpha_text:
            return

        start_letter = alpha_text[0]
        end_letter = alpha_text[-1]
        entry = " ".join(text.split())

        if game["expected_letter"] and start_letter != game["expected_letter"]:
            await message.add_reaction("❌")
            return await message.reply(f"Wait! Word must start with **'{game['expected_letter'].upper()}'**.")

        if entry in game["used_words"]:
            await message.add_reaction("♻️")
            return await message.reply(f"**'{entry}'** was already used.")

        if game["last_player"] == message.author.id:
            await message.add_reaction("⏳")
            return await message.reply("Let someone else take a turn first!")

        game["used_words"].add(entry)
        game["expected_letter"] = end_letter
        game["last_player"] = message.author.id
        await message.add_reaction("✅")
        await message.channel.send(f"Next letter is: **{end_letter.upper()}** 🎵")

    # AI Tarot & Horoscope
    @commands.hybrid_command(name="tarot", description="Draw an AI-interpreted mystical Tarot card reading")
    async def tarot(self, ctx):
        arcana = [
            ("The Fool", "🃏"), ("The Magician", "✨"), ("The High Priestess", "🌙"),
            ("The Empress", "👑"), ("The Emperor", "🏛️"), ("The Hierophant", "📜"),
            ("The Lovers", "💕"), ("The Chariot", "⚔️"), ("Strength", "🦁"),
            ("The Hermit", "🕯️"), ("Wheel of Fortune", "🎡"), ("Justice", "⚖️"),
            ("The Star", "⭐"), ("The Moon", "🌕"), ("The Sun", "☀️"), ("The World", "🌍")
        ]
        card, emoji = random.choice(arcana)
        await ctx.defer()

        prompt = f"Give a mystical, inspiring 2-sentence tarot interpretation for '{card}'. Include love, career, or spiritual guidance."
        try:
            interpretation = await generate_ai(prompt, system_instruction="You are an ancient mystical tarot reader.")
        except Exception:
            interpretation = "New beginnings and sudden revelations will guide you to unexpected success."

        embed = discord.Embed(
            title=f"{emoji} AI Tarot Divination: {card}",
            description=f"🔮 **Oracle Guidance:**\n*{interpretation}*",
            color=discord.Color.purple(),
            timestamp=datetime.now(timezone.utc),
        )
        embed.set_footer(text=f"Drawn for {ctx.author.display_name} • Powered by Gemini AI")
        await ctx.reply(embed=embed)

    @commands.hybrid_command(name="horoscope", description="Daily AI astrological horoscope: &horoscope <aries/taurus/gemini...>")
    async def horoscope(self, ctx, sign: str):
        s = sign.lower().strip()
        signs = ["aries", "taurus", "gemini", "cancer", "leo", "virgo", "libra", "scorpio", "sagittarius", "capricorn", "aquarius", "pisces"]
        if s not in signs:
            return await ctx.reply(f"❌ Choose a valid zodiac sign: `{', '.join(signs)}`.")

        await ctx.defer()
        prompt = f"Generate a short, inspiring daily horoscope reading for zodiac sign {s.title()}. Include celestial mood, lucky number, and lucky color."
        try:
            reading = await generate_ai(prompt, system_instruction="You are an expert astrologer.")
        except Exception:
            reading = f"The stars align in your favor today! Trust your creative intuition and bold choices."

        embed = discord.Embed(
            title=f"✨ AI Daily Horoscope: {s.title()}",
            description=f"🌟 {reading}",
            color=discord.Color.gold(),
            timestamp=datetime.now(timezone.utc),
        )
        embed.set_footer(text=f"Astrological Chart for {ctx.author.display_name} • Powered by Gemini AI")
        await ctx.reply(embed=embed)

    @commands.command(name="card_draw", description="Draw a random card from a standard 52-card deck")
    async def card_draw(self, ctx):
        suits = ["♠️ Spades", "♥️ Hearts", "♦️ Diamonds", "♣️ Clubs"]
        ranks = ["Ace", "2", "3", "4", "5", "6", "7", "8", "9", "10", "Jack", "Queen", "King"]
        card = f"{random.choice(ranks)} of {random.choice(suits)}"
        await ctx.reply(f"🃏 You drew the **{card}**!")

async def setup(bot):
    await bot.add_cog(Minigames(bot))
