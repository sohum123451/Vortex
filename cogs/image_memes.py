import io
import urllib.parse
import aiohttp
import discord
from discord.ext import commands
from utils import MAIN_COLOR, ERROR_COLOR

class ImageMemes(commands.Cog):
    """Dynamic meme generator, image filters, avatar overlays, and visual effects."""

    def __init__(self, bot):
        self.bot = bot

    def get_target_avatar(self, ctx, member: discord.Member = None) -> str:
        target = member or ctx.author
        return target.display_avatar.url

    async def fetch_image(self, ctx, url: str) -> discord.File:
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, timeout=10) as resp:
                    if resp.status == 200:
                        data = await resp.read()
                        return discord.File(fp=io.BytesIO(data), filename="image.png")
            except Exception:
                pass
        return None

    @commands.hybrid_command(name="wasted", description="GTA Wasted avatar overlay effect")
    async def wasted(self, ctx, member: discord.Member = None):
        await ctx.defer()
        avatar = self.get_target_avatar(ctx, member)
        url = f"https://some-random-api.com/canvas/overlay/wasted?avatar={urllib.parse.quote(avatar)}"
        file = await self.fetch_image(ctx, url)
        if file:
            await ctx.reply(file=file)
        else:
            await ctx.reply("❌ Failed to generate Wasted image.")

    @commands.hybrid_command(name="triggered", description="Triggered animated avatar overlay")
    async def triggered(self, ctx, member: discord.Member = None):
        await ctx.defer()
        avatar = self.get_target_avatar(ctx, member)
        url = f"https://some-random-api.com/canvas/overlay/triggered?avatar={urllib.parse.quote(avatar)}"
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, timeout=10) as resp:
                    if resp.status == 200:
                        data = await resp.read()
                        file = discord.File(fp=io.BytesIO(data), filename="triggered.gif")
                        return await ctx.reply(file=file)
            except Exception:
                pass
        await ctx.reply("❌ Failed to generate Triggered gif.")

    @commands.hybrid_command(name="jail", description="Put an avatar behind jail bars")
    async def jail(self, ctx, member: discord.Member = None):
        await ctx.defer()
        avatar = self.get_target_avatar(ctx, member)
        url = f"https://some-random-api.com/canvas/overlay/jail?avatar={urllib.parse.quote(avatar)}"
        file = await self.fetch_image(ctx, url)
        if file:
            await ctx.reply(file=file)
        else:
            await ctx.reply("❌ Failed to generate Jail image.")

    @commands.hybrid_command(name="wanted", description="Generate a Western Wanted Poster for an avatar")
    async def wanted(self, ctx, member: discord.Member = None):
        await ctx.defer()
        avatar = self.get_target_avatar(ctx, member)
        url = f"https://some-random-api.com/canvas/misc/wanted?avatar={urllib.parse.quote(avatar)}"
        file = await self.fetch_image(ctx, url)
        if file:
            await ctx.reply(file=file)
        else:
            await ctx.reply("❌ Failed to generate Wanted poster.")

    @commands.command(name="pixelate", description="Pixelate a user avatar")
    async def pixelate(self, ctx, member: discord.Member = None):
        await ctx.defer()
        avatar = self.get_target_avatar(ctx, member)
        url = f"https://some-random-api.com/canvas/filter/pixelate?avatar={urllib.parse.quote(avatar)}"
        file = await self.fetch_image(ctx, url)
        if file:
            await ctx.reply(file=file)
        else:
            await ctx.reply("❌ Failed to pixelate avatar.")

    @commands.command(name="invert", description="Invert avatar colors")
    async def invert(self, ctx, member: discord.Member = None):
        await ctx.defer()
        avatar = self.get_target_avatar(ctx, member)
        url = f"https://some-random-api.com/canvas/filter/invert?avatar={urllib.parse.quote(avatar)}"
        file = await self.fetch_image(ctx, url)
        if file:
            await ctx.reply(file=file)
        else:
            await ctx.reply("❌ Failed to invert avatar.")

    @commands.command(name="grayscale", description="Convert avatar to black & white grayscale")
    async def grayscale(self, ctx, member: discord.Member = None):
        await ctx.defer()
        avatar = self.get_target_avatar(ctx, member)
        url = f"https://some-random-api.com/canvas/filter/greyscale?avatar={urllib.parse.quote(avatar)}"
        file = await self.fetch_image(ctx, url)
        if file:
            await ctx.reply(file=file)
        else:
            await ctx.reply("❌ Failed to convert avatar to grayscale.")

    @commands.command(name="blur", description="Apply blur filter to user avatar")
    async def blur(self, ctx, member: discord.Member = None):
        await ctx.defer()
        avatar = self.get_target_avatar(ctx, member)
        url = f"https://some-random-api.com/canvas/filter/blur?avatar={urllib.parse.quote(avatar)}"
        file = await self.fetch_image(ctx, url)
        if file:
            await ctx.reply(file=file)
        else:
            await ctx.reply("❌ Failed to blur avatar.")

    @commands.command(name="sepia", description="Apply vintage sepia tone to avatar")
    async def sepia(self, ctx, member: discord.Member = None):
        await ctx.defer()
        avatar = self.get_target_avatar(ctx, member)
        url = f"https://some-random-api.com/canvas/filter/sepia?avatar={urllib.parse.quote(avatar)}"
        file = await self.fetch_image(ctx, url)
        if file:
            await ctx.reply(file=file)
        else:
            await ctx.reply("❌ Failed to apply sepia tone.")

    @commands.command(name="drake", description="Generate a Drake Hotline Bling meme: &drake <top_text> | <bottom_text>")
    async def drake(self, ctx, *, text: str):
        parts = [p.strip() for p in text.split("|")]
        if len(parts) < 2:
            return await ctx.reply("❌ Usage: `&drake <Disliked Thing> | <Liked Thing>`")
        top, bottom = urllib.parse.quote(parts[0]), urllib.parse.quote(parts[1])
        url = f"https://api.memegen.link/images/drake/{top}/{bottom}.png"
        file = await self.fetch_image(ctx, url)
        if file:
            await ctx.reply(file=file)
        else:
            await ctx.reply("❌ Failed to generate Drake meme.")

    @commands.command(name="pooh", description="Tuxedo Winnie the Pooh meme: &pooh <normal_text> | <fancy_text>")
    async def pooh(self, ctx, *, text: str):
        parts = [p.strip() for p in text.split("|")]
        if len(parts) < 2:
            return await ctx.reply("❌ Usage: `&pooh <Normal Thing> | <Fancy Thing>`")
        top, bottom = urllib.parse.quote(parts[0]), urllib.parse.quote(parts[1])
        url = f"https://api.memegen.link/images/pooh/{top}/{bottom}.png"
        file = await self.fetch_image(ctx, url)
        if file:
            await ctx.reply(file=file)
        else:
            await ctx.reply("❌ Failed to generate Pooh meme.")

    @commands.command(name="custom_meme", description="Generate a meme template: &custom_meme <template> <top_text> | <bottom_text>")
    async def custom_meme(self, ctx, template: str, *, text: str):
        parts = [p.strip() for p in text.split("|")]
        top = urllib.parse.quote(parts[0])
        bottom = urllib.parse.quote(parts[1]) if len(parts) > 1 else "_"
        url = f"https://api.memegen.link/images/{template}/{top}/{bottom}.png"
        file = await self.fetch_image(ctx, url)
        if file:
            await ctx.reply(file=file)
        else:
            await ctx.reply(f"❌ Failed to generate meme template `{template}`. Popular templates: `drake`, `doge`, `fine`, `buzz`, `fry`, `sponge`.")

    @commands.command(name="avatar_art", description="Generate a unique geometric pixel avatar from text")
    async def avatar_art(self, ctx, *, seed: str):
        url = f"https://api.dicebear.com/7.x/identicon/png?seed={urllib.parse.quote(seed)}"
        file = await self.fetch_image(ctx, url)
    @commands.command(name="meme_doge", description="Doge meme: &meme_doge <top> | <bottom>")
    async def meme_doge(self, ctx, *, text: str):
        parts = [p.strip() for p in text.split("|")]
        top = urllib.parse.quote(parts[0])
        bot = urllib.parse.quote(parts[1]) if len(parts) > 1 else "_"
        file = await self.fetch_image(ctx, f"https://api.memegen.link/images/doge/{top}/{bot}.png")
        if file: await ctx.reply(file=file)
        else: await ctx.reply("❌ Error generating meme.")

    @commands.command(name="meme_stonks", description="Stonks meme: &meme_stonks <text>")
    async def meme_stonks(self, ctx, *, text: str):
        t = urllib.parse.quote(text)
        file = await self.fetch_image(ctx, f"https://api.memegen.link/images/stonks/{t}/_.png")
        if file: await ctx.reply(file=file)
        else: await ctx.reply("❌ Error generating meme.")

    @commands.command(name="meme_not_stonks", description="Not Stonks meme: &meme_not_stonks <text>")
    async def meme_not_stonks(self, ctx, *, text: str):
        t = urllib.parse.quote(text)
        file = await self.fetch_image(ctx, f"https://api.memegen.link/images/not-stonks/{t}/_.png")
        if file: await ctx.reply(file=file)
        else: await ctx.reply("❌ Error generating meme.")

    @commands.command(name="meme_change_mind", description="Change My Mind meme: &meme_change_mind <text>")
    async def meme_change_mind(self, ctx, *, text: str):
        t = urllib.parse.quote(text)
        file = await self.fetch_image(ctx, f"https://api.memegen.link/images/cmm/{t}/_.png")
        if file: await ctx.reply(file=file)
        else: await ctx.reply("❌ Error generating meme.")

    @commands.command(name="meme_clown", description="Clown putting on makeup: &meme_clown <t1> | <t2>")
    async def meme_clown(self, ctx, *, text: str):
        parts = [p.strip() for p in text.split("|")]
        t1 = urllib.parse.quote(parts[0])
        t2 = urllib.parse.quote(parts[1]) if len(parts) > 1 else "_"
        file = await self.fetch_image(ctx, f"https://api.memegen.link/images/clown/{t1}/{t2}.png")
        if file: await ctx.reply(file=file)
        else: await ctx.reply("❌ Error generating meme.")

    @commands.command(name="meme_gru", description="Gru's Plan meme: &meme_gru <step1> | <step2> | <step3>")
    async def meme_gru(self, ctx, *, text: str):
        parts = [p.strip() for p in text.split("|")]
        t1 = urllib.parse.quote(parts[0])
        t2 = urllib.parse.quote(parts[1]) if len(parts) > 1 else "_"
        file = await self.fetch_image(ctx, f"https://api.memegen.link/images/gru/{t1}/{t2}.png")
        if file: await ctx.reply(file=file)
        else: await ctx.reply("❌ Error generating meme.")

    @commands.command(name="meme_fine", description="This is Fine dog in fire: &meme_fine <text>")
    async def meme_fine(self, ctx, *, text: str):
        t = urllib.parse.quote(text)
        file = await self.fetch_image(ctx, f"https://api.memegen.link/images/fine/{t}/_.png")
        if file: await ctx.reply(file=file)
        else: await ctx.reply("❌ Error generating meme.")

    @commands.command(name="meme_sponge", description="Mocking Spongebob: &meme_sponge <text>")
    async def meme_sponge(self, ctx, *, text: str):
        t = urllib.parse.quote(text)
        file = await self.fetch_image(ctx, f"https://api.memegen.link/images/mocking/{t}/_.png")
        if file: await ctx.reply(file=file)
        else: await ctx.reply("❌ Error generating meme.")

    @commands.command(name="meme_buzz", description="Buzz Lightyear Everywhere: &meme_buzz <subject>")
    async def meme_buzz(self, ctx, *, text: str):
        t = urllib.parse.quote(text)
        file = await self.fetch_image(ctx, f"https://api.memegen.link/images/buzz/{t}/{t}_everywhere.png")
        if file: await ctx.reply(file=file)
        else: await ctx.reply("❌ Error generating meme.")

async def setup(bot):
    await bot.add_cog(ImageMemes(bot))
