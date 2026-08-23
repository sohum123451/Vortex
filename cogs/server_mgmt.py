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
    @commands.hybrid_command(name="sticky", description="Set a sticky message that stays at the bottom of channel")
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

    @commands.hybrid_command(name="unsticky", description="Remove sticky message from channel")
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

    @commands.command(name="server_features_list", description="View enabled Discord server features")
    async def server_features_list(self, ctx):
        if ctx.guild:
            feats = ctx.guild.features
            await ctx.reply(f"🌟 **Features ({len(feats)}):** " + (", ".join(feats) if feats else "None"))

async def setup(bot):
    await bot.add_cog(ServerManagement(bot))
