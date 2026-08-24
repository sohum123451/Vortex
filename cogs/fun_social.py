import random
import aiohttp
import discord
from discord.ext import commands
from utils import MAIN_COLOR, INFO_COLOR, SUCCESS_COLOR, WARN_COLOR

class FunSocial(commands.Cog):
    """Fun, memes, social matchmaking, jokes, trivia facts, and ASCII formatting tools."""

    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="eightball", description="Ask the magic 8-ball a question")
    async def eightball(self, ctx, *, question: str):
        res = [
            "Yes, definitely.", "It is decidedly so.", "Without a doubt.",
            "Yes - definitely.", "You may rely on it.", "As I see it, yes.",
            "Most likely.", "Outlook good.", "Yes.", "Signs point to yes.",
            "Reply hazy, try again.", "Ask again later.", "Better not tell you now.",
            "Cannot predict now.", "Concentrate and ask again.",
            "Don't count on it.", "My reply is no.", "My sources say no.",
            "Outlook not so good.", "Very doubtful."
        ]
        await ctx.reply(f"🎱 **Question:** {question}\n🔮 **Answer:** {random.choice(res)}")

    @commands.hybrid_command(name="ship", description="Calculate love compatibility between two members")
    async def ship(self, ctx, user1: discord.Member, user2: discord.Member = None):
        u2 = user2 or ctx.author
        combined = sorted([user1.id, u2.id])
        random.seed(combined[0] + combined[1])
        percent = random.randint(1, 100)
        random.seed()

        bar_len = 10
        filled = int(percent / 10)
        bar = "💖" * filled + "🖤" * (bar_len - filled)
        comment = (
            "Soulmates destined forever! 💍" if percent >= 85
            else "Great chemistry! 💕" if percent >= 60
            else "Casual friendship territory! 🤝" if percent >= 35
            else "Better stay away from each other! 🥀"
        )
        embed = discord.Embed(
            title=f"💘 Love Compatibility: {user1.display_name} + {u2.display_name}",
            description=f"**Compatibility Rating:** `{percent}%`\n{bar}\n\n*{comment}*",
            color=discord.Color.magenta(),
        )
        await ctx.reply(embed=embed)

    @commands.hybrid_command(name="meme", description="Get a trending meme from Reddit")
    async def meme(self, ctx):
        await ctx.defer()
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get("https://meme-api.com/gimme", timeout=5) as resp:
                    if resp.status != 200:
                        return await ctx.reply("❌ Could not fetch meme.")
                    data = await resp.json()
                    embed = discord.Embed(title=data.get("title", "Meme"), url=data.get("postLink", ""), color=MAIN_COLOR)
                    embed.set_image(url=data.get("url"))
                    embed.set_footer(text=f"👍 {data.get('ups', 0)} upvotes • r/{data.get('subreddit')}")
                    await ctx.reply(embed=embed)
            except Exception as e:
                await ctx.reply(f"❌ Meme API error: {e}")

    @commands.hybrid_command(name="joke", description="Get a random joke")
    async def joke(self, ctx):
        jokes = [
            "Why do programmers prefer dark mode? Because light attracts bugs!",
            "Why do Java developers wear glasses? Because they don't C#!",
            "There are 10 types of people in the world: those who understand binary, and those who don't.",
            "How many programmers does it take to change a light bulb? None, it's a hardware problem!",
            "Why was the JavaScript developer sad? Because they didn't know how to 'null' their feelings.",
            "A SQL query walks into a bar, walks up to two tables and asks: 'Can I join you?'",
        ]
        await ctx.reply(f"😄 **{random.choice(jokes)}**")

    @commands.command(name="dadjoke", description="Get a classic dad joke")
    async def dadjoke(self, ctx):
        dad_jokes = [
            "I'm reading a book on anti-gravity. It's impossible to put down!",
            "Did you hear about the guy who invented Lifesavers? They say he made a mint!",
            "Why don't skeletons fight each other? They don't have the guts.",
            "What do you call fake spaghetti? An impasta!",
            "Want to hear a joke about paper? Never mind, it's tearable.",
        ]
        await ctx.reply(f"👨 **Dad Joke:** {random.choice(dad_jokes)}")

    @commands.command(name="fact", description="Get a fascinating trivia fact")
    async def fact(self, ctx):
        facts = [
            "Honey never spoils. Archaeologists have found 3,000-year-old honey that is completely edible.",
            "Octopuses have three hearts, nine brains, and blue blood.",
            "The first computer bug was an actual real moth found trapped inside a Harvard Mark II computer in 1947.",
            "Venus is the only planet in our solar system that spins clockwise.",
            "Bananas are curved because they grow towards the sun against gravity (negative geotropism).",
            "A cloud can weigh more than a million pounds.",
        ]
        await ctx.reply(f"🧠 **Fact:** {random.choice(facts)}")

    @commands.command(name="choose", description="Choose between multiple options: &choose pizza, burger, tacos")
    async def choose(self, ctx, *, options: str):
        choices = [opt.strip() for opt in options.split(",") if opt.strip()]
        if len(choices) < 2:
            return await ctx.reply("❌ Please provide at least 2 choices separated by commas (e.g. `&choose pizza, burger`).")
        await ctx.reply(f"🎯 I choose: **{random.choice(choices)}**!")

    @commands.command(name="howgay", description="Gay rate machine")
    async def howgay(self, ctx, member: discord.Member = None):
        target = member or ctx.author
        random.seed(target.id)
        rate = random.randint(0, 100)
        random.seed()
        await ctx.reply(f"🏳️‍🌈 **{target.display_name}** is `{rate}%` gay!")

    @commands.command(name="simp", description="Simp rate machine")
    async def simp(self, ctx, member: discord.Member = None):
        target = member or ctx.author
        random.seed(target.id + 1)
        rate = random.randint(0, 100)
        random.seed()
        await ctx.reply(f"🥺 **{target.display_name}** is `{rate}%` simp!")

    @commands.command(name="chad", description="Chad / Gigachad rate machine")
    async def chad(self, ctx, member: discord.Member = None):
        target = member or ctx.author
        random.seed(target.id + 2)
        rate = random.randint(10, 100)
        random.seed()
        await ctx.reply(f"🗿 **{target.display_name}** is `{rate}%` Gigachad!")

    @commands.command(name="roll", description="Roll a dice: &roll 20")
    async def roll(self, ctx, sides: int = 6):
        await ctx.reply(f"🎲 Rolled a **{random.randint(1, max(1, sides))}** (d{sides})")

    @commands.command(name="coinflip", description="Flip a coin")
    async def coinflip(self, ctx):
        await ctx.reply(f"🪙 **{random.choice(['Heads', 'Tails'])}**")

    @commands.command(name="reverse", description="Reverse input text: &reverse hello")
    async def reverse_text(self, ctx, *, text: str):
        await ctx.reply(f"🔄 `{text[::-1]}`")

    @commands.command(name="emojify", description="Convert text to large regional indicator emojis")
    async def emojify(self, ctx, *, text: str):
        out = []
        for char in text.lower():
            if char.isalpha():
                out.append(f":regional_indicator_{char}:")
            elif char == " ":
                out.append("   ")
            else:
                out.append(char)
        await ctx.reply(" ".join(out)[:2000])

    @commands.command(name="wholesome", description="Give a wholesome compliment")
    async def wholesome(self, ctx, member: discord.Member = None):
        target = member or ctx.author
        compliments = [
            "Your positive energy lights up the entire server!",
            "You have an amazing sense of humor!",
            "You are smarter than you give yourself credit for!",
            "You're a true champion and a great friend!",
            "Your creativity inspires everyone around you!",
        ]
        await ctx.reply(f"💖 {target.mention}, {random.choice(compliments)}")

    @commands.command(name="insult", description="Playful humorous roast / insult")
    async def insult(self, ctx, member: discord.Member = None):
        target = member or ctx.author
        insults = [
            "You're the reason the instructions on shampoo bottles exist.",
            "If I had a dollar for every smart thing you said, I'd be broke.",
            "You bring everyone so much joy... whenever you leave the voice channel.",
            "I'd agree with you but then we'd both be wrong.",
        ]
        await ctx.reply(f"🔥 {target.mention}, {random.choice(insults)}")

    @commands.command(name="fortune", description="Crack open a fortune cookie")
    async def fortune(self, ctx):
        fortunes = [
            "A thrilling opportunity awaits you in the near future.",
            "Your hard work will pay off sooner than you expect.",
            "Good news will come to you by mail or discord ping.",
            "Trust your intuition, it will guide you to success.",
            "Great things take time; stay patient and keep building.",
        ]
        await ctx.reply(f"🥠 **Fortune Cookie:** *\"{random.choice(fortunes)}\"*")

    @commands.command(name="showerthought", description="Mind-blowing shower thought")
    async def showerthought(self, ctx):
        thoughts = [
            "Water isn't wet by itself; it only makes other things wet.",
            "Your future self is watching you right now through your memories.",
            "The brain named itself.",
            "Mirrors don't break; they just multiply.",
            "Nothing is on fire; fire is on things.",
        ]
        await ctx.reply(f"🚿 **Shower Thought:** *\"{random.choice(thoughts)}\"*")

    @commands.command(name="dogfact", description="Get a random dog fact")
    async def dogfact(self, ctx):
        facts = [
            "Dogs' sense of smell is about 10,000 to 100,000 times more acute than humans.",
            "A dog's nose print is unique, much like a human's fingerprint.",
            "Three dogs survived the historical sinking of the Titanic.",
        ]
        await ctx.reply(f"🐶 **Dog Fact:** {random.choice(facts)}")

    @commands.command(name="catfact", description="Get a random cat fact")
    async def catfact(self, ctx):
        facts = [
            "Cats spend roughly 70% of their entire lives sleeping.",
            "A cat can jump up to six times its own height in a single bound.",
            "Cats have 32 muscles in each of their ears.",
        ]
        await ctx.reply(f"🐱 **Cat Fact:** {random.choice(facts)}")

    @commands.command(name="advice", description="Get insightful life advice")
    async def advice(self, ctx):
        advices = [
            "Never make permanent decisions on temporary emotions.",
            "Comparison is the thief of joy; focus on your own journey.",
            "Drink plenty of water and get enough sleep tonight.",
            "Consistency beats talent when talent doesn't work hard.",
        ]
        await ctx.reply(f"💡 **Life Advice:** *\"{random.choice(advices)}\"*")

    @commands.command(name="pickup_line", description="Get a smooth pickup line")
    async def pickup_line(self, ctx):
        lines = [
            "Are you a Wi-Fi router? Because I'm feeling a strong connection.",
            "Do you have a map? Because I just got lost in your eyes.",
            "Are you Google? Because you have everything I've been searching for.",
        ]
        await ctx.reply(f"😏 **Pickup Line:** *\"{random.choice(lines)}\"*")

    @commands.command(name="clown", description="Clown rate meter")
    async def clown(self, ctx, member: discord.Member = None):
        target = member or ctx.author
        rate = random.randint(0, 100)
        await ctx.reply(f"🤡 **{target.display_name}** is `{rate}%` clown!")

    @commands.command(name="sus", description="Among Us sus meter")
    async def sus(self, ctx, member: discord.Member = None):
        target = member or ctx.author
        rate = random.randint(0, 100)
        imposter = "🚨 IMPOSTER DETECTED!" if rate > 75 else "😇 Crewmate innocent."
        await ctx.reply(f"📮 **{target.display_name}** is `{rate}%` sus! *{imposter}*")

    @commands.command(name="iq", description="Galaxy brain IQ tester")
    async def iq(self, ctx, member: discord.Member = None):
        target = member or ctx.author
        iq_val = random.randint(50, 220)
        await ctx.reply(f"🧠 **{target.display_name}'s IQ:** `{iq_val}`")

    @commands.command(name="dank", description="Dank meme meter")
    async def dank(self, ctx, member: discord.Member = None):
        target = member or ctx.author
        rate = random.randint(10, 100)
        await ctx.reply(f"🔥 **{target.display_name}** is `{rate}%` dank!")

    @commands.command(name="boop", description="Boop someone's nose")
    async def boop(self, ctx, member: discord.Member):
        await ctx.reply(f"👃 **Boop!** {ctx.author.mention} gently booped {member.mention}'s nose!")

    @commands.command(name="vibe_check", description="Run a vibe check on a member")
    async def vibe_check(self, ctx, member: discord.Member = None):
        target = member or ctx.author
        passed = random.choice([True, True, False])
        if passed:
            await ctx.reply(f"✨ **Vibe Check:** {target.mention} passed the vibe check with flying colors! 🌟")
        else:
            await ctx.reply(f"💀 **Vibe Check:** {target.mention} failed the vibe check. Bad vibes detected! 🚨")

    @commands.command(name="f", description="Press F to pay respects")
    async def f_respects(self, ctx, *, reason: str = None):
        r_str = f" for **{reason}**" if reason else ""
        await ctx.reply(f"🫡 **{ctx.author.display_name}** has paid their respects{r_str}. 💐")

    @commands.command(name="kill", description="Fictional playful battle defeat")
    async def kill(self, ctx, member: discord.Member):
        ways = [
            f"{ctx.author.mention} hit {member.mention} with a giant squeaky hammer!",
            f"{ctx.author.mention} dropped a piano on {member.mention} Looney Tunes style!",
            f"{ctx.author.mention} banished {member.mention} to the shadow realm!",
        ]
        await ctx.reply(f"☠️ {random.choice(ways)}")

    @commands.command(name="marry", description="Propose to marry a member")
    async def marry(self, ctx, member: discord.Member):
        if member == ctx.author:
            return await ctx.reply("❌ You cannot marry yourself!")
        await ctx.reply(f"💍 **Marriage Proposal!** {ctx.author.mention} proposed to {member.mention}! Do you say YES? 💖")

    @commands.command(name="rizz_meter", description="Check a member's rizz percentage")
    async def rizz_meter(self, ctx, member: discord.Member = None):
        tgt = member or ctx.author
        rate = random.randint(1, 100)
        res = "🗿 W RIZZ!" if rate > 80 else "💀 L RIZZ!" if rate < 25 else "😎 Solid rizz."
        await ctx.reply(f"✨ **{tgt.display_name}'s Rizz:** `{rate}%` — {res}")

    @commands.command(name="friendship_meter", description="Calculate friendship affinity between two members")
    async def friendship_meter(self, ctx, m1: discord.Member, m2: discord.Member = None):
        m2 = m2 or ctx.author
        rate = random.randint(30, 100)
        await ctx.reply(f"🤝 **Friendship Affinity:** {m1.mention} & {m2.mention} = `{rate}%` Besties!")

    @commands.command(name="chaos_meter", description="Check chaos alignment level")
    async def chaos_meter(self, ctx, member: discord.Member = None):
        tgt = member or ctx.author
        rate = random.randint(1, 100)
        await ctx.reply(f"🌪️ **{tgt.display_name}'s Chaos Level:** `{rate}%` Chaotic Energy!")

    @commands.command(name="luck_meter", description="Daily luck percentage")
    async def luck_meter(self, ctx, member: discord.Member = None):
        tgt = member or ctx.author
        rate = random.randint(1, 100)
        await ctx.reply(f"🍀 **{tgt.display_name}'s Luck Today:** `{rate}%`")

    @commands.command(name="chad_meter", description="GigaChad rating")
    async def chad_meter(self, ctx, member: discord.Member = None):
        tgt = member or ctx.author
        rate = random.randint(1, 100)
        await ctx.reply(f"🗿 **{tgt.display_name}'s GigaChad Energy:** `{rate}%`")

    @commands.command(name="simp_meter", description="Simp percentage meter")
    async def simp_meter(self, ctx, member: discord.Member = None):
        tgt = member or ctx.author
        rate = random.randint(1, 100)
        await ctx.reply(f"🥺 **{tgt.display_name}** is `{rate}%` simp!")

    @commands.command(name="sanity_meter", description="Check remaining sanity percentage")
    async def sanity_meter(self, ctx, member: discord.Member = None):
        tgt = member or ctx.author
        rate = random.randint(0, 100)
        await ctx.reply(f"🧠 **{tgt.display_name}'s Sanity:** `{rate}%` remaining.")

    @commands.command(name="gamer_meter", description="Pro gamer score")
    async def gamer_meter(self, ctx, member: discord.Member = None):
        tgt = member or ctx.author
        rate = random.randint(1, 100)
        await ctx.reply(f"🎮 **{tgt.display_name}'s Gamer Score:** `{rate}%` MLG Pro!")

    @commands.command(name="coolness_meter", description="Check coolness factor")
    async def coolness_meter(self, ctx, member: discord.Member = None):
        tgt = member or ctx.author
        rate = random.randint(1, 100)
        await ctx.reply(f"🕶️ **{tgt.display_name}'s Coolness:** `{rate}%` ice cold!")

    @commands.command(name="dadjoke", description="Get a classic dad joke")
    async def dadjoke(self, ctx):
        jokes = [
            "Why don't skeletons fight each other? They don't have the guts.",
            "I'm reading a book on anti-gravity. I just can't put it down!",
            "What do you call a fake noodle? An impasta!",
            "Why do cows have hooves instead of feet? Because they lactose!",
            "How do you organize a space party? You planet!",
        ]
        await ctx.reply(f"👴 {random.choice(jokes)}")

    @commands.command(name="chucknorris", description="Random Chuck Norris fact")
    async def chucknorris(self, ctx):
        facts = [
            "Chuck Norris can delete the Recycle Bin.",
            "When Chuck Norris does a push-up, he isn't lifting himself up, he's pushing the Earth down.",
            "Chuck Norris counted to infinity... twice.",
            "Time waits for no man. Unless that man is Chuck Norris.",
        ]
        await ctx.reply(f"🤠 {random.choice(facts)}")

async def setup(bot):
    await bot.add_cog(FunSocial(bot))
