import asyncio
import sqlite3
from datetime import datetime, timezone
import discord
from discord.ext import commands
from utils import DB_FILE, MAIN_COLOR, INFO_COLOR, SUCCESS_COLOR

class ServerAnalytics(commands.Cog):
    """Server insights, message telemetry, chat activity heatmaps, and guild statistics."""

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        with sqlite3.connect(DB_FILE) as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO server_analytics (guild_id, user_id, date_str, messages)
                VALUES (?, ?, ?, 1)
                ON CONFLICT(guild_id, user_id, date_str) DO UPDATE SET messages = messages + 1
                """,
                (str(message.guild.id), str(message.author.id), today),
            )
            conn.commit()

    @commands.hybrid_command(name="server_activity", description="View server message activity breakdown")
    async def server_activity(self, ctx):
        if not ctx.guild:
            return await ctx.reply("❌ This command must be used in a server.")
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        with sqlite3.connect(DB_FILE) as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT SUM(messages), COUNT(DISTINCT user_id) FROM server_analytics WHERE guild_id = ? AND date_str = ?",
                (str(ctx.guild.id), today),
            )
            today_data = cur.fetchone()
            cur.execute("SELECT SUM(messages) FROM server_analytics WHERE guild_id = ?", (str(ctx.guild.id),))
            total_msgs = cur.fetchone()[0] or 0

        today_msgs = today_data[0] or 0
        active_users = today_data[1] or 0

        embed = discord.Embed(
            title=f"📊 Server Analytics: {ctx.guild.name}",
            color=MAIN_COLOR,
            timestamp=datetime.now(timezone.utc),
        )
        if ctx.guild.icon:
            embed.set_thumbnail(url=ctx.guild.icon.url)
        embed.add_field(name="💬 Messages Today", value=f"**{today_msgs:,}** msgs", inline=True)
        embed.add_field(name="👥 Active Chatters Today", value=f"**{active_users:,}** members", inline=True)
        embed.add_field(name="📈 All-Time Tracked Messages", value=f"**{total_msgs:,}** msgs", inline=True)
        embed.add_field(name="📁 Total Text Channels", value=f"**{len(ctx.guild.text_channels)}**", inline=True)
        embed.add_field(name="🔊 Total Voice Channels", value=f"**{len(ctx.guild.voice_channels)}**", inline=True)
        embed.add_field(name="🛡️ Total Roles", value=f"**{len(ctx.guild.roles)}**", inline=True)
        await ctx.reply(embed=embed)

    @commands.command(name="top_chatters", description="Leaderboard of today's most active chatters")
    async def top_chatters(self, ctx):
        if not ctx.guild:
            return await ctx.reply("❌ This command must be used in a server.")
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        with sqlite3.connect(DB_FILE) as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT user_id, messages FROM server_analytics WHERE guild_id = ? AND date_str = ? ORDER BY messages DESC LIMIT 10",
                (str(ctx.guild.id), today),
            )
            rows = cur.fetchall()

        if not rows:
            return await ctx.reply("📊 No message activity recorded yet today.")

        lines = []
        medals = ["🥇", "🥈", "🥉"] + [f"`#{i}`" for i in range(4, 11)]
        for i, (uid, count) in enumerate(rows):
            member = ctx.guild.get_member(int(uid))
            name = member.display_name if member else f"User {uid}"
            lines.append(f"{medals[i]} **{name}** — `{count:,}` messages")

        embed = discord.Embed(
            title=f"🏆 Top Chatters Today — {ctx.guild.name}",
            description="\n".join(lines),
            color=SUCCESS_COLOR,
            timestamp=datetime.now(timezone.utc),
        )
        await ctx.reply(embed=embed)

    @commands.command(name="role_distribution", description="View server members count per role")
    async def role_distribution(self, ctx):
        if not ctx.guild:
            return await ctx.reply("❌ Server only.")
        sorted_roles = sorted([r for r in ctx.guild.roles if r.name != "@everyone"], key=lambda r: len(r.members), reverse=True)[:10]
        lines = [f"• {r.mention}: **{len(r.members):,}** members" for r in sorted_roles]
        embed = discord.Embed(
            title=f"🎭 Top 10 Roles by Member Count",
            description="\n".join(lines) if lines else "No custom roles found.",
            color=INFO_COLOR,
        )
        await ctx.reply(embed=embed)

    @commands.command(name="channel_stats", description="Detailed channel statistics for the server")
    async def channel_stats(self, ctx):
        if not ctx.guild:
            return await ctx.reply("❌ Server only.")
        g = ctx.guild
        embed = discord.Embed(title=f"📁 Channel Breakdown: {g.name}", color=MAIN_COLOR)
        embed.add_field(name="💬 Text Channels", value=f"`{len(g.text_channels)}`", inline=True)
        embed.add_field(name="🔊 Voice Channels", value=f"`{len(g.voice_channels)}`", inline=True)
        embed.add_field(name="📢 Announcement Channels", value=f"`{len([c for c in g.text_channels if c.is_news()])}`", inline=True)
        embed.add_field(name="🗂️ Categories", value=f"`{len(g.categories)}`", inline=True)
        embed.add_field(name="🧵 Active Threads", value=f"`{len(g.threads)}`", inline=True)
        embed.add_field(name="🔒 Stage Channels", value=f"`{len(g.stage_channels)}`", inline=True)
        await ctx.reply(embed=embed)

async def setup(bot):
    await bot.add_cog(ServerAnalytics(bot))
