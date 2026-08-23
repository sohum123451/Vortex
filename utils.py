import os
import re
import sqlite3
from datetime import datetime, timedelta, timezone
import discord
from discord.errors import Forbidden

DB_FILE = "bot_database.db"

MAIN_COLOR = discord.Color.blurple()
SUCCESS_COLOR = discord.Color.green()
ERROR_COLOR = discord.Color.red()
WARN_COLOR = discord.Color.gold()
INFO_COLOR = discord.Color.blue()

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def parse_time(time_str: str):
    if not time_str:
        return None
    match = re.match(r"^(\d+)([smhdw])$", time_str.strip().lower())
    if not match:
        return None
    val, unit = match.groups()
    val = int(val)
    if val <= 0:
        return None
    units = {
        "s": timedelta(seconds=val),
        "m": timedelta(minutes=val),
        "h": timedelta(hours=val),
        "d": timedelta(days=val),
        "w": timedelta(weeks=val),
    }
    return units.get(unit)

async def dm_user(user, msg):
    try:
        if isinstance(msg, discord.Embed):
            await user.send(embed=msg)
        else:
            await user.send(msg)
    except Exception:
        pass

async def get_modlog(guild):
    channel = discord.utils.get(guild.text_channels, name="mod-logs")
    if not channel:
        try:
            channel = await guild.create_text_channel("mod-logs")
        except Exception:
            return None
    return channel

async def send_log(ctx, action, target, reason="None", duration=None):
    if not ctx.guild:
        return
    channel = await get_modlog(ctx.guild)
    if not channel:
        return
    embed = discord.Embed(
        title=f"🛡️ {action}",
        color=ERROR_COLOR,
        timestamp=datetime.now(timezone.utc),
    )
    embed.add_field(name="Target", value=f"{target} (`{getattr(target, 'id', target)}`)", inline=False)
    embed.add_field(name="Moderator", value=f"{ctx.author.mention}", inline=False)
    embed.add_field(name="Reason", value=reason, inline=False)
    if duration:
        embed.add_field(name="Duration", value=str(duration), inline=False)
    try:
        await channel.send(embed=embed)
    except Exception:
        pass

def role_guard(ctx, member: discord.Member):
    if member == ctx.guild.owner:
        return "❌ You cannot moderate the server owner."
    if member == ctx.author:
        return "❌ You cannot perform this moderation action on yourself."
    if member == ctx.guild.me:
        return "❌ You cannot moderate me with my own command!"
    if ctx.author.top_role <= member.top_role and ctx.author != ctx.guild.owner:
        return "❌ You cannot moderate someone with an equal or higher role than yourself."
    if ctx.guild.me.top_role <= member.top_role:
        return "❌ I cannot moderate this member because their highest role is equal to or higher than mine."
    return None
