import asyncio
import random
import re
import discord
from discord.ext import commands
from utils import MAIN_COLOR, INFO_COLOR, SUCCESS_COLOR, WARN_COLOR

DARES = [
    "Send 'I can't believe you'd do that to me.' to someone and wait for their reply.",
    "DM someone 'I have something to tell you that might change everything.' and stop.",
    "Send 'You know what? You're right. I'll just leave you all to it.' to a chat.",
    "Ask someone 'What’s the worst thing you’ve ever thought about me?'",
    "Post 'Honestly, I'm not sure I can do this anymore.' in a public channel.",
    "Send 'I’m starting to question everything.' to someone you know well.",
    "Tell someone 'You’re not fooling anyone.' without any context.",
    "DM a friend 'I’ve been keeping something from you, and it’s really affecting me.'",
    "Say 'This whole situation is a disaster, and it's partly your fault.'",
    "Ask someone 'Are you secretly judging me right now?'",
]

TRUTHS = [
    "Who in this server annoys you the most?",
    "Who here would you remove from the server if you could?",
    "Have you ever talked badly about someone here behind their back?",
    "Who do you trust the least in this server?",
    "Who do you think is the most fake person you know?",
    "Who here tries too hard to be funny or cool?",
    "Who do you secretly avoid talking to in DMs?",
    "Who here would you never want to meet in real life?",
    "Have you ever lied to someone in this server?",
    "Have you ever muted someone here because they were annoying?",
]

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

class Minigames(commands.Cog):
    """Interactive multiplayer board games, word chains, and party games."""

    def __init__(self, bot):
        self.bot = bot
        self.tod_games = {}
        self.antakshari_games = {}

    @commands.hybrid_command(name="tictactoe", description="Play 2-player Tic-Tac-Toe on an interactive button grid")
    async def tictactoe(self, ctx, opponent: discord.Member):
        if opponent == ctx.author or opponent.bot:
            return await ctx.reply("❌ Please choose a real human member as your opponent.")
        view = TicTacToeView(ctx.author, opponent)
        await ctx.reply(f"🎮 **Tic-Tac-Toe:** {ctx.author.mention} (X) vs {opponent.mention} (O)\nTurn: {ctx.author.mention}", view=view)

    @commands.hybrid_command(name="rps", description="Play Rock, Paper, Scissors vs Bot")
    async def rps(self, ctx, choice: str):
        choices = ["rock", "paper", "scissors"]
        user_choice = choice.lower()
        if user_choice not in choices:
            return await ctx.reply("❌ Choose `rock`, `paper`, or `scissors`.")
        bot_choice = random.choice(choices)

        if user_choice == bot_choice:
            result = "It's a tie! 🤝"
        elif (
            (user_choice == "rock" and bot_choice == "scissors")
            or (user_choice == "paper" and bot_choice == "rock")
            or (user_choice == "scissors" and bot_choice == "paper")
        ):
            result = "You won! 🎉"
        else:
            result = "I won! 🤖"

        await ctx.reply(f"🤖 I chose **{bot_choice.upper()}**. {result}")

    @commands.hybrid_command(name="guess", description="Number guessing game (1 to 100)")
    async def guess_game(self, ctx):
        number = random.randint(1, 100)
        await ctx.reply("🔢 I am thinking of a number between **1 and 100**. You have **6 tries**! Guess in chat:")

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content.isdigit()

        for attempt in range(1, 7):
            try:
                msg = await self.bot.wait_for("message", check=check, timeout=25)
                guess = int(msg.content)
                if guess == number:
                    return await msg.reply(f"🎉 **Correct!** The number was **{number}**! You got it in `{attempt}` tries!")
                elif guess < number:
                    await msg.reply(f"📈 **Higher!** ({6 - attempt} tries left)")
                else:
                    await msg.reply(f"📉 **Lower!** ({6 - attempt} tries left)")
            except asyncio.TimeoutError:
                return await ctx.send(f"⏰ Time ran out! The number was **{number}**.")

        await ctx.send(f"😢 Game Over! The number was **{number}**.")

    @commands.hybrid_command(name="wyr", description="Would You Rather dilemma question")
    async def would_you_rather(self, ctx):
        dilemmas = [
            ("Have the ability to fly", "Have the ability to be invisible"),
            ("Always be 15 minutes early", "Always be 20 minutes late"),
            ("Know the history of every object you touch", "Talk to animals"),
            ("Live without music", "Live without movies/shows"),
            ("Be able to teleport anywhere", "Be able to read minds"),
        ]
        opt1, opt2 = random.choice(dilemmas)
        embed = discord.Embed(
            title="🤔 Would You Rather?",
            description=f"🅰️ **{opt1}**\n\n*— OR —*\n\n🅱️ **{opt2}**",
            color=WARN_COLOR,
        )
        msg = await ctx.reply(embed=embed)
        await msg.add_reaction("🅰️")
        await msg.add_reaction("🅱️")

    # Truth or Dare
    @commands.hybrid_command(name="tod", description="Start a Truth or Dare lobby in this channel")
    async def tod_start(self, ctx):
        if ctx.channel.id in self.tod_games:
            return await ctx.reply("❌ A game is already active in this channel.")
        self.tod_games[ctx.channel.id] = {
            "host": ctx.author,
            "players": [ctx.author],
            "started": False,
            "current_player_index": 0,
        }
        embed = discord.Embed(
            title="🎮 Truth or Dare Lobby",
            description=f"**Host:** {ctx.author.mention}\n\nType `&join` to join or `&start` to begin.",
            color=INFO_COLOR,
        )
        await ctx.send(embed=embed)

    @commands.command(name="join", description="Join active Truth or Dare lobby")
    async def join(self, ctx):
        game = self.tod_games.get(ctx.channel.id)
        if not game or game["started"]:
            return await ctx.reply("❌ No joinable lobby.")
        if ctx.author in game["players"]:
            return await ctx.reply("❌ You already joined.")
        game["players"].append(ctx.author)
        await ctx.reply(f"✅ {ctx.author.display_name} joined! ({len(game['players'])} players)")

    @commands.command(name="start", description="Host starts Truth or Dare game")
    async def start(self, ctx):
        game = self.tod_games.get(ctx.channel.id)
        if not game or ctx.author != game["host"]:
            return await ctx.reply("❌ Only the host can start.")
        if len(game["players"]) < 2:
            return await ctx.reply("❌ Need at least 2 players.")
        game["started"] = True
        random.shuffle(game["players"])
        await ctx.reply("🚀 Turn order randomized. Starting now!")
        await self.next_tod_turn(ctx)

    @commands.command(name="next", description="Move to next player in Truth or Dare")
    async def next_cmd(self, ctx):
        game = self.tod_games.get(ctx.channel.id)
        if not game or not game["started"] or ctx.author != game["host"]:
            return await ctx.reply("❌ Only host can advance turns.")
        game["current_player_index"] = (game["current_player_index"] + 1) % len(game["players"])
        await self.next_tod_turn(ctx)

    async def next_tod_turn(self, ctx):
        game = self.tod_games[ctx.channel.id]
        player = game["players"][game["current_player_index"]]
        choice = random.choice(["Truth", "Dare"])
        question = random.choice(TRUTHS if choice == "Truth" else DARES)

        embed = discord.Embed(title=f"🎲 {player.display_name}'s Turn", color=WARN_COLOR)
        embed.add_field(name=f"Category: {choice}", value=f"**{question}**")
        embed.set_footer(text="Host: use &next for next turn")
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

    @commands.command(name="card_draw", description="Draw a random card from a standard 52-card deck")
    async def card_draw(self, ctx):
        suits = ["♠️ Spades", "♥️ Hearts", "♦️ Diamonds", "♣️ Clubs"]
        ranks = ["Ace", "2", "3", "4", "5", "6", "7", "8", "9", "10", "Jack", "Queen", "King"]
        card = f"{random.choice(ranks)} of {random.choice(suits)}"
        await ctx.reply(f"🃏 You drew the **{card}**!")

    @commands.command(name="tarot", description="Draw a mystical Major Arcana Tarot reading")
    async def tarot(self, ctx):
        arcana = [
            ("The Fool", "New beginnings, innocence, spontaneity, free spirit", "🃏"),
            ("The Magician", "Manifestation, resourcefulness, power, inspired action", "✨"),
            ("The High Priestess", "Intuition, sacred knowledge, divine feminine, subconscious", "🌙"),
            ("The Empress", "Femininity, beauty, nature, nurturing, abundance", "👑"),
            ("The Emperor", "Authority, structure, control, father figure", "🏛️"),
            ("The Hierophant", "Spiritual wisdom, religious beliefs, conformity, tradition", "📜"),
            ("The Lovers", "Love, harmony, relationships, values alignment", "💕"),
            ("The Chariot", "Control, willpower, success, action, determination", "⚔️"),
            ("Strength", "Courage, persuasion, influence, compassion", "🦁"),
            ("The Hermit", "Soul-searching, introspection, inner guidance", "🕯️"),
            ("Wheel of Fortune", "Good luck, karma, life cycles, destiny, turning point", "🎡"),
            ("Justice", "Fairness, truth, cause and effect, law", "⚖️"),
            ("The Star", "Hope, faith, purpose, renewal, spirituality", "⭐"),
            ("The Moon", "Illusion, fear, anxiety, subconscious, intuition", "🌕"),
            ("The Sun", "Positivity, fun, warmth, success, vitality", "☀️"),
            ("The World", "Completion, integration, accomplishment, travel", "🌍"),
        ]
        card, meaning, emoji = random.choice(arcana)
        embed = discord.Embed(
            title=f"{emoji} Tarot Reading: {card}",
            description=f"🔮 **Divination Meaning:**\n*{meaning}*",
            color=discord.Color.purple(),
        )
        await ctx.reply(embed=embed)

    @commands.command(name="horoscope", description="Daily astrological horoscope: &horoscope <aries/taurus/gemini...>")
    async def horoscope(self, ctx, sign: str):
        s = sign.lower().strip()
        signs = ["aries", "taurus", "gemini", "cancer", "leo", "virgo", "libra", "scorpio", "sagittarius", "capricorn", "aquarius", "pisces"]
        if s not in signs:
            return await ctx.reply(f"❌ Invalid zodiac sign. Choose from: `{', '.join(signs)}`.")
        fortunes = [
            "Today brings sudden clarity on a project you've been working on.",
            "A cosmic alignment favors creative expression and bold decisions today.",
            "Take time to rest and recharge your energy this evening.",
            "An unexpected message will bring a smile to your face.",
            "Financial intuition is sharp today; trust your gut instincts.",
        ]
        embed = discord.Embed(
            title=f"✨ Daily Horoscope: {s.title()}",
            description=f"🌟 {random.choice(fortunes)}\n\n🍀 **Lucky Number:** `{random.randint(1, 99)}` • **Lucky Color:** `{random.choice(['Emerald', 'Crimson', 'Sapphire', 'Gold', 'Violet'])}`",
            color=discord.Color.gold(),
        )
        await ctx.reply(embed=embed)

    @commands.command(name="rps_spock", description="Play Rock, Paper, Scissors, Lizard, Spock: &rps_spock <move>")
    async def rps_spock(self, ctx, choice: str):
        c = choice.lower().strip()
        moves = ["rock", "paper", "scissors", "lizard", "spock"]
        if c not in moves:
            return await ctx.reply("❌ Choose `rock`, `paper`, `scissors`, `lizard`, or `spock`.")
        bot_m = random.choice(moves)
        rules = {
            "scissors": ["paper", "lizard"],
            "paper": ["rock", "spock"],
            "rock": ["lizard", "scissors"],
            "lizard": ["spock", "paper"],
            "spock": ["scissors", "rock"],
        }
        if c == bot_m:
            res = "🤝 It's a tie!"
        elif bot_m in rules[c]:
            res = f"🎉 **You Win!** `{c.title()}` beats `{bot_m.title()}`!"
        else:
            res = f"😢 **Bot Wins!** `{bot_m.title()}` beats `{c.title()}`!"
        await ctx.reply(f"🤖 I chose **{bot_m.title()}**.\n{res}")

async def setup(bot):
    await bot.add_cog(Minigames(bot))
