import asyncio
import os
import sys
import sqlite3
from datetime import datetime, timezone
from threading import Thread

# Ensure Windows terminal handles UTF-8 emojis cleanly
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import discord
from discord.ext import commands
from dotenv import load_dotenv
from flask import Flask
from utils import DB_FILE, MAIN_COLOR, ERROR_COLOR

load_dotenv()

# ==========================================
# 🌐 FLASK KEEP ALIVE SERVER
# ==========================================
app = Flask("")

@app.route("/")
def home():
    return "⚡ Vortex Discord Bot is running & fully operational!"

def run():
    app.run(host="0.0.0.0", port=8080)

def keep_alive():
    t = Thread(target=run, daemon=True)
    t.start()

# ==========================================
# 🗄️ SQLITE DATABASE INITIALIZATION
# ==========================================
def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS warnings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                reason TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS tempbans (
                user_id TEXT PRIMARY KEY,
                guild_id TEXT NOT NULL,
                unban_time TEXT NOT NULL
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS giveaways (
                message_id TEXT PRIMARY KEY,
                channel_id TEXT NOT NULL,
                end_time REAL NOT NULL,
                winners INTEGER NOT NULL,
                prize TEXT NOT NULL,
                host_id TEXT NOT NULL,
                rigged_id TEXT
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS economy (
                user_id TEXT PRIMARY KEY,
                balance INTEGER DEFAULT 0,
                bank INTEGER DEFAULT 0,
                daily_streak INTEGER DEFAULT 0,
                last_daily TEXT,
                last_weekly TEXT,
                last_work TEXT,
                last_crime TEXT,
                inventory TEXT DEFAULT '{}'
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS afk (
                user_id TEXT PRIMARY KEY,
                reason TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sticky (
                channel_id TEXT PRIMARY KEY,
                message_text TEXT NOT NULL,
                last_msg_id TEXT
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                channel_id TEXT NOT NULL,
                reminder_text TEXT NOT NULL,
                remind_time REAL NOT NULL
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS levels (
                guild_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                xp INTEGER DEFAULT 0,
                level INTEGER DEFAULT 0,
                messages INTEGER DEFAULT 0,
                PRIMARY KEY (guild_id, user_id)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS rpg_players (
                user_id TEXT PRIMARY KEY,
                class_type TEXT DEFAULT 'Warrior',
                level INTEGER DEFAULT 1,
                xp INTEGER DEFAULT 0,
                hp INTEGER DEFAULT 100,
                max_hp INTEGER DEFAULT 100,
                attack INTEGER DEFAULT 15,
                defense INTEGER DEFAULT 10,
                coins INTEGER DEFAULT 100,
                equipped_weapon TEXT DEFAULT 'Wooden Sword',
                equipped_armor TEXT DEFAULT 'Cloth Tunic',
                pet TEXT DEFAULT 'None',
                dungeon_floor INTEGER DEFAULT 1
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS rpg_inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                item_name TEXT NOT NULL,
                item_type TEXT NOT NULL,
                quantity INTEGER DEFAULT 1,
                power INTEGER DEFAULT 0
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS custom_tags (
                guild_id TEXT NOT NULL,
                tag_name TEXT NOT NULL,
                content TEXT NOT NULL,
                author_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                uses INTEGER DEFAULT 0,
                PRIMARY KEY (guild_id, tag_name)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS autoresponders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id TEXT NOT NULL,
                trigger_text TEXT NOT NULL,
                response_text TEXT NOT NULL,
                is_exact INTEGER DEFAULT 0
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS crypto_portfolio (
                user_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                amount REAL NOT NULL,
                buy_price REAL NOT NULL,
                PRIMARY KEY (user_id, symbol)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS server_analytics (
                guild_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                date_str TEXT NOT NULL,
                messages INTEGER DEFAULT 0,
                PRIMARY KEY (guild_id, user_id, date_str)
            )
        """)

        # Auto-migrate missing columns for existing economy table
        cur.execute("PRAGMA table_info(economy)")
        existing_cols = [row[1] for row in cur.fetchall()]
        cols_to_add = [
            ("daily_streak", "INTEGER DEFAULT 0"),
            ("last_daily", "TEXT"),
            ("last_weekly", "TEXT"),
            ("last_work", "TEXT"),
            ("last_crime", "TEXT"),
            ("inventory", "TEXT DEFAULT '{}'"),
        ]
        for col_name, col_def in cols_to_add:
            if col_name not in existing_cols:
                try:
                    cur.execute(f"ALTER TABLE economy ADD COLUMN {col_name} {col_def}")
                except Exception:
                    pass

        conn.commit()

init_db()

# ==========================================
# 🚨 GLOBAL ERROR HANDLER
# ==========================================
class ErrorHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        # Unwrap CommandInvokeError
        orig_error = getattr(error, 'original', error)

        if isinstance(error, commands.CommandNotFound):
            return

        if isinstance(error, commands.NotOwner):
            return await ctx.reply("🔒 **Restricted:** This command is exclusive to the Bot Owner.")

        if isinstance(error, commands.CommandOnCooldown):
            mins, secs = divmod(int(error.retry_after), 60)
            hours, mins = divmod(mins, 60)
            time_fmt = f"{hours}h {mins}m {secs}s" if hours else f"{mins}m {secs}s" if mins else f"{secs}s"
            return await ctx.reply(f"⏳ **Cooldown:** Please wait `{time_fmt}` before reusing this command.")

        if isinstance(error, commands.MissingPermissions):
            perms = ", ".join(f"`{p}`" for p in error.missing_permissions)
            return await ctx.reply(f"❌ **Permission Denied:** You require {perms} permission.")

        if isinstance(error, commands.BotMissingPermissions):
            perms = ", ".join(f"`{p}`" for p in error.missing_permissions)
            return await ctx.reply(f"⚠️ **Bot Missing Permissions:** I require {perms} permission in this channel.")

        if isinstance(error, commands.MemberNotFound):
            return await ctx.reply("❌ **Member Not Found:** Please mention a valid server member.")

        if isinstance(error, commands.ChannelNotFound):
            return await ctx.reply("❌ **Channel Not Found:** Please mention a valid channel.")

        if isinstance(error, commands.RoleNotFound):
            return await ctx.reply("❌ **Role Not Found:** Please specify a valid role.")

        if isinstance(error, commands.MissingRequiredArgument):
            cmd_name = ctx.command.qualified_name if ctx.command else "command"
            return await ctx.reply(f"❌ **Missing Argument:** `{error.param.name}` is required. Type `&help {cmd_name}` for usage details.")

        if isinstance(error, commands.BadArgument):
            return await ctx.reply(f"❌ **Invalid Argument:** {error}")

        print(f"Unhandled Error in {ctx.command}: {orig_error}", flush=True)
        try:
            err_msg = str(orig_error)
            await ctx.reply(f"⚠️ **Command Notice:** `{err_msg[:300]}`")
        except Exception:
            pass

# ==========================================
# 🤖 BOT SETUP & COG AUTO-LOADER
# ==========================================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

class VortexBot(commands.Bot):
    async def setup_hook(self):
        self.start_time = datetime.now(timezone.utc)
        
        # Load developer extension if available
        try:
            await self.load_extension("jishaku")
        except Exception:
            pass

        # Global Error Handler
        await self.add_cog(ErrorHandler(self))

        # Dynamically load all Cogs in cogs/ directory
        cogs_dir = os.path.join(os.path.dirname(__file__), "cogs")
        loaded = []
        for filename in os.listdir(cogs_dir):
            if filename.endswith(".py") and not filename.startswith("__"):
                extension_name = f"cogs.{filename[:-3]}"
                try:
                    await self.load_extension(extension_name)
                    loaded.append(filename[:-3])
                except Exception as e:
                    print(f"❌ Failed to load cog {extension_name}: {e}", flush=True)

        print(f"🧩 Loaded {len(loaded)} Cogs: {', '.join(loaded)}", flush=True)
        
        # Sync hybrid slash commands with Discord
        try:
            synced = await self.tree.sync()
            print(f"✅ Synced {len(synced)} Slash Commands globally.", flush=True)
        except Exception as e:
            print(f"⚠️ Slash command sync warning: {e}", flush=True)

bot = VortexBot(
    command_prefix=commands.when_mentioned_or("&"),
    intents=intents,
    help_command=None,
)

@bot.event
async def on_ready():
    print(f"🌟 Vortex Bot logged in as {bot.user} (ID: {bot.user.id})", flush=True)
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="Under Sohum's Development ⚡",
        )
    )

if __name__ == "__main__":
    keep_alive()
    DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
    if not DISCORD_TOKEN:
        print("❌ DISCORD_TOKEN environment variable not found.")
    else:
        bot.run(DISCORD_TOKEN)
