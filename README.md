
# Quant Discord Bot

Quant is a versatile bot for your Discord servers. It offers music playback, moderation, AI-powered chat, Spotify integration, and much more. This bot is designed to provide a user-friendly experience.

---

## 🚀 Features

### 🎵 Music
- **`!play <song_name/URL>`**: Plays or adds a song to the queue.
- **`!playlist <Spotify_Playlist_Name>`**: Plays Spotify playlists (you need to link your Spotify account).
- **`!stop`**: Stops the music and disconnects the bot from the voice channel.
- **`!skip`**: Skips to the next song.

### 🌐 General
- **`!ping`**: Shows the bot's latency.
- **`!time`**: Shows the current time.
- **`!weather <city>`**: Searches for the weather in the specified city.
- **`!gsr <search>`**: Performs a Google search.
- **`!ytsr <search>`**: Performs a YouTube search.

### ✨ AI and Entertainment
- **`!quant <question>`**: Chat with AI.
- **`!image <prompt>`**: Generates an image based on your prompt.
- **`!steam <game_name>`**: Shows the Steam price of the game.

### 🛠️ Moderation (Only 'Moderator' Role)
- **`!announcement`**: Creates an announcement step by step.
- **`!clear <number>`**: Deletes the specified number of messages (1-100).
- **`!mutetx <@user> <duration>`**: Mutes the user in text channels.
- **`!mutevc <@user> <duration>`**: Mutes the user in voice channels.
- **`!unmutetx <@user>`**: Unmutes the user in text channels.
- **`!unmutevc <@user>`**: Unmutes the user in voice channels.

---

## 📦 Installation

### 1. Install Required Dependencies
```bash
pip install -r requirements.txt
```
### Set Up Environmental Variables
1. Fill in the parts of the code that start with 'your' with your own information (if you don't have a Spotify ID, you will need to create a Spotify bot).
2. Download the FFmpeg module and add the path to the downloaded FFmpeg file in your system's Environment Variables under the Path section.

### Run the Bot
```bash
python Quant_git.py
```
Run your bot and enjoy!
