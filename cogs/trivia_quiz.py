import asyncio
import html
import random
import aiohttp
import discord
from discord.ext import commands
from utils import MAIN_COLOR, SUCCESS_COLOR, ERROR_COLOR, WARN_COLOR, INFO_COLOR

RIDDLES = [
    {"q": "I speak without a mouth and hear without ears. I have no body, but I come alive with wind. What am I?", "a": "echo"},
    {"q": "You see a boat filled with people. It has not sunk, but when you look again you don’t see a single person on the boat. Why?", "a": "married"},
    {"q": "The more of this there is, the less you see. What is it?", "a": "darkness"},
    {"q": "What has keys, but no locks; space, but no room; and you can enter, but not go in?", "a": "keyboard"},
    {"q": "What has hands, but cannot clap?", "a": "clock"},
    {"q": "What can travel around the world while staying in a corner?", "a": "stamp"},
    {"q": "What gets wetter the more it dries?", "a": "towel"},
]

FLAGS = [
    {"country": "Japan", "flag": "🇯🇵"},
    {"country": "Germany", "flag": "🇩🇪"},
    {"country": "Brazil", "flag": "🇧🇷"},
    {"country": "Canada", "flag": "🇨🇦"},
    {"country": "India", "flag": "🇮🇳"},
    {"country": "Australia", "flag": "🇦🇺"},
    {"country": "France", "flag": "🇫🇷"},
    {"country": "South Korea", "flag": "🇰🇷"},
    {"country": "Italy", "flag": "🇮🇹"},
    {"country": "United Kingdom", "flag": "🇬🇧"},
    {"country": "Egypt", "flag": "🇪🇬"},
]

WORDS = [
    "algorithm", "database", "encryption", "firewall", "javascript",
    "kubernetes", "middleware", "neuralnet", "polymorphism", "recursion",
    "blockchain", "framework", "asynchronous", "repository", "microservices"
]

class TriviaView(discord.ui.View):
    def __init__(self, author, correct_answer, options):
        super().__init__(timeout=30)
        self.author = author
        self.correct_answer = correct_answer
        self.answered = False

        for opt in options:
            btn = discord.ui.Button(label=opt[:80], style=discord.ButtonStyle.secondary)
            btn.callback = self.make_callback(opt)
            self.add_item(btn)

    def make_callback(self, chosen):
        async def button_callback(interaction: discord.Interaction):
            if interaction.user != self.author:
                return await interaction.response.send_message("❌ This is not your trivia game.", ephemeral=True)
            if self.answered:
                return
            self.answered = True

            for child in self.children:
                child.disabled = True
                if child.label == self.correct_answer[:80]:
                    child.style = discord.ButtonStyle.success
                elif child.label == chosen[:80]:
                    child.style = discord.ButtonStyle.danger

            if chosen == self.correct_answer:
                embed = discord.Embed(
                    title="🎉 Correct Answer!",
                    description=f"✅ You got it right! The answer is **{self.correct_answer}**.",
                    color=SUCCESS_COLOR,
                )
            else:
                embed = discord.Embed(
                    title="❌ Incorrect!",
                    description=f"You chose **{chosen}**.\nThe correct answer was **{self.correct_answer}**.",
                    color=ERROR_COLOR,
                )
            await interaction.response.edit_message(embed=embed, view=self)

        return button_callback

class TriviaQuiz(commands.Cog):
    """Multiplayer trivia, category quizzes, flag guessing, riddles, and word games."""

    def __init__(self, bot):
        self.bot = bot

    async def fetch_opentdb_question(self, category_id=None):
        url = "https://opentdb.com/api.php?amount=1&type=multiple"
        if category_id:
            url += f"&category={category_id}"
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, timeout=10) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data.get("results"):
                            q_data = data["results"][0]
                            q = html.unescape(q_data["question"])
                            c = html.unescape(q_data["correct_answer"])
                            opts = [html.unescape(x) for x in q_data["incorrect_answers"]]
                            opts.append(c)
                            random.shuffle(opts)
                            return q, c, opts, q_data.get("difficulty", "medium").title(), q_data.get("category", "General")
            except Exception:
                pass
        return None

    @commands.hybrid_command(name="trivia", description="Play general knowledge multiple-choice trivia")
    async def trivia(self, ctx):
        res = await self.fetch_opentdb_question()
        if not res:
            return await ctx.reply("❌ Trivia server is temporarily busy. Try again in a moment!")
        q, c, opts, diff, cat = res
        embed = discord.Embed(
            title=f"🧠 Trivia Quiz: {cat}",
            description=f"**{q}**\n\n*Difficulty:* `{diff}` • *Time:* `30s`",
            color=MAIN_COLOR,
        )
        view = TriviaView(ctx.author, c, opts)
        await ctx.reply(embed=embed, view=view)

    @commands.command(name="trivia_anime", description="Play anime & manga multiple-choice trivia")
    async def trivia_anime(self, ctx):
        res = await self.fetch_opentdb_question(category_id=31)
        if not res:
            return await ctx.reply("❌ Trivia server is temporarily busy.")
        q, c, opts, diff, cat = res
        embed = discord.Embed(
            title=f"🌸 Anime Trivia: {cat}",
            description=f"**{q}**\n\n*Difficulty:* `{diff}`",
            color=0xFF69B4,
        )
        view = TriviaView(ctx.author, c, opts)
        await ctx.reply(embed=embed, view=view)

    @commands.command(name="trivia_science", description="Play science & technology trivia")
    async def trivia_science(self, ctx):
        res = await self.fetch_opentdb_question(category_id=17)
        if not res:
            return await ctx.reply("❌ Trivia server is temporarily busy.")
        q, c, opts, diff, cat = res
        embed = discord.Embed(
            title=f"🔬 Science & Tech Trivia: {cat}",
            description=f"**{q}**\n\n*Difficulty:* `{diff}`",
            color=INFO_COLOR,
        )
        view = TriviaView(ctx.author, c, opts)
        await ctx.reply(embed=embed, view=view)

    @commands.command(name="trivia_gaming", description="Play video games trivia")
    async def trivia_gaming(self, ctx):
        res = await self.fetch_opentdb_question(category_id=15)
        if not res:
            return await ctx.reply("❌ Trivia server is temporarily busy.")
        q, c, opts, diff, cat = res
        embed = discord.Embed(
            title=f"🎮 Video Games Trivia: {cat}",
            description=f"**{q}**\n\n*Difficulty:* `{diff}`",
            color=WARN_COLOR,
        )
        view = TriviaView(ctx.author, c, opts)
        await ctx.reply(embed=embed, view=view)

    @commands.command(name="ai_trivia", aliases=["aitrivia", "custom_trivia"], description="Play an AI-generated trivia game on ANY custom topic: &ai_trivia [topic]")
    async def ai_trivia(self, ctx, *, topic: str = "General Knowledge"):
        """Generates dynamic 4-option trivia with interactive Discord buttons on any topic."""
        await ctx.defer()
        from utils import generate_ai
        prompt = f"""Generate 1 multiple choice trivia question about '{topic}'.
Respond in strict JSON format:
{{
  "question": "The question text",
  "correct": "The correct answer",
  "wrong": ["Incorrect 1", "Incorrect 2", "Incorrect 3"],
  "difficulty": "Easy/Medium/Hard"
}}"""
        try:
            res = await generate_ai(prompt, system_instruction="You are a trivia master. Respond strictly with raw JSON.")
            clean = res.strip().strip("`").replace("json", "").strip()
            import json
            data = json.loads(clean)
            q = data["question"]
            correct = data["correct"]
            options = data["wrong"] + [correct]
            random.shuffle(options)
            diff = data.get("difficulty", "Medium")

            embed = discord.Embed(
                title=f"🧠 AI Trivia: {topic.title()}",
                description=f"**{q}**\n\n*Difficulty:* `{diff}`",
                color=0x9B59B6,
            )
            embed.set_footer(text=f"Game for {ctx.author.display_name} • Powered by Gemini AI")
            view = TriviaView(ctx.author, correct, options)
            await ctx.reply(embed=embed, view=view)
        except Exception:
            # Fallback to OpenTDB
            res = await self.fetch_opentdb_question()
            if res:
                q, c, opts, diff, cat = res
                embed = discord.Embed(
                    title=f"🧠 General Trivia: {cat}",
                    description=f"**{q}**\n\n*Difficulty:* `{diff}`",
                    color=MAIN_COLOR,
                )
                view = TriviaView(ctx.author, c, opts)
                await ctx.reply(embed=embed, view=view)
            else:
                await ctx.reply("❌ Trivia server is temporarily busy.")

    @commands.command(name="riddle", description="Solve a mind-bending AI riddle")
    async def riddle(self, ctx):
        await ctx.defer()
        from utils import generate_ai
        prompt = """Generate a clever, poetic, original riddle.
Respond in strict JSON format:
{
  "question": "Riddle text here...",
  "answer": "short single-word answer",
  "hint": "a subtle 1-sentence hint"
}"""
        try:
            res = await generate_ai(prompt, system_instruction="You are a mystical sphinx riddle creator. Output JSON only.")
            clean = res.strip().strip("`").replace("json", "").strip()
            import json
            data = json.loads(clean)
            q = data["question"]
            a = data["answer"].strip()
            hint = data.get("hint", "Think outside the box!")
        except Exception:
            item = random.choice(RIDDLES)
            q = item["q"]
            a = item["a"]
            hint = "Think metaphorical!"

        embed = discord.Embed(
            title="🧩 Riddle of the Sphinx",
            description=f"**{q}**\n\n💡 *Hint:* ||{hint}||\n*Type your guess in chat within 35 seconds!*",
            color=INFO_COLOR,
        )
        embed.set_footer(text="Powered by Gemini AI")
        await ctx.reply(embed=embed)

        def check(m):
            return m.channel == ctx.channel and not m.author.bot

        try:
            msg = await self.bot.wait_for("message", check=check, timeout=35)
            if a.lower() in msg.content.lower():
                await msg.reply(f"🎉 **Brilliant!** {msg.author.mention} solved the riddle! The answer was **{a}**! 🏆")
            else:
                await ctx.send(f"❌ Not quite! The answer was: **{a}**.")
        except asyncio.TimeoutError:
            await ctx.send(f"⏳ **Time's up!** The answer was: **{a}**.")

    @commands.command(name="guess_flag", description="Guess the country from the flag emoji")
    async def guess_flag(self, ctx):
        item = random.choice(FLAGS)
        embed = discord.Embed(
            title="🚩 Guess the Country Flag!",
            description=f"# {item['flag']}\n\n*What country does this flag belong to? (30s)*",
            color=MAIN_COLOR,
        )
        await ctx.reply(embed=embed)

        def check(m):
            return m.channel == ctx.channel and not m.author.bot

        try:
            msg = await self.bot.wait_for("message", check=check, timeout=30)
            if item["country"].lower() in msg.content.lower():
                await msg.reply(f"🏆 **Spot on!** {msg.author.mention} got it right: **{item['country']}** {item['flag']}!")
            else:
                await ctx.send(f"❌ Not quite! The correct country was **{item['country']}** {item['flag']}.")
        except asyncio.TimeoutError:
            await ctx.send(f"⏳ **Time's up!** The country was **{item['country']}** {item['flag']}.")

    @commands.command(name="scramble", description="Unscramble the programming/tech word")
    async def scramble(self, ctx):
        word = random.choice(WORDS)
        scrambled = "".join(random.sample(word, len(word)))
        while scrambled == word:
            scrambled = "".join(random.sample(word, len(word)))

        embed = discord.Embed(
            title="🔤 Word Scramble Challenge",
            description=f"Unscramble this word:\n# `{scrambled.upper()}`\n\n*Type the unscrambled word in chat (30s)*",
            color=WARN_COLOR,
        )
        await ctx.reply(embed=embed)

        def check(m):
            return m.channel == ctx.channel and not m.author.bot and m.content.strip().lower() == word.lower()

        try:
            msg = await self.bot.wait_for("message", check=check, timeout=30)
            await msg.reply(f"🎉 **Winner!** {msg.author.mention} unscrambled the word: **{word.upper()}**!")
        except asyncio.TimeoutError:
            await ctx.send(f"⏳ **Time's up!** The word was: **{word.upper()}**.")

    @commands.command(name="math_quiz", description="Speed math calculation contest")
    async def math_quiz(self, ctx):
        a = random.randint(10, 99)
        b = random.randint(10, 99)
        op = random.choice(["+", "-", "*"])
        if op == "+":
            ans = a + b
        elif op == "-":
            ans = a - b
        else:
            a = random.randint(3, 15)
            b = random.randint(3, 15)
            ans = a * b

        embed = discord.Embed(
            title="⚡ Speed Math Contest",
            description=f"Calculate:\n# `{a} {op} {b} = ?`\n\n*First person to type the correct number wins! (20s)*",
            color=INFO_COLOR,
        )
        await ctx.reply(embed=embed)

        def check(m):
            return m.channel == ctx.channel and not m.author.bot and m.content.strip() == str(ans)

        try:
            msg = await self.bot.wait_for("message", check=check, timeout=20)
            await msg.reply(f"🏆 **Quick Math!** {msg.author.mention} answered correctly in record time: **{ans}**!")
        except asyncio.TimeoutError:
            await ctx.send(f"⏳ **Time's up!** The answer was: **{ans}**.")

    @commands.command(name="trivia_history", description="Play World History trivia")
    async def trivia_history(self, ctx):
        res = await self.fetch_opentdb_question(category_id=23)
        if not res: return await ctx.reply("❌ Trivia server busy.")
        q, c, opts, diff, cat = res
        embed = discord.Embed(title=f"📜 History Trivia: {cat}", description=f"**{q}**\n\n*Difficulty:* `{diff}`", color=0xD4AC0D)
        await ctx.reply(embed=embed, view=TriviaView(ctx.author, c, opts))

    @commands.command(name="trivia_geography", description="Play World Geography trivia")
    async def trivia_geography(self, ctx):
        res = await self.fetch_opentdb_question(category_id=22)
        if not res: return await ctx.reply("❌ Trivia server busy.")
        q, c, opts, diff, cat = res
        embed = discord.Embed(title=f"🌍 Geography Trivia: {cat}", description=f"**{q}**\n\n*Difficulty:* `{diff}`", color=0x27AE60)
        await ctx.reply(embed=embed, view=TriviaView(ctx.author, c, opts))

    @commands.command(name="trivia_music", description="Play Music & Songs trivia")
    async def trivia_music(self, ctx):
        res = await self.fetch_opentdb_question(category_id=12)
        if not res: return await ctx.reply("❌ Trivia server busy.")
        q, c, opts, diff, cat = res
        embed = discord.Embed(title=f"🎵 Music Trivia: {cat}", description=f"**{q}**\n\n*Difficulty:* `{diff}`", color=0x9B59B6)
        await ctx.reply(embed=embed, view=TriviaView(ctx.author, c, opts))

    @commands.command(name="trivia_film", description="Play Movies & Cinema trivia")
    async def trivia_film(self, ctx):
        res = await self.fetch_opentdb_question(category_id=11)
        if not res: return await ctx.reply("❌ Trivia server busy.")
        q, c, opts, diff, cat = res
        embed = discord.Embed(title=f"🎬 Cinema Trivia: {cat}", description=f"**{q}**\n\n*Difficulty:* `{diff}`", color=0xE74C3C)
        await ctx.reply(embed=embed, view=TriviaView(ctx.author, c, opts))

    @commands.command(name="trivia_mythology", description="Play World Mythology trivia")
    async def trivia_mythology(self, ctx):
        res = await self.fetch_opentdb_question(category_id=20)
        if not res: return await ctx.reply("❌ Trivia server busy.")
        q, c, opts, diff, cat = res
        embed = discord.Embed(title=f"⚡ Mythology Trivia: {cat}", description=f"**{q}**\n\n*Difficulty:* `{diff}`", color=0xF39C12)
        await ctx.reply(embed=embed, view=TriviaView(ctx.author, c, opts))

    @commands.command(name="trivia_sports", description="Play Sports trivia")
    async def trivia_sports(self, ctx):
        res = await self.fetch_opentdb_question(category_id=21)
        if not res: return await ctx.reply("❌ Trivia server busy.")
        q, c, opts, diff, cat = res
        embed = discord.Embed(title=f"⚽ Sports Trivia: {cat}", description=f"**{q}**\n\n*Difficulty:* `{diff}`", color=0x1ABC9C)
        await ctx.reply(embed=embed, view=TriviaView(ctx.author, c, opts))

    @commands.command(name="speed_multiply", description="Rapid multiplication contest")
    async def speed_multiply(self, ctx):
        a = random.randint(6, 19)
        b = random.randint(6, 19)
        ans = a * b
        embed = discord.Embed(title="⚡ Multiplication Blitz", description=f"# `{a} × {b} = ?`\n\n*First to answer correctly wins! (15s)*", color=INFO_COLOR)
        await ctx.reply(embed=embed)
        def check(m): return m.channel == ctx.channel and not m.author.bot and m.content.strip() == str(ans)
        try:
            msg = await self.bot.wait_for("message", check=check, timeout=15)
            await msg.reply(f"🏆 {msg.author.mention} solved it: **{ans}**!")
        except asyncio.TimeoutError:
            await ctx.send(f"⏳ Time's up! Answer was: **{ans}**.")

    @commands.command(name="speed_add", description="Rapid addition contest")
    async def speed_add(self, ctx):
        a = random.randint(45, 180)
        b = random.randint(45, 180)
        ans = a + b
        embed = discord.Embed(title="⚡ Addition Blitz", description=f"# `{a} + {b} = ?`\n\n*First to answer correctly wins! (15s)*", color=SUCCESS_COLOR)
        await ctx.reply(embed=embed)
        def check(m): return m.channel == ctx.channel and not m.author.bot and m.content.strip() == str(ans)
        try:
            msg = await self.bot.wait_for("message", check=check, timeout=15)
            await msg.reply(f"🏆 {msg.author.mention} solved it: **{ans}**!")
        except asyncio.TimeoutError:
            await ctx.send(f"⏳ Time's up! Answer was: **{ans}**.")

async def setup(bot):
    await bot.add_cog(TriviaQuiz(bot))
