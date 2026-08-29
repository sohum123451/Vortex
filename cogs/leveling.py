import asyncio
import time
import math
import sqlite3
from datetime import datetime, timezone
import discord
from discord.ext import commands, tasks
from utils import DB_FILE, MAIN_COLOR, INFO_COLOR, SUCCESS_COLOR, WARN_COLOR

def xp_for_level(lvl: int) -> int:
    """XP threshold needed to reach a given level."""
    return int(50 * (lvl ** 2) + 50 * lvl)

def calculate_level(total_xp: int) -> int:
    """Calculate the exact level from cumulative XP."""
    lvl = 0
    while total_xp >= xp_for_level(lvl + 1):
        lvl += 1
    return lvl

class Leveling(commands.Cog):
    """High-performance server XP, ranks, leveling cards, and leaderboard tracking system."""

    def __init__(self, bot):
        self.bot = bot
        # In-memory fast cache: {(guild_id, user_id): [xp, level, messages, dirty_flag]}
        self.cache = {}
        # Cooldown: {(guild_id, user_id): last_xp_timestamp} (60s cooldown)
        self.cooldowns = {}
        # Start background database sync loop
        self.flush_loop.start()

    def cog_unload(self):
        self.flush_loop.cancel()
        self.flush_cache_sync()

    def get_user_data(self, guild_id: str, user_id: str):
        key = (guild_id, user_id)
        if key in self.cache:
            return self.cache[key][0], self.cache[key][1], self.cache[key][2]
        
        # Load from DB on cache miss
        try:
            with sqlite3.connect(DB_FILE) as conn:
                cur = conn.cursor()
                cur.execute("SELECT xp, level, messages FROM levels WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
                row = cur.fetchone()
                if row:
                    xp = int(row[0] or 0)
                    lvl = int(row[1] or 0)
                    msgs = int(row[2] or 0)
                    self.cache[key] = [xp, lvl, msgs, False]
                    return xp, lvl, msgs
        except Exception as e:
            print(f"[Leveling] Cache miss read error: {e}", flush=True)

        # Default for new user
        self.cache[key] = [0, 0, 0, True]
        return 0, 0, 0

    def flush_cache_sync(self):
        """Flushes modified user XP records to Turso / SQLite."""
        dirty_items = [(k, v) for k, v in self.cache.items() if v[3]]
        if not dirty_items:
            return

        try:
            with sqlite3.connect(DB_FILE) as conn:
                cur = conn.cursor()
                for (gid, uid), data in dirty_items:
                    xp, lvl, msgs, _ = data
                    cur.execute(
                        "INSERT OR REPLACE INTO levels (guild_id, user_id, xp, level, messages) VALUES (?, ?, ?, ?, ?)",
                        (gid, uid, xp, lvl, msgs)
                    )
                    data[3] = False
                conn.commit()
        except Exception as e:
            print(f"[Leveling] Background flush error: {e}", flush=True)

    @tasks.loop(seconds=15)
    async def flush_loop(self):
        """Periodically sync in-memory leveling data to Turso cloud in background thread."""
        await asyncio.to_thread(self.flush_cache_sync)

    @flush_loop.before_loop
    async def before_flush_loop(self):
        await self.bot.wait_until_ready()

    @commands.hybrid_command(name="rank", description="Check your or another member's level and XP rank")
    async def rank(self, ctx, member: discord.Member = None):
        target = member or ctx.author
        gid, uid = str(ctx.guild.id), str(target.id)
        xp, level, msgs = self.get_user_data(gid, uid)
        
        current_lvl_xp = xp_for_level(level)
        next_lvl_xp = xp_for_level(level + 1)
        needed = next_lvl_xp - current_lvl_xp
        progress_xp = max(0, xp - current_lvl_xp)

        # Query rank position
        try:
            with sqlite3.connect(DB_FILE) as conn:
                cur = conn.cursor()
                cur.execute("SELECT COUNT(*) FROM levels WHERE guild_id = ? AND xp > ?", (gid, xp))
                row = cur.fetchone()
                pos = (row[0] if row else 0) + 1
        except Exception:
            pos = 1

        embed = discord.Embed(
            title=f"📈 {target.display_name}'s Level & Rank",
            color=MAIN_COLOR,
            timestamp=datetime.now(timezone.utc),
        )
        if target.display_avatar:
            embed.set_thumbnail(url=target.display_avatar.url)
        embed.add_field(name="🏆 Server Rank", value=f"**#{pos}**", inline=True)
        embed.add_field(name="⭐ Level", value=f"**{level}**", inline=True)
        embed.add_field(name="✨ Total XP", value=f"`{xp:,}` XP", inline=True)
        embed.add_field(name="💬 Messages Sent", value=f"`{msgs:,}`", inline=True)

        bar_len = 10
        percent = min(1.0, max(0.0, progress_xp / max(1, needed)))
        filled = int(percent * bar_len)
        bar = "🟩" * filled + "⬛" * (bar_len - filled)
        embed.add_field(name=f"Level {level + 1} Progress (`{progress_xp}/{needed}` XP)", value=f"{bar} `({int(percent*100)}%)`", inline=False)
        await ctx.reply(embed=embed)

    @commands.hybrid_command(name="levels", description="Top 10 highest level members in this server")
    async def levels_leaderboard(self, ctx):
        # Flush first to ensure fresh leaderboard
        await asyncio.to_thread(self.flush_cache_sync)
        try:
            with sqlite3.connect(DB_FILE) as conn:
                cur = conn.cursor()
                cur.execute("SELECT user_id, level, xp FROM levels WHERE guild_id = ? ORDER BY xp DESC LIMIT 10", (str(ctx.guild.id),))
                rows = cur.fetchall()
        except Exception as e:
            return await ctx.reply(f"❌ Error loading leaderboard: {e}")

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
        now = time.time()
        key = (gid, uid)

        # 60s cooldown per user to prevent spam and lag
        last_xp_time = self.cooldowns.get(key, 0)
        should_add_xp = (now - last_xp_time) >= 60

        # Retrieve current in-memory values instantly (0.001ms)
        if key not in self.cache:
            self.get_user_data(gid, uid)
            
        data = self.cache.get(key, [0, 0, 0, True])
        current_xp, current_lvl, current_msgs, _ = data
        
        new_msgs = current_msgs + 1
        new_xp = current_xp
        
        if should_add_xp:
            import random
            earned_xp = random.randint(15, 25)
            new_xp += earned_xp
            self.cooldowns[key] = now
            
        new_level = calculate_level(new_xp)
        
        # Check for legitimate level up
        leveled_up = new_level > current_lvl
        
        # Update cache in memory
        self.cache[key] = [new_xp, new_level, new_msgs, True]

        if leveled_up:
            try:
                await message.channel.send(
                    f"🎉 **Level Up!** Congratulations {message.author.mention}, you advanced to **Level {new_level}**! ⭐"
                )
            except Exception:
                pass

async def setup(bot):
    await bot.add_cog(Leveling(bot))
