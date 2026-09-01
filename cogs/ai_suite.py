import os
import aiohttp
import discord
from discord.ext import commands
from google import genai
from groq import AsyncGroq
from utils import MAIN_COLOR, INFO_COLOR, SUCCESS_COLOR, ERROR_COLOR

class AISuite(commands.Cog):
    """Next-generation generative AI suite powered by Gemini 3.6 Flash and Groq LLMs."""

    def __init__(self, bot):
        self.bot = bot
        gemini_key = os.getenv("GEMINI_API_KEY", "")
        self.gemini = genai.Client(api_key=gemini_key).aio if gemini_key else None
        groq_key = os.getenv("GROQ_API_KEY", "")
        self.groq = AsyncGroq(api_key=groq_key) if groq_key else None
        self.active_vai_users = set()
        self.user_memory = {}

    async def generate_ai(self, prompt: str, system_instruction: str = None):
        """Helper to generate text using Gemini 3.6 Flash with fallback."""
        if not self.gemini:
            raise Exception("Gemini API key is not configured.")

        contents = f"{system_instruction}\n\n{prompt}" if system_instruction else prompt
        try:
            res = await self.gemini.models.generate_content(
                model="gemini-3.6-flash",
                contents=contents,
            )
            return res.text.strip()
        except Exception:
            res = await self.gemini.models.generate_content(
                model="gemini-2.0-flash",
                contents=contents,
            )
            return res.text.strip()

    @commands.hybrid_command(name="chat", description="Chat with high-speed Gemini 3.6 AI")
    async def chat(self, ctx, *, prompt: str):
        await ctx.defer()
        try:
            ans = await self.generate_ai(prompt)
            if len(ans) > 2000:
                for i in range(0, len(ans), 2000):
                    await ctx.send(ans[i : i + 2000])
            else:
                await ctx.reply(ans)
        except Exception as e:
            await ctx.reply(f"❌ AI Error: {e}")

    @commands.hybrid_command(name="ask", description="Ask Gemini about an image attachment: attach image + &ask question")
    async def ask(self, ctx, *, question: str = "Explain what is in this image in detail."):
        if not ctx.message.attachments:
            return await ctx.reply("❌ Please attach an image to your message.")
        att = ctx.message.attachments[0]
        if not any(att.filename.lower().endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".webp"]):
            return await ctx.reply("❌ Please attach a valid image (`.png`, `.jpg`, `.jpeg`, `.webp`).")

        await ctx.defer()
        async with aiohttp.ClientSession() as session:
            async with session.get(att.url) as resp:
                img_bytes = await resp.read()

        try:
            res = await self.gemini.models.generate_content(
                model="gemini-3.6-flash",
                contents=[
                    genai.types.Part.from_bytes(data=img_bytes, mime_type=att.content_type or "image/png"),
                    question,
                ],
            )
            await ctx.reply(res.text.strip()[:2000])
        except Exception as e:
            await ctx.reply(f"❌ Vision AI error: {e}")

    @commands.hybrid_command(name="summarize", description="Summarize long text or articles into clean key points")
    async def summarize(self, ctx, *, text: str):
        await ctx.defer()
        try:
            ans = await self.generate_ai(f"Summarize the following text concisely in clean bullet points:\n\n{text}")
            await ctx.reply(f"📝 **Summary:**\n{ans[:2000]}")
        except Exception as e:
            await ctx.reply(f"❌ Error: {e}")

    @commands.hybrid_command(name="translate", description="Translate text: &translate Spanish Hello world")
    async def translate(self, ctx, target_language: str, *, text: str):
        await ctx.defer()
        try:
            ans = await self.generate_ai(f"Translate the following text into {target_language}. Output ONLY the translated text:\n\n{text}")
            await ctx.reply(f"🌐 **Translation ({target_language.title()}):**\n{ans[:2000]}")
        except Exception as e:
            await ctx.reply(f"❌ Error: {e}")

    @commands.hybrid_command(name="grammar", description="Fix grammar, spelling, and tone")
    async def grammar(self, ctx, *, text: str):
        await ctx.defer()
        try:
            ans = await self.generate_ai(f"Fix all grammar, punctuation, and wording for the text. Output the clean corrected version:\n\n{text}")
            await ctx.reply(f"✍️ **Grammar Fix:**\n{ans[:2000]}")
        except Exception as e:
            await ctx.reply(f"❌ Error: {e}")

    @commands.hybrid_command(name="code_explain", description="Explain, review, and debug code snippets")
    async def code_explain(self, ctx, *, code: str):
        await ctx.defer()
        try:
            ans = await self.generate_ai(f"Explain what this code does, identify any potential bugs, and suggest improvements:\n```\n{code}\n```")
            await ctx.reply(ans[:2000])
        except Exception as e:
            await ctx.reply(f"❌ Error: {e}")

    @commands.command(name="code_generate", description="Generate code in any language: &code_generate Python binary search")
    async def code_generate(self, ctx, language: str, *, prompt: str):
        await ctx.defer()
        try:
            ans = await self.generate_ai(f"Write high-quality, clean, well-commented {language} code for the following requirement:\n{prompt}")
            await ctx.reply(ans[:2000])
        except Exception as e:
            await ctx.reply(f"❌ Error: {e}")

    @commands.command(name="regex_gen", description="Generate a regular expression from plain English")
    async def regex_gen(self, ctx, *, description: str):
        await ctx.defer()
        try:
            ans = await self.generate_ai(f"Generate a clean Regex pattern matching: '{description}'. Provide the regex and a brief explanation of how it works.")
            await ctx.reply(f"🔍 **Regex Generator:**\n{ans[:2000]}")
        except Exception as e:
            await ctx.reply(f"❌ Error: {e}")

    @commands.command(name="sql_gen", description="Generate an SQL query from plain English")
    async def sql_gen(self, ctx, *, description: str):
        await ctx.defer()
        try:
            ans = await self.generate_ai(f"Generate an optimized SQL query for: '{description}'. Include code block and brief explanation.")
            await ctx.reply(f"🗄️ **SQL Query Generator:**\n{ans[:2000]}")
        except Exception as e:
            await ctx.reply(f"❌ Error: {e}")

    @commands.command(name="story", description="Generate an imaginative story: &story sci-fi cyberpunk hacker")
    async def story(self, ctx, *, theme: str):
        await ctx.defer()
        try:
            ans = await self.generate_ai(f"Write an engaging, exciting short story based on the theme: '{theme}'. Around 250 words.")
            await ctx.reply(f"📖 **Story:**\n{ans[:2000]}")
        except Exception as e:
            await ctx.reply(f"❌ Error: {e}")

    @commands.command(name="poem", description="Generate a poetic verse: &poem night sky and rain")
    async def poem(self, ctx, *, topic: str):
        await ctx.defer()
        try:
            ans = await self.generate_ai(f"Write a beautiful, rhyming poem about: '{topic}'.")
            await ctx.reply(f"📜 **Poem:**\n{ans[:2000]}")
        except Exception as e:
            await ctx.reply(f"❌ Error: {e}")

    @commands.command(name="roast", description="Playful AI roast of a server member")
    async def roast(self, ctx, member: discord.Member = None):
        target = member or ctx.author
        await ctx.defer()
        try:
            ans = await self.generate_ai(f"Generate a clever, funny, and witty roast for a Discord user named '{target.display_name}'. Keep it lighthearted and hilarious.")
            await ctx.reply(f"🔥 {target.mention} {ans}")
        except Exception as e:
            await ctx.reply(f"❌ Error: {e}")

    @commands.command(name="compliment", description="Wholesome AI compliment for a member")
    async def compliment(self, ctx, member: discord.Member = None):
        target = member or ctx.author
        await ctx.defer()
        try:
            ans = await self.generate_ai(f"Generate a sweet, uplifting, wholesome compliment for a friend named '{target.display_name}'.")
            await ctx.reply(f"💖 {target.mention} {ans}")
        except Exception as e:
            await ctx.reply(f"❌ Error: {e}")

    @commands.command(name="eli5", description="Explain a complex concept like I'm 5 years old")
    async def eli5(self, ctx, *, concept: str):
        await ctx.defer()
        try:
            ans = await self.generate_ai(f"Explain the concept of '{concept}' simply as if explaining to a 5-year-old child with fun analogies.")
            await ctx.reply(f"👶 **ELI5 ({concept.title()}):**\n{ans[:2000]}")
        except Exception as e:
            await ctx.reply(f"❌ Error: {e}")

    @commands.command(name="math_solver", description="Step-by-step mathematical reasoning solver")
    async def math_solver(self, ctx, *, problem: str):
        await ctx.defer()
        try:
            ans = await self.generate_ai(f"Solve the following math problem step-by-step with clear explanations:\n\n{problem}")
            await ctx.reply(f"📐 **Math Solution:**\n{ans[:2000]}")
        except Exception as e:
            await ctx.reply(f"❌ Error: {e}")

    # Conversational Companion AI (Vai)
    @commands.command(name="v_toggle", description="Toggle persistent conversational companion AI")
    async def v_toggle(self, ctx):
        self.active_vai_users.add(ctx.author.id)
        self.user_memory.setdefault(ctx.author.id, [])
        await ctx.reply("🚀 **Memory Companion AI Activated!** I will now reply to your messages in this channel.")

    @commands.command(name="v_stop", description="Stop conversational AI")
    async def v_stop(self, ctx):
        if ctx.author.id in self.active_vai_users:
            self.active_vai_users.remove(ctx.author.id)
            self.user_memory.pop(ctx.author.id, None)
            await ctx.reply("🛑 **Memory Companion AI Stopped.** Conversation memory cleared.")
        else:
            await ctx.reply("❌ Companion AI was not active for you.")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or message.author.id not in self.active_vai_users:
            return
        if message.content.startswith(("&", "/")):
            return

        async with message.channel.typing():
            history = self.user_memory.get(message.author.id, [])
            history.append({"role": "user", "content": message.content})
            if len(history) > 10:
                history = history[-10:]

            bot_response = None
            if self.groq:
                try:
                    messages = [{"role": "system", "content": "You are Vortex, a witty, charismatic, helpful Discord companion with conversational memory."}] + history
                    res = await self.groq.chat.completions.create(model="qwen/qwen3.8-27b", messages=messages)
                    bot_response = res.choices[0].message.content
                except Exception:
                    pass

            if not bot_response and self.gemini:
                try:
                    res = await self.gemini.models.generate_content(
                        model="gemini-3.6-flash",
                        contents=[h["content"] for h in history],
                    )
                    bot_response = res.text.strip()
                except Exception:
                    pass

            if bot_response:
                history.append({"role": "assistant", "content": bot_response})
                self.user_memory[message.author.id] = history
                await message.reply(bot_response[:2000])

    @commands.command(name="interview_prep", description="AI Mock technical/behavioral interview question: &interview_prep <role>")
    async def interview_prep(self, ctx, *, role: str):
        await ctx.defer()
        prompt = f"Generate 3 realistic interview questions (1 technical, 1 scenario-based, 1 behavioral) for a {role} role, plus bullet points on how to ace the answer."
        res = await self.generate_ai_response(prompt)
        embed = discord.Embed(title=f"🎯 Mock Interview Prep: {role.title()}", description=res[:4000], color=MAIN_COLOR)
        await ctx.reply(embed=embed)

    @commands.command(name="resume_bullet", description="AI Resume bullet point enhancer: &resume_bullet <rough_achievement>")
    async def resume_bullet(self, ctx, *, achievement: str):
        await ctx.defer()
        prompt = f"Transform this rough achievement into 3 high-impact, metric-driven resume bullet points using strong action verbs: '{achievement}'"
        res = await self.generate_ai_response(prompt)
        embed = discord.Embed(title="📄 Professional Resume Bullets", description=res[:4000], color=SUCCESS_COLOR)
        await ctx.reply(embed=embed)

    @commands.command(name="email_writer", description="AI Professional email drafting tool: &email_writer <purpose>")
    async def email_writer(self, ctx, *, purpose: str):
        await ctx.defer()
        prompt = f"Write a polished, professional email for the following scenario: '{purpose}'. Include subject line and formal sign-off."
        res = await self.generate_ai_response(prompt)
        embed = discord.Embed(title="✉️ Professional Email Draft", description=res[:4000], color=INFO_COLOR)
        await ctx.reply(embed=embed)

    @commands.command(name="regex_builder", description="AI Regular Expression builder: &regex_builder <what to match>")
    async def regex_builder(self, ctx, *, pattern_desc: str):
        await ctx.defer()
        prompt = f"Generate a Regex pattern for: '{pattern_desc}'. Provide the regex, explanation of tokens, and 2 test examples."
        res = await self.generate_ai_response(prompt)
        embed = discord.Embed(title="🔍 AI Regex Builder", description=res[:4000], color=MAIN_COLOR)
        await ctx.reply(embed=embed)

    @commands.command(name="haiku_writer", description="AI Japanese 5-7-5 Haiku generator: &haiku_writer <topic>")
    async def haiku_writer(self, ctx, *, topic: str):
        await ctx.defer()
        prompt = f"Write a beautiful 5-7-5 syllable Haiku poem about '{topic}'."
        res = await self.generate_ai_response(prompt)
        embed = discord.Embed(title=f"🌸 Haiku: {topic}", description=f"*{res}*", color=0xFF69B4)
        await ctx.reply(embed=embed)

    @commands.command(name="ai_limerick", description="AI Limerick generator: &ai_limerick <topic>")
    async def ai_limerick(self, ctx, *, topic: str):
        await ctx.defer()
        res = await self.generate_ai_response(f"Write a funny 5-line AABBA rhyme limerick about {topic}.")
        await ctx.reply(f"📜 **Limerick:**\n{res[:2000]}")

    @commands.command(name="ai_story_starter", description="AI Story hook generator: &ai_story_starter <genre>")
    async def ai_story_starter(self, ctx, *, genre: str):
        await ctx.defer()
        res = await self.generate_ai_response(f"Write an intriguing opening paragraph / hook for a {genre} story.")
        await ctx.reply(f"📖 **Story Hook ({genre.title()}):**\n{res[:2000]}")

    @commands.command(name="ai_rap_battle", description="AI Rap verse: &ai_rap_battle <topic>")
    async def ai_rap_battle(self, ctx, *, topic: str):
        await ctx.defer()
        res = await self.generate_ai_response(f"Drop 8 hot, rhythmic, rhyming rap bars about {topic}.")
        await ctx.reply(f"🎤 **Rap Bars:**\n{res[:2000]}")

    @commands.command(name="ai_pun", description="AI Puns generator: &ai_pun <subject>")
    async def ai_pun(self, ctx, *, subject: str):
        await ctx.defer()
        res = await self.generate_ai_response(f"Give me 3 witty, hilarious puns about {subject}.")
        await ctx.reply(f"🧀 **Puns:**\n{res[:2000]}")

    @commands.command(name="ai_tweet", description="AI Viral tweet drafter: &ai_tweet <topic>")
    async def ai_tweet(self, ctx, *, topic: str):
        await ctx.defer()
        res = await self.generate_ai_response(f"Draft a punchy, viral Twitter/X post with relevant hashtags about: {topic}")
        await ctx.reply(f"🐦 **Tweet Draft:**\n{res[:2000]}")

    @commands.command(name="ai_bio", description="AI Social profile bio generator: &ai_bio <persona/vibe>")
    async def ai_bio(self, ctx, *, vibe: str):
        await ctx.defer()
        res = await self.generate_ai_response(f"Write 3 creative Discord/Twitter profile bios with aesthetic emojis for someone who is: {vibe}")
        await ctx.reply(f"✨ **Profile Bios:**\n{res[:2000]}")

    @commands.command(name="ai_commit", description="AI Git commit message builder: &ai_commit <changes>")
    async def ai_commit(self, ctx, *, changes: str):
        await ctx.defer()
        res = await self.generate_ai_response(f"Generate conventional commit messages (feat, fix, refactor, chore) for these changes: {changes}")
        await ctx.reply(f"📦 **Git Commit Messages:**\n{res[:2000]}")

    @commands.command(name="ai_sql", description="AI SQL query writer: &ai_sql <requirement>")
    async def ai_sql(self, ctx, *, requirement: str):
        await ctx.defer()
        res = await self.generate_ai_response(f"Write a standard ANSI SQL query for this requirement and explain it briefly: {requirement}")
        await ctx.reply(f"🗄️ **SQL Query:**\n{res[:2000]}")

    @commands.command(name="ai_bash", description="AI Bash script command generator: &ai_bash <task>")
    async def ai_bash(self, ctx, *, task: str):
        await ctx.defer()
        res = await self.generate_ai_response(f"Provide the exact Bash / Linux shell command or script to accomplish: {task}")
        await ctx.reply(f"💻 **Bash Command:**\n{res[:2000]}")

    @commands.command(name="ai_css", description="AI Modern CSS snippet helper: &ai_css <effect/layout>")
    async def ai_css(self, ctx, *, effect: str):
        await ctx.defer()
        res = await self.generate_ai_response(f"Provide modern CSS (Flexbox/Grid/Backdrop-filter/Animation) code for: {effect}")
        await ctx.reply(f"🎨 **CSS Snippet:**\n{res[:2000]}")

    @commands.command(name="ai_color_palette", description="AI Color palette generator: &ai_color_palette <theme>")
    async def ai_color_palette(self, ctx, *, theme: str):
        await ctx.defer()
        res = await self.generate_ai_response(f"Generate a harmonious 5-color HEX palette for a '{theme}' UI theme with color names and usage tips.")
        await ctx.reply(f"🎨 **Color Palette:**\n{res[:2000]}")

    @commands.command(name="ai_debate", description="AI Debate argument builder: &ai_debate <topic>")
    async def ai_debate(self, ctx, *, topic: str):
        await ctx.defer()
        res = await self.generate_ai_response(f"Provide 2 strong arguments FOR and 2 strong arguments AGAINST: {topic}")
        await ctx.reply(f"⚖️ **Debate Arguments:**\n{res[:2000]}")

    @commands.command(name="ai_eli5", description="Explain like I'm 5 years old: &ai_eli5 <concept>")
    async def ai_eli5(self, ctx, *, concept: str):
        await ctx.defer()
        res = await self.generate_ai_response(f"Explain this complex concept in simple terms like I'm 5 years old using relatable metaphors: {concept}")
        await ctx.reply(f"👶 **ELI5 Explanation:**\n{res[:2000]}")

    @commands.command(name="ai_recipe", description="AI Recipe ideas from ingredients: &ai_recipe <ingredients>")
    async def ai_recipe(self, ctx, *, ingredients: str):
        await ctx.defer()
        res = await self.generate_ai_response(f"Suggest 2 delicious meals you can cook using primarily these ingredients: {ingredients}")
        await ctx.reply(f"🍳 **Recipe Ideas:**\n{res[:2000]}")

    @commands.command(name="ai_workout", description="AI Workout routine generator: &ai_workout <goal>")
    async def ai_workout(self, ctx, *, goal: str):
        await ctx.defer()
        res = await self.generate_ai_response(f"Create a quick 20-minute daily home workout routine for someone aiming for: {goal}")
        await ctx.reply(f"🏋️ **Workout Routine:**\n{res[:2000]}")

    @commands.command(name="ai_travel", description="AI Travel itinerary maker: &ai_travel <city> <days>")
    async def ai_travel(self, ctx, city: str, days: int = 3):
        await ctx.defer()
        res = await self.generate_ai_response(f"Create an exciting {days}-day travel itinerary for visiting {city}, including top attractions and food spots.")
        await ctx.reply(f"✈️ **{days}-Day Itinerary ({city.title()}):**\n{res[:2000]}")

    @commands.command(name="ai_gift", description="AI Gift idea recommendations: &ai_gift <person/interests>")
    async def ai_gift(self, ctx, *, person: str):
        await ctx.defer()
        res = await self.generate_ai_response(f"Suggest 5 thoughtful gift ideas across various budgets for: {person}")
        await ctx.reply(f"🎁 **Gift Recommendations:**\n{res[:2000]}")

    @commands.command(name="ai_book", description="AI Book recommendation: &ai_book <genre/favorite_book>")
    async def ai_book(self, ctx, *, favorite: str):
        await ctx.defer()
        res = await self.generate_ai_response(f"Recommend 3 books for someone who loves '{favorite}', with brief non-spoiler summaries.")
        await ctx.reply(f"📚 **Book Suggestions:**\n{res[:2000]}")

    @commands.command(name="ai_movie", description="AI Movie recommendation: &ai_movie <genre/favorite_movie>")
    async def ai_movie(self, ctx, *, favorite: str):
        await ctx.defer()
        res = await self.generate_ai_response(f"Recommend 3 films/shows for a fan of '{favorite}', with synopsis and where the appeal lies.")
        await ctx.reply(f"🎬 **Movie Recommendations:**\n{res[:2000]}")

    @commands.command(name="ai_docker", description="AI Dockerfile generator: &ai_docker <language/stack>")
    async def ai_docker(self, ctx, *, stack: str):
        await ctx.defer()
        res = await self.generate_ai_response(f"Write a production-ready, multi-stage optimized Dockerfile for a {stack} application with comments.")
        await ctx.reply(f"🐳 **Dockerfile:**\n{res[:2000]}")

    @commands.command(name="ai_summarize_bullet", description="AI Bullet summary: &ai_summarize_bullet <long_text>")
    async def ai_summarize_bullet(self, ctx, *, text: str):
        await ctx.defer()
        res = await self.generate_ai_response(f"Summarize this text into 3-5 concise, high-impact bullet points:\n\n{text}")
        await ctx.reply(f"📋 **Bullet Summary:**\n{res[:2000]}")

    @commands.command(name="ai_pros_cons", description="AI Pros & Cons analysis: &ai_pros_cons <decision>")
    async def ai_pros_cons(self, ctx, *, decision: str):
        await ctx.defer()
        res = await self.generate_ai_response(f"Provide a balanced, objective Pros vs Cons breakdown for: {decision}")
        await ctx.reply(f"⚖️ **Pros & Cons Analysis:**\n{res[:2000]}")

    @commands.command(name="ai_slogan", description="AI Brand slogan creator: &ai_slogan <product/brand>")
    async def ai_slogan(self, ctx, *, product: str):
        await ctx.defer()
        res = await self.generate_ai_response(f"Generate 5 catchy, memorable marketing taglines/slogans for: {product}")
        await ctx.reply(f"💡 **Brand Slogans:**\n{res[:2000]}")

    @commands.command(name="ai_spanish", description="AI English to Spanish translator: &ai_spanish <text>")
    async def ai_spanish(self, ctx, *, text: str):
        await ctx.defer()
        res = await self.generate_ai_response(f"Translate the following text to natural Spanish and provide phonetic pronunciation:\n\n{text}")
        await ctx.reply(f"🇪🇸 **Spanish Translation:**\n{res[:2000]}")

    @commands.command(name="ai_japanese", description="AI English to Japanese translator: &ai_japanese <text>")
    async def ai_japanese(self, ctx, *, text: str):
        await ctx.defer()
        res = await self.generate_ai_response(f"Translate to Japanese (Kanji/Kana) with Romaji and English breakdown:\n\n{text}")
        await ctx.reply(f"🇯🇵 **Japanese Translation:**\n{res[:2000]}")

    @commands.command(name="ai_french", description="AI English to French translator: &ai_french <text>")
    async def ai_french(self, ctx, *, text: str):
        await ctx.defer()
        res = await self.generate_ai_response(f"Translate to natural French:\n\n{text}")
        await ctx.reply(f"🇫🇷 **French Translation:**\n{res[:2000]}")

    @commands.command(name="ai_german", description="AI English to German translator: &ai_german <text>")
    async def ai_german(self, ctx, *, text: str):
        await ctx.defer()
        res = await self.generate_ai_response(f"Translate to German:\n\n{text}")
        await ctx.reply(f"🇩🇪 **German Translation:**\n{res[:2000]}")

    @commands.command(name="ai_hindi", description="AI English to Hindi translator: &ai_hindi <text>")
    async def ai_hindi(self, ctx, *, text: str):
        await ctx.defer()
        res = await self.generate_ai(f"Translate to Hindi (Devanagari script + English phonetic):\n\n{text}")
        await ctx.reply(f"🇮🇳 **Hindi Translation:**\n{res[:2000]}")

    @commands.hybrid_command(name="ai_persona", aliases=["persona", "roleplay"], description="Chat with any AI character: &ai_persona <character> <message>")
    async def ai_persona(self, ctx, character: str, *, message: str):
        """Talk to any fictional character, historical figure, or anime hero."""
        await ctx.defer()
        system = f"You are roleplaying completely in-character as {character}. Stay true to their personality, speech patterns, catchphrases, and demeanor. Keep replies under 300 words."
        try:
            res = await self.generate_ai(message, system_instruction=system)
            embed = discord.Embed(
                title=f"🎭 {character.title()}",
                description=res[:2000],
                color=0x9B59B6,
                timestamp=datetime.now(timezone.utc),
            )
            embed.set_footer(text=f"Roleplay Chat with {ctx.author.display_name}")
            await ctx.reply(embed=embed)
        except Exception as e:
            await ctx.reply(f"❌ AI Persona error: {e}")

    @commands.hybrid_command(name="ai_dungeon", aliases=["dungeon_story", "rpg_story"], description="Interactive choose-your-own-adventure story: &ai_dungeon [action]")
    async def ai_dungeon(self, ctx, *, action: str = "Begin my adventure in the Enchanted Kingdom"):
        """Interactive text RPG where every choice shapes the unfolding story."""
        await ctx.defer()
        system = "You are a master tabletop Dungeon Master. Write an immersive 2-paragraph fantasy adventure segment based on the player's action, and provide 3 numbered choices (1, 2, 3) at the end for what they can do next."
        try:
            res = await self.generate_ai(f"Player Action: {action}", system_instruction=system)
            embed = discord.Embed(
                title="🏰 AI Dungeon Chronicle",
                description=res[:2000],
                color=0xE67E22,
                timestamp=datetime.now(timezone.utc),
            )
            embed.set_footer(text="Type &ai_dungeon <your choice or action> to continue the journey!")
            await ctx.reply(embed=embed)
        except Exception as e:
            await ctx.reply(f"❌ Dungeon Master error: {e}")

    @commands.hybrid_command(name="ai_debate", aliases=["debate"], description="Generate a 2-sided structured debate: &ai_debate <topic>")
    async def ai_debate(self, ctx, *, topic: str):
        """Generates opposing arguments and a neutral philosophical verdict on any topic."""
        await ctx.defer()
        system = "You are an objective Oxford debate moderator. Provide strong Argument For, strong Argument Against, and a balanced synthesis verdict on the topic."
        try:
            res = await self.generate_ai(f"Debate Topic: {topic}", system_instruction=system)
            embed = discord.Embed(
                title=f"⚖️ AI Debate: {topic[:100]}",
                description=res[:2000],
                color=0x3498DB,
                timestamp=datetime.now(timezone.utc),
            )
            await ctx.reply(embed=embed)
        except Exception as e:
            await ctx.reply(f"❌ Debate error: {e}")

    @commands.hybrid_command(name="roast_server", description="AI analyzes the server and gives a playful roast")
    async def roast_server(self, ctx):
        """Playfully roasts the Discord server based on its stats and channel names."""
        if not ctx.guild:
            return await ctx.reply("❌ This command must be used in a Discord server.")
        await ctx.defer()
        channels = [c.name for c in ctx.guild.text_channels[:15]]
        roles = [r.name for r in ctx.guild.roles[1:10]]
        prompt = f"Server Name: {ctx.guild.name}\nMember Count: {ctx.guild.member_count}\nChannels: {', '.join(channels)}\nRoles: {', '.join(roles)}"
        system = "You are a witty, hilarious stand-up comedian. Write a playful, savage 2-paragraph roast of this Discord server. Keep it PG-13 friendly and funny."
        try:
            res = await self.generate_ai(prompt, system_instruction=system)
            embed = discord.Embed(
                title=f"🔥 Server Roast: {ctx.guild.name}",
                description=res[:2000],
                color=ERROR_COLOR,
                timestamp=datetime.now(timezone.utc),
            )
            embed.set_footer(text="All in good fun! • Powered by Gemini AI")
            await ctx.reply(embed=embed)
        except Exception as e:
            await ctx.reply(f"❌ Server Roast error: {e}")

    @commands.hybrid_command(name="ai_summarize_chat", description="Summarize recent channel messages with AI: &ai_summarize_chat [limit]")
    @commands.has_permissions(manage_messages=True)
    async def ai_summarize_chat(self, ctx, limit: int = 30):
        """Summarizes recent chat activity and conversations in the current channel."""
        if not 5 <= limit <= 100:
            return await ctx.reply("❌ Limit must be between 5 and 100 messages.")
        await ctx.defer()
        messages = []
        async for m in ctx.channel.history(limit=limit):
            if not m.author.bot and m.content:
                messages.append(f"{m.author.display_name}: {m.content[:150]}")
        messages.reverse()
        if not messages:
            return await ctx.reply("❌ No chat messages found to summarize.")

        chat_log = "\n".join(messages[:50])
        system = "You are an executive summarizer. Analyze this Discord channel chat log and provide a bullet-point summary of what was discussed, key topics, and major highlights."
        try:
            res = await self.generate_ai(chat_log, system_instruction=system)
            embed = discord.Embed(
                title=f"📝 Chat Summary (#{ctx.channel.name})",
                description=res[:2000],
                color=SUCCESS_COLOR,
                timestamp=datetime.now(timezone.utc),
            )
            embed.set_footer(text=f"Analyzed {len(messages)} recent messages")
            await ctx.reply(embed=embed)
        except Exception as e:
            await ctx.reply(f"❌ Summarize Chat error: {e}")

    @commands.hybrid_command(name="models", aliases=["ai_models", "llms"], description="View all 12+ live AI models across Google, Groq, and Pollinations")
    async def list_ai_models(self, ctx):
        """Displays the multi-cloud roster of active LLMs and free inference models."""
        from utils import AVAILABLE_MODELS
        embed = discord.Embed(
            title="🧠 Vortex Multi-Cloud AI Model Ecosystem",
            description="Vortex aggregates **3 independent cloud providers** with automatic 0ms failover:",
            color=0x9B59B6,
            timestamp=datetime.now(timezone.utc),
        )

        gemini_list = [f"• `{k}` — {v}" for k, v in AVAILABLE_MODELS.items() if "Google" in v or "gemini" in k]
        groq_list = [f"• `{k}` — {v}" for k, v in AVAILABLE_MODELS.items() if "Groq" in v]
        poll_list = [f"• `{k}` — {v}" for k, v in AVAILABLE_MODELS.items() if "Pollinations" in v]

        embed.add_field(name="🌐 Google Cloud (Multimodal & Fast)", value="\n".join(gemini_list), inline=False)
        embed.add_field(name="⚡ Groq Cloud (500 tokens/sec & DeepSeek-R1)", value="\n".join(groq_list), inline=False)
        embed.add_field(name="🌸 Pollinations Public Cloud (Zero-Key Unlimited)", value="\n".join(poll_list), inline=False)
        embed.set_footer(text="Use &model_chat <model> <prompt> to query any specific model!")
        await ctx.reply(embed=embed)

    @commands.hybrid_command(name="deepseek", aliases=["reason", "ai_reason"], description="Solve complex logic, coding, or math problems with DeepSeek-R1 reasoning")
    async def deepseek_reason(self, ctx, *, problem: str):
        """Uses DeepSeek-R1 Distill 70B via Groq for deep chain-of-thought step-by-step reasoning."""
        await ctx.defer()
        system = "You are DeepSeek-R1. Solve the problem with deep analytical precision, structured reasoning, and clear step-by-step mathematical or logical deductions."
        try:
            from utils import generate_ai
            res = await generate_ai(problem, system_instruction=system, specific_model="deepseek-r1")
            embed = discord.Embed(
                title="🧠 DeepSeek-R1 Analytical Deduction",
                description=res[:3900],
                color=0x1ABC9C,
                timestamp=datetime.now(timezone.utc),
            )
            embed.set_footer(text="DeepSeek R1 Distill 70B • Powered by Groq LPU")
            await ctx.reply(embed=embed)
        except Exception as e:
            await ctx.reply(f"❌ DeepSeek Reasoning error: {e}")

    @commands.hybrid_command(name="model_chat", aliases=["ask_model"], description="Chat with a specific AI model: &model_chat <deepseek/llama3/gemma/mistral/qwen/gpt4> <prompt>")
    async def model_chat(self, ctx, model_name: str, *, prompt: str):
        """Query a specific model from the multi-cloud ecosystem."""
        await ctx.defer()
        from utils import generate_ai
        m = model_name.lower().strip()
        alias_map = {
            "deepseek": "deepseek-r1",
            "r1": "deepseek-r1",
            "llama": "llama-3.3-70b",
            "llama3": "llama-3.3-70b",
            "gemma": "gemma2-9b",
            "gemma2": "gemma2-9b",
            "mistral": "mistral-large",
            "qwen": "qwen-2.5-72b",
            "gpt4": "gpt-4o-mini",
            "gemini": "gemini-3.6-flash",
        }
        target_model = alias_map.get(m, m)
        try:
            res = await generate_ai(prompt, specific_model=target_model)
            embed = discord.Embed(
                title=f"🤖 Model Response: {target_model}",
                description=res[:3900],
                color=MAIN_COLOR,
                timestamp=datetime.now(timezone.utc),
            )
            embed.set_footer(text=f"Requested by {ctx.author.display_name}")
            await ctx.reply(embed=embed)
        except Exception as e:
            await ctx.reply(f"❌ Error with model `{target_model}`: {e}")

    @commands.hybrid_command(name="imagine", aliases=["ai_image", "generate_image", "art"], description="Generate free high-quality AI artwork: &imagine <prompt>")
    async def imagine_art(self, ctx, *, prompt: str):
        """Generates stunning Flux / SDXL images directly using Pollinations keyless cloud engine."""
        await ctx.defer()
        import urllib.parse
        encoded = urllib.parse.quote(prompt)
        seed = random.randint(1000, 999999)
        image_url = f"https://image.pollinations.ai/prompt/{encoded}?width=1024&height=1024&model=flux&seed={seed}&nologo=true"

        embed = discord.Embed(
            title="🎨 AI Generative Artwork",
            description=f"**Prompt:** *\"{prompt[:300]}\"*",
            color=0xE91E63,
            timestamp=datetime.now(timezone.utc),
        )
        embed.set_image(url=image_url)
        embed.set_footer(text=f"Generated for {ctx.author.display_name} • Flux Model • Zero API Cost")
        await ctx.reply(embed=embed)

    @commands.hybrid_command(name="ask_web", aliases=["search_ai", "smart_search"], description="Search the web and synthesize an AI summary: &ask_web <query>")
    async def ask_web(self, ctx, *, query: str):
        """Searches Wikipedia & public web data and synthesizes an intelligent summarized answer."""
        await ctx.defer()
        import urllib.parse
        search_url = f"https://api.duckduckgo.com/?q={urllib.parse.quote(query)}&format=json&no_html=1&skip_disambig=1"
        web_context = ""
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(search_url, timeout=5) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        abstract = data.get("AbstractText", "")
                        heading = data.get("Heading", "")
                        if abstract:
                            web_context = f"Web Result for '{heading}': {abstract}"
            except Exception:
                pass

        system = "You are a real-time web research assistant. Provide an accurate, comprehensive, and up-to-date answer citing key facts."
        prompt = f"Web Search Context:\n{web_context}\n\nUser Question:\n{query}"
        try:
            from utils import generate_ai
            answer = await generate_ai(prompt, system_instruction=system)
            embed = discord.Embed(
                title=f"🌐 Web Research: {query[:100]}",
                description=answer[:3900],
                color=0x2ECC71,
                timestamp=datetime.now(timezone.utc),
            )
            embed.set_footer(text="Live Web Grounding • Multi-Model Synthesis")
            await ctx.reply(embed=embed)
        except Exception as e:
            await ctx.reply(f"❌ Web Search AI error: {e}")

async def setup(bot):
    await bot.add_cog(AISuite(bot))
