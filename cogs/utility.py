import asyncio
import math
import random
import sqlite3
import string
import urllib.parse
from datetime import datetime, timezone
import aiohttp
import discord
from discord.ext import commands, tasks
from utils import DB_FILE, MAIN_COLOR, INFO_COLOR, SUCCESS_COLOR, ERROR_COLOR, parse_time, dm_user

class Utility(commands.Cog):
    """Essential utility, lookup, calculation, weather, crypto, reminders, and server inspection suite."""

    def __init__(self, bot):
        self.bot = bot
        self.check_reminders.start()
        self.snipes = {}
        self.edit_snipes = {}

    def cog_unload(self):
        self.check_reminders.cancel()

    @commands.hybrid_command(name="ping", description="Check bot latency and gateway roundtrip")
    async def ping(self, ctx):
        await ctx.reply(f"🏓 Pong! Latency: `{round(self.bot.latency * 1000)}ms`")

    @commands.hybrid_command(name="uptime", description="Check system uptime")
    async def uptime(self, ctx):
        delta = datetime.now(timezone.utc) - self.bot.start_time
        await ctx.reply(f"⏱️ **Uptime:** `{str(delta).split('.')[0]}`")

    @commands.hybrid_command(name="serverinfo", description="View server details and stats")
    async def serverinfo(self, ctx):
        guild = ctx.guild
        embed = discord.Embed(title=guild.name, color=MAIN_COLOR, timestamp=datetime.now(timezone.utc))
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        embed.add_field(name="Owner", value=f"{guild.owner.mention}", inline=True)
        embed.add_field(name="Members", value=f"`{guild.member_count:,}`", inline=True)
        embed.add_field(name="Roles", value=f"`{len(guild.roles)}`", inline=True)
        embed.add_field(name="Text Channels", value=f"`{len(guild.text_channels)}`", inline=True)
        embed.add_field(name="Voice Channels", value=f"`{len(guild.voice_channels)}`", inline=True)
        embed.add_field(name="Created On", value=f"<t:{int(guild.created_at.timestamp())}:D>", inline=True)
        await ctx.reply(embed=embed)

    @commands.hybrid_command(name="userinfo", description="Inspect member profile, joined dates, and roles")
    async def userinfo(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        embed = discord.Embed(
            title=f"👤 User Profile: {member}",
            color=member.color if member.color.value != 0 else MAIN_COLOR,
            timestamp=datetime.now(timezone.utc),
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="User ID", value=f"`{member.id}`", inline=True)
        embed.add_field(name="Top Role", value=member.top_role.mention, inline=True)
        embed.add_field(name="Joined Server", value=f"<t:{int(member.joined_at.timestamp())}:R>", inline=True)
        embed.add_field(name="Account Created", value=f"<t:{int(member.created_at.timestamp())}:R>", inline=True)
        embed.add_field(name="Role Count", value=f"`{len(member.roles) - 1}`", inline=True)
        await ctx.reply(embed=embed)

    @commands.hybrid_command(name="avatar", description="Get full high-resolution user avatar")
    async def avatar(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        embed = discord.Embed(title=f"🖼️ {member.display_name}'s Avatar", color=MAIN_COLOR)
        embed.set_image(url=member.display_avatar.url)
        await ctx.reply(embed=embed)

    @commands.command(name="banner", description="Get user banner image")
    async def banner(self, ctx, member: discord.Member = None):
        target = member or ctx.author
        user = await self.bot.fetch_user(target.id)
        if not user.banner:
            return await ctx.reply(f"❌ {target.display_name} does not have a banner.")
        embed = discord.Embed(title=f"🖼️ {target.display_name}'s Banner", color=MAIN_COLOR)
        embed.set_image(url=user.banner.url)
        await ctx.reply(embed=embed)

    @commands.hybrid_command(name="calc", description="Safe math calculator: &calc 5 * (10 + 2)")
    async def calc(self, ctx, *, expression: str):
        allowed = set("0123456789+-*/().^% ")
        if not set(expression).issubset(allowed):
            return await ctx.reply("❌ Invalid characters in expression.")
        expr = expression.replace("^", "**")
        try:
            result = eval(expr, {"__builtins__": None}, {"sqrt": math.sqrt, "pi": math.pi, "sin": math.sin, "cos": math.cos})
            await ctx.reply(f"🧮 `{expression}` = **`{result}`**")
        except Exception as e:
            await ctx.reply(f"❌ Calculation error: {e}")

    @commands.hybrid_command(name="weather", description="Check global weather forecast: &weather Tokyo")
    async def weather(self, ctx, *, city: str):
        await ctx.defer()
        url = f"https://wttr.in/{urllib.parse.quote(city)}?format=j1"
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, timeout=5) as resp:
                    if resp.status != 200:
                        return await ctx.reply("❌ Could not fetch weather for that location.")
                    data = await resp.json()
                    current = data["current_condition"][0]
                    embed = discord.Embed(
                        title=f"🌤️ Weather for {city.title()}",
                        description=(
                            f"**{current['weatherDesc'][0]['value']}**\n"
                            f"🌡️ **Temperature:** {current['temp_C']}°C ({current['temp_F']}°F)\n"
                            f"💧 **Humidity:** {current['humidity']}%\n"
                            f"💨 **Wind:** {current['windspeedKmph']} km/h"
                        ),
                        color=INFO_COLOR,
                    )
                    await ctx.reply(embed=embed)
            except Exception as e:
                await ctx.reply(f"❌ Weather error: {e}")

    @commands.hybrid_command(name="crypto", description="Get live crypto price: &crypto btc")
    async def crypto(self, ctx, coin: str = "btc"):
        await ctx.defer()
        mapping = {"btc": "bitcoin", "eth": "ethereum", "sol": "solana", "doge": "dogecoin", "xrp": "ripple"}
        coin_id = mapping.get(coin.lower(), coin.lower())
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd&include_24hr_change=true"
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, timeout=5) as resp:
                    data = await resp.json()
                    if coin_id not in data:
                        return await ctx.reply(f"❌ Coin `{coin}` not found.")
                    price = data[coin_id]["usd"]
                    change = data[coin_id].get("usd_24h_change", 0)
                    trend = "📈" if change >= 0 else "📉"
                    embed = discord.Embed(
                        title=f"🪙 {coin_id.title()} Price",
                        description=f"💵 **Price:** `${price:,.2f} USD`\n{trend} **24h Change:** `{change:+.2f}%`",
                        color=SUCCESS_COLOR if change >= 0 else ERROR_COLOR,
                    )
                    await ctx.reply(embed=embed)
            except Exception as e:
                await ctx.reply(f"❌ Crypto error: {e}")

    @commands.hybrid_command(name="qr", description="Generate a QR code: &qr https://discord.com")
    async def qr(self, ctx, *, text: str):
        url = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={urllib.parse.quote(text)}"
        embed = discord.Embed(title="📱 Generated QR Code", color=MAIN_COLOR)
        embed.set_image(url=url)
        await ctx.reply(embed=embed)

    @commands.hybrid_command(name="wiki", description="Search Wikipedia: &wiki Python")
    async def wiki(self, ctx, *, query: str):
        await ctx.defer()
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(query)}"
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, timeout=5) as resp:
                    if resp.status != 200:
                        return await ctx.reply(f"❌ No article found for `{query}`.")
                    data = await resp.json()
                    embed = discord.Embed(
                        title=f"📚 {data.get('title')}",
                        description=data.get("extract", "")[:2000],
                        color=INFO_COLOR,
                        url=data.get("content_urls", {}).get("desktop", {}).get("page", ""),
                    )
                    if thumb := data.get("thumbnail", {}).get("source"):
                        embed.set_thumbnail(url=thumb)
                    await ctx.reply(embed=embed)
            except Exception as e:
                await ctx.reply(f"❌ Wiki error: {e}")

    @commands.command(name="define", description="Look up English dictionary word definition")
    async def define(self, ctx, word: str):
        await ctx.defer()
        url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{urllib.parse.quote(word)}"
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, timeout=5) as resp:
                    if resp.status != 200:
                        return await ctx.reply(f"❌ Definition not found for `{word}`.")
                    data = await resp.json()
                    meanings = data[0].get("meanings", [])
                    embed = discord.Embed(title=f"📖 Definition: {word.title()}", color=MAIN_COLOR)
                    for m in meanings[:3]:
                        part = m.get("partOfSpeech", "General")
                        defn = m["definitions"][0]["definition"]
                        embed.add_field(name=part.capitalize(), value=f"• {defn}", inline=False)
                    await ctx.reply(embed=embed)
            except Exception as e:
                await ctx.reply(f"❌ Dictionary error: {e}")

    @commands.command(name="color", description="Preview a hex color swatch: &color #5865F2")
    async def color(self, ctx, hex_code: str):
        code = hex_code.strip("#").upper()
        if len(code) != 6 or not all(c in string.hexdigits for c in code):
            return await ctx.reply("❌ Invalid 6-digit hex color format (e.g. `#5865F2`).")
        r, g, b = int(code[0:2], 16), int(code[2:4], 16), int(code[4:6], 16)
        url = f"https://singlecolorimage.com/get/{code}/400x150"
        embed = discord.Embed(
            title=f"🎨 Color: #{code}",
            description=f"**RGB:** `rgb({r}, {g}, {b})`\n**HEX:** `#{code}`",
            color=discord.Color(int(code, 16)),
        )
        embed.set_image(url=url)
        await ctx.reply(embed=embed)

    @commands.hybrid_command(name="remind", description="Set a reminder: &remind 10m Take dinner out")
    async def remind(self, ctx, time: str, *, reminder: str):
        delta = parse_time(time)
        if not delta:
            return await ctx.reply("❌ Invalid time format! Use `10m`, `1h`, `1d`.")
        remind_ts = (datetime.now(timezone.utc) + delta).timestamp()

        with sqlite3.connect(DB_FILE) as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO reminders (user_id, channel_id, reminder_text, remind_time) VALUES (?, ?, ?, ?)",
                (str(ctx.author.id), str(ctx.channel.id), reminder, remind_ts),
            )
            conn.commit()
        await ctx.reply(f"⏰ **Reminder set for <t:{int(remind_ts)}:R>:** `{reminder}`")

    @tasks.loop(seconds=10)
    async def check_reminders(self):
        now = datetime.now(timezone.utc).timestamp()
        with sqlite3.connect(DB_FILE) as conn:
            cur = conn.cursor()
            cur.execute("SELECT id, user_id, channel_id, reminder_text FROM reminders WHERE remind_time <= ?", (now,))
            due = cur.fetchall()
            for rid, uid, cid, text in due:
                user = self.bot.get_user(int(uid))
                channel = self.bot.get_channel(int(cid))
                msg = f"⏰ **Reminder for {user.mention if user else 'you'}!**\n> {text}"
                if channel:
                    try:
                        await channel.send(msg)
                    except Exception:
                        if user:
                            await dm_user(user, msg)
                elif user:
                    await dm_user(user, msg)
                cur.execute("DELETE FROM reminders WHERE id = ?", (rid,))
            conn.commit()

    @commands.hybrid_command(name="afk", description="Set AFK status: &afk Working on project")
    async def afk(self, ctx, *, reason="AFK"):
        with sqlite3.connect(DB_FILE) as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT OR REPLACE INTO afk (user_id, reason, timestamp) VALUES (?, ?, ?)",
                (str(ctx.author.id), reason, datetime.now(timezone.utc).isoformat()),
            )
            conn.commit()
        await ctx.reply(f"💤 {ctx.author.mention} is now AFK: **{reason}**")

    # Snipe & EditSnipe listeners
    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if not message.guild or message.author.bot:
            return
        self.snipes[message.channel.id] = (message.author, message.content, datetime.now(timezone.utc))

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if not before.guild or before.author.bot or before.content == after.content:
            return
        self.edit_snipes[before.channel.id] = (before.author, before.content, after.content, datetime.now(timezone.utc))

    @commands.hybrid_command(name="snipe", description="View recently deleted message in channel")
    async def snipe(self, ctx):
        data = self.snipes.get(ctx.channel.id)
        if not data:
            return await ctx.reply("❌ Nothing to snipe in this channel.")
        a, c, t = data
        embed = discord.Embed(title="🎯 Sniped Deleted Message", color=MAIN_COLOR, timestamp=t)
        embed.set_author(name=str(a), icon_url=a.display_avatar.url)
        embed.description = c or "*[No text content]*"
        await ctx.reply(embed=embed)

    @commands.command(name="editsnipe", description="View before/after of recently edited message")
    async def editsnipe(self, ctx):
        data = self.edit_snipes.get(ctx.channel.id)
        if not data:
            return await ctx.reply("❌ Nothing to edit-snipe in this channel.")
        a, before, after, t = data
        embed = discord.Embed(title="✏️ Edited Message Snipe", color=INFO_COLOR, timestamp=t)
        embed.set_author(name=str(a), icon_url=a.display_avatar.url)
        embed.add_field(name="Before", value=before or "*Empty*", inline=False)
        embed.add_field(name="After", value=after or "*Empty*", inline=False)
        await ctx.reply(embed=embed)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        with sqlite3.connect(DB_FILE) as conn:
            cur = conn.cursor()
            cur.execute("SELECT reason FROM afk WHERE user_id = ?", (str(message.author.id),))
            row = cur.fetchone()
            if row and not message.content.startswith(("&afk", "/afk")):
                cur.execute("DELETE FROM afk WHERE user_id = ?", (str(message.author.id),))
                conn.commit()
                await message.reply(f"👋 Welcome back {message.author.mention}! Your AFK status has been cleared.", delete_after=5)

            for mention in message.mentions:
                cur.execute("SELECT reason, timestamp FROM afk WHERE user_id = ?", (str(mention.id),))
                afk_row = cur.fetchone()
                if afk_row:
                    reason, ts = afk_row
                    await message.reply(f"💤 **{mention.display_name}** is AFK: *{reason}*", delete_after=6)

    @commands.command(name="password_gen", description="Generate a secure random password: &password_gen [length]")
    async def password_gen(self, ctx, length: int = 16):
        import string
        l = max(8, min(length, 64))
        chars = string.ascii_letters + string.digits + "!@#$%^&*()-_=+"
        pwd = "".join(random.choice(chars) for _ in range(l))
        try:
            await ctx.author.send(f"🔐 **Generated Secure Password ({l} chars):**\n`{pwd}`")
            await ctx.reply("📬 Sent your secure password to your DMs!")
        except Exception:
            await ctx.reply(f"🔐 **Generated Password:** `{pwd}`")

    @commands.command(name="uuid_gen", description="Generate a unique UUIDv4 identifier")
    async def uuid_gen(self, ctx):
        import uuid
        await ctx.reply(f"🆔 **UUIDv4:** `{uuid.uuid4()}`")

    @commands.command(name="color_random", description="Generate a random color preview and hex code")
    async def color_random(self, ctx):
        color_val = random.randint(0, 0xFFFFFF)
        hex_code = f"#{color_val:06X}"
        embed = discord.Embed(title=f"🎨 Color: {hex_code}", color=color_val)
        embed.set_thumbnail(url=f"https://singlecolorimage.com/get/{hex_code[1:]}/100x100")
        embed.add_field(name="HEX", value=f"`{hex_code}`", inline=True)
        embed.add_field(name="DECIMAL", value=f"`{color_val}`", inline=True)
        await ctx.reply(embed=embed)

    @commands.command(name="temp_c_to_f", description="Convert Celsius to Fahrenheit: &temp_c_to_f 25")
    async def temp_c_to_f(self, ctx, celsius: float):
        f = (celsius * 9/5) + 32
        await ctx.reply(f"🌡️ **{celsius}°C** = **{f:.2f}°F**")

    @commands.command(name="temp_f_to_c", description="Convert Fahrenheit to Celsius: &temp_f_to_c 77")
    async def temp_f_to_c(self, ctx, fahrenheit: float):
        c = (fahrenheit - 32) * 5/9
        await ctx.reply(f"🌡️ **{fahrenheit}°F** = **{c:.2f}°C**")

    @commands.command(name="dist_km_to_mi", description="Convert Kilometers to Miles: &dist_km_to_mi 10")
    async def dist_km_to_mi(self, ctx, km: float):
        mi = km * 0.621371
        await ctx.reply(f"📏 **{km} km** = **{mi:.2f} miles**")

    @commands.command(name="dist_mi_to_km", description="Convert Miles to Kilometers: &dist_mi_to_km 6.2")
    async def dist_mi_to_km(self, ctx, miles: float):
        km = miles / 0.621371
        await ctx.reply(f"📏 **{miles} miles** = **{km:.2f} km**")

    @commands.command(name="weight_kg_to_lb", description="Convert Kilograms to Pounds: &weight_kg_to_lb 70")
    async def weight_kg_to_lb(self, ctx, kg: float):
        lb = kg * 2.20462
        await ctx.reply(f"⚖️ **{kg} kg** = **{lb:.2f} lbs**")

    @commands.command(name="weight_lb_to_kg", description="Convert Pounds to Kilograms: &weight_lb_to_kg 154")
    async def weight_lb_to_kg(self, ctx, lb: float):
        kg = lb / 2.20462
        await ctx.reply(f"⚖️ **{lb} lbs** = **{kg:.2f} kg**")

    @commands.command(name="bmi_calc", description="Calculate Body Mass Index: &bmi_calc <weight_kg> <height_m>")
    async def bmi_calc(self, ctx, weight_kg: float, height_m: float):
        if height_m <= 0:
            return await ctx.reply("❌ Invalid height.")
        bmi = weight_kg / (height_m ** 2)
        category = "Underweight" if bmi < 18.5 else "Normal weight" if bmi < 25 else "Overweight" if bmi < 30 else "Obese"
        await ctx.reply(f"🩺 **BMI Score:** `{bmi:.1f}` — **{category}**")

    @commands.command(name="percentage", description="Calculate percentage: &percentage <part> <total>")
    async def percentage(self, ctx, part: float, total: float):
        if total == 0:
            return await ctx.reply("❌ Division by zero.")
        pct = (part / total) * 100
        await ctx.reply(f"📊 **{part}** is **{pct:.2f}%** of **{total}**")

    @commands.command(name="dice_d20", description="Roll a 20-sided D&D dice")
    async def dice_d20(self, ctx):
        val = random.randint(1, 20)
        crit = " 🌟 CRITICAL SUCCESS!" if val == 20 else " 💀 CRITICAL FAIL!" if val == 1 else ""
        await ctx.reply(f"🎲 **D20 Roll:** `{val}`{crit}")

    @commands.command(name="dice_d100", description="Roll a 100-sided percentile dice")
    async def dice_d100(self, ctx):
        await ctx.reply(f"🎲 **D100 Roll:** `{random.randint(1, 100)}`")

    @commands.command(name="server_icon", description="Get full-size server icon")
    async def server_icon(self, ctx):
        if not ctx.guild or not ctx.guild.icon:
            return await ctx.reply("❌ No server icon available.")
        embed = discord.Embed(title=f"🖼️ Icon: {ctx.guild.name}", color=MAIN_COLOR)
        embed.set_image(url=ctx.guild.icon.url)
        await ctx.reply(embed=embed)

    @commands.command(name="server_banner", description="Get full-size server banner")
    async def server_banner(self, ctx):
        if not ctx.guild or not ctx.guild.banner:
            return await ctx.reply("❌ No server banner available.")
        embed = discord.Embed(title=f"🖼️ Banner: {ctx.guild.name}", color=MAIN_COLOR)
        embed.set_image(url=ctx.guild.banner.url)
        await ctx.reply(embed=embed)

    @commands.command(name="role_info", description="View detailed information about a role")
    async def role_info(self, ctx, role: discord.Role):
        embed = discord.Embed(title=f"🎭 Role: {role.name}", color=role.color or MAIN_COLOR)
        embed.add_field(name="ID", value=f"`{role.id}`", inline=True)
        embed.add_field(name="Members", value=f"`{len(role.members)}`", inline=True)
        embed.add_field(name="Position", value=f"`{role.position}`", inline=True)
        embed.add_field(name="Mentionable", value=f"`{role.mentionable}`", inline=True)
        embed.add_field(name="Hoisted", value=f"`{role.hoist}`", inline=True)
        embed.add_field(name="Color HEX", value=f"`{str(role.color)}`", inline=True)
        await ctx.reply(embed=embed)

    @commands.command(name="boost_count", description="View server Nitro boost level and count")
    async def boost_count(self, ctx):
        if not ctx.guild:
            return await ctx.reply("❌ Server only.")
        g = ctx.guild
        embed = discord.Embed(title=f"🚀 Server Boosts: {g.name}", color=0xFF73FA)
        embed.add_field(name="Tier Level", value=f"Tier `{g.premium_tier}`", inline=True)
        embed.add_field(name="Total Boosts", value=f"💎 **{g.premium_subscription_count}** Boosts", inline=True)
        embed.add_field(name="Boosters", value=f"👥 **{len(g.premium_subscribers)}** Members", inline=True)
        await ctx.reply(embed=embed)

    @commands.command(name="calc_sqrt", description="Square root: &calc_sqrt 144")
    async def calc_sqrt(self, ctx, n: float):
        import math
        await ctx.reply(f"📐 **√{n}** = `{math.sqrt(n)}`")

    @commands.command(name="calc_pow", description="Power exponent: &calc_pow <base> <exp>")
    async def calc_pow(self, ctx, base: float, exp: float):
        await ctx.reply(f"📐 **{base}^{exp}** = `{base ** exp}`")

    @commands.command(name="calc_log", description="Natural logarithm: &calc_log 100")
    async def calc_log(self, ctx, n: float):
        import math
        await ctx.reply(f"📐 **ln({n})** = `{math.log(n):.4f}`")

    @commands.command(name="calc_sin", description="Trigonometric sine (degrees): &calc_sin 90")
    async def calc_sin(self, ctx, deg: float):
        import math
        await ctx.reply(f"📐 **sin({deg}°)** = `{math.sin(math.radians(deg)):.4f}`")

    @commands.command(name="calc_cos", description="Trigonometric cosine (degrees): &calc_cos 0")
    async def calc_cos(self, ctx, deg: float):
        import math
        await ctx.reply(f"📐 **cos({deg}°)** = `{math.cos(math.radians(deg)):.4f}`")

    @commands.command(name="conv_km_m", description="Kilometers to Meters: &conv_km_m 5")
    async def conv_km_m(self, ctx, km: float):
        await ctx.reply(f"📏 **{km} km** = `{km * 1000:,} meters`")

    @commands.command(name="conv_m_km", description="Meters to Kilometers: &conv_m_km 5000")
    async def conv_m_km(self, ctx, m: float):
        await ctx.reply(f"📏 **{m:,} m** = `{m / 1000} km`")

    @commands.command(name="conv_m_cm", description="Meters to Centimeters: &conv_m_cm 2")
    async def conv_m_cm(self, ctx, m: float):
        await ctx.reply(f"📏 **{m} m** = `{m * 100} cm`")

    @commands.command(name="conv_cm_m", description="Centimeters to Meters: &conv_cm_m 250")
    async def conv_cm_m(self, ctx, cm: float):
        await ctx.reply(f"📏 **{cm} cm** = `{cm / 100} m`")

    @commands.command(name="conv_kg_g", description="Kilograms to Grams: &conv_kg_g 2.5")
    async def conv_kg_g(self, ctx, kg: float):
        await ctx.reply(f"⚖️ **{kg} kg** = `{kg * 1000:,} grams`")

    @commands.command(name="conv_g_kg", description="Grams to Kilograms: &conv_g_kg 2500")
    async def conv_g_kg(self, ctx, g: float):
        await ctx.reply(f"⚖️ **{g:,} g** = `{g / 1000} kg`")

    @commands.command(name="conv_l_ml", description="Liters to Milliliters: &conv_l_ml 2")
    async def conv_l_ml(self, ctx, l: float):
        await ctx.reply(f"🥛 **{l} L** = `{l * 1000:,} mL`")

    @commands.command(name="conv_ml_l", description="Milliliters to Liters: &conv_ml_l 1500")
    async def conv_ml_l(self, ctx, ml: float):
        await ctx.reply(f"🥛 **{ml:,} mL** = `{ml / 1000} L`")

    @commands.command(name="conv_gb_mb", description="Gigabytes to Megabytes: &conv_gb_mb 8")
    async def conv_gb_mb(self, ctx, gb: float):
        await ctx.reply(f"💾 **{gb} GB** = `{gb * 1024:,} MB`")

    @commands.command(name="conv_mb_gb", description="Megabytes to Gigabytes: &conv_mb_gb 4096")
    async def conv_mb_gb(self, ctx, mb: float):
        await ctx.reply(f"💾 **{mb:,} MB** = `{mb / 1024:.2f} GB`")

    @commands.command(name="conv_tb_gb", description="Terabytes to Gigabytes: &conv_tb_gb 2")
    async def conv_tb_gb(self, ctx, tb: float):
        await ctx.reply(f"💾 **{tb} TB** = `{tb * 1024:,} GB`")

    @commands.command(name="conv_hours_mins", description="Hours to Minutes: &conv_hours_mins 3")
    async def conv_hours_mins(self, ctx, h: float):
        await ctx.reply(f"⏱️ **{h} hours** = `{h * 60:,} minutes`")

    @commands.command(name="conv_mins_secs", description="Minutes to Seconds: &conv_mins_secs 15")
    async def conv_mins_secs(self, ctx, m: float):
        await ctx.reply(f"⏱️ **{m} mins** = `{m * 60:,} seconds`")

    @commands.command(name="conv_days_hours", description="Days to Hours: &conv_days_hours 7")
    async def conv_days_hours(self, ctx, d: float):
        await ctx.reply(f"📅 **{d} days** = `{d * 24:,} hours`")

    @commands.command(name="conv_weeks_days", description="Weeks to Days: &conv_weeks_days 4")
    async def conv_weeks_days(self, ctx, w: float):
        await ctx.reply(f"📅 **{w} weeks** = `{w * 7:,} days`")

    @commands.command(name="time_utc", description="Current Universal Coordinated Time (UTC)")
    async def time_utc(self, ctx):
        now = datetime.now(timezone.utc)
        await ctx.reply(f"🌐 **UTC Time:** `{now.strftime('%Y-%m-%d %H:%M:%S UTC')}`")

    @commands.command(name="time_est", description="Current Eastern Standard Time (EST / New York)")
    async def time_est(self, ctx):
        from datetime import timedelta
        now = datetime.now(timezone.utc) - timedelta(hours=5)
        await ctx.reply(f"🗽 **EST (New York):** `{now.strftime('%Y-%m-%d %H:%M:%S EST')}`")

    @commands.command(name="time_pst", description="Current Pacific Standard Time (PST / Los Angeles)")
    async def time_pst(self, ctx):
        from datetime import timedelta
        now = datetime.now(timezone.utc) - timedelta(hours=8)
        await ctx.reply(f"🌉 **PST (Los Angeles):** `{now.strftime('%Y-%m-%d %H:%M:%S PST')}`")

    @commands.command(name="time_gmt", description="Current Greenwich Mean Time (GMT / London)")
    async def time_gmt(self, ctx):
        now = datetime.now(timezone.utc)
        await ctx.reply(f"🇬🇧 **GMT (London):** `{now.strftime('%Y-%m-%d %H:%M:%S GMT')}`")

    @commands.command(name="time_ist", description="Current Indian Standard Time (IST / New Delhi)")
    async def time_ist(self, ctx):
        from datetime import timedelta
        now = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
        await ctx.reply(f"🇮🇳 **IST (New Delhi):** `{now.strftime('%Y-%m-%d %H:%M:%S IST')}`")

    @commands.command(name="time_jst", description="Current Japan Standard Time (JST / Tokyo)")
    async def time_jst(self, ctx):
        from datetime import timedelta
        now = datetime.now(timezone.utc) + timedelta(hours=9)
        await ctx.reply(f"🇯🇵 **JST (Tokyo):** `{now.strftime('%Y-%m-%d %H:%M:%S JST')}`")

async def setup(bot):
    await bot.add_cog(Utility(bot))
