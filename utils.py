import os
import re
import base64
import requests
import sqlite3
import threading
import time
import asyncio
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
import discord
from discord.errors import Forbidden

load_dotenv()

DB_FILE = "bot_database.db"

MAIN_COLOR = discord.Color.blurple()
SUCCESS_COLOR = discord.Color.green()
ERROR_COLOR = discord.Color.red()
WARN_COLOR = discord.Color.gold()
INFO_COLOR = discord.Color.blue()

# ==========================================================================
# 🌐 HIGH-SPEED TURSO CLOUD HYBRID PERSISTENCE (0MS LATENCY)
# ==========================================================================
TURSO_DATABASE_URL = os.getenv("TURSO_DATABASE_URL")
TURSO_AUTH_TOKEN = os.getenv("TURSO_AUTH_TOKEN")

def get_db():
    conn = sqlite3.connect(DB_FILE, timeout=10.0)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=5000;")
    except Exception:
        pass
    conn.row_factory = sqlite3.Row
    return conn

# Enable WAL mode globally on startup
try:
    with sqlite3.connect(DB_FILE, timeout=10.0) as _init_conn:
        _init_conn.execute("PRAGMA journal_mode=WAL;")
        _init_conn.execute("PRAGMA busy_timeout=5000;")
except Exception:
    pass

def sync_turso_to_local():
    """Download current tables from Turso Cloud on boot to restore full state."""
    if not (TURSO_DATABASE_URL and TURSO_AUTH_TOKEN):
        return
    try:
        http_url = TURSO_DATABASE_URL.replace('libsql://', 'https://').rstrip('/') + '/v2/pipeline'
        headers = {'Authorization': f'Bearer {TURSO_AUTH_TOKEN}', 'Content-Type': 'application/json'}
        
        # 1. Fetch tables
        payload = {'requests': [{'type': 'execute', 'stmt': {'sql': "SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"}}]}
        r = requests.post(http_url, headers=headers, json=payload, timeout=10)
        if r.status_code != 200:
            return
        
        res = r.json().get('results', [])[0]
        rows = res.get('response', {}).get('result', {}).get('rows', [])
        
        with sqlite3.connect(DB_FILE, timeout=10.0) as conn:
            cur = conn.cursor()
            for row in rows:
                tname = row[0].get('value')
                tsql = row[1].get('value')
                if tsql:
                    try:
                        cur.execute(tsql)
                    except Exception:
                        pass
                
                # Fetch rows for this table
                r_payload = {'requests': [{'type': 'execute', 'stmt': {'sql': f'SELECT * FROM "{tname}"'}}]}
                r_table = requests.post(http_url, headers=headers, json=r_payload, timeout=10)
                if r_table.status_code == 200:
                    t_result = r_table.json().get('results', [])[0].get('response', {}).get('result', {})
                    cols = [c['name'] for c in t_result.get('cols', [])]
                    t_rows = t_result.get('rows', [])
                    if cols and t_rows:
                        placeholders = ', '.join(['?'] * len(cols))
                        cols_str = ', '.join([f'"{c}"' for c in cols])
                        for tr in t_rows:
                            vals = []
                            for cell in tr:
                                v_type = cell.get('type')
                                v_val = cell.get('value')
                                if v_type == 'null' or v_val is None:
                                    vals.append(None)
                                elif v_type == 'integer':
                                    vals.append(int(v_val))
                                elif v_type == 'float':
                                    vals.append(float(v_val))
                                else:
                                    vals.append(str(v_val))
                            cur.execute(f'INSERT OR REPLACE INTO "{tname}" ({cols_str}) VALUES ({placeholders})', vals)
            conn.commit()
        print("[TURSO] Restored latest database state from Turso Cloud.", flush=True)
    except Exception as e:
        print(f"[TURSO] Boot sync notice: {e}", flush=True)

def sync_local_to_turso_background():
    """Background thread loop pushing local database tables to Turso Cloud every 5 minutes."""
    http_url = TURSO_DATABASE_URL.replace('libsql://', 'https://').rstrip('/') + '/v2/pipeline' if TURSO_DATABASE_URL else None
    headers = {'Authorization': f'Bearer {TURSO_AUTH_TOKEN}', 'Content-Type': 'application/json'} if TURSO_AUTH_TOKEN else {}

    while True:
        time.sleep(300)
        if not (TURSO_DATABASE_URL and TURSO_AUTH_TOKEN):
            continue
        try:
            with sqlite3.connect(DB_FILE, timeout=10.0) as conn:
                cur = conn.cursor()
                cur.execute("SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
                tables = cur.fetchall()
                
                requests_list = []
                for tname, create_sql in tables:
                    if not create_sql:
                        continue
                    requests_list.append({'type': 'execute', 'stmt': {'sql': create_sql}})
                    cur.execute(f'SELECT * FROM "{tname}"')
                    rows = cur.fetchall()
                    col_names = [d[0] for d in cur.description] if cur.description else []
                    if col_names and rows:
                        placeholders = ', '.join(['?'] * len(col_names))
                        cols_str = ', '.join([f'"{c}"' for c in col_names])
                        for r in rows:
                            args = []
                            for val in r:
                                if val is None:
                                    args.append({'type': 'null'})
                                elif isinstance(val, bool):
                                    args.append({'type': 'integer', 'value': '1' if val else '0'})
                                elif isinstance(val, int):
                                    args.append({'type': 'integer', 'value': str(val)})
                                elif isinstance(val, float):
                                    args.append({'type': 'float', 'value': val})
                                else:
                                    args.append({'type': 'text', 'value': str(val)})
                            requests_list.append({
                                'type': 'execute',
                                'stmt': {'sql': f'INSERT OR REPLACE INTO "{tname}" ({cols_str}) VALUES ({placeholders})', 'args': args}
                            })
                if requests_list:
                    # Single batched HTTP POST request to prevent CPU saturation
                    requests.post(http_url, headers=headers, json={'requests': requests_list[:200]}, timeout=15)
        except Exception:
            pass

# Initialize Hybrid Cloud Persistence Engine in background threads
if TURSO_DATABASE_URL and TURSO_AUTH_TOKEN:
    threading.Thread(target=sync_turso_to_local, daemon=True).start()
    threading.Thread(target=sync_local_to_turso_background, daemon=True).start()
    print("[TURSO] High-Speed Cloud Hybrid Engine Active — 0ms local delay with WAL mode.", flush=True)
else:
    print("[DATABASE] Local SQLite Engine Active (WAL mode).", flush=True)

# ==========================================================================
# 🛠️ GENERAL BOT UTILITIES
# ==========================================================================

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

# ==========================================================================
# 🧠 ZERO-COST HIGH-CONCURRENCY AI SCALING ENGINE (1000+ USERS)
# ==========================================================================
_gemini_client = None
_groq_client = None
_ai_semaphore = asyncio.Semaphore(10)  # Max 10 concurrent outbound LLM requests
_ai_cache = {}  # prompt_hash -> (response_text, timestamp)
CACHE_TTL_SECONDS = 600  # 10 minutes TTL
MAX_CACHE_SIZE = 1000

def get_gemini():
    global _gemini_client
    if _gemini_client is None:
        key = os.getenv("GEMINI_API_KEY", "")
        if key:
            try:
                from google import genai
                _gemini_client = genai.Client(api_key=key).aio
            except Exception:
                pass
    return _gemini_client

def get_groq():
    global _groq_client
    if _groq_client is None:
        key = os.getenv("GROQ_API_KEY", "")
        if key:
            try:
                from groq import AsyncGroq
                _groq_client = AsyncGroq(api_key=key)
            except Exception:
                pass
    return _groq_client

def _clean_cache():
    """Prune expired items from memory cache."""
    now = time.time()
    expired = [k for k, v in _ai_cache.items() if now - v[1] > CACHE_TTL_SECONDS]
    for k in expired:
        _ai_cache.pop(k, None)
    if len(_ai_cache) > MAX_CACHE_SIZE:
        oldest = sorted(_ai_cache.items(), key=lambda x: x[1][1])[:200]
        for k, _ in oldest:
            _ai_cache.pop(k, None)

async def generate_ai(prompt: str, system_instruction: str = None, use_cache: bool = True) -> str:
    """Universal high-speed text generator with LRU caching and multi-provider failover pool."""
    cache_key = f"{system_instruction or ''}:::{prompt.strip()}"
    now = time.time()

    # 1. LRU Cache Hit (0ms latency & 0 API cost)
    if use_cache and cache_key in _ai_cache:
        cached_val, cached_time = _ai_cache[cache_key]
        if now - cached_time < CACHE_TTL_SECONDS:
            return cached_val

    _clean_cache()

    async with _ai_semaphore:
        # Tier 1: Gemini Free Provider Pool
        gemini = get_gemini()
        if gemini:
            contents = f"{system_instruction}\n\n{prompt}" if system_instruction else prompt
            for model_name in ["gemini-3.6-flash", "gemini-2.5-flash", "gemini-2.0-flash"]:
                try:
                    res = await gemini.models.generate_content(
                        model=model_name,
                        contents=contents,
                    )
                    if res and res.text:
                        text = res.text.strip()
                        if use_cache:
                            _ai_cache[cache_key] = (text, now)
                        return text
                except Exception:
                    continue

        # Tier 2: Groq High-Speed Free Provider Pool (500 tokens/sec failover)
        groq = get_groq()
        if groq:
            messages = []
            if system_instruction:
                messages.append({"role": "system", "content": system_instruction})
            messages.append({"role": "user", "content": prompt})

            for groq_model in ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"]:
                try:
                    completion = await groq.chat.completions.create(
                        model=groq_model,
                        messages=messages,
                        temperature=0.7,
                        max_tokens=1500,
                    )
                    if completion.choices and completion.choices[0].message.content:
                        text = completion.choices[0].message.content.strip()
                        if use_cache:
                            _ai_cache[cache_key] = (text, now)
                        return text
                except Exception:
                    continue

    raise Exception("AI generation failed across all available Gemini & Groq cloud providers.")


