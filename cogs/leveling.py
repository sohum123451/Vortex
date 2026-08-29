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
    """High-performance server XP, ranks, level-up message customization, and leaderboard tracking system."""

    def __init__(self, bot):
        self.bot = bot
        # In-memory fast cache: {(guild_id, user_id): [xp, level, messages, dirty_flag]}
        self.cache = {}
        # Server config cache: {guild_id: [channel_id, custom_msg, is_enabled]}
        self.config_cache = {}
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

        self.cache[key] = [0, 0, 0, True]
        return 0, 0, 0

    def get_guild_config(self, guild_id: str):
        if guild_id in self.config_cache:
            return self.config_cache[guild_id]

        default_msg = "🎉 **Level Up!** Congratulations {user}, you reached **Level {level}**! ⭐"
        try:
            with sqlite3.connect(DB_FILE) as conn:
                cur = conn.cursor()
                cur.execute("SELECT channel_id, custom_msg, is_enabled FROM level_config WHERE guild_id = ?", (guild_id,))
                row = cur.fetchone()
                if row:
                    config = [row[0] or "current", row[1] or default_msg, int(row[2] if row[2] is not None else 1)]
                    self.config_cache[guild_id] = config
                    return config
        except Exception:
            pass

        config = ["current", default_msg, 1]
        self.config_cache[guild_id] = config
        return config

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

    # ==========================================
    # ⚙️ LEVEL UP SETUP & CONFIGURATION COMMANDS
    # ==========================================

    @commands.hybrid_command(name="level_channel", description="Set channel for level-up announcements (current, dm, disabled, or #channel)")
    @commands.has_permissions(manage_guild=True)
    async def level_channel(self, ctx, target: str):
        gid = str(ctx.guild.id)
        config = self.get_guild_config(gid)

        t_clean = target.strip().lower()
        channel_id = "current"

        if t_clean in ["current", "same"]:
            channel_id = "current"
            msg = "💬 Level-up announcements will be sent in the **current channel** where members chat."
        elif t_clean in ["dm", "direct", "dms"]:
            channel_id = "dm"
            msg = "📬 Level-up announcements will be sent via **Direct Message (DM)** to the member."
        elif t_clean in ["disabled", "off", "none"]:
            channel_id = "disabled"
            config[2] = 0
            msg = "🔕 Level-up announcements are now **disabled** for this server."
        elif ctx.message.channel_mentions:
            chan = ctx.message.channel_mentions[0]
            channel_id = str(chan.id)
            msg = f"📢 Level-up announcements will now be sent in {chan.mention}."
        elif target.isdigit():
            chan = ctx.guild.get_channel(int(target))
            if chan:
                channel_id = str(chan.id)
                msg = f"📢 Level-up announcements will now be sent in {chan.mention}."
            else:
                return await ctx.reply("❌ Invalid channel ID provided.")
        else:
            return await ctx.reply("❌ Choose `current`, `dm`, `disabled`, or mention a `#channel`.")

        config[0] = channel_id
        if channel_id != "disabled":
            config[2] = 1

        self.config_cache[gid] = config
        with sqlite3.connect(DB_FILE) as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT OR REPLACE INTO level_config (guild_id, channel_id, custom_msg, is_enabled) VALUES (?, ?, ?, ?)",
                (gid, config[0], config[1], config[2])
            )
            conn.commit()

        await ctx.reply(msg)

    @commands.hybrid_command(name="level_msg", description="Set custom level-up message ({user}, {level}, {xp}, {server})")
    @commands.has_permissions(manage_guild=True)
    async def level_msg(self, ctx, *, template: str):
        gid = str(ctx.guild.id)
        config = self.get_guild_config(gid)
        config[1] = template

        self.config_cache[gid] = config
        with sqlite3.connect(DB_FILE) as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT OR REPLACE INTO level_config (guild_id, channel_id, custom_msg, is_enabled) VALUES (?, ?, ?, ?)",
                (gid, config[0], config[1], config[2])
            )
            conn.commit()

        sample = template.replace("{user}", ctx.author.mention).replace("{level}", "5").replace("{xp}", "1,450").replace("{server}", ctx.guild.name)
        embed = discord.Embed(
            title="✅ Custom Level-Up Message Saved",
            description=f"**Template:** `{template}`\n\n**Preview:**\n{sample}",
            color=SUCCESS_COLOR
        )
        await ctx.reply(embed=embed)

    @commands.hybrid_command(name="level_toggle", description="Toggle level-up announcements on or off")
    @commands.has_permissions(manage_guild=True)
    async def level_toggle(self, ctx):
        gid = str(ctx.guild.id)
        config = self.get_guild_config(gid)
        config[2] = 0 if config[2] == 1 else 1

        self.config_cache[gid] = config
        with sqlite3.connect(DB_FILE) as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT OR REPLACE INTO level_config (guild_id, channel_id, custom_msg, is_enabled) VALUES (?, ?, ?, ?)",
                (gid, config[0], config[1], config[2])
            )
            conn.commit()

        state = "Enabled 🔔" if config[2] == 1 else "Disabled 🔕"
        await ctx.reply(f"⭐ Server level-up announcements are now **{state}**.")

    @commands.hybrid_command(name="level_setup", description="View current server level-up configuration")
    async def level_setup(self, ctx):
        gid = str(ctx.guild.id)
        config = self.get_guild_config(gid)
        chan_setting, template, is_enabled = config

        if chan_setting == "current":
            chan_str = "Current Chat Channel"
        elif chan_setting == "dm":
            chan_str = "Direct Message (DM)"
        elif chan_setting == "disabled":
            chan_str = "Disabled"
        else:
            c = ctx.guild.get_channel(int(chan_setting))
            chan_str = c.mention if c else f"Channel ID `{chan_setting}`"

        status_str = "Enabled 🔔" if is_enabled == 1 else "Disabled 🔕"

        embed = discord.Embed(
            title=f"⚙️ Leveling Setup — {ctx.guild.name}",
            color=MAIN_COLOR,
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name="📢 Announcement Channel", value=chan_str, inline=True)
        embed.add_field(name="🔔 Status", value=status_str, inline=True)
        embed.add_field(name="💬 Message Template", value=f"`{template}`", inline=False)
        embed.add_field(name="💡 Customization Commands", value="`&level_channel <#chan|dm|disabled>`\n`&level_msg <template>`\n`&level_toggle`", inline=False)
        await ctx.reply(embed=embed)

    # Listener
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
        leveled_up = new_level > current_lvl
        self.cache[key] = [new_xp, new_level, new_msgs, True]

        if leveled_up:
            config = self.get_guild_config(gid)
            chan_setting, template, is_enabled = config
            
            if is_enabled == 1 and chan_setting != "disabled":
                formatted_msg = template.replace("{user}", message.author.mention)\
                                        .replace("{level}", str(new_level))\
                                        .replace("{xp}", f"{new_xp:,}")\
                                        .replace("{server}", message.guild.name)
                try:
                    if chan_setting == "dm":
                        await message.author.send(formatted_msg)
                    elif chan_setting == "current":
                        await message.channel.send(formatted_msg)
                    else:
                        target_chan = message.guild.get_channel(int(chan_setting))
                        if target_chan:
                            await target_chan.send(formatted_msg)
                        else:
                            await message.channel.send(formatted_msg)
                except Exception:
                    pass

async def setup(bot):
    await bot.add_cog(Leveling(bot))
