import asyncio
import io
import sqlite3
from datetime import datetime, timezone
import discord
from discord.ext import commands
from utils import DB_FILE, MAIN_COLOR, SUCCESS_COLOR, ERROR_COLOR, INFO_COLOR

class TicketCloseView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Close Ticket", emoji="🔒", style=discord.ButtonStyle.danger, custom_id="vortex_ticket_close")
    async def close_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("⚠️ Closing this ticket in 5 seconds...")
        await asyncio.sleep(5)
        try:
            await interaction.channel.delete()
        except Exception:
            pass

class TicketCreateView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Create Ticket", emoji="🎫", style=discord.ButtonStyle.primary, custom_id="vortex_ticket_create")
    async def create_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        user = interaction.user
        category = discord.utils.get(guild.categories, name="Tickets")
        if not category:
            category = await guild.create_category("Tickets")

        # Check existing ticket
        existing = discord.utils.get(category.text_channels, name=f"ticket-{user.name.lower()[:15]}")
        if existing:
            return await interaction.response.send_message(f"❌ You already have an open ticket in {existing.mention}!", ephemeral=True)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True),
        }
        chan = await category.create_text_channel(name=f"ticket-{user.name.lower()[:15]}", overwrites=overwrites)
        
        embed = discord.Embed(
            title=f"🎫 Ticket #{chan.name}",
            description=f"Welcome {user.mention}!\nPlease describe your issue or inquiry in detail. Support staff will assist you shortly.\n\nClick **Close Ticket** below when finished.",
            color=INFO_COLOR,
            timestamp=datetime.now(timezone.utc),
        )
        await chan.send(content=f"{user.mention} | Support Team", embed=embed, view=TicketCloseView())
        await interaction.response.send_message(f"✅ Ticket created in {chan.mention}!", ephemeral=True)

class Tickets(commands.Cog):
    """Interactive support ticket system with automated channel routing and transcripts."""

    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="ticket_setup", description="Deploy the ticket creation panel in current channel")
    @commands.has_permissions(administrator=True)
    async def ticket_setup(self, ctx, title: str = "Support Ticket Helpdesk"):
        embed = discord.Embed(
            title=f"🎫 {title}",
            description="Need help, want to report a user, or have questions for staff?\n\nClick the **Create Ticket** button below to open a private channel with our staff team.",
            color=MAIN_COLOR,
        )
        embed.set_footer(text="Vortex Automated Ticket Dispatcher")
        await ctx.channel.send(embed=embed, view=TicketCreateView())
        await ctx.reply("✅ Ticket panel deployed!", ephemeral=True)

    @commands.command(name="ticket_add", description="Add a member to the current ticket channel")
    @commands.has_permissions(manage_channels=True)
    async def ticket_add(self, ctx, member: discord.Member):
        if not ctx.channel.name.startswith("ticket-"):
            return await ctx.reply("❌ This command can only be used inside a ticket channel.")
        await ctx.channel.set_permissions(member, read_messages=True, send_messages=True)
        await ctx.reply(f"✅ Added {member.mention} to this ticket.")

    @commands.command(name="ticket_remove", description="Remove a member from the ticket channel")
    @commands.has_permissions(manage_channels=True)
    async def ticket_remove(self, ctx, member: discord.Member):
        if not ctx.channel.name.startswith("ticket-"):
            return await ctx.reply("❌ This command can only be used inside a ticket channel.")
        await ctx.channel.set_permissions(member, overwrite=None)
        await ctx.reply(f"❌ Removed {member.mention} from this ticket.")

    @commands.hybrid_command(name="ticket_close", description="Close and delete the current ticket channel")
    @commands.has_permissions(manage_channels=True)
    async def ticket_close(self, ctx):
        if not ctx.channel.name.startswith("ticket-"):
            return await ctx.reply("❌ This command can only be used inside a ticket channel.")
        await ctx.reply("🔒 Closing ticket in 5 seconds...")
        await asyncio.sleep(5)
        await ctx.channel.delete()

    @commands.command(name="ticket_transcript", description="Generate a text transcript of this ticket")
    @commands.has_permissions(manage_channels=True)
    async def ticket_transcript(self, ctx):
        if not ctx.channel.name.startswith("ticket-"):
            return await ctx.reply("❌ This command can only be used inside a ticket channel.")
        messages = [m async for m in ctx.channel.history(limit=500, oldest_first=True)]
        lines = [f"[{m.created_at.strftime('%Y-%m-%d %H:%M:%S')}] {m.author}: {m.clean_content}" for m in messages]
        buffer = io.StringIO("\n".join(lines))
        file = discord.File(fp=io.BytesIO(buffer.getvalue().encode()), filename=f"{ctx.channel.name}_transcript.txt")
        await ctx.reply(content="📄 **Ticket Transcript:**", file=file)

async def setup(bot):
    await bot.add_cog(Tickets(bot))
    bot.add_view(TicketCreateView())
    bot.add_view(TicketCloseView())
