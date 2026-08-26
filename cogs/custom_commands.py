import asyncio
import sqlite3
from datetime import datetime, timezone
import discord
from discord.ext import commands
from utils import DB_FILE, MAIN_COLOR, SUCCESS_COLOR, ERROR_COLOR, INFO_COLOR

class CustomCommands(commands.Cog):
    """Custom server tags, auto-responders, and snippet triggers."""

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return
        content = message.content.strip().lower()
        if not content or content.startswith("&"):
            return

        with sqlite3.connect(DB_FILE) as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT trigger_text, response_text, is_exact FROM autoresponders WHERE guild_id = ?",
                (str(message.guild.id),),
            )
            rows = cur.fetchall()

        for trigger, response, is_exact in rows:
            if is_exact and content == trigger.lower():
                return await message.channel.send(response)
            elif not is_exact and trigger.lower() in content:
                return await message.channel.send(response)

    @commands.hybrid_command(name="tag", description="Recall a custom server tag: &tag <tag_name>")
    async def tag(self, ctx, tag_name: str):
        if not ctx.guild:
            return await ctx.reply("❌ Server only.")
        tname = tag_name.lower().strip()
        with sqlite3.connect(DB_FILE) as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT content, uses FROM custom_tags WHERE guild_id = ? AND tag_name = ?",
                (str(ctx.guild.id), tname),
            )
            row = cur.fetchone()
            if not row:
                return await ctx.reply(f"❌ Tag `{tname}` does not exist. Use `&tag_add` to create it.")
            content, uses = row
            cur.execute(
                "UPDATE custom_tags SET uses = uses + 1 WHERE guild_id = ? AND tag_name = ?",
                (str(ctx.guild.id), tname),
            )
            conn.commit()

        await ctx.reply(content)

    @commands.command(name="tag_add", description="Create a custom server tag: &tag_add <name> <content>")
    @commands.has_permissions(manage_messages=True)
    async def tag_add(self, ctx, tag_name: str, *, content: str):
        tname = tag_name.lower().strip()
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(DB_FILE) as conn:
            cur = conn.cursor()
            try:
                cur.execute(
                    "INSERT INTO custom_tags (guild_id, tag_name, content, author_id, created_at, uses) VALUES (?, ?, ?, ?, ?, 0)",
                    (str(ctx.guild.id), tname, content, str(ctx.author.id), now),
                )
                conn.commit()
                await ctx.reply(f"✅ Tag `{tname}` created successfully!")
            except sqlite3.IntegrityError:
                await ctx.reply(f"❌ A tag named `{tname}` already exists. Use `&tag_edit`.")

    @commands.command(name="tag_edit", description="Edit an existing server tag: &tag_edit <name> <new_content>")
    @commands.has_permissions(manage_messages=True)
    async def tag_edit(self, ctx, tag_name: str, *, content: str):
        tname = tag_name.lower().strip()
        with sqlite3.connect(DB_FILE) as conn:
            cur = conn.cursor()
            cur.execute(
                "UPDATE custom_tags SET content = ? WHERE guild_id = ? AND tag_name = ?",
                (content, str(ctx.guild.id), tname),
            )
            if cur.rowcount == 0:
                return await ctx.reply(f"❌ Tag `{tname}` not found.")
            conn.commit()
        await ctx.reply(f"✏️ Tag `{tname}` updated successfully.")

    @commands.command(name="tag_delete", description="Delete a server tag: &tag_delete <name>")
    @commands.has_permissions(manage_messages=True)
    async def tag_delete(self, ctx, tag_name: str):
        tname = tag_name.lower().strip()
        with sqlite3.connect(DB_FILE) as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM custom_tags WHERE guild_id = ? AND tag_name = ?", (str(ctx.guild.id), tname))
            if cur.rowcount == 0:
                return await ctx.reply(f"❌ Tag `{tname}` not found.")
            conn.commit()
        await ctx.reply(f"🗑️ Tag `{tname}` deleted.")

    @commands.command(name="tag_list", description="List all custom tags created in this server")
    async def tag_list(self, ctx):
        if not ctx.guild:
            return await ctx.reply("❌ Server only.")
        with sqlite3.connect(DB_FILE) as conn:
            cur = conn.cursor()
            cur.execute("SELECT tag_name, uses FROM custom_tags WHERE guild_id = ? ORDER BY uses DESC", (str(ctx.guild.id),))
            rows = cur.fetchall()

        if not rows:
            return await ctx.reply("🏷️ No custom tags found in this server. Create one with `&tag_add`!")

        tag_strs = [f"`{name}` ({uses} uses)" for name, uses in rows]
        embed = discord.Embed(
            title=f"🏷️ Server Tags — {ctx.guild.name} ({len(rows)})",
            description=", ".join(tag_strs),
            color=MAIN_COLOR,
        )
        await ctx.reply(embed=embed)

    @commands.command(name="ar_add", description="Add an auto-responder trigger: &ar_add <trigger> | <response>")
    @commands.has_permissions(manage_guild=True)
    async def ar_add(self, ctx, *, text: str):
        parts = [p.strip() for p in text.split("|")]
        if len(parts) < 2:
            return await ctx.reply("❌ Usage: `&ar_add <trigger phrase> | <response message>`")
        trigger, response = parts[0], parts[1]

        with sqlite3.connect(DB_FILE) as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO autoresponders (guild_id, trigger_text, response_text, is_exact) VALUES (?, ?, ?, 0)",
                (str(ctx.guild.id), trigger, response),
            )
            conn.commit()
        await ctx.reply(f"🤖 Auto-responder created for trigger: `{trigger}`")

    @commands.command(name="ar_list", description="List all server auto-responders")
    @commands.has_permissions(manage_guild=True)
    async def ar_list(self, ctx):
        with sqlite3.connect(DB_FILE) as conn:
            cur = conn.cursor()
            cur.execute("SELECT id, trigger_text, response_text FROM autoresponders WHERE guild_id = ?", (str(ctx.guild.id),))
            rows = cur.fetchall()

        if not rows:
            return await ctx.reply("🤖 No auto-responders configured for this server.")

        lines = [f"**#{rid}** Trigger: `{trig}` ➔ `{resp[:40]}...`" for rid, trig, resp in rows]
        embed = discord.Embed(title=f"🤖 Auto-Responders ({len(rows)})", description="\n".join(lines), color=INFO_COLOR)
        await ctx.reply(embed=embed)

    @commands.command(name="tag_info", description="View author and creation info of a tag")
    async def tag_info(self, ctx, tag_name: str):
        tname = tag_name.lower().strip()
        with sqlite3.connect(DB_FILE) as conn:
            cur = conn.cursor()
            cur.execute("SELECT author_id, uses FROM custom_tags WHERE guild_id = ? AND tag_name = ?", (str(ctx.guild.id), tname))
            row = cur.fetchone()
        if not row:
            return await ctx.reply(f"❌ Tag `{tname}` not found.")
        author = self.bot.get_user(int(row[0])) or f"User ({row[0]})"
        await ctx.reply(f"🏷️ **Tag:** `{tname}`\n👤 **Creator:** {author}\n📊 **Uses:** `{row[1]}`")

    @commands.command(name="tag_raw", description="Get the raw markdown text of a tag")
    async def tag_raw(self, ctx, tag_name: str):
        tname = tag_name.lower().strip()
        with sqlite3.connect(DB_FILE) as conn:
            cur = conn.cursor()
            cur.execute("SELECT content FROM custom_tags WHERE guild_id = ? AND tag_name = ?", (str(ctx.guild.id), tname))
            row = cur.fetchone()
        if not row:
            return await ctx.reply(f"❌ Tag `{tname}` not found.")
        await ctx.reply(f"```markdown\n{row[0][:1900]}\n```")

    @commands.command(name="tag_search", description="Search tags matching a keyword: &tag_search <query>")
    async def tag_search(self, ctx, query: str):
        with sqlite3.connect(DB_FILE) as conn:
            cur = conn.cursor()
            cur.execute("SELECT tag_name FROM custom_tags WHERE guild_id = ? AND tag_name LIKE ?", (str(ctx.guild.id), f"%{query.lower()}%"))
            rows = cur.fetchall()
        if not rows:
            return await ctx.reply(f"🔍 No tags matched `{query}`.")
        tags = [f"`{r[0]}`" for r in rows]
        await ctx.reply(f"🔍 **Matching Tags ({len(tags)}):** {', '.join(tags)}")

    @commands.command(name="ar_delete", description="Delete an auto-responder by ID: &ar_delete <id>")
    @commands.has_permissions(manage_guild=True)
    async def ar_delete(self, ctx, ar_id: int):
        with sqlite3.connect(DB_FILE) as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM autoresponders WHERE guild_id = ? AND id = ?", (str(ctx.guild.id), ar_id))
            if cur.rowcount == 0:
                return await ctx.reply(f"❌ Auto-responder `#{ar_id}` not found.")
            conn.commit()
        await ctx.reply(f"🗑️ Auto-responder `#{ar_id}` removed.")

    @commands.command(name="ar_clear", description="Clear all auto-responders in this server")
    @commands.has_permissions(administrator=True)
    async def ar_clear(self, ctx):
        with sqlite3.connect(DB_FILE) as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM autoresponders WHERE guild_id = ?", (str(ctx.guild.id),))
            count = cur.rowcount
            conn.commit()
        await ctx.reply(f"🧹 Cleared **{count}** auto-responders.")

    @commands.command(name="quick_note", description="Store a private scratchpad note for yourself: &quick_note <text>")
    async def quick_note(self, ctx, *, text: str):
        await ctx.reply(f"📝 **Note Saved:** *\"{text[:500]}\"* (Stored in chat history)")

    @commands.command(name="echo_embed", description="Broadcast text inside a custom embed: &echo_embed <text>")
    @commands.has_permissions(manage_messages=True)
    async def echo_embed(self, ctx, *, text: str):
        embed = discord.Embed(description=text, color=MAIN_COLOR)
        await ctx.send(embed=embed)
        try: await ctx.message.delete()
        except Exception: pass

    @commands.command(name="announce_embed", description="Send formal announcement: &announce_embed <title> | <text>")
    @commands.has_permissions(mention_everyone=True)
    async def announce_embed(self, ctx, *, content: str):
        parts = [p.strip() for p in content.split("|")]
        title = parts[0] if len(parts) > 1 else "📢 Server Announcement"
        body = parts[1] if len(parts) > 1 else parts[0]
        embed = discord.Embed(title=title, description=body, color=WARN_COLOR)
        embed.set_footer(text=f"Announced by {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(CustomCommands(bot))
