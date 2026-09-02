import asyncio
import io
import os
import sqlite3
import subprocess
import sys
import textwrap
import traceback
from datetime import datetime, timezone
import discord
from discord.ext import commands
from utils import DB_FILE, MAIN_COLOR, SUCCESS_COLOR, ERROR_COLOR, INFO_COLOR

class Developer(commands.Cog):
    """Owner and developer-only tools for administration, debugging, and diagnostics."""

    def __init__(self, bot):
        self.bot = bot

    async def get_real_owner(self):
        app_info = await self.bot.application_info()
        owner_id = app_info.team.owner_id if app_info.team else app_info.owner.id
        try:
            return await self.bot.fetch_user(owner_id)
        except Exception:
            return app_info.owner

    @commands.hybrid_command(name="about", description="Information about the bot, developers, and hosting")
    async def about(self, ctx):
        owner = await self.get_real_owner()
        delta = datetime.now(timezone.utc) - self.bot.start_time
        uptime_str = str(delta).split(".")[0]

        total_members = sum(g.member_count for g in self.bot.guilds if g.member_count)
        total_channels = sum(len(g.channels) for g in self.bot.guilds)
        total_commands = len(set(self.bot.walk_commands()))

        embed = discord.Embed(
            title="⚡ Vortex Discord Bot — System & Developer Information",
            description=(
                "**Vortex** is an enterprise-grade, multi-purpose Discord bot built for high-performance communities.\n"
                "Featuring **Gemini 3.6 AI**, **500+ Modular Commands**, **Casino Economy**, **Live Sports**, and **Automated Security**."
            ),
            color=MAIN_COLOR,
            timestamp=datetime.now(timezone.utc),
        )
        if self.bot.user.display_avatar:
            embed.set_thumbnail(url=self.bot.user.display_avatar.url)

        embed.add_field(name="👑 Bot Creator", value=f"{owner.mention} (`{owner}`)\n**ID:** `{owner.id}`", inline=True)
        embed.add_field(name="🌐 Cloud Hosting", value="24/7 Production Server\nUptimeRobot Keep-Alive", inline=True)
        embed.add_field(name="⏱️ System Uptime", value=f"`{uptime_str}`", inline=True)
        embed.add_field(name="📊 Total Guilds / Users", value=f"🏰 **{len(self.bot.guilds):,}** Guilds\n👥 **{total_members:,}** Users", inline=True)
        embed.add_field(name="💬 Channels / Latency", value=f"📁 **{total_channels:,}** Channels\n🏓 `{round(self.bot.latency * 1000)}ms`", inline=True)
        embed.add_field(name="⚡ Total Commands Loaded", value=f"🛠️ **{total_commands}+** commands", inline=True)
        embed.add_field(name="💾 Database Engine", value="Turso Cloud Hybrid + SQLite WAL (0ms)", inline=True)
        embed.add_field(name="🧠 AI Technology", value="Google Gemini 3.6 Flash & Groq High-Speed Engine", inline=True)
        embed.set_footer(text="Developed with python discord.py • 24/7 High-Availability Cloud")
        await ctx.reply(embed=embed)

    @commands.hybrid_command(name="owner", description="View bot creator profile information")
    async def owner_info(self, ctx):
        owner = await self.get_real_owner()
        embed = discord.Embed(
            title=f"👑 Bot Creator: {owner.display_name}",
            color=discord.Color.gold(),
            timestamp=datetime.now(timezone.utc),
        )
        embed.set_thumbnail(url=owner.display_avatar.url)
        embed.add_field(name="Username", value=f"`{owner}`", inline=True)
        embed.add_field(name="User ID", value=f"`{owner.id}`", inline=True)
        embed.add_field(name="Account Created", value=f"<t:{int(owner.created_at.timestamp())}:R>", inline=False)
        if ctx.guild and ctx.guild.owner:
            embed.add_field(name="Server Owner", value=f"{ctx.guild.owner.mention} (`{ctx.guild.owner.id}`)", inline=False)
        await ctx.reply(embed=embed)

    # ==========================================
    # 🔒 RESTRICTED OWNER-ONLY COMMANDS
    # ==========================================

    @commands.command(name="eval", description="[Owner] Evaluate Python code asynchronously")
    @commands.is_owner()
    async def eval_code(self, ctx, *, code: str):
        code = code.strip("` \n")
        if code.startswith("python"):
            code = code[6:].strip()

        env = {
            "bot": self.bot,
            "ctx": ctx,
            "channel": ctx.channel,
            "author": ctx.author,
            "guild": ctx.guild,
            "message": ctx.message,
            "asyncio": asyncio,
            "discord": discord,
        }

        stdout = io.StringIO()
        to_compile = f"async def func():\n{textwrap.indent(code, '  ')}"

        try:
            exec(to_compile, env)
        except Exception as e:
            return await ctx.reply(f"```py\n[Compile Error]: {e}\n```")

        func = env["func"]
        try:
            sys.stdout = stdout
            result = await func()
            out = stdout.getvalue()
        except Exception:
            out = stdout.getvalue()
            result = traceback.format_exc()
        finally:
            sys.stdout = sys.__stdout__

        if result is not None:
            out = f"{out}\n[Return Value]: {result}".strip()
        if not out:
            out = "[Execution Completed with no output]"

        if len(out) > 1900:
            out = out[:1900] + "\n...[Truncated]"
        await ctx.reply(f"```py\n{out}\n```")

    @commands.command(name="exec", description="[Owner] Execute shell command on AWS EC2")
    @commands.is_owner()
    async def exec_shell(self, ctx, *, command: str):
        msg = await ctx.reply(f"⚙️ Running shell command: `{command}`...")
        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
            out = stdout.decode() or stderr.decode() or "Command completed with no output."
            if len(out) > 1900:
                out = out[:1900] + "\n...[Truncated]"
            await msg.edit(content=f"```sh\n{out}\n```")
        except asyncio.TimeoutError:
            await msg.edit(content="❌ Shell command timed out (30s limit).")
        except Exception as e:
            await msg.edit(content=f"❌ Error: {e}")

    @commands.command(name="sql", description="[Owner] Execute SQLite query directly")
    @commands.is_owner()
    async def sql_query(self, ctx, *, query: str):
        try:
            with sqlite3.connect(DB_FILE) as conn:
                cur = conn.cursor()
                cur.execute(query)
                if query.strip().upper().startswith("SELECT"):
                    rows = cur.fetchall()
                    cols = [d[0] for d in cur.description] if cur.description else []
                    out = f"Columns: {cols}\n" + "\n".join([str(r) for r in rows[:15]])
                    if len(rows) > 15:
                        out += f"\n...({len(rows) - 15} more rows)"
                else:
                    conn.commit()
                    out = f"Query executed successfully. Affected rows: {cur.rowcount}"
            if len(out) > 1900:
                out = out[:1900] + "..."
            await ctx.reply(f"```sql\n{out}\n```")
        except Exception as e:
            await ctx.reply(f"❌ SQL Error: {e}")

    @commands.command(name="servers", description="[Owner] List all servers the bot is in")
    @commands.is_owner()
    async def servers_list(self, ctx):
        guilds = sorted(self.bot.guilds, key=lambda g: g.member_count or 0, reverse=True)
        lines = []
        for idx, g in enumerate(guilds[:25], start=1):
            lines.append(f"**#{idx}** `{g.id}` — **{g.name}** ({g.member_count:,} members) | Owner: `{g.owner}`")
        embed = discord.Embed(
            title=f"🏰 Connected Servers ({len(guilds)})",
            description="\n".join(lines),
            color=MAIN_COLOR,
        )
        await ctx.reply(embed=embed)

    @commands.command(name="leave", description="[Owner] Make the bot leave a guild by ID")
    @commands.is_owner()
    async def leave_guild(self, ctx, guild_id: int):
        guild = self.bot.get_guild(guild_id)
        if not guild:
            return await ctx.reply("❌ Guild not found.")
        await guild.leave()
        await ctx.reply(f"👋 Successfully left guild: **{guild.name}** (`{guild_id}`).")

    @commands.command(name="dm", description="[Owner] Send a DM to a user by ID")
    @commands.is_owner()
    async def dm_command(self, ctx, user_id: int, *, message: str):
        user = await self.bot.fetch_user(user_id)
        if not user:
            return await ctx.reply("❌ User not found.")
        try:
            await user.send(f"📬 **Message from Vortex Bot Developers:**\n\n{message}")
            await ctx.reply(f"✅ DM delivered to {user.mention} (`{user.id}`).")
        except Exception as e:
            await ctx.reply(f"❌ Could not DM user: {e}")

    @commands.command(name="broadcast", description="[Owner] Broadcast a message to all guilds")
    @commands.is_owner()
    async def broadcast(self, ctx, *, message: str):
        sent = 0
        embed = discord.Embed(
            title="📢 Vortex Global Broadcast",
            description=message,
            color=MAIN_COLOR,
            timestamp=datetime.now(timezone.utc),
        )
        embed.set_footer(text="Official Developer Announcement")
        for g in self.bot.guilds:
            chan = g.system_channel or next((c for c in g.text_channels if c.permissions_for(g.me).send_messages), None)
            if chan:
                try:
                    await chan.send(embed=embed)
                    sent += 1
                except Exception:
                    pass
        await ctx.reply(f"📢 Broadcast sent to **{sent}/{len(self.bot.guilds)}** servers.")

    @commands.command(name="setstatus", description="[Owner] Change online status (online, idle, dnd, invisible)")
    @commands.is_owner()
    async def set_status(self, ctx, status_str: str):
        mapping = {
            "online": discord.Status.online,
            "idle": discord.Status.idle,
            "dnd": discord.Status.dnd,
            "invisible": discord.Status.invisible,
        }
        stat = mapping.get(status_str.lower())
        if not stat:
            return await ctx.reply("❌ Choose `online`, `idle`, `dnd`, or `invisible`.")
        await self.bot.change_presence(status=stat)
        await ctx.reply(f"✅ Status updated to `{status_str}`.")

    @commands.command(name="setactivity", description="[Owner] Change bot activity: &setactivity [type] <name>")
    @commands.is_owner()
    async def set_activity(self, ctx, *, activity_text: str):
        types = {
            "playing": discord.ActivityType.playing,
            "watching": discord.ActivityType.watching,
            "listening": discord.ActivityType.listening,
            "competing": discord.ActivityType.competing,
        }
        parts = activity_text.split(maxsplit=1)
        if len(parts) > 1 and parts[0].lower() in types:
            act_type = types[parts[0].lower()]
            name = parts[1]
        else:
            act_type = discord.ActivityType.watching
            name = activity_text

        if ctx.message and ctx.message.mentions:
            for m in ctx.message.mentions:
                name = name.replace(f"<@{m.id}>", f"@{m.display_name}").replace(f"<@!{m.id}>", f"@{m.display_name}")

        await self.bot.change_presence(activity=discord.Activity(type=act_type, name=name))
        await ctx.reply(f"✅ Activity updated to: **{act_type.name.title()}** `{name}`")

    @commands.command(name="backup_db", description="[Owner] Download a copy of SQLite database file")
    @commands.is_owner()
    async def backup_database(self, ctx):
        if not os.path.exists(DB_FILE):
            return await ctx.reply("❌ Database file does not exist.")
        file = discord.File(DB_FILE, filename=f"bot_database_{int(datetime.now().timestamp())}.db")
        await ctx.author.send(content="💾 **Database Backup:**", file=file)
        await ctx.reply("📬 Database file sent to your DMs!")

    @commands.command(name="sync", description="[Owner] Sync slash commands globally")
    @commands.is_owner()
    async def sync_commands(self, ctx):
        msg = await ctx.reply("🔄 Syncing slash commands globally...")
        try:
            synced = await self.bot.tree.sync()
            await msg.edit(content=f"✅ Successfully synced **{len(synced)}** slash commands globally.")
        except Exception as e:
            await msg.edit(content=f"❌ Error syncing commands: {e}")

    @commands.command(name="clearsync", description="[Owner] Clear guild-specific slash commands to fix duplicates")
    @commands.is_owner()
    async def clear_guild_sync(self, ctx):
        msg = await ctx.reply("🧹 Clearing guild-specific slash commands for this server...")
        try:
            self.bot.tree.clear_commands(guild=ctx.guild)
            await self.bot.tree.sync(guild=ctx.guild)
            await msg.edit(content=f"✅ Cleared guild-specific commands for **{ctx.guild.name}**. Any duplicate slash commands have been removed.")
        except Exception as e:
            await msg.edit(content=f"❌ Error clearing guild sync: {e}")

    @commands.command(name="lasterror", aliases=["last_error", "errlog"], description="[Owner] View the most recent system error and full traceback")
    async def view_last_error(self, ctx):
        last_err = getattr(self.bot, "_last_error_log", None)
        if not last_err:
            return await ctx.reply("✅ **System Clean:** No unhandled runtime errors have been recorded in this session.")

        embed = discord.Embed(
            title="🔍 Recent Command Exception Traceback",
            description=f"**Command:** `{last_err.get('command')}`\n**Invoker:** `{last_err.get('user')}`\n**Time:** <t:{int(last_err.get('time').timestamp())}:R>",
            color=ERROR_COLOR,
            timestamp=last_err.get('time'),
        )
        embed.add_field(name="⚠️ Exception", value=f"```py\n{last_err.get('error')[:400]}\n```", inline=False)
        trace_str = last_err.get('trace', '')
        if trace_str:
            embed.add_field(name="📋 Full Stack Trace", value=f"```py\n{trace_str[-1200:]}\n```", inline=False)
        await ctx.reply(embed=embed)

    @commands.hybrid_command(name="ram", aliases=["memory", "meminfo", "resources"], description="[Admin] Check live Render RAM and process memory usage")
    async def memory_info(self, ctx):
        """Displays real-time memory stats, RSS allocation, and Render 512MB quota health."""
        import gc
        import psutil

        process = psutil.Process(os.getpid())
        mem_info = process.memory_info()
        rss_mb = mem_info.rss / (1024 * 1024)
        vms_mb = mem_info.vms / (1024 * 1024)

        render_limit_mb = 512.0
        used_pct = (rss_mb / render_limit_mb) * 100

        # Health status badge
        if used_pct < 50:
            health = "🟢 Optimal (<50%)"
            color = SUCCESS_COLOR
        elif used_pct < 80:
            health = "🟡 Moderate (50-80%)"
            color = MAIN_COLOR
        else:
            health = "🔴 Warning (>80%)"
            color = ERROR_COLOR

        embed = discord.Embed(
            title="📊 Live Memory & Render Container Health",
            description=f"**Render Free-Tier Allocation:** `512.0 MB RAM`\n**Container Health:** {health}",
            color=color,
            timestamp=datetime.now(timezone.utc),
        )
        embed.add_field(name="💾 Process RSS (Resident)", value=f"`{rss_mb:.1f} MB` ({used_pct:.1f}%)", inline=True)
        embed.add_field(name="🧠 Virtual Memory (VMS)", value=f"`{vms_mb:.1f} MB`", inline=True)
        embed.add_field(name="🧹 Cached Channels", value=f"`{len(self.bot.cached_messages):,}` msgs", inline=True)
        embed.add_field(name="🧩 Loaded Cogs", value=f"`{len(self.bot.cogs)}` modules", inline=True)
        embed.add_field(name="⚡ Active Guilds", value=f"`{len(self.bot.guilds):,}` servers", inline=True)
        embed.add_field(name="⏱️ System Uptime", value=f"`{str(datetime.now(timezone.utc) - self.bot.start_time).split('.')[0]}`", inline=True)

        embed.set_footer(text="Automated memory optimization runs every 10 mins • Type &gc to force clean")
        await ctx.reply(embed=embed)

    @commands.command(name="gc", aliases=["clearmem", "free_ram"], description="[Owner] Force run Python garbage collection and SQLite WAL compaction")
    @commands.is_owner()
    async def force_gc(self, ctx):
        """Force runs gc.collect() and frees unreferenced memory back to the OS."""
        import gc
        import psutil

        proc = psutil.Process(os.getpid())
        before_mb = proc.memory_info().rss / (1024 * 1024)

        collected = gc.collect()
        with sqlite3.connect(DB_FILE) as conn:
            conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            conn.execute("PRAGMA shrink_memory")

        after_mb = proc.memory_info().rss / (1024 * 1024)
        diff = before_mb - after_mb

        embed = discord.Embed(
            title="🧹 Memory Garbage Collection Executed",
            description=(
                f"• **Garbage Objects Reclaimed:** `{collected:,}` objects\n"
                f"• **Before Clean:** `{before_mb:.1f} MB`\n"
                f"• **After Clean:** `{after_mb:.1f} MB`\n"
                f"• **Freed Memory:** `{diff:.2f} MB`"
            ),
            color=SUCCESS_COLOR,
            timestamp=datetime.now(timezone.utc),
        )
        await ctx.reply(embed=embed)

async def setup(bot):
    await bot.add_cog(Developer(bot))

