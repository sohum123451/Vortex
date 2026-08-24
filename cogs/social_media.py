import asyncio
import urllib.parse
from datetime import datetime, timezone
import aiohttp
import discord
from discord.ext import commands
from utils import MAIN_COLOR, INFO_COLOR, SUCCESS_COLOR, ERROR_COLOR

class SocialMedia(commands.Cog):
    """Developer, gaming, and social media lookups (GitHub, PyPI, NPM, Steam, Reddit, YouTube)."""

    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="github_user", description="Lookup a GitHub developer profile")
    async def github_user(self, ctx, username: str):
        await ctx.defer()
        url = f"https://api.github.com/users/{urllib.parse.quote(username)}"
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, timeout=8) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        embed = discord.Embed(
                            title=f"🐙 GitHub: {data.get('name') or username}",
                            url=data["html_url"],
                            description=data.get("bio") or "*No bio provided.*",
                            color=0x24292E,
                        )
                        embed.set_thumbnail(url=data["avatar_url"])
                        embed.add_field(name="📦 Public Repos", value=f"`{data['public_repos']:,}`", inline=True)
                        embed.add_field(name="👥 Followers", value=f"`{data['followers']:,}`", inline=True)
                        embed.add_field(name="🌟 Following", value=f"`{data['following']:,}`", inline=True)
                        embed.add_field(name="📍 Location", value=data.get("location") or "N/A", inline=True)
                        embed.add_field(name="🏢 Company", value=data.get("company") or "N/A", inline=True)
                        embed.add_field(name="📅 Joined", value=data["created_at"][:10], inline=True)
                        return await ctx.reply(embed=embed)
            except Exception:
                pass
        await ctx.reply(f"❌ Could not find GitHub user `{username}`.")

    @commands.hybrid_command(name="github_repo", description="Lookup a GitHub open-source repository")
    async def github_repo(self, ctx, owner: str, repo: str):
        await ctx.defer()
        url = f"https://api.github.com/repos/{urllib.parse.quote(owner)}/{urllib.parse.quote(repo)}"
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, timeout=8) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        embed = discord.Embed(
                            title=f"📂 {data['full_name']}",
                            url=data["html_url"],
                            description=data.get("description") or "*No description.*",
                            color=0x24292E,
                        )
                        embed.add_field(name="⭐ Stars", value=f"`{data['stargazers_count']:,}`", inline=True)
                        embed.add_field(name="🍴 Forks", value=f"`{data['forks_count']:,}`", inline=True)
                        embed.add_field(name="🐞 Open Issues", value=f"`{data['open_issues_count']:,}`", inline=True)
                        embed.add_field(name="💻 Primary Language", value=data.get("language") or "N/A", inline=True)
                        embed.add_field(name="⚖️ License", value=data.get("license", {}).get("spdx_id") if data.get("license") else "None", inline=True)
                        return await ctx.reply(embed=embed)
            except Exception:
                pass
        await ctx.reply(f"❌ Repository `{owner}/{repo}` not found.")

    @commands.command(name="pypi", description="Search for a Python library on PyPI")
    async def pypi(self, ctx, package_name: str):
        url = f"https://pypi.org/pypi/{urllib.parse.quote(package_name)}/json"
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, timeout=8) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        info = data["info"]
                        embed = discord.Embed(
                            title=f"🐍 PyPI: {info['name']} v{info['version']}",
                            url=info["package_url"],
                            description=info.get("summary") or "*No summary available.*",
                            color=0x3775A9,
                        )
                        embed.add_field(name="👤 Author", value=info.get("author") or "N/A", inline=True)
                        embed.add_field(name="⚖️ License", value=info.get("license") or "N/A", inline=True)
                        embed.add_field(name="📥 Install Command", value=f"`pip install {info['name']}`", inline=False)
                        return await ctx.reply(embed=embed)
            except Exception:
                pass
        await ctx.reply(f"❌ Python package `{package_name}` not found on PyPI.")

    @commands.command(name="npm", description="Search for a JavaScript/Node.js package on NPM")
    async def npm(self, ctx, package_name: str):
        url = f"https://registry.npmjs.org/{urllib.parse.quote(package_name)}"
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, timeout=8) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        latest = data.get("dist-tags", {}).get("latest")
                        ver_data = data.get("versions", {}).get(latest, {})
                        embed = discord.Embed(
                            title=f"📦 NPM: {data['name']} v{latest}",
                            url=f"https://www.npmjs.com/package/{data['name']}",
                            description=data.get("description") or "*No description.*",
                            color=0xCB3837,
                        )
                        embed.add_field(name="⚖️ License", value=ver_data.get("license") or "N/A", inline=True)
                        embed.add_field(name="📥 Install Command", value=f"`npm i {data['name']}`", inline=False)
                        return await ctx.reply(embed=embed)
            except Exception:
                pass
        await ctx.reply(f"❌ NPM package `{package_name}` not found.")

    @commands.command(name="reddit", description="Fetch trending post from a subreddit: &reddit <subreddit_name>")
    async def reddit(self, ctx, subreddit: str):
        url = f"https://www.reddit.com/r/{urllib.parse.quote(subreddit)}/hot.json?limit=15"
        headers = {"User-Agent": "VortexBot/1.0"}
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, headers=headers, timeout=8) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        posts = [p["data"] for p in data["data"]["children"] if not p["data"].get("over_18", False)]
                        if posts:
                            post = posts[0]
                            embed = discord.Embed(
                                title=f"🤖 r/{subreddit}: {post['title'][:250]}",
                                url=f"https://reddit.com{post['permalink']}",
                                color=0xFF4500,
                            )
                            if post.get("url") and any(post["url"].endswith(ext) for ext in [".jpg", ".png", ".gif"]):
                                embed.set_image(url=post["url"])
                            embed.add_field(name="👍 Upvotes", value=f"`{post['ups']:,}`", inline=True)
                            embed.add_field(name="💬 Comments", value=f"`{post['num_comments']:,}`", inline=True)
                            embed.add_field(name="👤 Author", value=f"u/{post['author']}", inline=True)
                            return await ctx.reply(embed=embed)
            except Exception:
                pass
        await ctx.reply(f"❌ Could not fetch posts from r/{subreddit}.")

    @commands.command(name="youtube_search", description="Search for videos on YouTube")
    async def youtube_search(self, ctx, *, query: str):
        encoded = urllib.parse.quote(query)
        url = f"https://www.youtube.com/results?search_query={encoded}"
        embed = discord.Embed(
            title=f"▶️ YouTube Search: {query}",
            description=f"🔗 [Click here to view search results on YouTube]({url})",
            color=0xFF0000,
        )
        await ctx.reply(embed=embed)

    @commands.command(name="reddit_memes", description="Trending post from r/memes")
    async def reddit_memes(self, ctx):
        await self.reddit(ctx, subreddit="memes")

    @commands.command(name="reddit_aww", description="Cute animals from r/aww")
    async def reddit_aww(self, ctx):
        await self.reddit(ctx, subreddit="aww")

    @commands.command(name="reddit_dank", description="Dank memes from r/dankmemes")
    async def reddit_dank(self, ctx):
        await self.reddit(ctx, subreddit="dankmemes")

    @commands.command(name="reddit_gaming", description="Gaming posts from r/gaming")
    async def reddit_gaming(self, ctx):
        await self.reddit(ctx, subreddit="gaming")

    @commands.command(name="reddit_ask", description="Questions from r/AskReddit")
    async def reddit_ask(self, ctx):
        await self.reddit(ctx, subreddit="AskReddit")

    @commands.command(name="reddit_tech", description="Technology news from r/technology")
    async def reddit_tech(self, ctx):
        await self.reddit(ctx, subreddit="technology")

    @commands.command(name="duckduckgo", description="Search DuckDuckGo: &duckduckgo <query>")
    async def duckduckgo(self, ctx, *, query: str):
        url = f"https://duckduckgo.com/?q={urllib.parse.quote(query)}"
        embed = discord.Embed(title=f"🦆 DuckDuckGo: {query}", description=f"🔗 [View Search Results]({url})", color=0xDE5833)
        await ctx.reply(embed=embed)

    @commands.command(name="wikipedia_search", description="Search Wikipedia articles: &wikipedia_search <query>")
    async def wikipedia_search(self, ctx, *, query: str):
        url = f"https://en.wikipedia.org/wiki/Special:Search?search={urllib.parse.quote(query)}"
        embed = discord.Embed(title=f"📚 Wikipedia: {query}", description=f"🔗 [Read on Wikipedia]({url})", color=0x2F3136)
        await ctx.reply(embed=embed)

    @commands.command(name="twitch_search", description="Search Twitch streamers: &twitch_search <channel>")
    async def twitch_search(self, ctx, *, channel: str):
        url = f"https://www.twitch.tv/{urllib.parse.quote(channel)}"
        embed = discord.Embed(title=f"🟣 Twitch: {channel}", description=f"🔗 [Watch Stream on Twitch]({url})", color=0x9146FF)
        await ctx.reply(embed=embed)

async def setup(bot):
    await bot.add_cog(SocialMedia(bot))
