import urllib.parse
import discord
from discord.ext import commands
from utils import MAIN_COLOR, INFO_COLOR, SUCCESS_COLOR, WARN_COLOR

SOUNDS = {
    "airhorn": "https://www.myinstants.com/media/sounds/airhorn.mp3",
    "applause": "https://www.myinstants.com/media/sounds/applause.mp3",
    "bruh": "https://www.myinstants.com/media/sounds/bruh.mp3",
    "drumroll": "https://www.myinstants.com/media/sounds/drum_roll.mp3",
    "fail": "https://www.myinstants.com/media/sounds/sad-trombone.mp3",
    "victory": "https://www.myinstants.com/media/sounds/victory_fanfare.mp3",
    "fart": "https://www.myinstants.com/media/sounds/perfect-fart.mp3",
    "bonk": "https://www.myinstants.com/media/sounds/bonk.mp3",
}

class SoundboardTTS(commands.Cog):
    """Voice soundboard clips, Text-to-Speech generators, and voice channel telemetry."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="tts_url", description="Generate a Text-to-Speech audio link for any text")
    async def tts_url(self, ctx, *, text: str):
        encoded = urllib.parse.quote(text[:200])
        url = f"https://translate.google.com/translate_tts?ie=UTF-8&client=tw-ob&q={encoded}&tl=en"
        embed = discord.Embed(
            title="🗣️ Text-to-Speech Audio Stream",
            description=f"**Message:** *\"{text[:200]}\"*\n\n🔊 [Click to Play / Download Audio Stream]({url})",
            color=SUCCESS_COLOR,
        )
        await ctx.reply(embed=embed)

    @commands.command(name="soundboard", description="List all available soundboard audio clips")
    async def soundboard(self, ctx):
        embed = discord.Embed(title="🔊 Vortex Instant Soundboard", color=INFO_COLOR)
        for name, url in SOUNDS.items():
            embed.add_field(name=f"🎵 {name.title()}", value=f"[Play Audio Clip]({url})\n*Cmd:* `&sound_{name}`", inline=True)
        await ctx.reply(embed=embed)

    @commands.command(name="sound_airhorn", description="Play / link airhorn sound")
    async def sound_airhorn(self, ctx):
        await ctx.reply(f"📢 **Airhorn!** 🔊 {SOUNDS['airhorn']}")

    @commands.command(name="sound_bruh", description="Play / link bruh sound")
    async def sound_bruh(self, ctx):
        await ctx.reply(f"🗿 **BRUH** 🔊 {SOUNDS['bruh']}")

    @commands.command(name="sound_applause", description="Play / link applause sound")
    async def sound_applause(self, ctx):
        await ctx.reply(f"👏 **Applause!** 🔊 {SOUNDS['applause']}")

    @commands.command(name="sound_bonk", description="Play / link bonk sound effect")
    async def sound_bonk(self, ctx):
        await ctx.reply(f"🔨 **BONK!** 🔊 {SOUNDS['bonk']}")

    @commands.command(name="sound_victory", description="Play / link victory fanfare sound")
    async def sound_victory(self, ctx):
        await ctx.reply(f"🎺 **VICTORY!** 🔊 {SOUNDS['victory']}")

    @commands.command(name="sound_fart", description="Play / link fart sound effect")
    async def sound_fart(self, ctx):
        await ctx.reply("💨 **FART!** 🔊 https://www.myinstants.com/media/sounds/perfect-fart.mp3")

    @commands.command(name="sound_oof", description="Roblox OOF sound")
    async def sound_oof(self, ctx):
        await ctx.reply("💀 **OOF!** 🔊 https://www.myinstants.com/media/sounds/roblox-death-sound_1.mp3")

    @commands.command(name="sound_nope", description="Engineer NOPE sound")
    async def sound_nope(self, ctx):
        await ctx.reply("🚫 **NOPE!** 🔊 https://www.myinstants.com/media/sounds/engineer_no01.mp3")

    @commands.command(name="sound_yeet", description="YEET sound effect")
    async def sound_yeet(self, ctx):
        await ctx.reply("🚀 **YEET!** 🔊 https://www.myinstants.com/media/sounds/yeet.mp3")

    @commands.command(name="sound_fbi", description="FBI Open Up sound")
    async def sound_fbi(self, ctx):
        await ctx.reply("🚨 **FBI OPEN UP!** 🔊 https://www.myinstants.com/media/sounds/fbi-open-up_1.mp3")

    @commands.command(name="sound_mission_passed", description="GTA San Andreas Mission Passed")
    async def sound_mission_passed(self, ctx):
        await ctx.reply("⭐ **MISSION PASSED! + RESPECT** 🔊 https://www.myinstants.com/media/sounds/gta-san-andreas-mission-passed.mp3")

    @commands.command(name="sound_windows_xp", description="Windows XP startup chime")
    async def sound_windows_xp(self, ctx):
        await ctx.reply("💻 **Windows XP Startup** 🔊 https://www.myinstants.com/media/sounds/windows-xp-startup.mp3")

    @commands.command(name="sound_discord_ping", description="Discord notification sound")
    async def sound_discord_ping(self, ctx):
        await ctx.reply("🔔 **Discord Notification** 🔊 https://www.myinstants.com/media/sounds/discord-notification.mp3")

    @commands.command(name="sound_goat", description="Screaming goat sound")
    async def sound_goat(self, ctx):
        await ctx.reply("🐐 **Screaming Goat!** 🔊 https://www.myinstants.com/media/sounds/screaming-goat.mp3")

    @commands.command(name="sound_illuminati", description="X-Files Illuminati theme")
    async def sound_illuminati(self, ctx):
        await ctx.reply("👁️ **Illuminati Confirmed** 🔊 https://www.myinstants.com/media/sounds/x-files-theme.mp3")

    @commands.command(name="sound_run", description="AWOLNATION Run sound")
    async def sound_run(self, ctx):
        await ctx.reply("🏃‍♂️ **RUN!** 🔊 https://www.myinstants.com/media/sounds/run-vine-sound-effect.mp3")

    @commands.command(name="sound_violin", description="Sad violin sound")
    async def sound_violin(self, ctx):
        await ctx.reply("🎻 **Sad Violin** 🔊 https://www.myinstants.com/media/sounds/sad-violin.mp3")

    @commands.command(name="sound_tada", description="Ta-da fanfare sound")
    async def sound_tada(self, ctx):
        await ctx.reply("🎉 **TA-DA!** 🔊 https://www.myinstants.com/media/sounds/tada.mp3")

    @commands.command(name="sound_alarm", description="Nuclear siren alarm sound")
    async def sound_alarm(self, ctx):
        await ctx.reply("🚨 **SIREN ALARM!** 🔊 https://www.myinstants.com/media/sounds/emergency-alarm.mp3")

    @commands.command(name="sound_levelup", description="8-bit Level Up chime")
    async def sound_levelup(self, ctx):
        await ctx.reply("🆙 **LEVEL UP!** 🔊 https://www.myinstants.com/media/sounds/level-up.mp3")

    @commands.command(name="sound_explosion", description="Explosion sound effect")
    async def sound_explosion(self, ctx):
        await ctx.reply("💥 **KABOOM!** 🔊 https://www.myinstants.com/media/sounds/explosion.mp3")

    @commands.command(name="sound_cheering", description="Crowd cheering sound")
    async def sound_cheering(self, ctx):
        await ctx.reply("🥳 **Crowd Cheering!** 🔊 https://www.myinstants.com/media/sounds/cheering.mp3")

async def setup(bot):
    await bot.add_cog(SoundboardTTS(bot))
