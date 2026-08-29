import os
import re
import base64
import requests
import sqlite3
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
# 🌐 TURSO SERVERLESS CLOUD SQLITE ADAPTER (100% PERSISTENCE FOR RENDER)
# ==========================================================================
TURSO_DATABASE_URL = os.getenv("TURSO_DATABASE_URL")
TURSO_AUTH_TOKEN = os.getenv("TURSO_AUTH_TOKEN")


class TursoRow(tuple):
    def __new__(cls, cols, values):
        instance = super(TursoRow, cls).__new__(cls, values)
        instance._cols = cols
        instance._col_map = {name.lower(): idx for idx, name in enumerate(cols)} if cols else {}
        return instance

    def __getitem__(self, item):
        if isinstance(item, str):
            idx = self._col_map.get(item.lower())
            if idx is None:
                raise IndexError(f"No such column in row: {item}")
            return super().__getitem__(idx)
        return super().__getitem__(item)

    def get(self, key, default=None):
        if isinstance(key, str):
            idx = self._col_map.get(key.lower())
            if idx is not None:
                return super().__getitem__(idx)
        return default

    def keys(self):
        return self._cols

class TursoCursor:
    def __init__(self, conn):
        self.conn = conn
        self.description = None
        self.rowcount = 0
        self.lastrowid = None
        self._rows = []
        self._pos = 0

    def _convert_param(self, val):
        if val is None:
            return {'type': 'null'}
        elif isinstance(val, bool):
            return {'type': 'integer', 'value': '1' if val else '0'}
        elif isinstance(val, int):
            return {'type': 'integer', 'value': str(val)}
        elif isinstance(val, float):
            return {'type': 'float', 'value': val}
        elif isinstance(val, (bytes, bytearray)):
            return {'type': 'blob', 'base64': base64.b64encode(val).decode('ascii')}
        else:
            return {'type': 'text', 'value': str(val)}

    def _parse_row_val(self, item):
        t = item.get('type')
        v = item.get('value')
        if t == 'null' or v is None:
            return None
        elif t == 'integer':
            return int(v)
        elif t == 'float':
            return float(v)
        elif t == 'blob':
            return base64.b64decode(item.get('base64', ''))
        return str(v)

    def execute(self, sql, params=None):
        stmt = {'sql': sql}
        if params:
            if isinstance(params, (list, tuple)):
                stmt['args'] = [self._convert_param(p) for p in params]
            elif isinstance(params, dict):
                stmt['named_args'] = [{'name': k, 'value': self._convert_param(v)} for k, v in params.items()]
            else:
                stmt['args'] = [self._convert_param(params)]
        
        payload = {'requests': [{'type': 'execute', 'stmt': stmt}]}
        resp = self.conn._request(payload)
        res = resp['results'][0]
        if res.get('type') == 'error':
            raise Exception(res.get('error', {}).get('message', 'Turso SQL Error'))
        
        result_data = res.get('response', {}).get('result', {})
        cols = [c['name'] for c in result_data.get('cols', [])]
        self.description = [(c, None, None, None, None, None, None) for c in cols] if cols else None
        self.rowcount = result_data.get('affected_row_count', 0)
        self.lastrowid = result_data.get('last_insert_rowid')
        raw_rows = result_data.get('rows', [])
        
        self._rows = [TursoRow(cols, [self._parse_row_val(col) for col in r]) for r in raw_rows]
        self._pos = 0
        return self

    def executemany(self, sql, seq_of_params):
        for params in seq_of_params:
            self.execute(sql, params)
        return self

    def fetchone(self):
        if self._pos < len(self._rows):
            r = self._rows[self._pos]
            self._pos += 1
            return r
        return None

    def fetchall(self):
        r = self._rows[self._pos:]
        self._pos = len(self._rows)
        return r

    def fetchmany(self, size=None):
        if size is None:
            size = 1
        end = min(self._pos + size, len(self._rows))
        r = self._rows[self._pos:end]
        self._pos = end
        return r

    def close(self):
        self._rows = []

    def __iter__(self):
        return self

    def __next__(self):
        r = self.fetchone()
        if r is None:
            raise StopIteration
        return r

class TursoConnection:
    def __init__(self, url, token):
        http_url = url.replace('libsql://', 'https://').rstrip('/') + '/v2/pipeline'
        self.url = http_url
        self.token = token
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        })
        self.row_factory = None

    def _request(self, payload):
        r = self.session.post(self.url, json=payload, timeout=12)
        r.raise_for_status()
        return r.json()

    def cursor(self):
        return TursoCursor(self)

    def execute(self, sql, params=None):
        cur = self.cursor()
        return cur.execute(sql, params)

    def executemany(self, sql, seq_of_params):
        cur = self.cursor()
        return cur.executemany(sql, seq_of_params)

    def commit(self):
        pass

    def rollback(self):
        pass

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

# Setup global database connection provider
def get_db():
    if TURSO_DATABASE_URL and TURSO_AUTH_TOKEN:
        return TursoConnection(TURSO_DATABASE_URL, TURSO_AUTH_TOKEN)
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

# Dynamically route sqlite3.connect when Turso is configured
_original_sqlite_connect = sqlite3.connect

def connect_db_router(database=DB_FILE, *args, **kwargs):
    if TURSO_DATABASE_URL and TURSO_AUTH_TOKEN:
        return TursoConnection(TURSO_DATABASE_URL, TURSO_AUTH_TOKEN)
    return _original_sqlite_connect(database, *args, **kwargs)

if TURSO_DATABASE_URL and TURSO_AUTH_TOKEN:
    sqlite3.connect = connect_db_router
    try:
        print("[TURSO] Turso Cloud Database Active - Permanent persistence enabled.", flush=True)
    except Exception:
        pass
else:
    try:
        print("[DATABASE] Local SQLite Database Active.", flush=True)
    except Exception:
        pass

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
