# Vortex Discord Bot 🚀

Vortex is a powerful, fully-featured, modular Discord bot built with `discord.py` (v2.x). It features a robust architecture with specialized cogs covering advanced audio/music playback, AI chat, moderation, economy, ticket support, leveling, games, and server management.

---

## 🌟 Key Features

* **🔊 Advanced Music Player**: High-fidelity YouTube and Spotify audio streaming, 24/7 web radios (Lofi, Synthwave, J-Pop, Smooth Jazz, Classical Piano, Chill, and Gaming) with optimized stream volumes, queue management, loop controls, and custom volume levels.
* **🤖 AI Suite**: Live chatbot integrations and AI tools powered by Groq, Gemini, and OpenAI.
* **🔨 Complete Moderation**: Kick, ban, warn, purge, mute, and server-management tools to keep your channels safe.
* **💰 Economy & RPG**: Rich leveling systems, virtual currency, daily rewards, server shop, and miniature text-based adventure games.
* **🎮 Gaming & Minigames**: Interactive trivia quizzes, Anime lookup, stock/crypto trackers, and classic chat minigames.
* **🎟️ Support Tickets**: Modular system for members to open support tickets with server staff.
* **📊 Server Analytics**: Automated message counters, active user tracking, and database logging.

---

## 🛠️ Prerequisites & Setup

Ensure you have **Python 3.10+** installed on your system.

### 1. Clone & Install Dependencies
Initialize the directory, navigate to the folder, and run:
```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables
Create a file named `.env` in the root directory (this is automatically ignored by Git) and fill in your API tokens:
```env
DISCORD_TOKEN=your_discord_bot_token
GEMINI_API_KEY=your_gemini_api_key
GROQ_API_KEY=your_groq_api_key
```

### 3. Audio Support (FFmpeg)
To stream audio using the Music cog, **FFmpeg** must be installed on your host system and added to your system's PATH.

---

## 🚀 Running the Bot

To start the bot, run the main entry point:
```bash
python main.py
```

---

## ⌨️ Command Aliases & Shortcuts

Many command shortcuts have been added for convenience. Use either `/` (hybrid slash commands) or the prefix `&`:

| Category | Command | Shortcuts / Aliases | Description |
| :--- | :--- | :--- | :--- |
| **Music** | `play` | `p`, `start` | Play/search audio streams |
| | `pause` | `ps`, `hold` | Pause current track |
| | `resume` | `r`, `unpause` | Resume paused track |
| | `skip` | `s`, `next` | Skip to next track in queue |
| | `stop` | `dc`, `disconnect`, `leave` | Stop and leave channel |
| | `queue` | `q`, `list` | View playlist queue |
| | `nowplaying` | `np`, `song`, `current` | View details of currently playing track |
| | `volume` | `vol`, `v` | Set volume level (1-100%) |
| | `loop` | `lp`, `repeat` | Toggle looping single track |
| | `loopqueue` | `lq`, `loopall`, `repeatall` | Toggle looping full queue |
| | `shuffle` | `shf`, `mix` | Shuffle queue order |
| | `remove` | `rm`, `delete`, `del` | Remove specific song by index |
| | `clear_queue`| `cq`, `clear` | Clear the playlist queue |
| **Radios** | `radio_lofi` | `lofi`, `rl` | Stream 24/7 Lofi beats (volume calibrated) |
| | `radio_synthwave` | `synthwave`, `rs` | Stream 24/7 Synthwave beats |
| | `radio_anime` | `anime`, `ra` | Stream J-Pop / Anime OSTs |
| | `radio_chill` | `chill`, `rc` | Stream Ambient lounge music |
| | `radio_jazz` | `jazz`, `rj` | Stream Smooth Coffee Jazz |
| | `radio_classical` | `classical`, `piano`, `rcp` | Stream Classical Piano |
| | `radio_gaming`| `gaming`, `rg` | Stream Gaming bass tracks |

---

## 📁 Repository Structure

```text
├── cogs/                  # Modular category controllers
│   ├── ai_suite.py        # Gemini & Groq integrations
│   ├── music.py           # Audio streaming & web radios
│   ├── moderation.py      # Moderation command system
│   ├── economy.py         # Currency & shop logic
│   └── ...
├── main.py                # Main bot bootstrapper and loader
├── utils.py               # Shared utility functions and constants
├── requirements.txt       # Python libraries
├── LICENSE                # MIT License terms
├── TOS.md                 # Terms of Service guidelines
└── PRIVACY_POLICY.md      # Data usage statement
```

---

## 📜 License & Compliance

This project is licensed under the MIT License. Please review [TOS.md](TOS.md) and [PRIVACY_POLICY.md](PRIVACY_POLICY.md) before hosting public instances of this bot to ensure compliance with Discord's Developer Terms.
