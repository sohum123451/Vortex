# Vortex Discord Bot ⚡

[![Discord.py](https://img.shields.io/badge/discord.py-v2.3+-5865F2?style=for-the-badge&logo=discord&logoColor=white)](https://discordpy.readthedocs.io/)
[![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![NVIDIA NIM](https://img.shields.io/badge/NVIDIA-NIM%20550B-76B900?style=for-the-badge&logo=nvidia&logoColor=white)](https://www.nvidia.com/)
[![Groq](https://img.shields.io/badge/Groq-DeepSeek--R1-F55036?style=for-the-badge)](https://groq.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)

**Vortex** is a hyper-scalable, multi-cloud AI-powered Discord super-bot built on `discord.py` (v2.x). Unifying 640+ modular commands across 25 categories, Vortex pairs cutting-edge enterprise AI inference with high-bitrate voice audio, 24/7 web radios, rich casino economy, automated anti-raid moderation, and a glassmorphic web dashboard with real-time server management.

🌐 **Live Web Dashboard:** [https://vortex-bot-mmha.onrender.com](https://vortex-bot-mmha.onrender.com)  
🤖 **Invite Vortex to Discord:** [Add to Server (OAuth2)](https://discord.com/oauth2/authorize?client_id=1464522902379561100&permissions=8&scope=bot%20applications.commands)

---

## 🌟 Core Superpowers

### 🧠 Multi-Cloud AI Suite
* **NVIDIA NIM Cloud**: Access enterprise `nemotron-3-ultra-550b` reasoning models with massive 1,000,000 token context windows via `&nemotron <prompt>`.
* **Groq LPU Acceleration**: High-speed 500 tok/sec reasoning powered by `deepseek-r1-distill-llama-70b` and `llama-3.3-70b-versatile` via `&deepseek <problem>`.
* **Google Gemini 3.6 Flash**: Multimodal vision and conversational intelligence via `&chat <prompt>` and `&ask <image>`.
* **Flux & SDXL AI Art Generation**: Keyless, high-resolution generative image synthesis via `&imagine <prompt>`.
* **Autonomous Web Synthesis**: Real-time web retrieval and fact synthesis via `&ask_web <query>` and zero-shot actions via `&do <action>`.

### ⚙️ Dynamic Server Prefix System
* Configure per-server custom prefixes stored in SQLite/Turso with instant in-memory LRU caching.
* Commands: `&setprefix <prefix>`, `&prefix`, `&resetprefix`.
* Bot mention `@Vortex` always functions as an immutable fallback prefix.

### 🎵 High-Bitrate Music & 24/7 Radios
* Ultra-low latency voice audio streaming from YouTube and SoundCloud with full playlist queues, volume sliders, looping, and track scrubbing.
* 24/7 Curated Web Radios: Lofi Hip-Hop, Synthwave, Smooth Coffee Jazz, Classical Piano, Anime OSTs, and Gaming Bass.
* Interactive web player with live equalizer waveform animations and queue manipulation.

### 🛡️ Moderation & Anti-Raid Defense
* Enterprise-grade moderation: `&kick`, `&ban`, `&tempban`, `&timeout`, `&warn`, `&warnings`, `&purge`, `&lock`, `&unlock`, and `&slowmode`.
* Real-time audit logs and user infraction tracking.

### 🎰 Economy, Casino & RPG Dungeons
* Complete virtual currency economy: `&balance`, `&daily`, `&work`, `&crime`, `&rob`, `&pay`, and `&leaderboard`.
* Interactive Discord UI casino: 21 Blackjack (Hit/Stand buttons), 3-Reel Slots, and Coinflip.
* Multi-floor RPG dungeon crawler with combat encounters, loot, and experience leveling.

### 💻 Cyberpunk Web Dashboard
* Flask + Discord OAuth2 web portal with animated glassmorphic design tokens.
* Live server selector with real-time bot membership detection.
* Collapsible sidebar docking (275px expanded / 78px compact) with persistent state memory.
* Live 640-command search explorer with dynamic category filtering pills.

---

## 🏗️ Architecture & Cog Structure

```text
Vortex/
├── cogs/                         # Modular Discord.py Cogs
│   ├── ai_suite.py               # NVIDIA NIM, Groq, Gemini & Flux AI engines
│   ├── server_mgmt.py            # Custom server prefixes & management
│   ├── music.py                  # Voice audio streaming & 24/7 web radios
│   ├── moderation.py             # Ban, kick, warn, timeout & channel locks
│   ├── economy.py                # Balance, daily, work, crime & transfer
│   ├── casino.py                 # Interactive Blackjack & Slots minigames
│   ├── leveling.py               # XP gain, level-up cards & announcements
│   ├── rpg.py                    # Multi-floor text RPG dungeon adventures
│   ├── games.py                  # TicTacToe, RPS, Truth or Dare, Memes
│   ├── tickets.py                # Support desk ticketing system
│   ├── utility.py                # Calculator, Crypto rates, Weather & Reminders
│   ├── giveaways.py              # Server giveaway management & timers
│   ├── logs.py                   # Automated server event audit logging
│   └── help.py                   # Dynamic command catalog & categorized help
├── static/
│   ├── css/dashboard.css         # Modern glassmorphism design system
│   ├── js/dashboard.js           # Realtime AJAX state sync & command explorer
│   └── images/                   # High-res 3D Cyberpunk mascot & banners
├── templates/
│   ├── index.html                # Public landing page with live command search
│   ├── selector.html             # Discord OAuth2 server switcher grid
│   └── dashboard.html            # Unified administration dashboard
├── main.py                       # Application bootstrapper (Bot + Flask Web)
├── utils.py                      # Database helpers, rate limiters & formatters
├── requirements.txt              # Production dependency manifest
├── TOS.md                        # Terms of Service & Compliance
├── PRIVACY_POLICY.md             # Data Protection & Privacy Statement
└── LICENSE                       # MIT License
```

---

## 🚀 Quick Start & Local Setup

### 1. Prerequisites
* **Python 3.10+**
* **FFmpeg** installed and added to system `PATH` (required for voice audio playback).
* A Discord Application from the [Discord Developer Portal](https://discord.com/developers/applications) with all **Privileged Gateway Intents** enabled (Server Members, Presence, Message Content).

### 2. Installation
```bash
# Clone the repository
git clone https://github.com/sohum123451/Vortex.git
cd Vortex

# Install Python dependencies
pip install -r requirements.txt
```

### 3. Environment Variables
Create a `.env` file in the root directory:
```env
# Discord Configuration
DISCORD_TOKEN=your_discord_bot_token_here
DISCORD_CLIENT_ID=your_discord_application_client_id
DISCORD_CLIENT_SECRET=your_discord_oauth2_client_secret
REDIRECT_URI=http://localhost:5000/callback

# Multi-Cloud AI API Keys
NVIDIA_API_KEY=nvapi-your_nvidia_nim_api_key
GROQ_API_KEY=gsk_your_groq_api_key
GEMINI_API_KEY=AIzaSy_your_gemini_api_key

# Web Security
SECRET_KEY=your_random_flask_session_secret_key
PORT=5000
```

### 4. Run Vortex
```bash
python main.py
```
* **Discord Bot**: Connects to the Discord WebSocket Gateway and syncs slash commands.
* **Web Dashboard**: Boots locally on `http://localhost:5000`.

---

## 📜 Compliance & License

Distributed under the **MIT License**. See [`LICENSE`](LICENSE) for details.  
Please review [`TOS.md`](TOS.md) and [`PRIVACY_POLICY.md`](PRIVACY_POLICY.md) for usage and data privacy guidelines.
