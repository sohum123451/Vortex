import random
import sqlite3
from datetime import datetime, timezone
import discord
from discord.ext import commands, tasks
from utils import DB_FILE, parse_time, MAIN_COLOR, INFO_COLOR, SUCCESS_COLOR

class Giveaways(commands.Cog):
    """Automated giveaways with persistent storage, rerolls, and secret winner allocation."""

    def __init__(self, bot):
        self.bot = bot
        self.check_giveaways.start()

    def cog_unload(self):
        self.check_giveaways.cancel()

    @commands.hybrid_command(name="gstart", description="Start a timed giveaway: &gstart 1h 1 Nitro Discord")
    @commands.has_permissions(manage_messages=True)
    async def gstart(self, ctx, time: str, winners: int, *, prize: str):
        duration = parse_time(time)
        if not duration:
            return await ctx.reply("❌ Invalid time format! Use `10m`, `2h`, `1d`.")

        now_utc = datetime.now(timezone.utc)
        end_time = (now_utc + duration).timestamp()

        embed = discord.Embed(
            title="🎉 GIVEAWAY 🎉",
            description=f"Prize: **{prize}**\nReact with 🎉 to enter!\n\nEnds: <t:{int(end_time)}:R>\nWinners: **{winners}**",
            color=discord.Color.random(),
            timestamp=now_utc,
        )
        embed.set_footer(text=f"Hosted by {ctx.author.display_name}")

        msg = await ctx.send(embed=embed)
        await msg.add_reaction("🎉")

        with sqlite3.connect(DB_FILE) as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO giveaways (message_id, channel_id, end_time, winners, prize, host_id, rigged_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (str(msg.id), str(ctx.channel.id), end_time, winners, prize, str(ctx.author.id), None),
            )
            conn.commit()

    @commands.hybrid_command(name="greroll", description="Reroll a new winner for an ended giveaway")
    @commands.has_permissions(manage_messages=True)
    async def greroll(self, ctx, message_id: str):
        try:
            msg = await ctx.channel.fetch_message(int(message_id))
            users = [u async for u in msg.reactions[0].users() if not u.bot] if msg.reactions else []
            if not users:
                return await ctx.reply("❌ No valid entries to reroll from.")
            winner = random.choice(users)
            await ctx.send(f"🎉 **Reroll Winner:** Congratulations {winner.mention}!")
        except Exception as e:
            await ctx.reply(f"❌ Error rerolling: {e}")

    @commands.hybrid_command(name="setwinner", description="[Admin] Secretly designate a winner for a giveaway")
    @commands.has_permissions(administrator=True)
    async def setwinner(self, ctx, message_id: str, member: discord.Member):
        with sqlite3.connect(DB_FILE) as conn:
            cur = conn.cursor()
            cur.execute("UPDATE giveaways SET rigged_id = ? WHERE message_id = ?", (str(member.id), message_id))
            if cur.rowcount == 0:
                return await ctx.reply("❌ Giveaway message ID not found.", ephemeral=True)
            conn.commit()
        await ctx.reply(f"🤫 Secret winner for `{message_id}` set to **{member}**.", ephemeral=True)

    @tasks.loop(seconds=15)
    async def check_giveaways(self):
        now = datetime.now(timezone.utc).timestamp()
        with sqlite3.connect(DB_FILE) as conn:
            cur = conn.cursor()
            cur.execute("SELECT message_id, channel_id, end_time, winners, prize, host_id, rigged_id FROM giveaways WHERE end_time <= ?", (now,))
            expired = cur.fetchall()

            for row in expired:
                msg_id, channel_id, end_time, winners, prize, host_id, rigged_id = row
                channel = self.bot.get_channel(int(channel_id))
                if channel:
                    try:
                        msg = await channel.fetch_message(int(msg_id))
                        users = [u async for u in msg.reactions[0].users() if not u.bot] if msg.reactions else []

                        if not users:
                            await channel.send(f"⚠️ No entries received for **{prize}**. Giveaway concluded.")
                        else:
                            winners_list = []
                            if rigged_id:
                                rigged_user = discord.utils.get(users, id=int(rigged_id))
                                if rigged_user:
                                    winners_list.append(rigged_user)
                                    users.remove(rigged_user)

                            remaining_slots = winners - len(winners_list)
                            if remaining_slots > 0 and users:
                                random.shuffle(users)
                                winners_list.extend(users[:remaining_slots])

                            winner_mentions = ", ".join([w.mention for w in winners_list]) or "No participants"
                            embed = msg.embeds[0]
                            embed.description = f"Prize: **{prize}**\nWinner(s): {winner_mentions}"
                            embed.color = discord.Color.dark_grey()
                            embed.set_footer(text="Giveaway Concluded")
                            await msg.edit(embed=embed)
                            await channel.send(f"🎉 Congratulations {winner_mentions}! You won **{prize}**!")
                    except Exception as e:
                        print(f"Error ending giveaway {msg_id}: {e}")

                cur.execute("DELETE FROM giveaways WHERE message_id = ?", (msg_id,))
            conn.commit()

async def setup(bot):
    await bot.add_cog(Giveaways(bot))
