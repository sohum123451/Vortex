import asyncio
import functools
import re
import urllib.parse
import discord
from discord.ext import commands
import yt_dlp as youtube_dl
from utils import MAIN_COLOR, SUCCESS_COLOR, WARN_COLOR, ERROR_COLOR, INFO_COLOR

import os

# yt-dlp configuration with mobile/embedded client rotation & cookie support
cookies_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cookies.txt")
ytdl_format_options = {
    'format': 'bestaudio[ext=m4a]/bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'ytsearch',
    'source_address': '0.0.0.0',
    'extractor_args': {
        'youtube': {
            'player_client': ['ios', 'android', 'mweb', 'web'],
            'player_skip': ['configs'],
        }
    },
    'http_headers': {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
    }
}

if os.path.exists(cookies_file):
    ytdl_format_options['cookiefile'] = cookies_file

def make_ffmpeg_audio(url_or_path, http_headers=None):
    import shutil
    before = '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'
    opts = {'before_options': before, 'options': '-vn -loglevel panic -ar 48000 -ac 2'}
    executable = shutil.which('ffmpeg') or 'ffmpeg'
    return discord.FFmpegPCMAudio(url_or_path, executable=executable, **opts)

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)
ytdl_sc = youtube_dl.YoutubeDL({**ytdl_format_options, 'default_search': 'scsearch'})

RADIO_STREAMS = {
    "lofi": ("https://stream.zeno.fm/f3wvbbqmdg8uv", "Lofi Hip Hop Chill Beats ☕", 0.6),
    "synthwave": ("https://stream.nightride.fm/nightride.mp3", "Synthwave / Cyberpunk 80s 🌌", 0.8),
    "anime": ("https://listen.moe/stream", "Anime OST & J-Pop Hits 🌸", 0.8),
    "chill": ("https://stream.zeno.fm/0r0xa792kwzuv", "Chillout Lounge & Ambient 🍃", 0.7),
    "jazz": ("https://stream.somafm.com/sonicuniverse-128-mp3", "Smooth Coffee Jazz 🎷", 0.7),
    "classical": ("https://stream.srg-ssr.ch/m/rsc_de/mp3_128", "Peaceful Classical Piano & Orchestra 🎹", 0.7),
    "gaming": ("https://stream.somafm.com/groovesalad-256-mp3", "Epic 256kbps HD Gaming & Electro 🎮", 0.7),
}

def format_duration(duration):
    if not duration:
        return "Stream"
    try:
        total_seconds = int(float(duration))
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        return f"{minutes}:{seconds:02d}"
    except Exception:
        return "Stream"

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.8):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title', 'Unknown Title')
        self.url = data.get('url', '')
        self.webpage_url = data.get('webpage_url', '')
        self.duration = data.get('duration', 0)
        self.thumbnail = data.get('thumbnail', '')
        self.uploader = data.get('uploader', 'Unknown Artist')

    @classmethod
    async def from_query(cls, query, *, loop=None, stream=True):
        loop = loop or asyncio.get_event_loop()
        
        if not query.startswith(("http://", "https://", "ytsearch:", "scsearch:", "ytsearch1:")):
            search_query = f"ytsearch1:{query}"
        else:
            search_query = query

        # 1. First attempt: Standard YouTube extractor
        try:
            to_run = functools.partial(ytdl.extract_info, search_query, download=not stream)
            data = await loop.run_in_executor(None, to_run)
            if data and 'entries' in data:
                if not data['entries']:
                    raise Exception("No YouTube results.")
                data = data['entries'][0]
            if not data or not data.get('url'):
                raise Exception("Missing audio URL from YouTube.")
        except Exception as yt_err:
            # 2. Fallback attempt: SoundCloud search fallback
            clean_query = query
            if "youtube.com" in query or "youtu.be" in query:
                clean_query = re.sub(r'https?://[^\s]+', '', query).strip() or query
            
            sc_query = f"scsearch:{clean_query}" if not clean_query.startswith("scsearch:") else clean_query
            try:
                to_run_sc = functools.partial(ytdl_sc.extract_info, sc_query, download=not stream)
                data = await loop.run_in_executor(None, to_run_sc)
                if data and 'entries' in data:
                    if not data['entries']:
                        raise Exception("No SoundCloud results.")
                    data = data['entries'][0]
            except Exception:
                raise yt_err

        if not data:
            raise Exception("No search results found.")

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        headers = data.get('http_headers')
        return cls(make_ffmpeg_audio(filename, headers), data=data)

    @classmethod
    def from_url(cls, url, title, duration=0):
        data = {'title': title, 'url': url, 'webpage_url': url, 'duration': duration, 'thumbnail': '', 'uploader': 'Web Radio'}
        return cls(make_ffmpeg_audio(url), data=data)

class MusicPlayerState:
    def __init__(self, guild_id):
        self.guild_id = guild_id
        self.queue = []
        self.current = None
        self.voice_client = None
        self.loop_single = False
        self.loop_queue = False
        self.volume = 0.7

class MusicControls(discord.ui.View):
    def __init__(self, cog, ctx):
        super().__init__(timeout=180)
        self.cog = cog
        self.ctx = ctx

    @discord.ui.button(label="⏯️ Pause/Resume", style=discord.ButtonStyle.primary)
    async def toggle_play(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = interaction.guild.voice_client
        if not vc:
            return await interaction.response.send_message("❌ No music playing.", ephemeral=True)
        if vc.is_playing():
            vc.pause()
            await interaction.response.send_message("⏸️ Paused playback.", ephemeral=True)
        elif vc.is_paused():
            vc.resume()
            await interaction.response.send_message("▶️ Resumed playback.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Nothing is active.", ephemeral=True)

    @discord.ui.button(label="⏭️ Skip", style=discord.ButtonStyle.secondary)
    async def skip_track(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = interaction.guild.voice_client
        if not vc or not vc.is_playing():
            return await interaction.response.send_message("❌ Nothing to skip.", ephemeral=True)
        vc.stop()
        await interaction.response.send_message("⏭️ Skipped to next track.", ephemeral=True)

    @discord.ui.button(label="📜 Queue", style=discord.ButtonStyle.secondary)
    async def view_queue(self, interaction: discord.Interaction, button: discord.ui.Button):
        state = self.cog.get_state(interaction.guild_id)
        if not state.queue and not state.current:
            return await interaction.response.send_message("📭 Queue is currently empty.", ephemeral=True)
        desc = [f"**Now Playing:** 🎵 `{state.current.title if state.current else 'None'}`\n"]
        for idx, s in enumerate(state.queue[:10], start=1):
            dur = format_duration(s.duration)
            desc.append(f"**{idx}.** `{s.title}` — `{dur}`")
        if len(state.queue) > 10:
            desc.append(f"\n*...and {len(state.queue) - 10} more songs in queue.*")
        embed = discord.Embed(title="🎶 Music Queue", description="\n".join(desc), color=MAIN_COLOR)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="⏹️ Stop", style=discord.ButtonStyle.danger)
    async def stop_music(self, interaction: discord.Interaction, button: discord.ui.Button):
        state = self.cog.get_state(interaction.guild_id)
        state.queue.clear()
        state.current = None
        vc = interaction.guild.voice_client
        if vc:
            await vc.disconnect()
        await interaction.response.send_message("⏹️ Music stopped and disconnected.", ephemeral=True)

class Music(commands.Cog):
    """High-fidelity voice audio streamer, YouTube/Spotify search, 24/7 web radios, and queue controls."""

    def __init__(self, bot):
        self.bot = bot
        self.states = {}

    def get_state(self, guild_id: int) -> MusicPlayerState:
        if guild_id not in self.states:
            self.states[guild_id] = MusicPlayerState(guild_id)
        return self.states[guild_id]

    def play_next_song(self, ctx):
        state = self.get_state(ctx.guild.id)
        vc = ctx.guild.voice_client
        if not vc:
            return

        if state.loop_single and state.current:
            source = state.current
            vc.play(source, after=lambda e: self.play_next_song(ctx))
            return

        if state.queue:
            next_source = state.queue.pop(0)
            if state.loop_queue and state.current:
                state.queue.append(state.current)
            state.current = next_source
            next_source.volume = state.volume
            vc.play(next_source, after=lambda e: self.play_next_song(ctx))
            
            dur = format_duration(next_source.duration)
            embed = discord.Embed(
                title="🎵 Now Playing",
                description=f"**[{next_source.title}]({next_source.webpage_url})**\n\n⏱️ Duration: `{dur}` | 👤 Artist: `{next_source.uploader}`",
                color=SUCCESS_COLOR,
            )
            if next_source.thumbnail:
                embed.set_thumbnail(url=next_source.thumbnail)
            asyncio.run_coroutine_threadsafe(ctx.send(embed=embed, view=MusicControls(self, ctx)), self.bot.loop)
        else:
            state.current = None

    async def ensure_voice(self, ctx):
        if not ctx.author.voice or not ctx.author.voice.channel:
            await ctx.reply("❌ You must join a voice channel first!")
            return False
        if not ctx.guild.voice_client:
            await ctx.author.voice.channel.connect()
        elif ctx.guild.voice_client.channel != ctx.author.voice.channel:
            await ctx.guild.voice_client.move_to(ctx.author.voice.channel)
        return True

    @commands.hybrid_command(name="play", aliases=["p"], description="Play a song from YouTube, Spotify link, or search keyword")
    async def play(self, ctx, *, query: str):
        if not await self.ensure_voice(ctx):
            return
        await ctx.defer()
        state = self.get_state(ctx.guild.id)
        try:
            source = await YTDLSource.from_query(query, loop=self.bot.loop, stream=True)
        except Exception as e:
            return await ctx.reply(f"❌ Failed to extract audio: `{e}`")

        vc = ctx.guild.voice_client
        if vc.is_playing() or vc.is_paused():
            state.queue.append(source)
            dur = format_duration(source.duration)
            embed = discord.Embed(
                title="➕ Added to Queue",
                description=f"**[{source.title}]({source.webpage_url})**\n⏱️ Duration: `{dur}` | 📊 Position: `#{len(state.queue)}`",
                color=MAIN_COLOR,
            )
            if source.thumbnail:
                embed.set_thumbnail(url=source.thumbnail)
            await ctx.reply(embed=embed)
        else:
            state.current = source
            source.volume = state.volume
            vc.play(source, after=lambda e: self.play_next_song(ctx))
            dur = format_duration(source.duration)
            embed = discord.Embed(
                title="🎵 Now Playing",
                description=f"**[{source.title}]({source.webpage_url})**\n\n⏱️ Duration: `{dur}` | 👤 Artist: `{source.uploader}`",
                color=SUCCESS_COLOR,
            )
            if source.thumbnail:
                embed.set_thumbnail(url=source.thumbnail)
            await ctx.reply(embed=embed, view=MusicControls(self, ctx))

    @commands.hybrid_command(name="pause", aliases=["ps", "hold"], description="Pause the currently playing music")
    async def pause(self, ctx):
        vc = ctx.guild.voice_client
        if vc and vc.is_playing():
            vc.pause()
            await ctx.reply("⏸️ Playback paused.")
        else:
            await ctx.reply("❌ Nothing is currently playing.")

    @commands.hybrid_command(name="resume", aliases=["r", "unpause"], description="Resume paused music")
    async def resume(self, ctx):
        vc = ctx.guild.voice_client
        if vc and vc.is_paused():
            vc.resume()
            await ctx.reply("▶️ Playback resumed.")
        else:
            await ctx.reply("❌ Music is not paused.")

    @commands.hybrid_command(name="skip", aliases=["s"], description="Skip to the next song in the queue")
    async def skip(self, ctx):
        vc = ctx.guild.voice_client
        if vc and (vc.is_playing() or vc.is_paused()):
            vc.stop()
            await ctx.reply("⏭️ Skipped current track.")
        else:
            await ctx.reply("❌ Nothing to skip.")

    @commands.hybrid_command(name="stop", aliases=["st"], description="Stop music and clear the entire playlist queue")
    async def stop(self, ctx):
        state = self.get_state(ctx.guild.id)
        state.queue.clear()
        state.current = None
        vc = ctx.guild.voice_client
        if vc:
            await vc.disconnect()
            await ctx.reply("⏹️ Music stopped and disconnected from voice channel.")
        else:
            await ctx.reply("❌ Bot is not in a voice channel.")

    @commands.hybrid_command(name="queue", aliases=["q", "list"], description="Display all songs currently in the queue")
    async def queue(self, ctx):
        state = self.get_state(ctx.guild.id)
        if not state.current and not state.queue:
            return await ctx.reply("📭 The queue is completely empty.")

        desc = []
        if state.current:
            dur = format_duration(state.current.duration)
            desc.append(f"**Now Playing:** 🎵 [{state.current.title}]({state.current.webpage_url}) (`{dur}`)\n")

        if state.queue:
            desc.append("**Up Next:**")
            for idx, song in enumerate(state.queue[:10], start=1):
                dur = format_duration(song.duration)
                desc.append(f"**{idx}.** [{song.title}]({song.webpage_url}) (`{dur}`)")
            if len(state.queue) > 10:
                desc.append(f"\n*...and {len(state.queue) - 10} more songs in queue.*")

        embed = discord.Embed(title=f"🎶 Music Queue — {ctx.guild.name}", description="\n".join(desc), color=MAIN_COLOR)
        await ctx.reply(embed=embed)

    @commands.hybrid_command(name="nowplaying", aliases=["np", "song", "current"], description="Show details of the song currently playing")
    async def nowplaying(self, ctx):
        state = self.get_state(ctx.guild.id)
        if not state.current:
            return await ctx.reply("❌ Nothing is currently playing.")
        song = state.current
        dur = format_duration(song.duration)
        embed = discord.Embed(
            title="🎵 Now Playing",
            description=f"**[{song.title}]({song.webpage_url})**\n\n⏱️ **Duration:** `{dur}`\n👤 **Channel:** `{song.uploader}`\n🔊 **Volume:** `{int(state.volume * 100)}%`",
            color=SUCCESS_COLOR,
        )
        if song.thumbnail:
            embed.set_thumbnail(url=song.thumbnail)
        await ctx.reply(embed=embed, view=MusicControls(self, ctx))

    @commands.hybrid_command(name="volume", aliases=["vol", "v"], description="Set playback volume (1-100%): &volume 80")
    async def volume(self, ctx, vol: int):
        if not 1 <= vol <= 100:
            return await ctx.reply("❌ Volume must be between 1 and 100.")
        state = self.get_state(ctx.guild.id)
        state.volume = vol / 100
        vc = ctx.guild.voice_client
        if vc and vc.source:
            vc.source.volume = state.volume
        await ctx.reply(f"🔊 Volume set to **{vol}%**.")

    @commands.command(name="loop", aliases=["lp", "repeat"], description="Toggle single song looping")
    async def loop(self, ctx):
        state = self.get_state(ctx.guild.id)
        state.loop_single = not state.loop_single
        mode = "Enabled 🔂" if state.loop_single else "Disabled ❌"
        await ctx.reply(f"🔂 Single song loop: **{mode}**")

    @commands.command(name="loopqueue", aliases=["lq", "loopall", "repeatall"], description="Toggle full queue looping")
    async def loopqueue(self, ctx):
        state = self.get_state(ctx.guild.id)
        state.loop_queue = not state.loop_queue
        mode = "Enabled 🔁" if state.loop_queue else "Disabled ❌"
        await ctx.reply(f"🔁 Queue loop: **{mode}**")

    @commands.command(name="shuffle", aliases=["shf", "mix"], description="Randomly shuffle the order of songs in queue")
    async def shuffle(self, ctx):
        import random
        state = self.get_state(ctx.guild.id)
        if len(state.queue) < 2:
            return await ctx.reply("❌ Need at least 2 songs in queue to shuffle.")
        random.shuffle(state.queue)
        await ctx.reply(f"🔀 Shuffled **{len(state.queue)}** songs in queue.")

    @commands.command(name="remove", aliases=["rm", "delete", "del"], description="Remove a specific song from queue: &remove <index>")
    async def remove(self, ctx, index: int):
        state = self.get_state(ctx.guild.id)
        if not 1 <= index <= len(state.queue):
            return await ctx.reply(f"❌ Invalid index. Queue length is {len(state.queue)}.")
        removed = state.queue.pop(index - 1)
        await ctx.reply(f"🗑️ Removed **{removed.title}** from queue.")

    @commands.command(name="clear_queue", aliases=["cq", "clear"], description="Clear all upcoming songs from queue")
    async def clear_queue(self, ctx):
        state = self.get_state(ctx.guild.id)
        count = len(state.queue)
        state.queue.clear()
        await ctx.reply(f"🧹 Cleared **{count}** songs from queue.")

    @commands.command(name="join_vc", aliases=["connect", "joinvc"], description="Make the bot join your active voice channel")
    async def join_vc(self, ctx):
        if await self.ensure_voice(ctx):
            await ctx.reply(f"🔊 Joined voice channel: **{ctx.author.voice.channel.name}**")

    @commands.command(name="leave_vc", aliases=["dc", "disconnect", "leavevc"], description="Disconnect the bot from voice channel")
    async def leave_vc(self, ctx):
        vc = ctx.guild.voice_client
        if vc:
            await vc.disconnect()
            await ctx.reply("👋 Disconnected from voice channel.")
        else:
            await ctx.reply("❌ Not connected to any voice channel.")

    # 24/7 Web Radios
    @commands.command(name="radio_lofi", aliases=["lofi", "rl"], description="Stream 24/7 Lofi Hip Hop Beats radio")
    async def radio_lofi(self, ctx):
        await self.start_radio(ctx, "lofi")

    @commands.command(name="radio_synthwave", aliases=["synthwave", "rs"], description="Stream 24/7 Synthwave & Retrowave radio")
    async def radio_synthwave(self, ctx):
        await self.start_radio(ctx, "synthwave")

    @commands.command(name="radio_anime", aliases=["ra", "radioanime"], description="Stream 24/7 Anime OST & J-Pop radio")
    async def radio_anime(self, ctx):
        await self.start_radio(ctx, "anime")

    @commands.command(name="radio_chill", aliases=["chill", "rc"], description="Stream 24/7 Chillout Lounge radio")
    async def radio_chill(self, ctx):
        await self.start_radio(ctx, "chill")

    @commands.command(name="radio_jazz", aliases=["jazz", "rj"], description="Stream 24/7 Smooth Coffee Jazz radio")
    async def radio_jazz(self, ctx):
        await self.start_radio(ctx, "jazz")

    @commands.command(name="radio_classical", aliases=["classical", "piano", "rcp"], description="Stream 24/7 Peaceful Classical Piano radio")
    async def radio_classical(self, ctx):
        await self.start_radio(ctx, "classical")

    @commands.command(name="radio_gaming", aliases=["gaming", "rg"], description="Stream 24/7 Epic Gaming Beats radio")
    async def radio_gaming(self, ctx):
        await self.start_radio(ctx, "gaming")

    async def start_radio(self, ctx, radio_key: str):
        if not await self.ensure_voice(ctx):
            return
        url, title, vol_factor = RADIO_STREAMS[radio_key]
        state = self.get_state(ctx.guild.id)
        state.queue.clear()
        source = YTDLSource.from_url(url, title)
        source.volume = min(state.volume * vol_factor, 2.0)
        state.current = source
        vc = ctx.guild.voice_client
        if vc.is_playing() or vc.is_paused():
            vc.stop()
        vc.play(source)
        
        calculated_vol = int(source.volume * 100)
        embed = discord.Embed(
            title="📻 24/7 Live Web Radio Started",
            description=(
                f"🎶 **Station:** `{title}`\n"
                f"🔊 **Stream:** `{url}`\n"
                f"🎚️ **Current Volume:** `{calculated_vol}%` (optimized for this stream)\n\n"
                f"💡 *Tip: You can adjust the volume anytime using `/volume <1-100>` (or `&volume <1-100>`).*"
            ),
            color=0x9B59B6,
        )
        await ctx.reply(embed=embed, view=MusicControls(self, ctx))

async def setup(bot):
    await bot.add_cog(Music(bot))
