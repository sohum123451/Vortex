import aiohttp
import urllib.parse
import discord
from discord.ext import commands
from utils import MAIN_COLOR, INFO_COLOR, SUCCESS_COLOR

class AnimeGaming(commands.Cog):
    """Anime, manga, Pokemon, Minecraft, and gaming lookup and utility suite."""

    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="anime", description="Search anime database on MyAnimeList/Jikan")
    async def anime_search(self, ctx, *, title: str):
        await ctx.defer()
        url = f"https://api.jikan.moe/v4/anime?q={urllib.parse.quote(title)}&limit=1"
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, timeout=6) as resp:
                    if resp.status != 200:
                        return await ctx.reply(f"❌ Anime `{title}` not found.")
                    data = await resp.json()
                    results = data.get("data", [])
                    if not results:
                        return await ctx.reply(f"❌ No anime results found for `{title}`.")
                    a = results[0]
                    embed = discord.Embed(
                        title=a.get("title"),
                        url=a.get("url"),
                        description=a.get("synopsis", "No synopsis available.")[:1000] + "...",
                        color=MAIN_COLOR,
                    )
                    if img := a.get("images", {}).get("jpg", {}).get("image_url"):
                        embed.set_thumbnail(url=img)
                    embed.add_field(name="⭐ Score", value=f"`{a.get('score', 'N/A')}`", inline=True)
                    embed.add_field(name="📺 Episodes", value=f"`{a.get('episodes', 'N/A')}`", inline=True)
                    embed.add_field(name="📅 Status", value=f"`{a.get('status', 'N/A')}`", inline=True)
                    await ctx.reply(embed=embed)
            except Exception as e:
                await ctx.reply(f"❌ Anime lookup error: {e}")

    @commands.hybrid_command(name="manga", description="Search manga database on Jikan")
    async def manga_search(self, ctx, *, title: str):
        await ctx.defer()
        url = f"https://api.jikan.moe/v4/manga?q={urllib.parse.quote(title)}&limit=1"
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, timeout=6) as resp:
                    data = await resp.json()
                    results = data.get("data", [])
                    if not results:
                        return await ctx.reply(f"❌ No manga found for `{title}`.")
                    m = results[0]
                    embed = discord.Embed(
                        title=m.get("title"),
                        url=m.get("url"),
                        description=m.get("synopsis", "")[:1000] + "...",
                        color=INFO_COLOR,
                    )
                    if img := m.get("images", {}).get("jpg", {}).get("image_url"):
                        embed.set_thumbnail(url=img)
                    embed.add_field(name="⭐ Score", value=f"`{m.get('score', 'N/A')}`", inline=True)
                    embed.add_field(name="📖 Chapters", value=f"`{m.get('chapters', 'N/A')}`", inline=True)
                    await ctx.reply(embed=embed)
            except Exception as e:
                await ctx.reply(f"❌ Manga lookup error: {e}")

    @commands.hybrid_command(name="pokemon", description="Look up Pokemon stats and types")
    async def pokemon(self, ctx, name: str):
        await ctx.defer()
        url = f"https://pokeapi.co/api/v2/pokemon/{name.lower().strip()}"
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, timeout=5) as resp:
                    if resp.status != 200:
                        return await ctx.reply(f"❌ Pokemon `{name}` not found.")
                    data = await resp.json()
                    types = ", ".join([t["type"]["name"].title() for t in data["types"]])
                    height = data["height"] / 10
                    weight = data["weight"] / 10
                    sprite = data["sprites"]["other"]["official-artwork"]["front_default"] or data["sprites"]["front_default"]

                    embed = discord.Embed(title=f"🐾 #{data['id']} {data['name'].title()}", color=SUCCESS_COLOR)
                    if sprite:
                        embed.set_thumbnail(url=sprite)
                    embed.add_field(name="Types", value=f"`{types}`", inline=True)
                    embed.add_field(name="Height / Weight", value=f"`{height}m` / `{weight}kg`", inline=True)
                    embed.add_field(name="Base Experience", value=f"`{data.get('base_experience', 'N/A')}`", inline=True)
                    await ctx.reply(embed=embed)
            except Exception as e:
                await ctx.reply(f"❌ PokeAPI error: {e}")

    @commands.hybrid_command(name="mc_skin", description="Get Minecraft player skin by username")
    async def mc_skin(self, ctx, username: str):
        embed = discord.Embed(title=f"⛏️ Minecraft Skin: {username}", color=MAIN_COLOR)
        embed.set_image(url=f"https://minotar.net/armor/body/{username}/200.png")
        await ctx.reply(embed=embed)

    @commands.command(name="genshin_character", description="Look up a Genshin Impact character")
    async def genshin_character(self, ctx, *, character: str):
        c = character.lower().strip().replace(" ", "-")
        url = f"https://genshin.jmp.blue/characters/{c}"
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, timeout=5) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        embed = discord.Embed(title=f"✨ Genshin Impact: {data.get('name')}", description=data.get("description", ""), color=MAIN_COLOR)
                        embed.add_field(name="Vision", value=data.get("vision", "N/A"), inline=True)
                        embed.add_field(name="Weapon", value=data.get("weapon", "N/A"), inline=True)
                        embed.add_field(name="Nation", value=data.get("nation", "N/A"), inline=True)
                        embed.add_field(name="Rarity", value=f"⭐ {data.get('rarity', 'N/A')}", inline=True)
                        return await ctx.reply(embed=embed)
            except Exception:
                pass
        await ctx.reply(f"❌ Character `{character}` not found.")

    @commands.command(name="anime_quote", description="Get a random inspirational or dramatic anime quote")
    async def anime_quote(self, ctx):
        url = "https://animechan.xyz/api/random"
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, timeout=5) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        embed = discord.Embed(title=f"🌸 {data.get('anime')}", description=f"\"{data.get('quote')}\"\n\n— **{data.get('character')}**", color=0xFF69B4)
                        return await ctx.reply(embed=embed)
            except Exception:
                pass
        await ctx.reply("🌸 *\"Whatever you do, enjoy it to the fullest! That is the secret of life.\"* — **Rider (Fate/Zero)**")

    @commands.command(name="waifu", description="Get a random waifu picture")
    async def waifu(self, ctx):
        url = "https://api.waifu.pics/sfw/waifu"
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, timeout=5) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        embed = discord.Embed(title="💖 Random Waifu", color=0xFF69B4)
                        embed.set_image(url=data.get("url"))
                        return await ctx.reply(embed=embed)
            except Exception:
                pass
        await ctx.reply("❌ Unable to fetch waifu image.")

    @commands.command(name="neko", description="Get a cute neko picture")
    async def neko(self, ctx):
        url = "https://api.waifu.pics/sfw/neko"
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, timeout=5) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        embed = discord.Embed(title="🐾 Neko!", color=0xFF69B4)
                        embed.set_image(url=data.get("url"))
                        return await ctx.reply(embed=embed)
            except Exception:
                pass
        await ctx.reply("❌ Unable to fetch neko.")

    @commands.command(name="hug", description="Hug a member")
    async def hug(self, ctx, member: discord.Member):
        embed = discord.Embed(title="🫂 Warm Hug", description=f"{ctx.author.mention} warmly hugged {member.mention}!", color=0xFF69B4)
        await ctx.reply(embed=embed)

    @commands.command(name="pat", description="Pat a member on the head")
    async def pat(self, ctx, member: discord.Member):
        embed = discord.Embed(title="🐾 Headpat", description=f"{ctx.author.mention} patted {member.mention} on the head!", color=0xFF69B4)
        await ctx.reply(embed=embed)

    @commands.command(name="slap", description="Slap a member")
    async def slap(self, ctx, member: discord.Member):
        embed = discord.Embed(title="💥 SLAP!", description=f"{ctx.author.mention} slapped {member.mention} across the face!", color=0xED4245)
        await ctx.reply(embed=embed)

    @commands.command(name="kiss", description="Kiss a member")
    async def kiss(self, ctx, member: discord.Member):
        embed = discord.Embed(title="💋 Kiss", description=f"{ctx.author.mention} gave {member.mention} a sweet kiss!", color=0xFF69B4)
        await ctx.reply(embed=embed)

    @commands.command(name="cuddle", description="Cuddle with a member")
    async def cuddle(self, ctx, member: discord.Member):
        embed = discord.Embed(title="🧸 Cuddle", description=f"{ctx.author.mention} cuddled closely with {member.mention}!", color=0xFF69B4)
        await ctx.reply(embed=embed)

    @commands.command(name="punch", description="Punch a member")
    async def punch(self, ctx, member: discord.Member):
        embed = discord.Embed(title="🥊 Punch!", description=f"{ctx.author.mention} punched {member.mention}!", color=0xED4245)
        await ctx.reply(embed=embed)

    @commands.command(name="poke", description="Poke a member")
    async def poke(self, ctx, member: discord.Member):
        embed = discord.Embed(title="👉 Poke", description=f"{ctx.author.mention} poked {member.mention}!", color=INFO_COLOR)
        await ctx.reply(embed=embed)

    @commands.command(name="bite", description="Bite a member playfully")
    async def bite(self, ctx, member: discord.Member):
        embed = discord.Embed(title="🦷 Chomp!", description=f"{ctx.author.mention} bit {member.mention}!", color=0xE67E22)
        await ctx.reply(embed=embed)

    @commands.command(name="wink", description="Wink at someone")
    async def wink(self, ctx, member: discord.Member = None):
        tgt = f"at {member.mention}" if member else "smoothly"
        embed = discord.Embed(title="😉 Wink", description=f"{ctx.author.mention} winked {tgt}!", color=INFO_COLOR)
        await ctx.reply(embed=embed)

    @commands.command(name="blush", description="Blush shyly")
    async def blush(self, ctx):
        embed = discord.Embed(title="😳 Blush", description=f"{ctx.author.mention} is blushing furiously!", color=0xFF69B4)
        await ctx.reply(embed=embed)

    @commands.command(name="cry", description="Cry tears")
    async def cry(self, ctx):
        embed = discord.Embed(title="😭 Tears", description=f"{ctx.author.mention} is crying...", color=0x3498DB)
        await ctx.reply(embed=embed)

    @commands.command(name="dance", description="Dance happily")
    async def dance(self, ctx):
        embed = discord.Embed(title="💃 Dance", description=f"{ctx.author.mention} is grooving on the dance floor!", color=SUCCESS_COLOR)
        await ctx.reply(embed=embed)

    @commands.command(name="smile", description="Smile brightly")
    async def smile(self, ctx):
        embed = discord.Embed(title="😊 Smile", description=f"{ctx.author.mention} smiled warmly!", color=SUCCESS_COLOR)
        await ctx.reply(embed=embed)

    @commands.command(name="highfive", description="High-five a member")
    async def highfive(self, ctx, member: discord.Member):
        embed = discord.Embed(title="✋ High Five!", description=f"{ctx.author.mention} high-fived {member.mention}!", color=SUCCESS_COLOR)
        await ctx.reply(embed=embed)

    @commands.command(name="tickle", description="Tickle a member")
    async def tickle(self, ctx, member: discord.Member):
        embed = discord.Embed(title="🤣 Tickle!", description=f"{ctx.author.mention} tickled {member.mention}!", color=MAIN_COLOR)
        await ctx.reply(embed=embed)

    @commands.command(name="feed", description="Feed a member food")
    async def feed(self, ctx, member: discord.Member):
        embed = discord.Embed(title="🍰 Nom Nom!", description=f"{ctx.author.mention} fed {member.mention} a delicious treat!", color=0xE67E22)
        await ctx.reply(embed=embed)

    @commands.command(name="smug", description="Give a smug look")
    async def smug(self, ctx):
        await ctx.reply(f"😏 {ctx.author.mention} gives a supremely smug look.")

    @commands.command(name="stare", description="Stare intensely at someone")
    async def stare(self, ctx, member: discord.Member = None):
        tgt = f"at {member.mention}" if member else "into the abyss"
        await ctx.reply(f"👀 {ctx.author.mention} is staring intensely {tgt}...")

    @commands.command(name="pout", description="Pout cutely")
    async def pout(self, ctx):
        await ctx.reply(f"😤 {ctx.author.mention} is pouting cutely!")

    @commands.command(name="shrug", description="Shrug shoulders")
    async def shrug(self, ctx):
        await ctx.reply(f"🤷 ¯\\_(ツ)_/¯")

    @commands.command(name="sleepy", description="Act sleepy")
    async def sleepy(self, ctx):
        await ctx.reply(f"🥱 {ctx.author.mention} is getting super sleepy... *yawn*")

    @commands.command(name="nom", description="Nom on some food")
    async def nom(self, ctx):
        await ctx.reply(f"🍙 {ctx.author.mention} is munching happily! *nom nom nom*")

    @commands.command(name="glare", description="Glare angrily at someone")
    async def glare(self, ctx, member: discord.Member = None):
        tgt = f"at {member.mention}" if member else "menacingly"
        await ctx.reply(f"😠 {ctx.author.mention} is glaring {tgt}!")

    @commands.command(name="handhold", description="Hold hands with someone")
    async def handhold(self, ctx, member: discord.Member):
        await ctx.reply(f"🤝 {ctx.author.mention} is holding hands with {member.mention}! *lewd!*")

    @commands.command(name="wave_hi", description="Wave hello to someone")
    async def wave_hi(self, ctx, member: discord.Member = None):
        tgt = f"at {member.mention}" if member else "to everyone"
        await ctx.reply(f"👋 {ctx.author.mention} waved {tgt}!")

    @commands.command(name="thumbs_up", description="Give a thumbs up")
    async def thumbs_up(self, ctx):
        await ctx.reply(f"👍 {ctx.author.mention} gives a big thumbs up!")

    @commands.command(name="celebrate", description="Celebrate victory")
    async def celebrate(self, ctx):
        await ctx.reply(f"🥳 {ctx.author.mention} is throwing confetti and celebrating!")

    @commands.command(name="cheer", description="Cheer someone on")
    async def cheer(self, ctx, member: discord.Member = None):
        tgt = member.mention if member else "the team"
        await ctx.reply(f"📣 {ctx.author.mention} is cheering loudly for {tgt}!")

    @commands.command(name="sip_tea", description="Sip tea calmly")
    async def sip_tea(self, ctx):
        await ctx.reply(f"☕ {ctx.author.mention} sips tea calmly while watching the chaos unfold.")

    @commands.command(name="popcorn", description="Eat popcorn while spectating")
    async def popcorn(self, ctx):
        await ctx.reply(f"🍿 {ctx.author.mention} grabs popcorn and enjoys the show.")

    @commands.command(name="facepalm_rp", description="Facepalm in disbelief")
    async def facepalm_rp(self, ctx):
        await ctx.reply(f"🤦 {ctx.author.mention} facepalms in utter disbelief.")

    @commands.command(name="salute_rp", description="Salute with respect")
    async def salute_rp(self, ctx, member: discord.Member = None):
        tgt = f"to {member.mention}" if member else "with deep respect"
        await ctx.reply(f"🫡 {ctx.author.mention} salutes {tgt}!")

    @commands.command(name="laugh_rp", description="Laugh out loud")
    async def laugh_rp(self, ctx):
        await ctx.reply(f"🤣 {ctx.author.mention} bursts into laughter! Hahaha!")

    @commands.command(name="gasp", description="Gasp in shock")
    async def gasp(self, ctx):
        await ctx.reply(f"😱 {ctx.author.mention} gasps in shock!")

async def setup(bot):
    await bot.add_cog(AnimeGaming(bot))
