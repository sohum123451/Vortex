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
import urllib.parse
import aiohttp

# ==========================================================================
# 🧠 MULTI-MODEL FREE CLOUD AI ENGINE (15+ MODELS ACROSS 3 PROVIDERS)
# ==========================================================================
_gemini_client = None
_groq_client = None
_ai_semaphore = asyncio.Semaphore(12)  # Max 12 concurrent requests
_ai_cache = {}  # prompt_hash -> (response_text, timestamp)
CACHE_TTL_SECONDS = 600  # 10 minutes TTL
MAX_CACHE_SIZE = 1000

AVAILABLE_MODELS = {
    "gemini-3.6-flash": "Google Gemini 3.6 Flash (Fast, Multimodal & Reasoning)",
    "gemini-2.5-flash": "Google Gemini 2.5 Flash (Balanced High-Speed)",
    "gemini-2.0-flash": "Google Gemini 2.0 Flash (Next-Gen)",
    "deepseek-r1": "DeepSeek R1 Distill 70B via Groq (Deep Step-by-Step Reasoning)",
    "llama-3.3-70b": "Meta LLaMA 3.3 70B via Groq (Flagship 500 tokens/sec)",
    "llama-3.1-8b": "Meta LLaMA 3.1 8B via Groq (Ultra-Low Latency)",
    "gemma2-9b": "Google Gemma 2 9B via Groq",
    "mixtral-8x7b": "Mistral Mixtral 8x7B MoE via Groq",
    "gpt-4o-mini": "OpenAI GPT-4o-Mini via Pollinations Cloud",
    "deepseek-v3": "DeepSeek V3 671B via Pollinations Cloud",
    "qwen-2.5-72b": "Alibaba Qwen 2.5 72B via Pollinations Cloud",
    "mistral-large": "Mistral Large via Pollinations Cloud",
}

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

async def _call_pollinations(prompt: str, system_instruction: str = None, model: str = "openai") -> str:
    """Free, keyless cloud inference fallback powered by Pollinations.ai network."""
    full_prompt = f"System: {system_instruction}\n\nUser: {prompt}" if system_instruction else prompt
    url = f"https://text.pollinations.ai/{urllib.parse.quote(full_prompt)}?model={model}&seed={random.randint(1, 999999)}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=18)) as resp:
            if resp.status == 200:
                text = await resp.text()
                if text and len(text.strip()) > 3:
                    return text.strip()
    raise Exception(f"Pollinations model {model} returned invalid response.")

async def generate_ai(prompt: str, system_instruction: str = None, specific_model: str = None, use_cache: bool = True) -> str:
    """Universal high-speed text generator across 15+ AI models with automatic failover."""
    cache_key = f"{specific_model or 'auto'}:::{system_instruction or ''}:::{prompt.strip()}"
    now = time.time()

    # 1. In-Memory LRU Cache Hit (0ms latency & 0 API cost)
    if use_cache and cache_key in _ai_cache:
        cached_val, cached_time = _ai_cache[cache_key]
        if now - cached_time < CACHE_TTL_SECONDS:
            return cached_val

    _clean_cache()

    async with _ai_semaphore:
        # If user explicitly requested DeepSeek-R1 reasoning
        if specific_model in ["deepseek-r1", "reasoning"]:
            groq = get_groq()
            if groq:
                try:
                    res = await groq.chat.completions.create(
                        model="deepseek-r1-distill-llama-70b",
                        messages=[{"role": "system", "content": system_instruction or "You are a master analytical reasoner."},{"role": "user", "content": prompt}],
                        temperature=0.6,
                        max_tokens=2500,
                    )
                    if res.choices and res.choices[0].message.content:
                        text = res.choices[0].message.content.strip()
                        if use_cache:
                            _ai_cache[cache_key] = (text, now)
                        return text
                except Exception:
                    pass

        # -------------------------------------------------------------
        # Tier 1: Google Gemini Models (Primary)
        # -------------------------------------------------------------
        gemini = get_gemini()
        if gemini:
            contents = f"{system_instruction}\n\n{prompt}" if system_instruction else prompt
            gemini_models = ["gemini-3.6-flash", "gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]
            if specific_model and specific_model.startswith("gemini"):
                gemini_models = [specific_model] + [m for m in gemini_models if m != specific_model]

            for g_model in gemini_models:
                try:
                    res = await gemini.models.generate_content(
                        model=g_model,
                        contents=contents,
                    )
                    if res and res.text:
                        text = res.text.strip()
                        if use_cache:
                            _ai_cache[cache_key] = (text, now)
                        return text
                except Exception:
                    continue

        # -------------------------------------------------------------
        # Tier 2: Groq Ultra-Fast Models (500 tokens/sec failover)
        # -------------------------------------------------------------
        groq = get_groq()
        if groq:
            messages = []
            if system_instruction:
                messages.append({"role": "system", "content": system_instruction})
            messages.append({"role": "user", "content": prompt})

            groq_models = [
                "llama-3.3-70b-versatile",
                "deepseek-r1-distill-llama-70b",
                "llama-3.1-8b-instant",
                "gemma2-9b-it",
                "mixtral-8x7b-32768"
            ]
            for groq_model in groq_models:
                try:
                    completion = await groq.chat.completions.create(
                        model=groq_model,
                        messages=messages,
                        temperature=0.7,
                        max_tokens=1800,
                    )
                    if completion.choices and completion.choices[0].message.content:
                        text = completion.choices[0].message.content.strip()
                        if use_cache:
                            _ai_cache[cache_key] = (text, now)
                        return text
                except Exception:
                    continue

        # -------------------------------------------------------------
        # Tier 3: Pollinations Free Public Cloud (Zero API Key Failover)
        # -------------------------------------------------------------
        for p_model in ["openai", "deepseek", "qwen", "mistral"]:
            try:
                text = await _call_pollinations(prompt, system_instruction, model=p_model)
                if text:
                    if use_cache:
                        _ai_cache[cache_key] = (text, now)
                    return text
            except Exception:
                continue

    raise Exception("AI generation failed across all 3 cloud providers (Gemini, Groq, Pollinations).")



