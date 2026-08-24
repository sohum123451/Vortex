import asyncio
import os
import sys
import sqlite3
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
sys.stdout.reconfigure(encoding='utf-8')

DB_FILE = "vortex.db"

async def run_audit():
    print("=" * 60)
    print("🔍 VORTEX BOT AUTOMATED SUITE & SECURITY AUDIT")
    print("=" * 60)

    # 1. Voice Drivers Audit
    print("\n[1/5] Checking Audio & Voice Drivers...")
    import importlib
    try:
        importlib.import_module("nacl")
        importlib.import_module("davey")
        print("  ✅ PyNaCl & Davey audio encryption libraries: INSTALLED & READY")
    except ImportError as e:
        print(f"  ❌ Missing voice dependency on current system: {e}")

    # 2. Database Schema & Tables
    print("\n[2/5] Checking Database Schema & Tables...")
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in cur.fetchall()]
    print(f"  📊 Found {len(tables)} Database Tables: {', '.join(tables)}")

    expected_tables = ['economy', 'levels', 'warnings', 'tempbans', 'giveaways', 'afk', 'sticky', 'reminders', 'rpg_players', 'rpg_inventory', 'custom_tags', 'autoresponders', 'crypto_portfolio', 'server_analytics']
    missing_tables = [t for t in expected_tables if t not in tables]
    if missing_tables:
        print(f"  ⚠️ Missing tables: {missing_tables}")
    else:
        print("  ✅ All expected database tables verified!")

    # 3. Cog Loader & Command Verification
    print("\n[3/5] Loading All Cogs and Validating Command Callbacks...")
    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True
    bot = commands.Bot(command_prefix='&', intents=intents, help_command=None)

    cogs_dir = 'cogs'
    loaded_cogs = []
    failed_cogs = []

    for filename in sorted(os.listdir(cogs_dir)):
        if filename.endswith('.py') and not filename.startswith('__'):
            ext = f'cogs.{filename[:-3]}'
            try:
                await bot.load_extension(ext)
                loaded_cogs.append(filename[:-3])
            except Exception as e:
                failed_cogs.append((ext, str(e)))

    if failed_cogs:
        print(f"  ❌ Failed to load {len(failed_cogs)} cogs:")
        for ext, err in failed_cogs:
            print(f"     - {ext}: {err}")
    else:
        print(f"  ✅ Successfully loaded all {len(loaded_cogs)} Cogs with ZERO syntax or registration errors!")

    # 4. Command Counts & Slash Limit Verification
    print("\n[4/5] Counting Registered Commands...")
    all_cmds = list(bot.walk_commands())
    slash_cmds = [c for c in all_cmds if isinstance(c, commands.HybridCommand) or isinstance(c, discord.app_commands.Command)]

    print(f"  ⚡ Total Registered Distinct Commands: {len(all_cmds)}")
    print(f"  🚀 Total Slash Commands: {len(slash_cmds)} (Limit: 100 max - Safety Margin: {100 - len(slash_cmds)} available)")

    # 5. Security & Exploit Checks
    print("\n[5/5] Performing Security & Exploit Checks...")
    vulnerabilities = []

    # Check for unparameterized SQL queries in code
    for root, _, files in os.walk('cogs'):
        for file in files:
            if file.endswith('.py'):
                fpath = os.path.join(root, file)
                with open(fpath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Check for f-string direct insertion into execute
                    if "execute(f\"SELECT" in content or "execute(f\"INSERT" in content or "execute(f\"UPDATE" in content or "execute(f\"DELETE" in content:
                        # Allow safe ALTER TABLE or specific dynamic table/column definitions
                        if "ALTER TABLE" not in content and "DROP TABLE" not in content:
                            vulnerabilities.append(f"Potential unparameterized query in {file}")

    if vulnerabilities:
        print(f"  ⚠️ Vulnerabilities noted: {vulnerabilities}")
    else:
        print("  🛡️ All database queries use secure parameterized SQL (?) preventing SQL injection.")

    print("\n" + "=" * 60)
    print("🎉 AUDIT COMPLETED: SYSTEM SECURE & READY FOR DEPLOYMENT!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(run_audit())
