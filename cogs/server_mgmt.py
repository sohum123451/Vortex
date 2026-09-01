import asyncio
import json
import sqlite3
from datetime import datetime, timezone
import discord
from discord.ext import commands
from utils import DB_FILE, MAIN_COLOR, SUCCESS_COLOR, ERROR_COLOR, INFO_COLOR, WARN_COLOR

class ServerManagement(commands.Cog):
    """Server administration, role automation, channel control, and announcement tools."""

    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="announce", description="Send styled announcement embed: &announce #channel Title | Message")
    @commands.has_permissions(manage_guild=True)
    async def announce(self, ctx, channel: discord.TextChannel, title: str, *, message: str):
        embed = discord.Embed(
            title=f"📢 {title}",
            description=message,
            color=MAIN_COLOR,
            timestamp=datetime.now(timezone.utc),
        )
        embed.set_footer(text=f"Announced by {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
        await channel.send(embed=embed)
        await ctx.reply(f"✅ Announcement sent to {channel.mention}!")

    @commands.hybrid_command(name="embed", description="Create custom embed: &embed Title | Description | [Color Hex]")
    @commands.has_permissions(manage_messages=True)
    async def embed_create(self, ctx, *, raw_input: str):
        parts = [p.strip() for p in raw_input.split("|")]
        if len(parts) < 2:
            return await ctx.reply("❌ Usage: `&embed Title | Description | [#HEX_COLOR]`")
        title = parts[0]
        desc = parts[1]
        color = MAIN_COLOR
        if len(parts) >= 3:
            hex_val = parts[2].strip("#")
            if len(hex_val) == 6:
                try:
                    color = discord.Color(int(hex_val, 16))
                except ValueError:
                    pass

        embed = discord.Embed(title=title, description=desc, color=color, timestamp=datetime.now(timezone.utc))
        embed.set_footer(text=f"Requested by {ctx.author.display_name}")
        await ctx.channel.send(embed=embed)

    @commands.hybrid_command(name="poll", description="Create interactive poll: &poll Question | Opt1 | Opt2 ...")
    async def poll(self, ctx, *, poll_input: str):
        parts = [p.strip() for p in poll_input.split("|")]
        if len(parts) < 3:
            return await ctx.reply("❌ Usage: `&poll Question | Option 1 | Option 2 [| Option 3...]` (up to 10)")
        question = parts[0]
        options = parts[1:11]
        emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]

        desc = [f"{emojis[i]} **{opt}**" for i, opt in enumerate(options)]
        embed = discord.Embed(
            title=f"📊 {question}",
            description="\n\n".join(desc),
            color=INFO_COLOR,
            timestamp=datetime.now(timezone.utc),
        )
        embed.set_footer(text=f"Poll created by {ctx.author.display_name}")
        poll_msg = await ctx.send(embed=embed)
        for i in range(len(options)):
            await poll_msg.add_reaction(emojis[i])

    # Sticky Messages
    @commands.command(name="sticky", description="Set a sticky message that stays at the bottom of channel")
    @commands.has_permissions(manage_messages=True)
    async def sticky(self, ctx, *, text: str):
        with sqlite3.connect(DB_FILE) as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT OR REPLACE INTO sticky (channel_id, message_text, last_msg_id) VALUES (?, ?, ?)",
                (str(ctx.channel.id), text, None),
            )
            conn.commit()
        await ctx.reply(f"📌 Sticky message set for {ctx.channel.mention}!")

    @commands.command(name="unsticky", description="Remove sticky message from channel")
    @commands.has_permissions(manage_messages=True)
    async def unsticky(self, ctx):
        with sqlite3.connect(DB_FILE) as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM sticky WHERE channel_id = ?", (str(ctx.channel.id),))
            conn.commit()
        await ctx.reply(f"🧹 Removed sticky message from {ctx.channel.mention}.")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return

        with sqlite3.connect(DB_FILE) as conn:
            cur = conn.cursor()
            cur.execute("SELECT message_text, last_msg_id FROM sticky WHERE channel_id = ?", (str(message.channel.id),))
            row = cur.fetchone()
            if row:
                text, last_msg_id = row
                if last_msg_id:
                    try:
                        old_msg = await message.channel.fetch_message(int(last_msg_id))
                        await old_msg.delete()
                    except Exception:
                        pass
                embed = discord.Embed(description=f"📌 **Sticky Note:**\n{text}", color=WARN_COLOR)
                new_msg = await message.channel.send(embed=embed)
                cur.execute("UPDATE sticky SET last_msg_id = ? WHERE channel_id = ?", (str(new_msg.id), str(message.channel.id)))
                conn.commit()

    # Role Management
    @commands.command(name="rolecreate", description="Create a server role: &rolecreate ModRole #FF0000")
    @commands.has_permissions(manage_roles=True)
    async def rolecreate(self, ctx, name: str, color_hex: str = None):
        color = discord.Color.default()
        if color_hex:
            try:
                color = discord.Color(int(color_hex.strip("#"), 16))
            except ValueError:
                pass
        role = await ctx.guild.create_role(name=name, color=color)
        await ctx.reply(f"✅ Role created: {role.mention}")

    @commands.command(name="roledelete", description="Delete a server role")
    @commands.has_permissions(manage_roles=True)
    async def roledelete(self, ctx, role: discord.Role):
        await role.delete()
        await ctx.reply(f"🗑️ Deleted role **{role.name}**.")

    @commands.command(name="roleadd", description="Add a role to a member")
    @commands.has_permissions(manage_roles=True)
    async def roleadd(self, ctx, member: discord.Member, role: discord.Role):
        await member.add_roles(role)
        await ctx.reply(f"✅ Added {role.mention} to {member.mention}.")

    @commands.command(name="roleremove", description="Remove a role from a member")
    @commands.has_permissions(manage_roles=True)
    async def roleremove(self, ctx, member: discord.Member, role: discord.Role):
        await member.remove_roles(role)
        await ctx.reply(f"❌ Removed {role.mention} from {member.mention}.")

    @commands.command(name="role_all", description="Mass-assign a role to all human members")
    @commands.has_permissions(administrator=True)
    async def role_all(self, ctx, role: discord.Role):
        msg = await ctx.reply(f"⏳ Mass-assigning {role.mention} to all humans...")
        count = 0
        for m in ctx.guild.members:
            if not m.bot and role not in m.roles:
                try:
                    await m.add_roles(role)
                    count += 1
                except Exception:
                    pass
        await msg.edit(content=f"✅ Assigned {role.mention} to **{count}** members.")

    @commands.command(name="role_bots", description="Mass-assign a role to all bot members")
    @commands.has_permissions(administrator=True)
    async def role_bots(self, ctx, role: discord.Role):
        msg = await ctx.reply(f"⏳ Mass-assigning {role.mention} to all bots...")
        count = 0
        for m in ctx.guild.members:
            if m.bot and role not in m.roles:
                try:
                    await m.add_roles(role)
                    count += 1
                except Exception:
                    pass
        await msg.edit(content=f"✅ Assigned {role.mention} to **{count}** bots.")

    @commands.command(name="channel_create", description="Create a new text or voice channel")
    @commands.has_permissions(manage_channels=True)
    async def channel_create(self, ctx, name: str, chan_type: str = "text"):
        if chan_type.lower() == "voice":
            c = await ctx.guild.create_voice_channel(name)
        else:
            c = await ctx.guild.create_text_channel(name)
        await ctx.reply(f"✅ Created channel: {c.mention if chan_type.lower() == 'text' else c.name}")

    @commands.command(name="channel_delete", description="Delete a channel")
    @commands.has_permissions(manage_channels=True)
    async def channel_delete(self, ctx, channel: discord.abc.GuildChannel = None):
        target = channel or ctx.channel
        await target.delete()
        if target != ctx.channel:
            await ctx.reply(f"🗑️ Deleted channel `{target.name}`.")

    @commands.command(name="channel_rename", description="Rename a channel")
    @commands.has_permissions(manage_channels=True)
    async def channel_rename(self, ctx, channel: discord.abc.GuildChannel, new_name: str):
        await channel.edit(name=new_name)
        await ctx.reply(f"✏️ Renamed channel to **{new_name}**.")

    @commands.command(name="server_emojis", description="List all server emojis with count breakdown")
    async def server_emojis(self, ctx):
        static = [str(e) for e in ctx.guild.emojis if not e.animated]
        animated = [str(e) for e in ctx.guild.emojis if e.animated]
        embed = discord.Embed(
            title=f"🎭 Server Emojis ({len(ctx.guild.emojis)})",
            color=MAIN_COLOR,
        )
        embed.add_field(name=f"Static ({len(static)})", value=" ".join(static[:30]) or "None", inline=False)
        embed.add_field(name=f"Animated ({len(animated)})", value=" ".join(animated[:30]) or "None", inline=False)
        await ctx.reply(embed=embed)

    @commands.command(name="role_hoist", description="Make a role displayed separately on member list")
    @commands.has_permissions(manage_roles=True)
    async def role_hoist(self, ctx, role: discord.Role):
        await role.edit(hoist=True)
        await ctx.reply(f"✅ Role {role.mention} is now hoisted (displayed separately).")

    @commands.command(name="role_unhoist", description="Remove hoist from a role")
    @commands.has_permissions(manage_roles=True)
    async def role_unhoist(self, ctx, role: discord.Role):
        await role.edit(hoist=False)
        await ctx.reply(f"✅ Role {role.mention} is now unhoisted.")

    @commands.command(name="role_mentionable", description="Make a role mentionable by everyone")
    @commands.has_permissions(manage_roles=True)
    async def role_mentionable(self, ctx, role: discord.Role):
        await role.edit(mentionable=True)
        await ctx.reply(f"✅ Role {role.mention} is now mentionable.")

    @commands.command(name="role_unmentionable", description="Make a role unmentionable by everyone")
    @commands.has_permissions(manage_roles=True)
    async def role_unmentionable(self, ctx, role: discord.Role):
        await role.edit(mentionable=False)
        await ctx.reply(f"✅ Role {role.mention} is now unmentionable.")

    @commands.command(name="channel_rename", description="Rename a text/voice channel")
    @commands.has_permissions(manage_channels=True)
    async def channel_rename(self, ctx, channel: discord.abc.GuildChannel, *, new_name: str):
        old = channel.name
        await channel.edit(name=new_name)
        await ctx.reply(f"✏️ Renamed channel `#{old}` to `#{new_name}`.")

    @commands.command(name="channel_topic_set", description="Set channel topic description")
    @commands.has_permissions(manage_channels=True)
    async def channel_topic_set(self, ctx, *, topic_text: str):
        if isinstance(ctx.channel, discord.TextChannel):
            await ctx.channel.edit(topic=topic_text)
            await ctx.reply(f"📝 Channel topic updated: *\"{topic_text}\"*")
        else:
            await ctx.reply("❌ Channel topic only available in text channels.")

    @commands.command(name="channel_nsfw_on", description="Mark channel as Age-Restricted (NSFW)")
    @commands.has_permissions(manage_channels=True)
    async def channel_nsfw_on(self, ctx):
        if isinstance(ctx.channel, discord.TextChannel):
            await ctx.channel.edit(nsfw=True)
            await ctx.reply("🔞 Channel is now marked as Age-Restricted (NSFW).")

    @commands.command(name="channel_nsfw_off", description="Remove Age-Restricted mark from channel")
    @commands.has_permissions(manage_channels=True)
    async def channel_nsfw_off(self, ctx):
        if isinstance(ctx.channel, discord.TextChannel):
            await ctx.channel.edit(nsfw=False)
            await ctx.reply("🟢 Age-Restricted flag removed from channel.")

    @commands.command(name="channel_sync_perms", description="Sync channel permissions with its category")
    @commands.has_permissions(manage_channels=True)
    async def channel_sync_perms(self, ctx):
        if ctx.channel.category:
            await ctx.channel.sync_permissions()
            await ctx.reply(f"🔄 Synced permissions with category **{ctx.channel.category.name}**.")
        else:
            await ctx.reply("❌ This channel is not inside a category.")

    @commands.command(name="server_name_view", description="View server name and ID")
    async def server_name_view(self, ctx):
        if ctx.guild:
            await ctx.reply(f"🏰 **Server:** `{ctx.guild.name}` (ID: `{ctx.guild.id}`)")

    @commands.command(name="server_owner_view", description="View guild owner")
    async def server_owner_view(self, ctx):
        if ctx.guild and ctx.guild.owner:
            await ctx.reply(f"👑 **Guild Owner:** {ctx.guild.owner.mention} (`{ctx.guild.owner}`)")

    @commands.command(name="server_created", description="View server creation date")
    async def server_created(self, ctx):
        if ctx.guild:
            await ctx.reply(f"📅 **Server Created:** <t:{int(ctx.guild.created_at.timestamp())}:F> (<t:{int(ctx.guild.created_at.timestamp())}:R>)")

    @commands.command(name="server_roles_list", description="View all role names in server")
    async def server_roles_list(self, ctx):
        if ctx.guild:
            roles = [r.name for r in ctx.guild.roles if r.name != "@everyone"]
            await ctx.reply(f"🎭 **Roles ({len(roles)}):** " + ", ".join(roles[:25]))

    # =========================================================================
    # ⚙️ CUSTOM SERVER PREFIX SYSTEM
    # =========================================================================

    @commands.hybrid_command(name="setprefix", description="Change the bot command prefix for this server: &setprefix <prefix>")
    @commands.has_permissions(manage_guild=True)
    async def setprefix(self, ctx, new_prefix: str):
        """Changes the prefix used to invoke commands in this server."""
        if not ctx.guild:
            return await ctx.reply("❌ Custom prefixes can only be configured inside a Discord server.")
        
        clean_prefix = new_prefix.strip()
        if len(clean_prefix) > 10:
            return await ctx.reply("❌ Prefix cannot exceed 10 characters.")
        if any(c.isspace() for c in clean_prefix):
            return await ctx.reply("❌ Prefix cannot contain whitespace spaces.")

        gid = str(ctx.guild.id)
        with sqlite3.connect(DB_FILE) as conn:
            cur = conn.cursor()
            cur.execute("INSERT OR REPLACE INTO guild_prefixes (guild_id, prefix) VALUES (?, ?)", (gid, clean_prefix))
            conn.commit()

        # Update cache in main module
        import main
        main._prefix_cache[gid] = clean_prefix

        embed = discord.Embed(
            title="⚙️ Server Prefix Updated!",
            description=(
                f"✅ The command prefix for **{ctx.guild.name}** is now set to **`{clean_prefix}`**\n\n"
                f"• Example: `{clean_prefix}help` or `{clean_prefix}ping`\n"
                f"• You can also mention the bot anytime: {self.bot.user.mention} `help`\n"
                f"• Reset anytime with: `{clean_prefix}resetprefix`"
            ),
            color=SUCCESS_COLOR,
            timestamp=datetime.now(timezone.utc),
        )
        embed.set_footer(text=f"Changed by {ctx.author.display_name} • Default prefix '&' remains active")
        await ctx.reply(embed=embed)

    @commands.hybrid_command(name="prefix", description="View the current server command prefix")
    async def view_prefix(self, ctx):
        """Shows the active prefix configured for the server."""
        if not ctx.guild:
            return await ctx.reply("🤖 Default Prefix: `&`")
        
        gid = str(ctx.guild.id)
        current = "&"
        with sqlite3.connect(DB_FILE) as conn:
            cur = conn.cursor()
            cur.execute("SELECT prefix FROM guild_prefixes WHERE guild_id = ?", (gid,))
            row = cur.fetchone()
            if row:
                current = row[0]

        embed = discord.Embed(
            title="⚙️ Server Command Prefix",
            description=(
                f"The active prefix for **{ctx.guild.name}** is: **`{current}`**\n\n"
                f"• Run commands like: `{current}help`\n"
                f"• Change prefix (Admins): `{current}setprefix <new_prefix>`\n"
                f"• Mention prefix: {self.bot.user.mention} `help`"
            ),
            color=MAIN_COLOR,
            timestamp=datetime.now(timezone.utc),
        )
        await ctx.reply(embed=embed)

    @commands.command(name="resetprefix", description="Reset server prefix back to default '&'")
    @commands.has_permissions(manage_guild=True)
    async def resetprefix(self, ctx):
        """Resets the server prefix back to default '&'."""
        if not ctx.guild:
            return await ctx.reply("❌ This command must be used in a server.")
        
        gid = str(ctx.guild.id)
        with sqlite3.connect(DB_FILE) as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM guild_prefixes WHERE guild_id = ?", (gid,))
            conn.commit()

        import main
        main._prefix_cache.pop(gid, None)

        await ctx.reply("🔄 Prefix has been reset back to default: **`&`**")

    # =========================================================================
    # 🌐 OFFICIAL SUPPORT SERVER SETUP SUITE (&setup_support_server, &support)
    # =========================================================================

    @commands.command(name="setup_support_server", aliases=["makesupportserver", "support_setup", "init_support", "make_support_server", "remake_support_server"], description="[Admin/Owner] Turn this server into a 100% launch-ready, beautifully structured official Vortex Bot Support HQ")
    @commands.has_permissions(administrator=True)
    async def setup_support_server_cmd(self, ctx, mode: str = None):
        """1-Click enterprise support server builder: roles, 5 categories, ticket desk, sandbox, and permanent invite."""
        if not ctx.guild:
            return await ctx.reply("❌ This command must be executed within a Discord server.")

        bot_member = ctx.guild.me
        if not bot_member.guild_permissions.manage_channels or not bot_member.guild_permissions.manage_roles:
            return await ctx.reply("❌ **Missing Permissions:** Vortex requires `Manage Channels` and `Manage Roles` to construct the Support HQ.")

        msg = await ctx.reply("⚡ **Constructing Enterprise Vortex Support HQ**\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n🟡 `[Step 1/5]` Cleaning up old channels (if requested) & configuring roles...")

        # If user passed 'clean' or 'remake', clean previous channels
        if mode and mode.lower() in ["clean", "remake", "reset", "purge"]:
            for ch in list(ctx.guild.channels):
                if ch.id != ctx.channel.id:
                    try:
                        await ch.delete(reason="Support HQ Remake")
                    except Exception:
                        pass

        # 1. Create Roles Hierarchy
        founder_role = discord.utils.get(ctx.guild.roles, name="👑 Vortex Founder")
        if not founder_role:
            founder_role = await ctx.guild.create_role(
                name="👑 Vortex Founder",
                color=discord.Color.from_rgb(241, 196, 15),
                hoist=True,
                mentionable=True,
                reason="Official Support Server Setup"
            )

        manager_role = discord.utils.get(ctx.guild.roles, name="🛡️ Support Manager")
        if not manager_role:
            manager_role = await ctx.guild.create_role(
                name="🛡️ Support Manager",
                color=discord.Color.from_rgb(230, 126, 34),
                hoist=True,
                mentionable=True,
                reason="Official Support Server Setup"
            )

        agent_role = discord.utils.get(ctx.guild.roles, name="🛠️ Support Agent")
        if not agent_role:
            agent_role = await ctx.guild.create_role(
                name="🛠️ Support Agent",
                color=discord.Color.from_rgb(0, 210, 255),
                hoist=True,
                mentionable=True,
                reason="Official Support Server Setup"
            )

        vip_role = discord.utils.get(ctx.guild.roles, name="💎 VIP Supporter")
        if not vip_role:
            vip_role = await ctx.guild.create_role(
                name="💎 VIP Supporter",
                color=discord.Color.from_rgb(155, 89, 182),
                hoist=True,
                reason="Official Support Server Setup"
            )

        community_role = discord.utils.get(ctx.guild.roles, name="⚡ Community")
        if not community_role:
            community_role = await ctx.guild.create_role(
                name="⚡ Community",
                color=discord.Color.from_rgb(46, 204, 113),
                hoist=True,
                reason="Official Support Server Setup"
            )

        try:
            await ctx.author.add_roles(founder_role, manager_role, agent_role)
        except Exception:
            pass

        await msg.edit(content=(
            "⚡ **Constructing Enterprise Vortex Support HQ**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🟢 `[Step 1/5]` Roles & permission hierarchy active\n"
            "🟡 `[Step 2/5]` **Building Categories** — Creating 4 operational hubs...\n"
            "⚪ `[Step 3/5]` Setting up channels & permission overrides\n"
            "⚪ `[Step 4/5]` Deploying Ticket Desk & Welcome Guides\n"
            "⚪ `[Step 5/5]` Complete"
        ))

        # Permissions Overwrites
        read_only = {
            ctx.guild.default_role: discord.PermissionOverwrite(read_messages=True, send_messages=False),
            founder_role: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_messages=True),
            manager_role: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_messages=True),
            agent_role: discord.PermissionOverwrite(read_messages=True, send_messages=False),
        }
        ticket_overwrites = {
            ctx.guild.default_role: discord.PermissionOverwrite(read_messages=True, send_messages=False),
            agent_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            manager_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            founder_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }
        standard_overwrites = {
            ctx.guild.default_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            founder_role: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_messages=True),
        }

        # 2. CATEGORY 1: INFORMATION & WELCOME
        cat_info = await ctx.guild.create_category("📌 ━━ INFORMATION ━━", overwrites=read_only)
        ch_welcome = await ctx.guild.create_text_channel("👋┃welcome", category=cat_info, overwrites=read_only)
        ch_announcements = await ctx.guild.create_text_channel("📢┃announcements", category=cat_info, overwrites=read_only)
        ch_rules = await ctx.guild.create_text_channel("📜┃rules-and-faq", category=cat_info, overwrites=read_only)
        ch_links = await ctx.guild.create_text_channel("🔗┃official-links", category=cat_info, overwrites=read_only)

        # 3. CATEGORY 2: SUPPORT & HELP DESK
        cat_support = await ctx.guild.create_category("🎫 ━━ SUPPORT DESK ━━", overwrites=standard_overwrites)
        ch_tickets = await ctx.guild.create_text_channel("🎫┃open-a-ticket", category=cat_support, overwrites=ticket_overwrites)
        ch_help = await ctx.guild.create_text_channel("❓┃community-help", category=cat_support)
        ch_bugs = await ctx.guild.create_text_channel("🐛┃bug-reports", category=cat_support)
        ch_suggestions = await ctx.guild.create_text_channel("💡┃feature-requests", category=cat_support)

        # 4. CATEGORY 3: BOT PLAYGROUND & AI
        cat_bot = await ctx.guild.create_category("🤖 ━━ BOT PLAYGROUND ━━", overwrites=standard_overwrites)
        ch_cmds1 = await ctx.guild.create_text_channel("🤖┃bot-commands", category=cat_bot)
        ch_ai = await ctx.guild.create_text_channel("🧠┃ai-chat-lounge", category=cat_bot)
        ch_casino = await ctx.guild.create_text_channel("🎰┃casino-economy", category=cat_bot)
        ch_rpg = await ctx.guild.create_text_channel("⚔️┃games-and-rpg", category=cat_bot)

        # 5. CATEGORY 4: COMMUNITY & VOICE
        cat_community = await ctx.guild.create_category("💬 ━━ COMMUNITY LOUNGE ━━", overwrites=standard_overwrites)
        ch_chat = await ctx.guild.create_text_channel("💬┃general-chat", category=cat_community)
        ch_memes = await ctx.guild.create_text_channel("📷┃media-and-memes", category=cat_community)
        await ctx.guild.create_voice_channel("🔊┃Voice Lounge (01)", category=cat_community)
        await ctx.guild.create_voice_channel("🎵┃Music Room (01)", category=cat_community)

        await msg.edit(content=(
            "⚡ **Constructing Enterprise Vortex Support HQ**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🟢 `[Step 1/5]` Roles & hierarchy active\n"
            "🟢 `[Step 2/5]` 4 Categories created\n"
            "🟢 `[Step 3/5]` 16 Channels & Voice rooms configured\n"
            "🟡 `[Step 4/5]` **Deploying Ticket Desk & Guides** — Setting up interactive views...\n"
            "⚪ `[Step 5/5]` Complete"
        ))

        # Welcome Guide
        embed_welcome = discord.Embed(
            title="⚡ Welcome to the Official Vortex Discord Bot Support Server!",
            description=(
                "**Vortex** is an enterprise-grade multi-purpose Discord bot built for high-performance communities.\n\n"
                "**Getting Started:**\n"
                f"• 📜 Read server rules in {ch_rules.mention}\n"
                f"• 🎫 Need support or help? Open a ticket in {ch_tickets.mention}\n"
                f"• 🤖 Test 500+ bot commands in {ch_cmds1.mention}\n"
                f"• 💡 Submit telemetry ideas in {ch_suggestions.mention}\n"
                f"• 💬 Hangout with our community in {ch_chat.mention}\n\n"
                "**Official Links:**\n"
                "🌐 **Web Dashboard:** [vortex-bot-mmha.onrender.com](https://vortex-bot-mmha.onrender.com)\n"
                "🤖 **Invite Bot:** [Add Vortex to Your Server](https://discord.com/oauth2/authorize?client_id=1464522902379561100&permissions=8&scope=bot%20applications.commands)"
            ),
            color=MAIN_COLOR,
            timestamp=datetime.now(timezone.utc),
        )
        embed_welcome.set_footer(text="Official Vortex Support HQ • 24/7 High-Availability")
        await ch_welcome.send(embed=embed_welcome)

        # Rules & FAQ
        embed_rules = discord.Embed(
            title="📜 Support Server Guidelines & Rules",
            description=(
                "**1. Be Respectful**: Treat all members and staff with courtesy and professionalism.\n"
                f"**2. Dedicated Bot Channels**: Please keep command testing and spam within {ch_cmds1.mention} and {ch_ai.mention}.\n"
                f"**3. Ticket Protocol**: Open only 1 ticket at a time in {ch_tickets.mention}.\n"
                "**4. No Self-Promotion / Advertising**: Keep all discussions relevant to Vortex and gaming.\n"
                "**5. Discord Terms**: Strictly follow all Discord Community Guidelines and Terms of Service."
            ),
            color=INFO_COLOR,
        )
        await ch_rules.send(embed=embed_rules)

        # Official Links
        embed_links = discord.Embed(
            title="🔗 Vortex Official Ecosystem Links",
            description=(
                "• 🌐 **Web Dashboard:** [vortex-bot-mmha.onrender.com](https://vortex-bot-mmha.onrender.com)\n"
                "• 🤖 **OAuth2 Bot Invite:** [Invite Vortex](https://discord.com/oauth2/authorize?client_id=1464522902379561100&permissions=8&scope=bot%20applications.commands)\n"
                "• 📜 **Terms of Service:** [Terms of Service](https://vortex-bot-mmha.onrender.com/tos)\n"
                "• 🔒 **Privacy Policy:** [Privacy Policy](https://vortex-bot-mmha.onrender.com/privacy)\n"
                "• 💻 **Source Repository:** [GitHub sohum123451/Vortex](https://github.com/sohum123451/Vortex)"
            ),
            color=SUCCESS_COLOR,
        )
        await ch_links.send(embed=embed_links)

        # Deploy Interactive Ticket Desk
        tickets_cog = self.bot.get_cog("Tickets")
        if tickets_cog:
            try:
                ticket_desk_embed = discord.Embed(
                    title="🎫 Vortex Official Support Desk",
                    description=(
                        "Need assistance with bot configuration, custom server prefixes, AI integrations, or reporting issues?\n\n"
                        "Click the **Open Ticket** button below to create a private channel with our staff team!"
                    ),
                    color=MAIN_COLOR,
                )
                ticket_desk_embed.set_footer(text="Official Vortex Ticket System • Fast Response Times")
                from cogs.tickets import TicketLauncher
                await ch_tickets.send(embed=ticket_desk_embed, view=TicketLauncher())
            except Exception as te:
                print(f"Ticket desk deployment notice: {te}")

        # 6. Generate Permanent Invite & Store as Official Support Server
        invite = await ch_welcome.create_invite(max_age=0, max_uses=0, reason="Official Support Server Invite")
        invite_url = invite.url

        with sqlite3.connect(DB_FILE) as conn:
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS bot_global_config (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)
            cur.execute("INSERT OR REPLACE INTO bot_global_config (key, value) VALUES ('support_server_id', ?)", (str(ctx.guild.id),))
            cur.execute("INSERT OR REPLACE INTO bot_global_config (key, value) VALUES ('support_server_invite', ?)", (invite_url,))
            conn.commit()

        final_embed = discord.Embed(
            title="🎉 Enterprise Support Server Ready for Launch!",
            description=(
                f"**{ctx.guild.name}** is now configured as the **Official Support Headquarters of Vortex Bot**!\n\n"
                f"• **Welcome Hub:** {ch_welcome.mention}\n"
                f"• **Announcements:** {ch_announcements.mention}\n"
                f"• **Support Ticket Desk:** {ch_tickets.mention}\n"
                f"• **Bot Command Sandbox:** {ch_cmds1.mention}\n"
                f"• **AI Chat Lounge:** {ch_ai.mention}\n"
                f"• **Permanent Invite URL:** [Join Support Server]({invite_url})"
            ),
            color=SUCCESS_COLOR,
            timestamp=datetime.now(timezone.utc),
        )
        final_embed.set_footer(text="Use &support anywhere in any server to fetch this invite link")
        await msg.edit(content=None, embed=final_embed)

    @commands.hybrid_command(name="support", aliases=["supportserver", "helpserver", "officialserver"], description="Get the official Vortex Bot support server invite link")
    async def support_link(self, ctx):
        """Returns the official support server invite link and web dashboard."""
        invite_url = "https://discord.gg/vortex"
        with sqlite3.connect(DB_FILE) as conn:
            cur = conn.cursor()
            try:
                cur.execute("SELECT value FROM bot_global_config WHERE key = 'support_server_invite'")
                row = cur.fetchone()
                if row and row[0]:
                    invite_url = row[0]
            except Exception:
                pass

        embed = discord.Embed(
            title="⚡ Vortex Official Support & Community HQ",
            description=(
                "Need help, want to report a bug, or request a feature? Join our official community server!\n\n"
                f"🔗 **Support Server:** [Click to Join Community]({invite_url})\n"
                "🌐 **Web Dashboard:** [vortex-bot-mmha.onrender.com](https://vortex-bot-mmha.onrender.com)\n"
                "🤖 **Add Vortex to Your Server:** [OAuth2 Invite Link](https://discord.com/oauth2/authorize?client_id=1464522902379561100&permissions=8&scope=bot%20applications.commands)"
            ),
            color=MAIN_COLOR,
            timestamp=datetime.now(timezone.utc),
        )
        embed.set_footer(text="Official 24/7 Vortex Support")
        await ctx.reply(embed=embed)

async def setup(bot):
    await bot.add_cog(ServerManagement(bot))

