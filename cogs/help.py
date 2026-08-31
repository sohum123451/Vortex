import discord
from discord.ext import commands
from datetime import datetime, timezone

THEME_COLOR = 0x5865F2  # Sleek Discord Blurple / Royal Indigo
MOD_COLOR = 0xED4245    # Crimson Red
AI_COLOR = 0x9B59B6     # Vibrant Purple
ECO_COLOR = 0xF1C40F    # Gold
UTIL_COLOR = 0x3498DB   # Electric Blue
FUN_COLOR = 0x2ECC71    # Emerald Green

def base_embed(title: str, description: str, color: int = THEME_COLOR) -> discord.Embed:
    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=datetime.now(timezone.utc),
    )
    embed.set_footer(text="Vortex Bot • Use &help <command> for syntax • Prefix: & or /")
    return embed

# ==========================================
# 📊 SLEEK CATEGORY EMBEDS
# ==========================================

def help_home_embed(bot: commands.Bot) -> discord.Embed:
    if not hasattr(bot, "_cached_total_cmds") or not bot._cached_total_cmds:
        bot._cached_total_cmds = len(list(bot.walk_commands()))
    total_cmds = bot._cached_total_cmds
    latency = round(bot.latency * 1000)
    
    desc = (
        "⚡ **Vortex Dashboard**\n"
        f"A multi-purpose Discord bot with **{total_cmds} modular commands**.\n"
        "Powered by **Google Gemini 3.6 Flash**, **Automated Moderation**, **Casino Economy**, and **Live Sports**.\n\n"
        f"📡 **Gateway Latency:** `{latency}ms`  •  🌐 **Servers:** `{len(bot.guilds)}`  •  🧩 **Modules:** `{len(bot.cogs)}`\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )
    embed = base_embed("⚡ Vortex Command Center", desc, THEME_COLOR)
    if bot.user and bot.user.display_avatar:
        embed.set_thumbnail(url=bot.user.display_avatar.url)

    embed.add_field(
        name="🛡️ Moderation (28)",
        value="`kick` `ban` `softban` `tempban` `timeout` `warn` `purge` `lock` `slowmode`",
        inline=True,
    )
    embed.add_field(
        name="🤖 AI Suite (17)",
        value="`chat` `ask` `summarize` `translate` `grammar` `code_explain` `roast`",
        inline=True,
    )
    embed.add_field(
        name="💰 Economy & Casino (19)",
        value="`balance` `daily` `work` `crime` `blackjack` `slots` `gamble` `rob` `pay`",
        inline=True,
    )
    embed.add_field(
        name="⚡ Utility & Tools (17)",
        value="`calc` `weather` `crypto` `qr` `wiki` `define` `remind` `afk` `snipe`",
        inline=True,
    )
    embed.add_field(
        name="🎮 Minigames & Fun (26)",
        value="`tictactoe` `rps` `guess` `tod` `antakshari` `meme` `eightball` `ship`",
        inline=True,
    )
    embed.add_field(
        name="⚙️ Server & Tickets (20)",
        value="`announce` `embed` `poll` `sticky` `ticket_setup` `roleadd` `role_all`",
        inline=True,
    )
    embed.add_field(
        name="🏏 Sports & Entertainment (10)",
        value="`live` `track` `anime` `manga` `pokemon` `gstart` `rank` `levels`",
        inline=True,
    )
    embed.add_field(
        name="👑 Developer Controls (13)",
        value="`about` `owner` `eval` `exec` `sql` `servers` `broadcast` `restart`",
        inline=True,
    )
    embed.add_field(
        name="💡 Quick Guide",
        value="Select a category from the dropdown below to explore detailed command usage.",
        inline=False,
    )
    return embed

def help_mod_embed() -> discord.Embed:
    e = base_embed("🛡️ Moderation & Enforcement Suite", "Server security, smart multi-filter purge, and member infractions.", MOD_COLOR)
    e.add_field(
        name="🧹 Smart Purge System",
        value=(
            "• `&purge <N>` — Purge N messages\n"
            "• `&purge <N> bots` — Purge bot messages only\n"
            "• `&purge <N> humans` — Purge human messages only\n"
            "• `&purge <N> @User` — Purge specific user's messages\n"
            "• `&purge <N> links` — Purge messages containing URLs\n"
            "• `&purge <N> match <text>` — Purge containing keywords"
        ),
        inline=False,
    )
    e.add_field(
        name="⚖️ Punishments & Infractions",
        value=(
            "• `&kick <@user> [reason]` — Kick member\n"
            "• `&ban <@user> [reason]` — Ban member from server\n"
            "• `&unban <user_id> [reason]` — Unban member by ID\n"
            "• `&softban <@user> [reason]` — Ban & unban (clears message history)\n"
            "• `&tempban <@user> <10m/1h/1d> [reason]` — Temporary timed ban\n"
            "• `&timeout <@user> <10m/1h/1d> [reason]` — Mute member with Discord timeout\n"
            "• `&untimeout <@user>` — Remove timeout\n"
            "• `&warn <@user> [reason]` — Issue formal infraction\n"
            "• `&warnings [@user]` — View member warning case logs\n"
            "• `&clearwarnings <@user>` — Wipe warnings\n"
            "• `&delwarn <id>` — Delete single warning"
        ),
        inline=False,
    )
    e.add_field(
        name="🔒 Channel Controls & Voice",
        value=(
            "• `&lock` / `&unlock` — Lock/unlock channel for standard members\n"
            "• `&lockdown` / `&unlockdown` — Emergency server-wide lock\n"
            "• `&slowmode <seconds>` — Adjust chat rate (0 to disable)\n"
            "• `&nick <@user> [name]` / `&resetnick <@user>`\n"
            "• `&vckick <@user>` / `&vcmove <@user> <#channel>`\n"
            "• `&deafen <@user>` / `&undeafen <@user>` / `&banlist`"
        ),
        inline=False,
    )
    return e

def help_ai_embed() -> discord.Embed:
    e = base_embed("🤖 AI & Intelligent Suite", "Powered by Google Gemini 3.6 Flash & Groq High-Speed Engines.", AI_COLOR)
    e.add_field(
        name="⚡ Autonomous AI Dynamic Runner",
        value=(
            "• `&do <instruction>` — **Zero-Shot Dynamic Action:** Ask the bot to do *anything* on the server even if no command exists!"
        ),
        inline=False,
    )
    e.add_field(
        name="🧠 Advanced AI Roleplay & Adventure",
        value=(
            "• `&ai_persona <character> <msg>` — Talk to any fictional or historical character\n"
            "• `&ai_dungeon [action]` — Interactive choose-your-own-adventure fantasy RPG\n"
            "• `&ai_debate <topic>` — 2-Sided structured debate with neutral verdict\n"
            "• `&roast_server` — Playful AI roast of the server setup\n"
            "• `&ai_summarize_chat [limit]` — Executive summary of recent channel chat"
        ),
        inline=False,
    )
    e.add_field(
        name="💬 Core Conversational & Tools",
        value=(
            "• `&chat <prompt>` — High-speed conversational AI\n"
            "• `&ask <question>` — Multimodal image Q&A *(attach image + &ask)*\n"
            "• `&summarize <text>` — Key bullet-point text summarization\n"
            "• `&translate <language> <text>` — Multi-language translation\n"
            "• `&grammar <text>` — Fix spelling, grammar, and improve phrasing"
        ),
        inline=False,
    )
    e.add_field(
        name="💻 Developer & Problem Solving",
        value=(
            "• `&code_explain <code>` — Code logic analyzer & bug detector\n"
            "• `&code_generate <lang> <prompt>` — Generate clean production code\n"
            "• `&regex_gen <description>` — Generate regex patterns from English\n"
            "• `&sql_gen <description>` — Generate optimized SQL queries\n"
            "• `&math_solver <problem>` — Step-by-step mathematical reasoning\n"
            "• `&eli5 <concept>` — Explain concepts simply like I'm 5"
        ),
        inline=False,
    )
    return e

def help_eco_embed() -> discord.Embed:
    e = base_embed("💰 Economy & Casino Suite", "Persistent database economy with jobs, banking, and casino mini-games.", ECO_COLOR)
    e.add_field(
        name="💵 Daily Income & Career",
        value=(
            "• `&balance [@user]` — View wallet and bank cash\n"
            "• `&daily` — Claim 24h bonus + streak multiplier\n"
            "• `&weekly` — Claim 7-day reward\n"
            "• `&work` — Work shifts (20m cooldown)\n"
            "• `&crime` — High risk heist for large cash rewards\n"
            "• `&slut` — Quick street hustle for coins\n"
            "• `&beg` — Ask for spare pocket change\n"
            "• `&fish` / `&hunt` / `&dig` — Gather valuable resources"
        ),
        inline=False,
    )
    e.add_field(
        name="🏦 Banking & Trading",
        value=(
            "• `&deposit <amount/all>` — Safely store cash in the bank\n"
            "• `&withdraw <amount/all>` — Withdraw cash to wallet\n"
            "• `&pay <@user> <amount>` — Send money to another member\n"
            "• `&rob <@user>` — Attempt stealing cash from a wallet\n"
            "• `&leaderboard` — Server wealth ranking"
        ),
        inline=False,
    )
    e.add_field(
        name="🎰 Casino Mini-Games",
        value=(
            "• `&blackjack <bet>` — 21 Blackjack with interactive **Hit** & **Stand** buttons\n"
            "• `&slots <bet>` — 3-Reel casino slots (up to 10x jackpot)\n"
            "• `&gamble <amount> <heads/tails>` — Double or nothing coinflip\n"
            "• `&roulette <bet> <red/black/green/number>` — Roulette wheel"
        ),
        inline=False,
    )
    return e

def help_util_embed() -> discord.Embed:
    e = base_embed("⚡ Utility & Productive Tools", "Calculators, live forecasts, crypto prices, reminders, and server tools.", UTIL_COLOR)
    e.add_field(
        name="🔍 Data & Real-Time Lookups",
        value=(
            "• `&calc <expression>` — Safe math evaluator (e.g. `&calc 5*(10+2)`)\n"
            "• `&weather <city>` — Live global weather and wind reports\n"
            "• `&crypto <coin>` — Real-time crypto price & 24h trend (e.g. `&crypto btc`)\n"
            "• `&qr <url/text>` — Generate scannable QR code image\n"
            "• `&wiki <query>` — Search Wikipedia articles with summary cards\n"
            "• `&define <word>` — English dictionary definitions & phonetics\n"
            "• `&color <#hex>` — Color swatch preview & RGB values"
        ),
        inline=False,
    )
    e.add_field(
        name="⏰ Reminders & Inspection",
        value=(
            "• `&remind <time> <text>` — Set reminder alert (`10m`, `2h`, `1d`)\n"
            "• `&afk [reason]` — Auto-replies when mentioned while away\n"
            "• `&snipe` — Recover the most recently deleted message\n"
            "• `&editsnipe` — Inspect previously edited message\n"
            "• `&userinfo [@user]` / `&serverinfo` / `&avatar [@user]` / `&banner [@user]`\n"
            "• `&ping` / `&uptime`"
        ),
        inline=False,
    )
    return e

def help_games_embed() -> discord.Embed:
    e = base_embed("🎮 Minigames & Fun Social", "Multiplayer interactive games, Reddit memes, and party minigames.", FUN_COLOR)
    e.add_field(
        name="🕹️ Interactive Multiplayer",
        value=(
            "• `&tictactoe <@user>` — 2-Player interactive button grid\n"
            "• `&rps <rock/paper/scissors>` — Rock, Paper, Scissors\n"
            "• `&guess` — Number guessing minigame (1-100)\n"
            "• `&wyr` — Would You Rather question cards\n"
            "• `&tod` — Truth or Dare room (`&join`, `&start`, `&next`, `&endtod`)\n"
            "• `&antakshari` — Word chain game (`&endakshari`)"
        ),
        inline=False,
    )
    e.add_field(
        name="🎉 Memes & Social Matchmaking",
        value=(
            "• `&meme` — Trending Reddit meme\n"
            "• `&eightball <question>` — Classic 8-Ball oracle\n"
            "• `&ship <user1> [user2]` — Love compatibility meter (%)\n"
            "• `&joke` / `&dadjoke` / `&fact` / `&insult [@user]` / `&compliment [@user]`\n"
            "• `&choose <opt1, opt2...>` — Random decision maker\n"
            "• `&howgay [@user]` / `&simp [@user]` / `&chad [@user]`\n"
            "• `&roll [sides]` / `&coinflip` / `&reverse <text>` / `&emojify <text>` / `&clap <text>`"
        ),
        inline=False,
    )
    return e

def help_server_embed() -> discord.Embed:
    e = base_embed("⚙️ Server, Tickets & Specialized Modules", "Announcements, role tools, support tickets, sports, and giveaways.", THEME_COLOR)
    e.add_field(
        name="📢 Server Administration",
        value=(
            "• `&announce <#channel> <Title> | <Message>` — Send styled embed announcement\n"
            "• `&embed <Title> | <Desc> | [#HEX]` — Custom embed builder\n"
            "• `&poll <Question> | <Opt1> | <Opt2>` — Interactive reaction poll\n"
            "• `&sticky <message>` / `&unsticky` — Pinned sticky notes in channel\n"
            "• `&rolecreate <name> [#hex]` / `&roledelete <role>`\n"
            "• `&roleadd <@user> <role>` / `&roleremove <@user> <role>`\n"
            "• `&role_all <role>` / `&role_bots <role>` — Mass role assignment\n"
            "• `&channel_create <name> [text/voice]` / `&channel_delete` / `&channel_rename`\n"
            "• `&server_emojis` — List server emojis"
        ),
        inline=False,
    )
    e.add_field(
        name="🎫 Support Ticket Desk",
        value=(
            "• `&ticket_setup [Title]` — Deploy interactive ticket panel with button\n"
            "• `&ticket_add <@user>` — Add member to ticket channel\n"
            "• `&ticket_remove <@user>` — Remove member from ticket channel\n"
            "• `&ticket_close` — Close and delete ticket channel\n"
            "• `&ticket_transcript` — Generate downloadable transcript file"
        ),
        inline=False,
    )
    e.add_field(
        name="🏏 Sports, Anime & Giveaways",
        value=(
            "• `&live` — Show ongoing live cricket matches\n"
            "• `&track <match_id>` — Pin 20s auto-refreshing live scorecard\n"
            "• `&stoptracking` — Stop automatic updates\n"
            "• `&anime <title>` / `&manga <title>` / `&pokemon <name>` / `&mc_skin <name>`\n"
            "• `&gstart <time> <winners> <prize>` — Start timed giveaway (`10m`, `1d`)\n"
            "• `&greroll <msg_id>` — Pick a new giveaway winner\n"
            "• `&rank [@user]` / `&levels` — Chat XP ranks and leaderboard"
        ),
        inline=False,
    )
    return e

def help_rpg_embed() -> discord.Embed:
    e = base_embed("⚔️ RPG Adventure & Dungeons", "Turn-based combat, wilderness hunting, bosses, armory, and pets.", 0xE67E22)
    e.add_field(name="Character & Class", value="• `&rpg_profile [@user]` — View hero level, XP, and stats\n• `&classes` — List all classes\n• `&chooseclass <class>` — Choose your class\n• `&heal_hero` — Restore HP at town healer", inline=False)
    e.add_field(name="Wilderness & Dungeons", value="• `&hunt_monster` — Hunt monsters for Gold & XP\n• `&dungeon` — Delve into high dungeon floors\n• `&boss_raid` — Fight legendary bosses\n• `&pvp_duel @user` — Challenge member to wager duel", inline=False)
    e.add_field(name="Armory & Companions", value="• `&rpg_shop` — Browse weapons, armor & potions\n• `&buy_gear <item>` — Purchase equipment\n• `&pet_shop` — View companion pets\n• `&adopt_pet <pet>` — Adopt pet with stat buffs", inline=False)
    return e

def help_img_embed() -> discord.Embed:
    e = base_embed("🖼️ Image & Meme Generator", "Dynamic avatar overlays, canvas filters, and meme creators.", 0x9B59B6)
    e.add_field(name="Avatar Overlays", value="• `&wasted [@user]` — GTA Wasted overlay\n• `&triggered [@user]` — Animated triggered GIF\n• `&jail [@user]` — Put behind jail bars\n• `&wanted [@user]` — Western wanted poster", inline=False)
    e.add_field(name="Filters & Memes", value="• `&pixelate` / `&invert` / `&grayscale` / `&blur` / `&sepia`\n• `&drake <dislike> | <like>` — Drake hotline meme\n• `&pooh <normal> | <fancy>` — Tuxedo Pooh meme\n• `&custom_meme <template> <text>` — Custom meme generator\n• `&avatar_art <seed>` — Unique identicon artwork", inline=False)
    return e

def help_trivia_embed() -> discord.Embed:
    e = base_embed("🧠 Trivia & Word Quizzes", "Multiplayer trivia, riddles, flag guessing, and speed math.", 0x2ECC71)
    e.add_field(name="Interactive Quizzes", value="• `&trivia` — General knowledge trivia with buttons\n• `&trivia_anime` — Anime & manga trivia\n• `&trivia_science` — Science & tech trivia\n• `&trivia_gaming` — Video game trivia", inline=False)
    e.add_field(name="Minigame Challenges", value="• `&riddle` — Solve a riddle in chat\n• `&guess_flag` — Identify country flag emoji\n• `&scramble` — Unscramble programming word\n• `&math_quiz` — Speed math calculation contest", inline=False)
    return e

def help_crypto_embed() -> discord.Embed:
    e = base_embed("📈 Crypto, Stocks & Portfolio", "Live financial market data, gas trackers, and paper trading.", 0xF1C40F)
    e.add_field(name="Live Market Data", value="• `&crypto_market` — Top crypto prices & 24h changes\n• `&gas_tracker` — Ethereum network gas fees\n• `&fear_greed` — Crypto Fear & Greed index\n• `&forex <amt> <from> <to>` — Currency exchange converter", inline=False)
    e.add_field(name="Virtual Paper Trading", value="• `&paper_portfolio` — View simulated crypto portfolio\n• `&paper_buy <btc/eth/sol> <amt>` — Buy paper crypto\n• `&paper_sell <btc/eth/sol> <amt>` — Sell paper crypto", inline=False)
    return e

def help_social_embed() -> discord.Embed:
    e = base_embed("🌐 Developer & Social Lookups", "GitHub, package registries, Reddit, and video searches.", 0x34495E)
    e.add_field(name="Developer Tools", value="• `&github_user <username>` — GitHub profile stats\n• `&github_repo <owner> <repo>` — GitHub repository details\n• `&pypi <package>` — Python package lookup\n• `&npm <package>` — Node.js package lookup", inline=False)
    e.add_field(name="Media & Communities", value="• `&reddit <subreddit>` — Top trending Reddit post\n• `&youtube_search <query>` — Search YouTube videos", inline=False)
    return e

def help_analytics_embed() -> discord.Embed:
    e = base_embed("📊 Server Telemetry & Analytics", "Chat telemetry, active chatters, and server heatmaps.", 0x3498DB)
    e.add_field(name="Insights", value="• `&server_activity` — Server messages & active chatters\n• `&top_chatters` — Today's message leaderboard\n• `&role_distribution` — Top roles by member count\n• `&channel_stats` — Detailed channel breakdown", inline=False)
    return e

def help_tags_embed() -> discord.Embed:
    e = base_embed("🏷️ Custom Tags & Auto-Responders", "Server tag snippets and automated response triggers.", 0x1ABC9C)
    e.add_field(name="Custom Tags", value="• `&tag <name>` — Recall custom tag\n• `&tag_add <name> <content>` — Create a tag\n• `&tag_edit <name> <content>` — Edit tag\n• `&tag_delete <name>` — Remove tag\n• `&tag_list` — View all server tags", inline=False)
    e.add_field(name="Auto-Responders", value="• `&ar_add <trigger> | <response>` — Add auto-responder\n• `&ar_list` — View active server auto-responders", inline=False)
    return e

def help_sound_embed() -> discord.Embed:
    e = base_embed("🔊 Soundboard & Audio Tools", "Voice soundboard clips, Text-to-Speech, and voice telemetry.", 0x95A5A6)
    e.add_field(name="Voice & Audio", value="• `&tts_url <text>` — Generate Text-to-Speech audio link\n• `&soundboard` — List all soundboard clips\n• `&sound_airhorn` / `&sound_bruh` / `&sound_applause` / `&sound_bonk` / `&sound_victory`\n• `&vc_info` — Voice channel bitrate and member stats", inline=False)
    return e

def help_dev_embed() -> discord.Embed:
    e = base_embed("👑 Developer & System Controls", "Bot diagnostics, statistics, and owner maintenance tools.", 0x2F3136)
    e.add_field(
        name="⚡ Autonomous AI Code Modifier & Dynamic Action",
        value=(
            "• `&patch <instruction>` — AI Chat-to-Code modifier with auto-backup, syntax check & hot-reloading\n"
            "• `&rollback` — Undo last AI code modification\n"
            "• `&do <prompt>` — Zero-shot dynamic action execution on the fly\n"
            "• `&viewcode <file>` — Inspect bot source code directly in Discord\n"
            "• `&cogs` / `&reloadcog <cog>` — Cog manager & live hot-reload"
        ),
        inline=False,
    )
    e.add_field(
        name="Public Diagnostics",
        value=(
            "• `&about` — System specifications, AWS EC2 hosting, uptime, and developer profile\n"
            "• `&owner` — Bot creator profile card"
        ),
        inline=False,
    )
    e.add_field(
        name="🔒 Owner Maintenance Tools",
        value=(
            "• `&eval <code>` — Asynchronous Python code evaluation\n"
            "• `&exec <cmd>` — Shell terminal execution on host\n"
            "• `&sql <query>` — Direct SQLite database queries\n"
            "• `&servers` — Connected guilds directory\n"
            "• `&leave <guild_id>` — Leave a guild\n"
            "• `&broadcast <message>` — Global announcement\n"
            "• `&dm <user_id> <message>` — Direct message a user\n"
            "• `&setstatus <online/idle/dnd>` / `&setactivity <type> <name>`\n"
            "• `&backup_db` — Export database\n"
            "• `&restart` — Restart process"
        ),
        inline=False,
    )
    return e

# ==========================================
# 🎛️ CLEAN SINGLE-ROW INTERACTIVE UI
# ==========================================

def help_music_embed() -> discord.Embed:
    e = base_embed("🎵 Music Streaming & 24/7 Web Radio", "High-fidelity audio streaming, YouTube/Spotify search, queues, and 24/7 radio stations.", 0x1DB954)
    e.add_field(name="Playback & Queue", value="• `&play <query/url>` — Play song from YouTube or Spotify\n• `&pause` / `&resume` — Pause or resume track\n• `&skip` — Skip to next song in queue\n• `&stop` — Stop music and disconnect\n• `&queue` — View upcoming songs\n• `&nowplaying` (`&np`) — Current song information\n• `&volume <1-100>` — Adjust playback volume\n• `&loop` / `&loopqueue` — Toggle looping\n• `&shuffle` — Shuffle queue order", inline=False)
    e.add_field(name="24/7 Web Radio Stations", value="• `&radio_lofi` — 24/7 Lofi Hip Hop Beats ☕\n• `&radio_synthwave` — 24/7 Synthwave & Cyberpunk 🌌\n• `&radio_anime` — 24/7 Anime OST & J-Pop 🌸\n• `&radio_chill` — 24/7 Ambient Lounge 🍃\n• `&radio_jazz` — 24/7 Smooth Coffee Jazz 🎷\n• `&radio_classical` — 24/7 Peaceful Piano 🎹\n• `&radio_gaming` — 24/7 Gaming Electro Beats 🎮", inline=False)
    return e

class HelpSelect(discord.ui.Select):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        options = [
            discord.SelectOption(label="Home Overview", emoji="⚡", description="Dashboard & system telemetry", value="home"),
            discord.SelectOption(label="Music & 24/7 Radio", emoji="🎵", description="YouTube, Spotify, Queue, Radios", value="music"),
            discord.SelectOption(label="Moderation & Security", emoji="🛡️", description="Purge, Tempban, Timeout, Lock", value="mod"),
            discord.SelectOption(label="AI Suite & Intelligence", emoji="🤖", description="Gemini 3.6, Chat, Coding, Email", value="ai"),
            discord.SelectOption(label="RPG Adventure & Dungeons", emoji="⚔️", description="Classes, Dungeons, Bosses, Pets", value="rpg"),
            discord.SelectOption(label="Image & Meme Generator", emoji="🖼️", description="Wasted, Triggered, Drake, Filters", value="img"),
            discord.SelectOption(label="Trivia & Word Quizzes", emoji="🧠", description="Multiplayer Trivia, Riddles, Flags", value="trivia"),
            discord.SelectOption(label="Crypto & Stocks", emoji="📈", description="Live Markets, Fear & Greed, Portfolio", value="crypto"),
            discord.SelectOption(label="Social & Dev Lookups", emoji="🌐", description="GitHub, PyPI, NPM, Reddit, Steam", value="social"),
            discord.SelectOption(label="Server Analytics", emoji="📊", description="Chat heatmaps, Top chatters, Roles", value="analytics"),
            discord.SelectOption(label="Custom Tags & Auto-Responders", emoji="🏷️", description="Server tags and smart triggers", value="tags"),
            discord.SelectOption(label="Soundboard & Audio", emoji="🔊", description="TTS, Voice clips, Sound effects", value="sound"),
            discord.SelectOption(label="Economy & Casino", emoji="💰", description="Daily, Blackjack, Slots, Rob", value="eco"),
            discord.SelectOption(label="Utility & Tools", emoji="⚡", description="Weather, Calc, Crypto, AFK", value="util"),
            discord.SelectOption(label="Minigames & Fun", emoji="🎮", description="TicTacToe, RPS, Truth or Dare", value="games"),
            discord.SelectOption(label="Server & Tickets", emoji="⚙️", description="Roles, Channels, Tickets, Cricket", value="server"),
            discord.SelectOption(label="Developer Controls", emoji="👑", description="Bot creator profile & diagnostics", value="dev"),
        ]
        super().__init__(placeholder="📂 Select a Module Category...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        val = self.values[0]
        mapping = {
            "home": help_home_embed(self.bot),
            "music": help_music_embed(),
            "mod": help_mod_embed(),
            "ai": help_ai_embed(),
            "rpg": help_rpg_embed(),
            "img": help_img_embed(),
            "trivia": help_trivia_embed(),
            "crypto": help_crypto_embed(),
            "social": help_social_embed(),
            "analytics": help_analytics_embed(),
            "tags": help_tags_embed(),
            "sound": help_sound_embed(),
            "eco": help_eco_embed(),
            "util": help_util_embed(),
            "games": help_games_embed(),
            "server": help_server_embed(),
            "dev": help_dev_embed(),
        }
        await interaction.response.edit_message(embed=mapping.get(val, help_home_embed(self.bot)), view=self.view)

class HelpView(discord.ui.View):
    def __init__(self, bot: commands.Bot, author: discord.User):
        super().__init__(timeout=120)
        self.bot = bot
        self.author = author
        self.add_item(HelpSelect(bot))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author.id:
            await interaction.response.send_message("❌ This help menu was requested by another user. Type `&help` for your own.", ephemeral=True)
            return False
        return True

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True

# ==========================================
# 🚀 HELP COG
# ==========================================

class Help(commands.Cog):
    """The interactive command dashboard for Vortex Bot."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command(
        name="help",
        description="Explore Vortex commands or get detailed help on a specific command",
    )
    async def help_command(self, ctx: commands.Context, *, query: str = None):
        """Interactive help menu or specific command lookup."""
        if ctx.interaction and not ctx.interaction.response.is_done():
            await ctx.defer()

        if not query:
            return await ctx.reply(embed=help_home_embed(self.bot), view=HelpView(self.bot, ctx.author))

        query_clean = query.strip().lower()

        # Check category shortcuts
        category_map = {
            "mod": help_mod_embed,
            "moderation": help_mod_embed,
            "ai": help_ai_embed,
            "aisuite": help_ai_embed,
            "eco": help_eco_embed,
            "economy": help_eco_embed,
            "casino": help_eco_embed,
            "util": help_util_embed,
            "utility": help_util_embed,
            "tools": help_util_embed,
            "game": help_games_embed,
            "games": help_games_embed,
            "minigames": help_games_embed,
            "fun": help_games_embed,
            "server": help_server_embed,
            "tickets": help_server_embed,
            "cricket": help_server_embed,
            "dev": help_dev_embed,
            "developer": help_dev_embed,
        }

        if query_clean in category_map:
            return await ctx.reply(embed=category_map[query_clean](), view=HelpView(self.bot, ctx.author))

        # Check individual command lookup
        cmd = self.bot.get_command(query_clean)
        if cmd and not cmd.hidden:
            aliases = ", ".join([f"`{a}`" for a in cmd.aliases]) if cmd.aliases else "None"
            usage = f"&{cmd.qualified_name} {cmd.signature}".strip() if cmd.signature else f"&{cmd.qualified_name}"
            cog_name = cmd.cog_name or "General"
            
            embed = discord.Embed(
                title=f"📖 Command: &{cmd.qualified_name}",
                description=cmd.description or cmd.help or "No detailed description provided.",
                color=THEME_COLOR,
                timestamp=datetime.now(timezone.utc),
            )
            embed.add_field(name="📌 Usage", value=f"`{usage}`", inline=False)
            embed.add_field(name="🏷️ Category", value=f"`{cog_name}`", inline=True)
            embed.add_field(name="🔀 Aliases", value=aliases, inline=True)
            embed.set_footer(text="Parameters in <> are required, [] are optional.")
            return await ctx.reply(embed=embed)

        await ctx.reply(
            f"❌ Could not find command or category `{query}`.\n"
            f"💡 Type `&help` to open the full interactive category dashboard.",
        )

async def setup(bot: commands.Bot):
    await bot.add_cog(Help(bot))
