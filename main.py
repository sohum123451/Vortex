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
from flask import Flask, jsonify, render_template, request
from utils import DB_FILE, MAIN_COLOR, ERROR_COLOR

load_dotenv()

# ==========================================
# 🌐 FLASK KEEP ALIVE SERVER
# ==========================================
app = Flask("", static_folder="static", template_folder="templates")

@app.route("/")
def home():
    return render_template("dashboard.html")

@app.route("/api/stats")
def get_stats():
    if not bot.is_ready():
        return jsonify({
            "ready": False,
            "guilds": 0,
            "users": 0,
            "ping": 0,
            "uptime": "0h 0m"
        })
    
    uptime_delta = datetime.now(timezone.utc) - bot.start_time
    hours, remainder = divmod(int(uptime_delta.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)
    uptime_str = f"{hours}h {minutes}m {seconds}s"
    
    total_levels_users = 0
    total_coins_in_circulation = 0
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM levels")
            total_levels_users = cur.fetchone()[0]
            cur.execute("SELECT SUM(balance + bank) FROM economy")
            res = cur.fetchone()[0]
            total_coins_in_circulation = res if res else 0
    except Exception:
        pass
        
    return jsonify({
        "ready": True,
        "guilds": len(bot.guilds),
        "users": sum(len(g.members) for g in bot.guilds),
        "ping": int(bot.latency * 1000),
        "uptime": uptime_str,
        "db_records": {
            "levels_users": total_levels_users,
            "coins": total_coins_in_circulation
        }
    })

@app.route("/api/leaderboards")
def get_leaderboards():
    economy_leaderboard = []
    levels_leaderboard = []
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cur = conn.cursor()
            cur.execute("SELECT user_id, balance, bank FROM economy ORDER BY (balance + bank) DESC LIMIT 10")
            for row in cur.fetchall():
                user_id = row[0]
                user = bot.get_user(int(user_id)) if bot.is_ready() else None
                username = user.name if user else f"User {user_id}"
                economy_leaderboard.append({
                    "username": username,
                    "balance": row[1],
                    "bank": row[2],
                    "total": row[1] + row[2]
                })
                
            cur.execute("SELECT user_id, level, xp FROM levels ORDER BY xp DESC LIMIT 10")
            for row in cur.fetchall():
                user_id = row[0]
                user = bot.get_user(int(user_id)) if bot.is_ready() else None
                username = user.name if user else f"User {user_id}"
                levels_leaderboard.append({
                    "username": username,
                    "level": row[1],
                    "xp": row[2]
                })
    except Exception as e:
        print(f"Error reading leaderboards for API: {e}")
        
    return jsonify({
        "economy": economy_leaderboard,
        "levels": levels_leaderboard
    })

@app.route("/api/music/state")
def get_music_state():
    if not bot.is_ready():
        return jsonify({"guilds": []})
        
    music_cog = bot.get_cog("Music")
    if not music_cog:
        return jsonify({"guilds": []})
        
    result = []
    for guild_id, state in music_cog.states.items():
        guild = bot.get_guild(guild_id)
        if not guild:
            continue
            
        current_track = None
        if state.current:
            current_track = {
                "title": state.current.title,
                "url": state.current.webpage_url,
                "uploader": state.current.uploader,
                "duration": state.current.duration
            }
            
        queue = []
        for s in state.queue:
            queue.append({
                "title": s.title,
                "duration": s.duration
            })
            
        vc = guild.voice_client
        is_playing = vc.is_playing() if vc else False
        is_paused = vc.is_paused() if vc else False
        
        result.append({
            "guild_id": str(guild_id),
            "guild_name": guild.name,
            "active": vc is not None,
            "is_playing": is_playing,
            "is_paused": is_paused,
            "volume": int(state.volume * 100),
            "current": current_track,
            "queue": queue
        })
        
    return jsonify({"guilds": result})

@app.route("/api/music/control", methods=["POST"])
def control_music():
    if not bot.is_ready():
        return jsonify({"error": "Bot is not ready"}), 400
        
    data = request.json or {}
    guild_id_str = data.get("guild_id")
    action = data.get("action")
    
    if not guild_id_str or not action:
        return jsonify({"error": "Missing guild_id or action"}), 400
        
    try:
        guild_id = int(guild_id_str)
    except ValueError:
        return jsonify({"error": "Invalid guild_id"}), 400
        
    guild = bot.get_guild(guild_id)
    if not guild:
        return jsonify({"error": "Guild not found"}), 404
        
    music_cog = bot.get_cog("Music")
    if not music_cog:
        return jsonify({"error": "Music cog not loaded"}), 500
        
    state = music_cog.get_state(guild_id)
    vc = guild.voice_client
    
    if action == "pause":
        if vc and vc.is_playing():
            vc.pause()
            return jsonify({"status": "paused"})
        return jsonify({"error": "Not playing"}), 400
        
    elif action == "resume":
        if vc and vc.is_paused():
            vc.resume()
            return jsonify({"status": "resumed"})
        return jsonify({"error": "Not paused"}), 400
        
    elif action == "skip":
        if vc and (vc.is_playing() or vc.is_paused()):
            vc.stop()
            return jsonify({"status": "skipped"})
        return jsonify({"error": "Nothing to skip"}), 400
        
    elif action == "volume":
        vol_val = data.get("value")
        if vol_val is None:
            return jsonify({"error": "Missing volume value"}), 400
        try:
            vol = int(vol_val)
            if not 1 <= vol <= 100:
                raise ValueError()
        except ValueError:
            return jsonify({"error": "Volume must be 1-100"}), 400
            
        state.volume = vol / 100
        if vc and vc.source:
            vc.source.volume = state.volume
        return jsonify({"status": "volume_set", "value": vol})
        
    return jsonify({"error": "Invalid action"}), 400

@app.route("/api/moderation")
def get_moderation_data():
    warnings = []
    tempbans = []
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cur = conn.cursor()
            cur.execute("SELECT id, guild_id, user_id, reason, timestamp FROM warnings ORDER BY id DESC LIMIT 50")
            for row in cur.fetchall():
                user_id = row[2]
                user = bot.get_user(int(user_id)) if bot.is_ready() else None
                username = user.name if user else f"User {user_id}"
                warnings.append({
                    "id": row[0],
                    "guild_id": row[1],
                    "user_id": user_id,
                    "username": username,
                    "reason": row[3],
                    "timestamp": row[4]
                })
            cur.execute("SELECT user_id, guild_id, unban_time FROM tempbans")
            for row in cur.fetchall():
                user_id = row[0]
                user = bot.get_user(int(user_id)) if bot.is_ready() else None
                username = user.name if user else f"User {user_id}"
                tempbans.append({
                    "user_id": user_id,
                    "username": username,
                    "guild_id": row[1],
                    "unban_time": row[2]
                })
    except Exception as e:
        print(f"Error fetching moderation data: {e}")
        
    return jsonify({
        "warnings": warnings,
        "tempbans": tempbans
    })

@app.route("/api/rpg/players")
def get_rpg_players():
    players = []
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT user_id, class_type, level, xp, hp, max_hp, attack, defense, coins, equipped_weapon, equipped_armor, dungeon_floor 
                FROM rpg_players 
                ORDER BY level DESC, xp DESC 
                LIMIT 15
            """)
            for row in cur.fetchall():
                user_id = row[0]
                user = bot.get_user(int(user_id)) if bot.is_ready() else None
                username = user.name if user else f"User {user_id}"
                players.append({
                    "user_id": user_id,
                    "username": username,
                    "class": row[1],
                    "level": row[2],
                    "xp": row[3],
                    "hp": f"{row[4]}/{row[5]}",
                    "attack": row[6],
                    "defense": row[7],
                    "coins": row[8],
                    "weapon": row[9],
                    "armor": row[10],
                    "floor": row[11]
                })
    except Exception as e:
        print(f"Error fetching RPG players: {e}")
        
    return jsonify({"players": players})

@app.route("/api/features/active")
def get_active_features():
    giveaways = []
    custom_tags = []
    autoresponders = []
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cur = conn.cursor()
            cur.execute("SELECT message_id, channel_id, end_time, winners, prize, host_id FROM giveaways")
            for row in cur.fetchall():
                host_id = row[5]
                host = bot.get_user(int(host_id)) if bot.is_ready() else None
                hostname = host.name if host else f"User {host_id}"
                
                is_active = row[2] > datetime.now().timestamp()
                giveaways.append({
                    "message_id": row[0],
                    "channel_id": row[1],
                    "end_time": row[2],
                    "winners": row[3],
                    "prize": row[4],
                    "host": hostname,
                    "is_active": is_active
                })
                
            cur.execute("SELECT guild_id, tag_name, author_id, uses FROM custom_tags")
            for row in cur.fetchall():
                author_id = row[2]
                author = bot.get_user(int(author_id)) if bot.is_ready() else None
                author_name = author.name if author else f"User {author_id}"
                custom_tags.append({
                    "guild_id": row[0],
                    "tag_name": row[1],
                    "author": author_name,
                    "uses": row[3]
                })
                
            cur.execute("SELECT guild_id, trigger_text, response_text, is_exact FROM autoresponders")
            for row in cur.fetchall():
                autoresponders.append({
                    "guild_id": row[0],
                    "trigger": row[1],
                    "response": row[2],
                    "is_exact": bool(row[3])
                })
    except Exception as e:
        print(f"Error fetching active features: {e}")
        
    return jsonify({
        "giveaways": giveaways,
        "custom_tags": custom_tags,
        "autoresponders": autoresponders
    })

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
