import asyncio
import re
import sqlite3
from datetime import datetime, timedelta, timezone
import discord
from discord.ext import commands, tasks
from utils import (
    DB_FILE,
    MAIN_COLOR,
    SUCCESS_COLOR,
    ERROR_COLOR,
    WARN_COLOR,
    parse_time,
    dm_user,
    send_log,
    role_guard,
)

class Moderation(commands.Cog):
    """Full-featured server moderation and enforcement suite with smart filters."""

    def __init__(self, bot):
        self.bot = bot
        self.unban_task.start()

    def cog_unload(self):
        self.unban_task.cancel()

    @commands.hybrid_command(name="kick", description="Kick a member from the server")
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member, *, reason="No reason provided"):
        if err := role_guard(ctx, member):
            return await ctx.reply(err)
        await dm_user(member, f"⚠️ You were kicked from **{ctx.guild.name}**\nReason: {reason}")
        await member.kick(reason=reason)
        await send_log(ctx, "Kick", member, reason)
        await ctx.reply(f"✅ Successfully kicked {member.mention} ({reason})")

    @commands.hybrid_command(name="ban", description="Ban a member from the server")
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, member: discord.Member, *, reason="No reason provided"):
        if err := role_guard(ctx, member):
            return await ctx.reply(err)
        await dm_user(member, f"⛔ You were banned from **{ctx.guild.name}**\nReason: {reason}")
        await member.ban(reason=reason)
        await send_log(ctx, "Ban", member, reason)
        await ctx.reply(f"⛔ Successfully banned {member.mention} ({reason})")

    @commands.hybrid_command(name="unban", description="Unban a user by ID")
    @commands.has_permissions(ban_members=True)
    async def unban(self, ctx, user_id: int, *, reason="Unbanned by moderator"):
        user = await self.bot.fetch_user(user_id)
        if not user:
            return await ctx.reply("❌ User not found.")
        await ctx.guild.unban(user, reason=reason)
        await send_log(ctx, "Unban", user, reason)
        await ctx.reply(f"🟢 Successfully unbanned **{user}**.")

    @commands.hybrid_command(name="softban", description="Ban and immediately unban to clear member messages")
    @commands.has_permissions(ban_members=True)
    async def softban(self, ctx, member: discord.Member, *, reason="Softban message purge"):
        if err := role_guard(ctx, member):
            return await ctx.reply(err)
        await dm_user(member, f"🧹 You were softbanned from **{ctx.guild.name}** (messages purged).")
        await member.ban(reason=reason, delete_message_days=7)
        await ctx.guild.unban(member, reason="Softban completed")
        await send_log(ctx, "Softban", member, reason)
        await ctx.reply(f"🧹 Softbanned {member.mention} — messages purged and unbanned.")

    @commands.hybrid_command(name="tempban", description="Temporarily ban a user: &tempban @user 1d [reason]")
    @commands.has_permissions(ban_members=True)
    async def tempban(self, ctx, member: discord.Member, time: str, *, reason="No reason provided"):
        duration = parse_time(time)
        if not duration:
            return await ctx.reply("❌ Invalid time format! Use `10m`, `1h`, `1d`, `1w`.")
        if err := role_guard(ctx, member):
            return await ctx.reply(err)

        await member.ban(reason=reason)
        unban_time = (datetime.now(timezone.utc) + duration).isoformat()

        with sqlite3.connect(DB_FILE) as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT OR REPLACE INTO tempbans (user_id, guild_id, unban_time) VALUES (?, ?, ?)",
                (str(member.id), str(ctx.guild.id), unban_time),
            )
            conn.commit()

        await dm_user(member, f"⏳ Temp-banned from **{ctx.guild.name}** for {time}\nReason: {reason}")
        await send_log(ctx, "Temp Ban", member, reason, time)
        await ctx.reply(f"⏳ Temp-banned {member.mention} for **{time}**.")

    @tasks.loop(seconds=30)
    async def unban_task(self):
        now = datetime.now(timezone.utc)
        with sqlite3.connect(DB_FILE) as conn:
            cur = conn.cursor()
            cur.execute("SELECT user_id, guild_id, unban_time FROM tempbans")
            records = cur.fetchall()

            for uid, gid, unban_time_str in records:
                if now >= datetime.fromisoformat(unban_time_str):
                    guild = self.bot.get_guild(int(gid))
                    if guild:
                        try:
                            user = await self.bot.fetch_user(int(uid))
                            await guild.unban(user, reason="Tempban expired automatically")
                        except Exception:
                            pass
                    cur.execute("DELETE FROM tempbans WHERE user_id = ?", (uid,))
                    conn.commit()

    @commands.hybrid_command(name="timeout", description="Timeout a member: &timeout @user 10m [reason]")
    @commands.has_permissions(moderate_members=True)
    async def timeout_cmd(self, ctx, member: discord.Member, time: str, *, reason="No reason provided"):
        if err := role_guard(ctx, member):
            return await ctx.reply(err)
        delta = parse_time(time)
        if not delta or delta.total_seconds() > 28 * 86400:
            return await ctx.reply("❌ Invalid duration! Use `10m`, `1h`, `1d` (max 28 days).")
        await member.timeout(delta, reason=reason)
        await dm_user(member, f"⏳ Timed out in **{ctx.guild.name}** for **{time}**.\nReason: {reason}")
        await send_log(ctx, "Timeout", member, reason, time)
        await ctx.reply(f"⏳ Timed out {member.mention} for **{time}**.")

    @commands.hybrid_command(name="untimeout", description="Remove timeout from a member")
    @commands.has_permissions(moderate_members=True)
    async def untimeout(self, ctx, member: discord.Member, *, reason="Timeout removed"):
        if err := role_guard(ctx, member):
            return await ctx.reply(err)
        await member.timeout(None, reason=reason)
        await send_log(ctx, "Untimeout", member, reason)
        await ctx.reply(f"🟢 Removed timeout from {member.mention}.")

    @commands.hybrid_command(name="warn", description="Warn a member for misconduct")
    @commands.has_permissions(moderate_members=True)
    async def warn(self, ctx, member: discord.Member, *, reason="No reason provided"):
        if err := role_guard(ctx, member):
            return await ctx.reply(err)

        uid = str(member.id)
        gid = str(ctx.guild.id)
        now_str = datetime.now(timezone.utc).isoformat()

        with sqlite3.connect(DB_FILE) as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO warnings (guild_id, user_id, reason, timestamp) VALUES (?, ?, ?, ?)",
                (gid, uid, reason, now_str),
            )
            cur.execute("SELECT COUNT(*) FROM warnings WHERE guild_id = ? AND user_id = ?", (gid, uid))
            count = cur.fetchone()[0]
            conn.commit()

        await dm_user(member, f"⚠️ Warning in **{ctx.guild.name}**\nReason: {reason}")
        await send_log(ctx, "Warn", member, reason)

        if count == 3:
            await member.timeout(timedelta(minutes=10), reason="Auto timeout (3 warnings reached)")
        elif count >= 10:
            await member.ban(reason="Auto ban (10 warnings reached)")

        await ctx.reply(f"⚠️ Warning issued to {member.mention} (Total warnings: `{count}`)")

    @commands.hybrid_command(name="warnings", description="View warnings history for a member")
    @commands.has_permissions(moderate_members=True)
    async def warnings(self, ctx, member: discord.Member = None):
        target = member or ctx.author
        uid, gid = str(target.id), str(ctx.guild.id)

        with sqlite3.connect(DB_FILE) as conn:
            cur = conn.cursor()
            cur.execute("SELECT id, reason, timestamp FROM warnings WHERE guild_id = ? AND user_id = ?", (gid, uid))
            records = cur.fetchall()

        if not records:
            return await ctx.reply(f"✅ {target.mention} has no warnings on record.")

        embed = discord.Embed(
            title=f"⚠️ Warnings for {target.display_name} ({len(records)})",
            color=WARN_COLOR,
        )
        for wid, reason, ts in records[-10:]:
            embed.add_field(name=f"Case #{wid} • {ts[:10]}", value=reason, inline=False)
        await ctx.reply(embed=embed)

    @commands.command(name="clearwarnings", description="Clear all warnings for a user")
    @commands.has_permissions(administrator=True)
    async def clearwarnings(self, ctx, member: discord.Member):
        with sqlite3.connect(DB_FILE) as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM warnings WHERE guild_id = ? AND user_id = ?", (str(ctx.guild.id), str(member.id)))
            conn.commit()
        await ctx.reply(f"🧹 Cleared all warnings for {member.mention}.")

    @commands.command(name="delwarn", description="Delete a single warning by ID")
    @commands.has_permissions(moderate_members=True)
    async def delwarn(self, ctx, warn_id: int):
        with sqlite3.connect(DB_FILE) as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM warnings WHERE id = ? AND guild_id = ?", (warn_id, str(ctx.guild.id)))
            if cur.rowcount == 0:
                return await ctx.reply("❌ Warning ID not found.")
            conn.commit()
        await ctx.reply(f"✅ Removed warning `#{warn_id}`.")

    # Smart Multi-Mode Purge
    @commands.hybrid_command(
        name="purge",
        description="Smart purge: &purge <amount> [bots | humans | links | @user | @role | match <text>]",
    )
    @commands.has_permissions(manage_messages=True)
    async def purge(self, ctx, amount: int, *, filter_type: str = None):
        if amount <= 0 or amount > 500:
            return await ctx.reply("❌ Please specify an amount between 1 and 500.")

        await ctx.defer(ephemeral=True)

        def check(msg):
            if not filter_type:
                return True
            f = filter_type.strip().lower()
            if f in ["bot", "bots"]:
                return msg.author.bot
            if f in ["human", "humans", "user", "users"]:
                return not msg.author.bot
            if f in ["link", "links", "url", "urls"]:
                return "http://" in msg.content.lower() or "https://" in msg.content.lower() or "discord.gg" in msg.content.lower()
            if f in ["embed", "embeds"]:
                return bool(msg.embeds or msg.attachments)
            if f.startswith("match "):
                keyword = f[6:].strip()
                return keyword in msg.content.lower()
            if ctx.message and ctx.message.role_mentions:
                role = ctx.message.role_mentions[0]
                return role in getattr(msg.author, "roles", [])
            if ctx.message and ctx.message.mentions:
                target = ctx.message.mentions[0]
                return msg.author.id == target.id
            if f.isdigit() and msg.author.id == int(f):
                return True
            return f in msg.content.lower()

        deleted = await ctx.channel.purge(limit=amount + 1, check=check)
        count = max(0, len(deleted) - (1 if ctx.interaction is None else 0))

        filter_desc = f" (Filter: `{filter_type}`)" if filter_type else ""
        msg = await ctx.channel.send(f"🧹 **Purged {count} message(s)**{filter_desc}.")
        await asyncio.sleep(4)
        try:
            await msg.delete()
        except Exception:
            pass

    @commands.command(name="purge_user", description="Purge messages from a specific user")
    @commands.has_permissions(manage_messages=True)
    async def purge_user(self, ctx, member: discord.Member, amount: int = 50):
        await self.purge(ctx, amount=amount, filter_type=str(member.id))

    @commands.command(name="purge_bots", description="Purge all bot messages")
    @commands.has_permissions(manage_messages=True)
    async def purge_bots(self, ctx, amount: int = 50):
        await self.purge(ctx, amount=amount, filter_type="bots")

    @commands.command(name="purge_links", description="Purge all messages containing URLs")
    @commands.has_permissions(manage_messages=True)
    async def purge_links(self, ctx, amount: int = 50):
        await self.purge(ctx, amount=amount, filter_type="links")

    @commands.command(name="purge_embeds", description="Purge messages containing embeds or images")
    @commands.has_permissions(manage_messages=True)
    async def purge_embeds(self, ctx, amount: int = 50):
        await self.purge(ctx, amount=amount, filter_type="embeds")

    @commands.command(name="slowmode", description="Set channel slowmode in seconds (0 to disable)")
    @commands.has_permissions(manage_channels=True)
    async def slowmode(self, ctx, seconds: int, channel: discord.TextChannel = None):
        target = channel or ctx.channel
        if seconds < 0 or seconds > 21600:
            return await ctx.reply("❌ Slowmode must be between 0 and 21,600 seconds.")
        await target.edit(slowmode_delay=seconds)
        status = f"`{seconds}s`" if seconds > 0 else "🟢 **Disabled**"
        await ctx.reply(f"🐢 Slowmode for {target.mention} set to {status}.")

    @commands.command(name="lock", description="Lock a channel from regular members")
    @commands.has_permissions(manage_channels=True)
    async def lock(self, ctx, channel: discord.TextChannel = None):
        target = channel or ctx.channel
        await target.set_permissions(ctx.guild.default_role, send_messages=False)
        await ctx.reply(f"🔒 Locked {target.mention}.")

    @commands.command(name="unlock", description="Unlock a channel for regular members")
    @commands.has_permissions(manage_channels=True)
    async def unlock(self, ctx, channel: discord.TextChannel = None):
        target = channel or ctx.channel
        await target.set_permissions(ctx.guild.default_role, send_messages=True)
        await ctx.reply(f"🔓 Unlocked {target.mention}.")

    @commands.command(name="lockdown", description="Emergency lockdown for all text channels")
    @commands.has_permissions(administrator=True)
    async def lockdown(self, ctx):
        count = 0
        for channel in ctx.guild.text_channels:
            try:
                await channel.set_permissions(ctx.guild.default_role, send_messages=False)
                count += 1
            except Exception:
                pass
        await ctx.reply(f"🔒 **Server Lockdown:** Locked `{count}` text channels.")

    @commands.command(name="unlockdown", description="Unlock all text channels from lockdown")
    @commands.has_permissions(administrator=True)
    async def unlockdown(self, ctx):
        count = 0
        for channel in ctx.guild.text_channels:
            try:
                await channel.set_permissions(ctx.guild.default_role, send_messages=True)
                count += 1
            except Exception:
                pass
        await ctx.reply(f"🔓 **Server Unlocked:** Restored `{count}` text channels.")

    @commands.command(name="nick", description="Change a member's nickname")
    @commands.has_permissions(manage_nicknames=True)
    async def nick(self, ctx, member: discord.Member, *, new_nick: str = None):
        if err := role_guard(ctx, member):
            return await ctx.reply(err)
        old = member.display_name
        await member.edit(nick=new_nick)
        await ctx.reply(f"✏️ Nickname changed for {member.mention}: `{old}` ➔ `{new_nick or member.name}`")

    @commands.command(name="resetnick", description="Reset a member's nickname")
    @commands.has_permissions(manage_nicknames=True)
    async def resetnick(self, ctx, member: discord.Member):
        await self.nick(ctx, member, new_nick=None)

    @commands.command(name="vckick", description="Disconnect a member from voice channel")
    @commands.has_permissions(move_members=True)
    async def vckick(self, ctx, member: discord.Member):
        if not member.voice or not member.voice.channel:
            return await ctx.reply("❌ Member is not connected to a voice channel.")
        if err := role_guard(ctx, member):
            return await ctx.reply(err)
        await member.move_to(None)
        await ctx.reply(f"🔌 Disconnected {member.mention} from voice.")

    @commands.command(name="vcmove", description="Move a member to another voice channel")
    @commands.has_permissions(move_members=True)
    async def vcmove(self, ctx, member: discord.Member, channel: discord.VoiceChannel):
        if not member.voice or not member.voice.channel:
            return await ctx.reply("❌ Member is not connected to voice.")
        await member.move_to(channel)
        await ctx.reply(f"🚚 Moved {member.mention} to {channel.mention}.")

    @commands.command(name="deafen", description="Server deafen a member in voice")
    @commands.has_permissions(deafen_members=True)
    async def deafen(self, ctx, member: discord.Member):
        if not member.voice:
            return await ctx.reply("❌ Member is not in voice.")
        await member.edit(deafen=True)
        await ctx.reply(f"🔇 Server deafened {member.mention}.")

    @commands.command(name="undeafen", description="Server undeafen a member in voice")
    @commands.has_permissions(deafen_members=True)
    async def undeafen(self, ctx, member: discord.Member):
        if not member.voice:
            return await ctx.reply("❌ Member is not in voice.")
        await member.edit(deafen=False)
        await ctx.reply(f"🔊 Server undeafened {member.mention}.")

    @commands.command(name="banlist", description="List banned users in the server")
    @commands.has_permissions(ban_members=True)
    async def banlist(self, ctx):
        bans = [entry async for entry in ctx.guild.bans(limit=25)]
        if not bans:
            return await ctx.reply("✅ No banned users in this server.")
        desc = [f"• **{b.user}** (`{b.user.id}`) — *{b.reason or 'No reason'}*" for b in bans]
        embed = discord.Embed(title=f"⛔ Server Bans ({len(bans)})", description="\n".join(desc), color=ERROR_COLOR)
        await ctx.reply(embed=embed)

    @commands.command(name="slowmode_off", description="Turn off slowmode in current channel")
    @commands.has_permissions(manage_channels=True)
    async def slowmode_off(self, ctx):
        await ctx.channel.edit(slowmode_delay=0)
        await ctx.reply("⚡ Slowmode disabled.")

    @commands.command(name="hide_channel", description="Hide channel from @everyone")
    @commands.has_permissions(manage_channels=True)
    async def hide_channel(self, ctx):
        await ctx.channel.set_permissions(ctx.guild.default_role, read_messages=False)
        await ctx.reply(f"🔒 Channel {ctx.channel.mention} is now hidden from @everyone.")

    @commands.command(name="unhide_channel", description="Unhide channel for @everyone")
    @commands.has_permissions(manage_channels=True)
    async def unhide_channel(self, ctx):
        await ctx.channel.set_permissions(ctx.guild.default_role, read_messages=True)
        await ctx.reply(f"🔓 Channel {ctx.channel.mention} is now visible to @everyone.")

    @commands.command(name="clone_channel", description="Clone the current channel with identical permissions")
    @commands.has_permissions(manage_channels=True)
    async def clone_channel(self, ctx):
        cloned = await ctx.channel.clone(name=f"{ctx.channel.name}-clone")
        await ctx.reply(f"🐑 Channel cloned successfully: {cloned.mention}")

    @commands.command(name="nuke_channel", description="Re-create channel to purge all messages and reset")
    @commands.has_permissions(administrator=True)
    async def nuke_channel(self, ctx):
        pos = ctx.channel.position
        new_ch = await ctx.channel.clone()
        await ctx.channel.delete()
        await new_ch.edit(position=pos)
        await new_ch.send("💣 **Channel Nuked!** Cleared all message history.", delete_after=10)

    @commands.command(name="nick_reset", description="Reset a member's nickname to their default username")
    @commands.has_permissions(manage_nicknames=True)
    async def nick_reset(self, ctx, member: discord.Member):
        if err := role_guard(ctx, member):
            return await ctx.reply(err)
        await member.edit(nick=None)
        await ctx.reply(f"🔄 Reset nickname for {member.mention}.")

    @commands.command(name="mute_vc_all", description="Mute all members currently in your voice channel")
    @commands.has_permissions(mute_members=True)
    async def mute_vc_all(self, ctx):
        if not ctx.author.voice or not ctx.author.voice.channel:
            return await ctx.reply("❌ You are not connected to a voice channel.")
        vc = ctx.author.voice.channel
        count = 0
        for m in vc.members:
            if m != ctx.author and not m.bot:
                try:
                    await m.edit(mute=True)
                    count += 1
                except Exception:
                    pass
        await ctx.reply(f"🔇 Muted **{count}** members in {vc.mention}.")

    @commands.command(name="unmute_vc_all", description="Unmute all members in your voice channel")
    @commands.has_permissions(mute_members=True)
    async def unmute_vc_all(self, ctx):
        if not ctx.author.voice or not ctx.author.voice.channel:
            return await ctx.reply("❌ You are not connected to a voice channel.")
        vc = ctx.author.voice.channel
        count = 0
        for m in vc.members:
            if not m.bot:
                try:
                    await m.edit(mute=False)
                    count += 1
                except Exception:
                    pass
        await ctx.reply(f"🔊 Unmuted **{count}** members in {vc.mention}.")

    @commands.command(name="role_add", description="Add a role to a member: &role_add @user @role")
    @commands.has_permissions(manage_roles=True)
    async def role_add(self, ctx, member: discord.Member, role: discord.Role):
        if err := role_guard(ctx, member):
            return await ctx.reply(err)
        await member.add_roles(role)
        await ctx.reply(f"✅ Added {role.mention} to {member.mention}.")

    @commands.command(name="role_remove", description="Remove a role from a member: &role_remove @user @role")
    @commands.has_permissions(manage_roles=True)
    async def role_remove(self, ctx, member: discord.Member, role: discord.Role):
        if err := role_guard(ctx, member):
            return await ctx.reply(err)
        await member.remove_roles(role)
        await ctx.reply(f"🗑️ Removed {role.mention} from {member.mention}.")

async def setup(bot):
    await bot.add_cog(Moderation(bot))
