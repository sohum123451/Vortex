import os
from datetime import datetime, timezone
import aiohttp
import discord
from discord.ext import commands, tasks
from utils import MAIN_COLOR, SUCCESS_COLOR, INFO_COLOR

class Cricket(commands.Cog):
    """Real-time cricket scorecards, ongoing match trackers, and schedules powered by CricAPI."""

    def __init__(self, bot):
        self.bot = bot
        self.api_key = os.getenv("CRICAPI_KEY", "")
        self.base_url = "https://api.cricapi.com/v1"
        self.tracking_match_id = None
        self.log_channel_id = None
        self.update_message = None

    async def cog_load(self):
        if not self.live_updater.is_running():
            self.live_updater.start()

    def cog_unload(self):
        self.live_updater.cancel()

    @commands.hybrid_command(name="live", description="Show ongoing live cricket matches and match IDs")
    async def live(self, ctx):
        await ctx.defer()
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(f"{self.base_url}/currentMatches?apikey={self.api_key}&offset=0") as resp:
                    data = await resp.json()
                    matches = data.get("data", [])
                    if not matches:
                        return await ctx.reply("🏏 No live matches currently in progress.")
                    embed = discord.Embed(title="🏏 Ongoing Live Cricket Matches", color=SUCCESS_COLOR)
                    for match in matches[:6]:
                        embed.add_field(
                            name=match.get("name"),
                            value=f"**ID:** `{match.get('id')}`\n**Status:** {match.get('status')}",
                            inline=False,
                        )
                    await ctx.reply(embed=embed)
            except Exception as e:
                await ctx.reply(f"❌ Cricket API error: {e}")

    @commands.hybrid_command(name="track", description="Start 20s real-time match scorecard auto-updates")
    @commands.has_permissions(manage_messages=True)
    async def track(self, ctx, match_id: str):
        self.tracking_match_id = match_id
        self.log_channel_id = ctx.channel.id
        self.update_message = None
        await ctx.reply(f"🏏 Auto-tracking scorecard for match `{match_id}` started in this channel.")

    @commands.hybrid_command(name="stoptracking", description="Stop live cricket scorecard updates")
    @commands.has_permissions(manage_messages=True)
    async def stoptracking(self, ctx):
        self.tracking_match_id = None
        self.update_message = None
        await ctx.reply("🛑 Match tracking stopped.")

    @tasks.loop(seconds=20)
    async def live_updater(self):
        if not self.log_channel_id or not self.tracking_match_id:
            return
        channel = self.bot.get_channel(self.log_channel_id)
        if not channel:
            return

        async with aiohttp.ClientSession() as session:
            url = f"{self.base_url}/match_info?apikey={self.api_key}&id={self.tracking_match_id}"
            try:
                async with session.get(url) as resp:
                    data = await resp.json()
                    if data.get("status") == "success":
                        m = data.get("data", {})
                        scores = m.get("score", [])
                        score_text = "\n".join([
                            f"**{s['inning']}**: {s['r']}/{s['w']} ({s['o']} ov)"
                            for s in scores
                        ])
                        live_embed = discord.Embed(title="🏏 Live Match Scorecard", color=INFO_COLOR)
                        live_embed.description = f"**{m.get('name')}**\n**Status:** {m.get('status')}\n\n{score_text or '*Score updating...*'}"
                        live_embed.set_footer(text=f"Last synced: {datetime.now().strftime('%H:%M:%S')}")

                        if self.update_message:
                            try:
                                await self.update_message.edit(embed=live_embed)
                            except Exception:
                                self.update_message = await channel.send(embed=live_embed)
                        else:
                            self.update_message = await channel.send(embed=live_embed)
            except Exception:
                pass

async def setup(bot):
    await bot.add_cog(Cricket(bot))
