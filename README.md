# Quant Bot

Quant Bot is a feature-rich, modular bot developed for Discord servers. It aims to make your server more interactive and manageable with features like moderation, music (YouTube & Spotify), AI integrations (text and image generation), a leveling/economy system, and various fun commands.

![Discord](https://img.shields.io/discord/1279064789116653643?label=Discord&logo=discord&style=for-the-badge)

## ✨ Key Features

- **🛡️ Advanced Moderation:** Warn and mute members, purge messages, make announcements, and detailed logging.
- **🎵 Comprehensive Music System:** Play songs/playlists from YouTube and Spotify, manage a queue, repeat songs, and more.
- **✨ AI Integrations:**
  - Smart chat with Google Gemini (`/quant`).
  - Generate images from text prompts using Stable Diffusion (`/image`).
- **🌟 Leveling & Economy System:**
  - Gain XP and level up by sending messages.
  - View your rank on the server leaderboard (`/leaderboard`).
  - A virtual economy with daily rewards, money transfers, and betting games (`/daily`, `/pay`, `/battle`).
- **🎉 Fun & Games:**
  - Interactive games like Blackjack (`/blackjack`) and betting-based Battles (`/battle`).
  - Classic fun commands like polls, dice rolls, coin flips, and a "find the difference" game.
- **🛠️ Utility Commands:** User/server info, avatar display, translation, Steam price lookup, and more.
- **⚙️ Server-Specific Settings:** Ability to set custom channels for welcome/goodbye messages.

## 🚀 Installation and Setup

Follow these steps to run this bot on your own server.

### 1. Prerequisites
- Python 3.8 or higher
- A Discord Bot Account
- Necessary API Keys (Google, HuggingFace, Spotify)

### 2. Installation
1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/user/quant-bot.git
    cd quant-bot
    ```

2.  **Install Dependencies:**
    If the project does not include a `requirements.txt` file, install the libraries manually with the following commands:
    ```bash
    pip install discord.py google-generativeai requests beautifulsoup4 yt-dlp spotipy pyfiglet googletrans==4.0.0-rc1
    pip install pynacl
    ```

3.  **Configuration (API Keys & Tokens):**
    Fill in the variables at the top of the code file with your own information, or set them up as environment variables in a `.env` file.
    - `DISCORD_BOT_TOKEN`: Your bot token from the Discord Developer Portal.
    - `GENAI_API_KEY`: Your Gemini API key from Google AI Studio.
    - `HF_TOKEN`: Your API token with `read` permissions from HuggingFace.
    - `SPOTIPY_CLIENT_ID`: Your Client ID from the Spotify Developer Dashboard.
    - `SPOTIPY_CLIENT_SECRET`: Your Client Secret from the Spotify Developer Dashboard.
    - `SPOTIPY_REDIRECT_URI`: The redirect URI you specified in your Spotify app (e.g., `http://localhost:8888/callback`).
    - `LOG_CHANNEL_ID`: The ID of the Discord text channel where moderation logs will be sent.

4.  **Discord Developer Portal Settings:**
    - Navigate to the **Privileged Gateway Intents** section in your bot's settings.
    - Enable both **SERVER MEMBERS INTENT** and **MESSAGE CONTENT INTENT**. These are required for the bot to access member information and message content.

5.  **Run the Bot:**
    ```bash
    python bot.py
    ```

## 📝 Command List

The bot operates using slash commands (`/`). Here is a list of the main commands:

| Category        | Command             | Description                                                   |
|-----------------|---------------------|---------------------------------------------------------------|
| **Moderation**  | `/warn`             | Warns a member with a specified reason.                       |
|                 | `/warnings`         | Lists a member's warnings.                                    |
|                 | `/mute`             | Mutes a member for a specified duration.                      |
|                 | `/unmute`           | Unmutes a member.                                             |
|                 | `/sil` (`purge`)    | Deletes a specified number of messages (1-100).               |
|                 | `/duyuru` (`announce`)| Sends an embedded announcement to a specified channel.      |
| **Level**       | `/rank`             | Shows your level and XP information.                          |
|                 | `/leaderboard`      | Displays the server's level leaderboard.                      |
|                 | `/daily`            | Claims your daily Quant reward.                               |
|                 | `/balance`          | Shows your Quant balance.                                     |
|                 | `/pay`              | Sends Quant to another member.                                |
| **Music**       | `/play`             | Plays or queues a song (YouTube/Spotify).                     |
|                 | `/stop`             | Stops the music and disconnects from the voice channel.       |
|                 | `/skip`             | Skips the currently playing song.                             |
|                 | `/skipall`          | Skips all repeats of the current song.                        |
|                 | `/playlist`         | Plays a playlist from your linked Spotify account.            |
|                 | `/spotify_login`    | Sends an authorization link to connect your Spotify account.  |
|                 | `/spotify_auth`     | Submits the authorization code from Spotify to the bot.       |
| **AI**          | `/quant`            | Chats with the AI.                                            |
|                 | `/resim` (`image`)  | Generates an image from a text prompt.                        |
| **Search/Info** | `/steam`            | Shows the Steam price of a game.                              |
|                 | `/gsr`, `/ytsr`     | Searches on Google and YouTube.                               |
|                 | `/havadurumu` (`weather`) | Searches for the weather in a city.                     |
| **Fun/Games**   | `/8ball`            | Asks a question to the magic 8-ball.                          |
|                 | `/roll`, `/flip`    | Rolls a die or flips a coin.                                  |
|                 | `/poll`             | Creates a simple poll.                                        |
|                 | `/game`, `/guess`   | Starts and makes a guess in the "find the difference" game.   |
|                 | `/battle`           | Engages in a betting-based battle against another member.     |
|                 | `/blackjack`        | Plays a game of betting-based Blackjack (21).                 |
| **Utility**     | `/userinfo`         | Displays detailed information about a member.                 |
|                 | `/serverinfo`       | Displays detailed information about the server.               |
|                 | `/avatar`           | Shows a member's avatar.                                      |
|                 | `/translate`        | Translates text to a specified language.                      |
|                 | `/ping`, `/saat` (`time`) | Shows the bot's latency and the current time.           |
| **Settings**    | `/settings welcome` | Sets the welcome message channel.                             |
|                 | `/settings goodbye` | Sets the goodbye message channel.                             |
