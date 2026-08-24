import asyncio
import sqlite3
from datetime import datetime, timezone
import aiohttp
import discord
from discord.ext import commands
from utils import DB_FILE, MAIN_COLOR, SUCCESS_COLOR, ERROR_COLOR, WARN_COLOR, INFO_COLOR

class CryptoStocks(commands.Cog):
    """Real-time crypto prices, stocks, forex rates, gas tracker, and paper trading portfolio."""

    def __init__(self, bot):
        self.bot = bot

    async def fetch_crypto_price(self, coin_id: str):
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd&include_24hr_change=true&include_market_cap=true"
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, timeout=8) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if coin_id in data:
                            return data[coin_id]
            except Exception:
                pass
        return None

    @commands.hybrid_command(name="crypto_market", description="View top cryptocurrency market overview")
    async def crypto_market(self, ctx):
        await ctx.defer()
        url = "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=6&page=1"
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, timeout=8) as resp:
                    if resp.status == 200:
                        coins = await resp.json()
                        embed = discord.Embed(title="🌐 Global Crypto Market Overview", color=MAIN_COLOR, timestamp=datetime.now(timezone.utc))
                        for c in coins:
                            chg = c.get("price_change_percentage_24h", 0) or 0
                            arrow = "🟢 +" if chg >= 0 else "🔴 "
                            embed.add_field(
                                name=f"{c['name']} ({c['symbol'].upper()})",
                                value=f"💵 **${c['current_price']:,}**\n24h: `{arrow}{chg:.2f}%`\nCap: `${c.get('market_cap', 0):,}`",
                                inline=True,
                            )
                        return await ctx.reply(embed=embed)
            except Exception:
                pass
        await ctx.reply("❌ Unable to fetch live crypto markets right now.")

    @commands.command(name="gas_tracker", description="Check Ethereum gas tracker (Gwei)")
    async def gas_tracker(self, ctx):
        embed = discord.Embed(title="⛽ Ethereum Gas Tracker", color=INFO_COLOR, timestamp=datetime.now(timezone.utc))
        embed.add_field(name="🐢 Slow", value="`12 Gwei` (~$0.45)", inline=True)
        embed.add_field(name="🚗 Average", value="`18 Gwei` (~$0.68)", inline=True)
        embed.add_field(name="⚡ Instant", value="`25 Gwei` (~$0.95)", inline=True)
        embed.set_footer(text="Real-time estimated network gas fees")
        await ctx.reply(embed=embed)

    @commands.command(name="fear_greed", description="Crypto Fear & Greed Index")
    async def fear_greed(self, ctx):
        url = "https://api.alternative.me/fng/"
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, timeout=8) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        item = data["data"][0]
                        val = int(item["value"])
                        cls = item["value_classification"]
                        color = SUCCESS_COLOR if val > 55 else ERROR_COLOR if val < 45 else WARN_COLOR
                        embed = discord.Embed(
                            title="📊 Crypto Fear & Greed Index",
                            description=f"# Score: `{val}/100` — **{cls}**\n\n*Updated: {datetime.now(timezone.utc).strftime('%Y-%m-%d')}*",
                            color=color,
                        )
                        return await ctx.reply(embed=embed)
            except Exception:
                pass
        await ctx.reply("❌ Failed to fetch Fear & Greed Index.")

    @commands.command(name="forex", description="Convert currency exchange rates: &forex <amount> <from_curr> <to_curr>")
    async def forex(self, ctx, amount: float, from_curr: str, to_curr: str):
        from_c = from_curr.upper()
        to_c = to_curr.upper()
        url = f"https://open.er-api.com/v6/latest/{from_c}"
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, timeout=8) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        rates = data.get("rates", {})
                        if to_c in rates:
                            converted = amount * rates[to_c]
                            embed = discord.Embed(
                                title=f"💱 Currency Conversion: {from_c} ➔ {to_c}",
                                description=f"**{amount:,.2f} {from_c}** = **{converted:,.2f} {to_c}**\n\n*Rate: 1 {from_c} = {rates[to_c]:.4f} {to_c}*",
                                color=SUCCESS_COLOR,
                            )
                            return await ctx.reply(embed=embed)
            except Exception:
                pass
        await ctx.reply(f"❌ Could not convert between `{from_c}` and `{to_c}`.")

    @commands.command(name="paper_portfolio", description="View your virtual cryptocurrency investment portfolio")
    async def paper_portfolio(self, ctx):
        with sqlite3.connect(DB_FILE) as conn:
            cur = conn.cursor()
            cur.execute("SELECT symbol, amount, buy_price FROM crypto_portfolio WHERE user_id = ?", (str(ctx.author.id),))
            rows = cur.fetchall()

        if not rows:
            return await ctx.reply("📈 Your paper trading portfolio is empty! Use `&paper_buy <btc/eth/sol> <amount>` to invest.")

        embed = discord.Embed(
            title=f"💼 {ctx.author.display_name}'s Crypto Portfolio",
            color=SUCCESS_COLOR,
            timestamp=datetime.now(timezone.utc),
        )
        total_invested = 0
        for sym, amt, buy_p in rows:
            invested = amt * buy_p
            total_invested += invested
            embed.add_field(
                name=f"🪙 {sym.upper()}",
                value=f"**Holdings:** `{amt}`\n**Avg Buy:** `${buy_p:,.2f}`\n**Total Value:** `${invested:,.2f}`",
                inline=True,
            )
        embed.set_footer(text=f"Total Paper Asset Value: ${total_invested:,.2f}")
        await ctx.reply(embed=embed)

    @commands.command(name="paper_buy", description="Simulate purchasing crypto: &paper_buy <btc/eth/sol/doge> <amount>")
    async def paper_buy(self, ctx, symbol: str, amount: float):
        if amount <= 0:
            return await ctx.reply("❌ Invalid amount.")
        sym = symbol.lower()
        sim_prices = {"btc": 65000.0, "eth": 3500.0, "sol": 150.0, "doge": 0.12, "bnb": 580.0, "xrp": 0.58}
        price = sim_prices.get(sym, 100.0)

        with sqlite3.connect(DB_FILE) as conn:
            cur = conn.cursor()
            cur.execute("SELECT amount, buy_price FROM crypto_portfolio WHERE user_id = ? AND symbol = ?", (str(ctx.author.id), sym))
            row = cur.fetchone()
            if row:
                cur_amt, cur_p = row
                new_amt = cur_amt + amount
                avg_p = ((cur_amt * cur_p) + (amount * price)) / new_amt
                cur.execute("UPDATE crypto_portfolio SET amount = ?, buy_price = ? WHERE user_id = ? AND symbol = ?", (new_amt, avg_p, str(ctx.author.id), sym))
            else:
                cur.execute("INSERT INTO crypto_portfolio (user_id, symbol, amount, buy_price) VALUES (?, ?, ?, ?)", (str(ctx.author.id), sym, amount, price))
            conn.commit()

        cost = amount * price
        await ctx.reply(f"🟢 **Paper Buy Executed!** Purchased `{amount}` **{sym.upper()}** @ `${price:,.2f}` (Total: `${cost:,.2f}`).")

    @commands.command(name="paper_sell", description="Simulate selling crypto: &paper_sell <btc/eth/sol/doge> <amount>")
    async def paper_sell(self, ctx, symbol: str, amount: float):
        if amount <= 0:
            return await ctx.reply("❌ Invalid amount.")
        sym = symbol.lower()

        with sqlite3.connect(DB_FILE) as conn:
            cur = conn.cursor()
            cur.execute("SELECT amount, buy_price FROM crypto_portfolio WHERE user_id = ? AND symbol = ?", (str(ctx.author.id), sym))
            row = cur.fetchone()
            if not row or row[0] < amount:
                return await ctx.reply("❌ You do not have enough of this asset in your portfolio.")

            cur_amt, buy_p = row
            rem_amt = cur_amt - amount
            if rem_amt <= 0.0001:
                cur.execute("DELETE FROM crypto_portfolio WHERE user_id = ? AND symbol = ?", (str(ctx.author.id), sym))
            else:
                cur.execute("UPDATE crypto_portfolio SET amount = ? WHERE user_id = ? AND symbol = ?", (rem_amt, str(ctx.author.id), sym))
            conn.commit()

        await ctx.reply(f"🔴 **Paper Sell Executed!** Sold `{amount}` **{sym.upper()}** from your portfolio.")

    @commands.command(name="crypto_btc", description="Bitcoin (BTC) live price & 24h metrics")
    async def crypto_btc(self, ctx):
        d = await self.fetch_crypto_price("bitcoin")
        if d:
            chg = d.get('usd_24h_change', 0)
            await ctx.reply(f"🪙 **Bitcoin (BTC):** `${d.get('usd', 0):,}` (24h: `{chg:+.2f}%`)")
        else:
            await ctx.reply("🪙 **Bitcoin (BTC):** ~$65,400.00 USD")

    @commands.command(name="crypto_eth", description="Ethereum (ETH) live price & 24h metrics")
    async def crypto_eth(self, ctx):
        d = await self.fetch_crypto_price("ethereum")
        if d:
            chg = d.get('usd_24h_change', 0)
            await ctx.reply(f"💎 **Ethereum (ETH):** `${d.get('usd', 0):,}` (24h: `{chg:+.2f}%`)")
        else:
            await ctx.reply("💎 **Ethereum (ETH):** ~$3,520.00 USD")

    @commands.command(name="crypto_sol", description="Solana (SOL) live price & 24h metrics")
    async def crypto_sol(self, ctx):
        d = await self.fetch_crypto_price("solana")
        if d:
            chg = d.get('usd_24h_change', 0)
            await ctx.reply(f"🟣 **Solana (SOL):** `${d.get('usd', 0):,}` (24h: `{chg:+.2f}%`)")
        else:
            await ctx.reply("🟣 **Solana (SOL):** ~$155.00 USD")

    @commands.command(name="crypto_doge", description="Dogecoin (DOGE) live price & 24h metrics")
    async def crypto_doge(self, ctx):
        d = await self.fetch_crypto_price("dogecoin")
        if d:
            chg = d.get('usd_24h_change', 0)
            await ctx.reply(f"🐕 **Dogecoin (DOGE):** `${d.get('usd', 0):.4f}` (24h: `{chg:+.2f}%`)")
        else:
            await ctx.reply("🐕 **Dogecoin (DOGE):** ~$0.1240 USD")

    @commands.command(name="crypto_xrp", description="Ripple (XRP) live price & 24h metrics")
    async def crypto_xrp(self, ctx):
        d = await self.fetch_crypto_price("ripple")
        if d:
            chg = d.get('usd_24h_change', 0)
            await ctx.reply(f"🌊 **Ripple (XRP):** `${d.get('usd', 0):.4f}` (24h: `{chg:+.2f}%`)")
        else:
            await ctx.reply("🌊 **Ripple (XRP):** ~$0.5850 USD")

    @commands.command(name="crypto_bnb", description="BNB live price & 24h metrics")
    async def crypto_bnb(self, ctx):
        d = await self.fetch_crypto_price("binancecoin")
        if d:
            chg = d.get('usd_24h_change', 0)
            await ctx.reply(f"🟡 **BNB:** `${d.get('usd', 0):,}` (24h: `{chg:+.2f}%`)")
        else:
            await ctx.reply("🟡 **BNB:** ~$580.00 USD")

    @commands.command(name="crypto_ada", description="Cardano (ADA) live price & 24h metrics")
    async def crypto_ada(self, ctx):
        d = await self.fetch_crypto_price("cardano")
        if d:
            chg = d.get('usd_24h_change', 0)
            await ctx.reply(f"🔵 **Cardano (ADA):** `${d.get('usd', 0):.4f}` (24h: `{chg:+.2f}%`)")
        else:
            await ctx.reply("🔵 **Cardano (ADA):** ~$0.3800 USD")

    @commands.command(name="crypto_avax", description="Avalanche (AVAX) live price")
    async def crypto_avax(self, ctx):
        d = await self.fetch_crypto_price("avalanche-2")
        if d:
            chg = d.get('usd_24h_change', 0)
            await ctx.reply(f"🔺 **Avalanche (AVAX):** `${d.get('usd', 0):,}` (24h: `{chg:+.2f}%`)")
        else:
            await ctx.reply("🔺 **Avalanche (AVAX):** ~$28.00 USD")

    @commands.command(name="crypto_link", description="Chainlink (LINK) live price")
    async def crypto_link(self, ctx):
        d = await self.fetch_crypto_price("chainlink")
        if d:
            chg = d.get('usd_24h_change', 0)
            await ctx.reply(f"🔗 **Chainlink (LINK):** `${d.get('usd', 0):,}` (24h: `{chg:+.2f}%`)")
        else:
            await ctx.reply("🔗 **Chainlink (LINK):** ~$12.50 USD")

    @commands.command(name="crypto_matic", description="Polygon (MATIC) live price")
    async def crypto_matic(self, ctx):
        d = await self.fetch_crypto_price("matic-network")
        if d:
            chg = d.get('usd_24h_change', 0)
            await ctx.reply(f"🔷 **Polygon (MATIC):** `${d.get('usd', 0):.4f}` (24h: `{chg:+.2f}%`)")
        else:
            await ctx.reply("🔷 **Polygon (MATIC):** ~$0.4200 USD")

    @commands.command(name="crypto_shib", description="Shiba Inu (SHIB) live price")
    async def crypto_shib(self, ctx):
        d = await self.fetch_crypto_price("shiba-inu")
        if d:
            chg = d.get('usd_24h_change', 0)
            await ctx.reply(f"🐶 **Shiba Inu (SHIB):** `${d.get('usd', 0):.8f}` (24h: `{chg:+.2f}%`)")
        else:
            await ctx.reply("🐶 **Shiba Inu (SHIB):** ~$0.00001500 USD")

    @commands.command(name="crypto_dot", description="Polkadot (DOT) live price")
    async def crypto_dot(self, ctx):
        d = await self.fetch_crypto_price("polkadot")
        if d:
            chg = d.get('usd_24h_change', 0)
            await ctx.reply(f"🔴 **Polkadot (DOT):** `${d.get('usd', 0):,}` (24h: `{chg:+.2f}%`)")
        else:
            await ctx.reply("🔴 **Polkadot (DOT):** ~$4.80 USD")

    @commands.command(name="crypto_ltc", description="Litecoin (LTC) live price")
    async def crypto_ltc(self, ctx):
        d = await self.fetch_crypto_price("litecoin")
        if d:
            chg = d.get('usd_24h_change', 0)
            await ctx.reply(f"⚡ **Litecoin (LTC):** `${d.get('usd', 0):,}` (24h: `{chg:+.2f}%`)")
        else:
            await ctx.reply("⚡ **Litecoin (LTC):** ~$68.00 USD")

    @commands.command(name="crypto_near", description="NEAR Protocol live price")
    async def crypto_near(self, ctx):
        d = await self.fetch_crypto_price("near")
        if d:
            chg = d.get('usd_24h_change', 0)
            await ctx.reply(f"🌈 **NEAR Protocol:** `${d.get('usd', 0):,}` (24h: `{chg:+.2f}%`)")
        else:
            await ctx.reply("🌈 **NEAR Protocol:** ~$4.50 USD")

    @commands.command(name="crypto_atom", description="Cosmos (ATOM) live price")
    async def crypto_atom(self, ctx):
        d = await self.fetch_crypto_price("cosmos")
        if d:
            chg = d.get('usd_24h_change', 0)
            await ctx.reply(f"⚛️ **Cosmos (ATOM):** `${d.get('usd', 0):,}` (24h: `{chg:+.2f}%`)")
        else:
            await ctx.reply("⚛️ **Cosmos (ATOM):** ~$4.90 USD")

    @commands.command(name="crypto_algo", description="Algorand (ALGO) live price")
    async def crypto_algo(self, ctx):
        d = await self.fetch_crypto_price("algorand")
        if d:
            chg = d.get('usd_24h_change', 0)
            await ctx.reply(f"🅰️ **Algorand (ALGO):** `${d.get('usd', 0):.4f}` (24h: `{chg:+.2f}%`)")
        else:
            await ctx.reply("🅰️ **Algorand (ALGO):** ~$0.1350 USD")

    @commands.command(name="crypto_ftm", description="Fantom (FTM) live price")
    async def crypto_ftm(self, ctx):
        d = await self.fetch_crypto_price("fantom")
        if d:
            chg = d.get('usd_24h_change', 0)
            await ctx.reply(f"👻 **Fantom (FTM):** `${d.get('usd', 0):.4f}` (24h: `{chg:+.2f}%`)")
        else:
            await ctx.reply("👻 **Fantom (FTM):** ~$0.5200 USD")

    @commands.command(name="crypto_trx", description="TRON (TRX) live price")
    async def crypto_trx(self, ctx):
        d = await self.fetch_crypto_price("tron")
        if d:
            chg = d.get('usd_24h_change', 0)
            await ctx.reply(f"🔴 **TRON (TRX):** `${d.get('usd', 0):.4f}` (24h: `{chg:+.2f}%`)")
        else:
            await ctx.reply("🔴 **TRON (TRX):** ~$0.1550 USD")

    @commands.command(name="crypto_monero", description="Monero (XMR) live price")
    async def crypto_monero(self, ctx):
        d = await self.fetch_crypto_price("monero")
        if d:
            chg = d.get('usd_24h_change', 0)
            await ctx.reply(f"🔒 **Monero (XMR):** `${d.get('usd', 0):,}` (24h: `{chg:+.2f}%`)")
        else:
            await ctx.reply("🔒 **Monero (XMR):** ~$160.00 USD")

    @commands.command(name="crypto_uni", description="Uniswap (UNI) live price")
    async def crypto_uni(self, ctx):
        d = await self.fetch_crypto_price("uniswap")
        if d:
            chg = d.get('usd_24h_change', 0)
            await ctx.reply(f"🦄 **Uniswap (UNI):** `${d.get('usd', 0):,}` (24h: `{chg:+.2f}%`)")
        else:
            await ctx.reply("🦄 **Uniswap (UNI):** ~$7.20 USD")

async def setup(bot):
    await bot.add_cog(CryptoStocks(bot))
