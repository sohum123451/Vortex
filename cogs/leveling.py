import math
import sqlite3
from datetime import datetime, timezone
import discord
from discord.ext import commands
from utils import DB_FILE, MAIN_COLOR, INFO_COLOR, SUCCESS_COLOR, WARN_COLOR

class Leveling(commands.Cog):
    """Server XP, ranks, leveling cards, and leaderboard tracking system."""

    def __init__(self, bot):
        self.bot = bot

    def get_user_xp(self, guild_id: str, user_id: str):
        with sqlite3.connect(DB_FILE) as conn:
            cur = conn.cursor()
            cur.execute("SELECT xp, level, messages FROM levels WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
            row = cur.fetchone()
            if not row:
                cur.execute("INSERT INTO levels (guild_id, user_id, xp, level, messages) VALUES (?, ?, 0, 0, 0)", (guild_id, user_id))
                conn.commit()
                return 0, 0, 0
            return row[0], row[1], row[2]

    @commands.hybrid_command(name="rank", description="Check your or another member's level and XP rank")
    async def rank(self, ctx, member: discord.Member = None):
        target = member or ctx.author
        gid, uid = str(ctx.guild.id), str(target.id)
        xp, level, msgs = self.get_user_xp(gid, uid)
        needed = (level + 1) * 150

        # Rank position
        with sqlite3.connect(DB_FILE) as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM levels WHERE guild_id = ? AND xp > ?", (gid, xp))
            pos = cur.fetchone()[0] + 1

        embed = discord.Embed(
            title=f"📈 {target.display_name}'s Level & Rank",
            color=MAIN_COLOR,
            timestamp=datetime.now(timezone.utc),
        )
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.add_field(name="🏆 Server Rank", value=f"**#{pos}**", inline=True)
        embed.add_field(name="⭐ Level", value=f"`{level}`", inline=True)
        embed.add_field(name="✨ XP", value=f"`{xp:,} / {needed:,}`", inline=True)
        embed.add_field(name="💬 Messages Sent", value=f"`{msgs:,}`", inline=True)

        bar_len = 10
        percent = min(1.0, xp / max(1, needed))
        filled = int(percent * bar_len)
        bar = "🟩" * filled + "⬛" * (bar_len - filled)
        embed.add_field(name="Progress", value=f"{bar} `({int(percent*100)}%)`", inline=False)
        await ctx.reply(embed=embed)

    @commands.hybrid_command(name="levels", description="Top 10 highest level members in this server")
    async def levels_leaderboard(self, ctx):
        with sqlite3.connect(DB_FILE) as conn:
            cur = conn.cursor()
            cur.execute("SELECT user_id, level, xp FROM levels WHERE guild_id = ? ORDER BY xp DESC LIMIT 10", (str(ctx.guild.id),))
            rows = cur.fetchall()

        if not rows:
            return await ctx.reply("📊 No leveling data recorded yet.")

        embed = discord.Embed(title=f"🏆 {ctx.guild.name} Level Leaderboard", color=WARN_COLOR)
        lines = []
        for rank, (uid, lvl, xp) in enumerate(rows, start=1):
            user = ctx.guild.get_member(int(uid)) or f"User ({uid})"
            medal = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else f"**#{rank}**"
            lines.append(f"{medal} {user} — **Lvl {lvl}** (`{xp:,}` XP)")
        embed.description = "\n".join(lines)
        await ctx.reply(embed=embed)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return
        if message.content.startswith(("&", "/")):
            return

        gid = str(message.guild.id)
        uid = str(message.author.id)

        with sqlite3.connect(DB_FILE) as conn:
            cur = conn.cursor()
            cur.execute("SELECT xp, level, messages FROM levels WHERE guild_id = ? AND user_id = ?", (gid, uid))
            row = cur.fetchone()
            if not row:
                cur.execute("INSERT INTO levels (guild_id, user_id, xp, level, messages) VALUES (?, ?, 15, 0, 1)", (gid, uid))
                conn.commit()
            else:
                xp, level, msgs = row
                new_xp = xp + 15
                new_msgs = msgs + 1
                needed = (level + 1) * 150
                new_level = level

                if new_xp >= needed:
                    new_level += 1
                    try:
                        await message.channel.send(
                            f"🎉 **Level Up!** Congratulations {message.author.mention}, you advanced to **Level {new_level}**! ⭐"
                        )
                    except Exception:
                        pass

                cur.execute("UPDATE levels SET xp = ?, level = ?, messages = ? WHERE guild_id = ? AND user_id = ?", (new_xp, new_level, new_msgs, gid, uid))
                conn.commit()

async def setup(bot):
    await bot.add_cog(Leveling(bot))
