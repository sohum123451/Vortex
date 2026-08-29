import os
import re
import base64
import requests
import sqlite3
import threading
import time
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
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

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
        
        with sqlite3.connect(DB_FILE) as conn:
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
    """Background thread loop pushing local database tables to Turso Cloud every 15s."""
    http_url = TURSO_DATABASE_URL.replace('libsql://', 'https://').rstrip('/') + '/v2/pipeline' if TURSO_DATABASE_URL else None
    headers = {'Authorization': f'Bearer {TURSO_AUTH_TOKEN}', 'Content-Type': 'application/json'} if TURSO_AUTH_TOKEN else {}

    while True:
        time.sleep(15)
        if not (TURSO_DATABASE_URL and TURSO_AUTH_TOKEN):
            continue
        try:
            with sqlite3.connect(DB_FILE) as conn:
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
                    # Send in chunks of 100 queries max to prevent HTTP payload bloat
                    for chunk_idx in range(0, len(requests_list), 100):
                        chunk = requests_list[chunk_idx:chunk_idx + 100]
                        requests.post(http_url, headers=headers, json={'requests': chunk}, timeout=10)
        except Exception:
            pass

# Initialize Hybrid Cloud Persistence Engine
if TURSO_DATABASE_URL and TURSO_AUTH_TOKEN:
    sync_turso_to_local()
    t = threading.Thread(target=sync_local_to_turso_background, daemon=True)
    t.start()
    print("[TURSO] High-Speed Cloud Hybrid Engine Active — 0ms local delay with permanent cloud sync.", flush=True)
else:
    print("[DATABASE] Local SQLite Engine Active.", flush=True)

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
