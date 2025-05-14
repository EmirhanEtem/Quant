import discord
from discord import File
from discord.ext import commands, tasks
import requests
from io import BytesIO
import google.generativeai as genai_google # Using google-generativeai
import datetime
import random
import yt_dlp
import asyncio
from bs4 import BeautifulSoup
import time
from urllib.parse import urlparse, parse_qs, quote as url_quote # For URL encoding
from spotipy.oauth2 import SpotifyOAuth
import spotipy
import json
import os
import pyfiglet # For the help command
from googletrans import Translator, LANGUAGES # For !translate command
import inspect
# You might need to install googletrans: pip install googletrans==4.0.0-rc1 
# --- Configuration ---
# Load sensitive data from environment variables if possible
SPOTIPY_CLIENT_ID = os.getenv("SPOTIPY_CLIENT_ID", "your_spotify_client_id_here")
SPOTIPY_CLIENT_SECRET = os.getenv("SPOTIPY_CLIENT_SECRET", "your_spotify_client_secret_here")
# IMPORTANT: This redirect URI must be active and registered in your Spotify App settings
SPOTIPY_REDIRECT_URI = os.getenv("SPOTIPY_REDIRECT_URI", "your_redirect_uri_here") # e.g., http://localhost:8888/callback

HF_TOKEN = os.getenv('HF_TOKEN', 'your_huggingface_token_here')
GENAI_API_KEY = os.getenv('GENAI_API_KEY', 'YOUR_GOOGLE_AI_API_KEY_HERE') # Replace with your actual API key
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN", "your_discord_bot_token_here")

LOG_CHANNEL_ID = 1287013533132914809 # Ensure this channel exists
BOT_CHANNEL_ID = 1180979476117606481
# --- Spotify OAuth Setup ---
sp_oauth = SpotifyOAuth(
    client_id=SPOTIPY_CLIENT_ID,
    client_secret=SPOTIPY_CLIENT_SECRET,
    redirect_uri=SPOTIPY_REDIRECT_URI,
    scope=["user-library-read", "playlist-read-private", "playlist-modify-public"],
    # cache_path=None # Explicitly disable Spotipy's default file caching
)

TOKEN_STORAGE_FILE = "user_spotify_tokens.json"

def load_spotify_tokens():
    try:
        if os.path.exists(TOKEN_STORAGE_FILE):
            with open(TOKEN_STORAGE_FILE, 'r') as f:
                return {int(k): v for k, v in json.load(f).items()}
        return {}
    except (FileNotFoundError, json.JSONDecodeError, ValueError) as e:
        print(f"Warning: Could not load/parse {TOKEN_STORAGE_FILE} ({e}). Starting with empty Spotify tokens.")
        return {}

def save_spotify_tokens(tokens):
    try:
        with open(TOKEN_STORAGE_FILE, 'w') as f:
            json.dump(tokens, f, indent=4)
    except Exception as e:
        print(f"Error saving Spotify tokens: {e}")

user_spotify_tokens = load_spotify_tokens()

# --- Google Generative AI Setup ---
try:
    if GENAI_API_KEY and GENAI_API_KEY != 'YOUR_GOOGLE_AI_API_KEY_HERE': # Basic check
        genai_google.configure(api_key=GENAI_API_KEY)
        print("Google Generative AI configured.")
    else:
        print("Google Generative AI API key not found or is a placeholder. !quant command may not work.")
except Exception as e:
    print(f"Failed to configure Google Generative AI: {e}")


# --- Bot Intents and Setup ---
intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.voice_states = True
bot = commands.Bot(command_prefix='!', intents=intents, case_insensitive=True, help_command=None)

if not hasattr(bot, 'sarki_kuyrugu'):
    bot.sarki_kuyrugu = [] # Stores (ctx, query_or_url, optional_sp_instance)
if not hasattr(bot, 'current_song_url'):
    bot.current_song_url = None # For potential 'seek' like commands in future

# --- Logging Events ---
@bot.event
async def on_message_delete(message):
    if message.author == bot.user: return
    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    if log_channel:
        embed = discord.Embed(description=f"🗑️ **Mesaj silindi:** {message.author.mention} tarafından\n**Kanal:** {message.channel.mention}\n**İçerik:**\n```{message.content}```", color=discord.Color.orange(), timestamp=datetime.datetime.now(datetime.timezone.utc))
        embed.set_footer(text=f"Kullanıcı ID: {message.author.id}")
        await log_channel.send(embed=embed)

@bot.event
async def on_message_edit(before, after):
    if before.author == bot.user or before.content == after.content: return
    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    if log_channel:
        embed = discord.Embed(description=f"✏️ **Mesaj düzenlendi:** {before.author.mention} tarafından\n**Kanal:** {before.channel.mention}\n[Mesaja Git]({after.jump_url})", color=discord.Color.blue(), timestamp=datetime.datetime.now(datetime.timezone.utc))
        embed.add_field(name="Önceki Hali", value=f"```{before.content}```", inline=False)
        embed.add_field(name="Sonraki Hali", value=f"```{after.content}```", inline=False)
        embed.set_footer(text=f"Kullanıcı ID: {before.author.id}")
        await log_channel.send(embed=embed)

@bot.event
async def on_member_update(before, after):
    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    if not log_channel: return

    if before.roles != after.roles:
        added_roles = [role for role in after.roles if role not in before.roles]
        removed_roles = [role for role in before.roles if role not in after.roles]
        if added_roles:
            await log_channel.send(f"✅ {after.mention} kullanıcısına **{', '.join([r.name for r in added_roles])}** rol(leri) verildi.")
        if removed_roles:
            await log_channel.send(f"❌ {after.mention} kullanıcısından **{', '.join([r.name for r in removed_roles])}** rol(leri) kaldırıldı.")

# --- Utility Commands ---
@bot.command(name='ping')
async def ping(ctx):
    await ctx.send(f'Pong! {round(bot.latency * 1000)}ms')

@bot.command(name='saat')
async def saat(ctx):
    now = datetime.datetime.now()
    current_time = now.strftime("%H:%M:%S")
    await ctx.send(f'🕒 Geçerli saat: {current_time}')

# --- Moderation Commands ---
@commands.has_role('Moderator') # Ensure 'Moderator' role exists
@bot.command(name='duyuru')
async def duyuru(ctx):
    def check(message):
        return message.author == ctx.author and message.channel == ctx.channel

    try:
        await ctx.send("Lütfen duyuru için bir başlık yazın (60s):")
        title_msg = await bot.wait_for("message", check=check, timeout=60.0)
        title = title_msg.content

        await ctx.send("Lütfen duyurunun içeriğini yazın (120s):")
        content_msg = await bot.wait_for("message", check=check, timeout=120.0)
        content = content_msg.content

        await ctx.send("Duyurunun gönderileceği kanalın adını veya ID'sini yazın (60s):")
        channel_msg = await bot.wait_for("message", check=check, timeout=60.0)
        channel_input = channel_msg.content
        
        target_channel = None
        if channel_input.isdigit():
            target_channel = bot.get_channel(int(channel_input))
        if not target_channel: # Try by name if ID failed or wasn't an ID
            target_channel = discord.utils.get(ctx.guild.text_channels, name=channel_input)
        
        if target_channel is None:
            await ctx.send(f"'{channel_input}' kanalı bulunamadı.")
            return

        embed = discord.Embed(title=title, description=content, color=discord.Color.blue())
        embed.set_footer(text=f"Duyuru yapan: {ctx.author.display_name}")
        embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
        await target_channel.send(embed=embed)
        await ctx.send(f"Duyuru başarıyla {target_channel.mention} kanalına gönderildi!")

    except asyncio.TimeoutError:
        await ctx.send("Zaman aşımına uğradınız. Lütfen yeniden deneyin.")
    except ValueError:
        await ctx.send("Hatalı bir kanal ID'si girdiniz.")
    except Exception as e:
        await ctx.send(f"Bir hata oluştu: {e}")

def parse_duration(duration_str: str) -> int:
    """Parses duration string like 1d, 10h, 30m, 5s into seconds."""
    unit = duration_str[-1].lower()
    value = int(duration_str[:-1])
    if unit == 's': return value
    if unit == 'm': return value * 60
    if unit == 'h': return value * 3600
    if unit == 'd': return value * 86400
    raise ValueError("Invalid duration unit. Use s, m, h, d.")

@commands.has_role('Moderator')
@bot.command(name='mutetx')
async def mute_text(ctx, member: discord.Member, duration_str: str):
    try:
        seconds = parse_duration(duration_str)
    except (ValueError, IndexError):
        await ctx.send('Süreyi doğru formatta girin. Örneğin: 1d, 10h, 30m, 5s.')
        return

    muted_role = discord.utils.get(ctx.guild.roles, name='Muted')
    if not muted_role:
        try:
            muted_role = await ctx.guild.create_role(name='Muted', reason="Metin susturma için rol oluşturuldu.")
            for channel in ctx.guild.text_channels:
                await channel.set_permissions(muted_role, send_messages=False, add_reactions=False)
            await ctx.send("'Muted' rolü oluşturuldu ve ayarlandı.")
        except discord.Forbidden:
            await ctx.send("Rol oluşturma veya izinleri ayarlama yetkim yok.")
            return
    
    try:
        await member.add_roles(muted_role, reason=f"Susturan: {ctx.author}, Süre: {duration_str}")
        await ctx.send(f"**{member.mention}, {duration_str} süreyle metin kanallarında susturuldu.**")
        await asyncio.sleep(seconds)
        if muted_role in member.roles: # Check if still muted by this role
            await member.remove_roles(muted_role, reason="Susturma süresi doldu.")
            await ctx.send(f"**{member.mention} için metin kanallarındaki susturma kaldırıldı.**")
    except discord.Forbidden:
        await ctx.send(f"{member.mention} üzerinde işlem yapma yetkim yok (rolü benden yüksek olabilir).")


@commands.has_role('Moderator')
@bot.command(name='mutevc')
async def mute_voice(ctx, member: discord.Member, duration_str: str):
    try:
        seconds = parse_duration(duration_str)
    except (ValueError, IndexError):
        await ctx.send('Süreyi doğru formatta girin. Örneğin: 1d, 10h, 30m, 5s.')
        return

    if not member.voice or not member.voice.channel:
        await ctx.send(f"{member.mention} bir ses kanalında değil.")
        return
    
    try:
        await member.edit(mute=True, reason=f"Susturan: {ctx.author}, Süre: {duration_str}")
        await ctx.send(f"**{member.mention}, {duration_str} süreyle ses kanallarında susturuldu.**")
        await asyncio.sleep(seconds)
        if member.voice and member.voice.mute: # Check if still muted by bot
             await member.edit(mute=False, reason="Susturma süresi doldu.")
             await ctx.send(f"**{member.mention} için ses kanallarındaki susturma kaldırıldı.**")
    except discord.Forbidden:
        await ctx.send(f"{member.mention} üzerinde işlem yapma yetkim yok.")


@commands.has_role('Moderator')
@bot.command(name='unmutetx')
async def unmutetx(ctx, member: discord.Member):
    muted_role = discord.utils.get(ctx.guild.roles, name='Muted')
    if muted_role and muted_role in member.roles:
        try:
            await member.remove_roles(muted_role, reason=f"Susturmayı kaldıran: {ctx.author}")
            await ctx.send(f"**{member.mention} kullanıcısının metin kanallarındaki susturması kaldırıldı.**")
        except discord.Forbidden:
            await ctx.send(f"{member.mention} üzerinde işlem yapma yetkim yok.")
    else:
        await ctx.send(f"**{member.mention} zaten metin kanallarında susturulmamış.**")

@commands.has_role('Moderator')
@bot.command(name='unmutevc')
async def unmutevc(ctx, member: discord.Member):
    if member.voice and member.voice.mute:
        try:
            await member.edit(mute=False, reason=f"Susturmayı kaldıran: {ctx.author}")
            await ctx.send(f"**{member.mention} kullanıcısının ses kanallarındaki susturması kaldırıldı.**")
        except discord.Forbidden:
            await ctx.send(f"{member.mention} üzerinde işlem yapma yetkim yok.")
    else:
        await ctx.send(f"**{member.mention} zaten sesli susturulmamış veya bir ses kanalında değil.**")


@bot.command(name="sil")
async def sil(ctx, number: int):
    if not 1 <= number <= 100: # Discord API limit for bulk delete is 100
        await ctx.send('Lütfen 1 ile 100 arasında bir sayı girin.')
        return
    try:
        deleted = await ctx.channel.purge(limit=number + 1) # +1 to include the command message itself
        await ctx.send(f'{len(deleted) - 1} mesaj silindi.', delete_after=5)
    except discord.Forbidden:
        await ctx.send("Mesajları silme yetkim yok.")
    except discord.HTTPException as e:
        await ctx.send(f"Mesajlar silinirken bir hata oluştu: {e}")

@bot.command(name='translate', aliases=['çeviri'])
async def translate_command(ctx, *, query: str):
    try:
        parts = query.split()
        if len(parts) < 2:
            await ctx.send("Kullanım: `!translate <çevirilecek metin> <hedef dil kodu>` (örn: `!translate hello world tr` veya `!translate merhaba dünya english`)")
            return

        target_language_input = parts[-1].lower()
        text_to_translate = " ".join(parts[:-1])

        if not text_to_translate:
            await ctx.send("Lütfen çevirmek için bir metin girin.")
            return

        actual_target_language_code = None
        if target_language_input in LANGUAGES: 
            actual_target_language_code = target_language_input
        else: 
            for code, name in LANGUAGES.items():
                if target_language_input == name.lower():
                    actual_target_language_code = code
                    break
        
        if not actual_target_language_code:
            await ctx.send(f"Geçersiz hedef dil: '{parts[-1]}'. Lütfen geçerli bir dil kodu (örn: en, tr) veya tam dil adı (örn: english, turkish) girin. Tam liste için `!diller` komutunu kullanabilirsiniz.")
            return

        translator = Translator()
        
        translation_result = await bot.loop.run_in_executor(
            None, translator.translate, text_to_translate, actual_target_language_code
        )

        final_translation = None
        if inspect.isawaitable(translation_result):
            print(f"DEBUG: translate_command received an awaitable from run_in_executor: {translation_result}. Awaiting it now.")
            final_translation = await translation_result
        else:
            final_translation = translation_result
        
        if final_translation is None or not hasattr(final_translation, 'src') or not hasattr(final_translation, 'text'):
            await ctx.send("Çeviri sonucu alınamadı veya beklenmedik bir formatta geldi.")
            print(f"DEBUG: Final translation object was None or malformed: {final_translation}")
            return

        source_lang_name = LANGUAGES.get(final_translation.src.lower(), final_translation.src.upper())
        target_lang_name = LANGUAGES.get(actual_target_language_code.lower(), actual_target_language_code.upper())

        embed = discord.Embed(title="Çeviri Sonucu", color=discord.Color.green())
        embed.add_field(name=f"Kaynak Metin ({source_lang_name})", value=f"```{text_to_translate}```", inline=False)
        embed.add_field(name=f"Çevrilen Metin ({target_lang_name})", value=f"```{final_translation.text}```", inline=False)
        embed.set_footer(text=f"Çeviren: Google Translate | İsteyen: {ctx.author.display_name}")
        embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
        await ctx.send(embed=embed)

    except Exception as e:
        await ctx.send(f"Çeviri sırasında bir hata oluştu: {str(e)}")
        print(f"Translate command error: {e} ({type(e)})")
        import traceback
        traceback.print_exc()

@bot.command(name="diller", aliases=["languages"])
async def list_languages(ctx):
    lang_list = [f"`{code}`: {name.capitalize()}" for code, name in LANGUAGES.items()]
    
    output = "Kullanılabilir Diller (Kod: Adı):\n"
    current_message = output
    messages_to_send = []

    for lang_entry in lang_list:
        if len(current_message) + len(lang_entry) + 2 > 1990: 
            messages_to_send.append(current_message)
            current_message = "" # Start new message part with "" not with "output"
        current_message += lang_entry + "\n"
    
    if current_message and current_message != output : # Add the last part if it has content beyond the header
        messages_to_send.append(current_message)
    elif not messages_to_send and current_message == output: # if only header was prepared
         messages_to_send.append(output + "Liste boş veya alınamadı.")


    if not messages_to_send: # Should not happen if LANGUAGES is populated
        await ctx.send("Dil listesi alınamadı.")
        return

    for msg_part in messages_to_send:
        await ctx.send(msg_part)
    await ctx.send("Çeviri için dil kodunu (örn: `en`) veya tam adını İngilizce küçük harf (örn: `english`) kullanabilirsiniz.")
# --- Spotify Authentication Commands ---
@bot.command(name='spotify_login')
async def spotify_login(ctx):
    auth_url = sp_oauth.get_authorize_url() # state parameter is handled by spotipy
    try:
        await ctx.author.send(
            f"Lütfen Spotify hesabına erişim izni vermek için şu bağlantıyı ziyaret et:\n{auth_url}\n\n"
            "Giriş yaptıktan ve uygulamaya izin verdikten sonra, tarayıcının adres çubuğundaki URL'ye geri yönlendirileceksin. "
            f"O URL'den (`{SPOTIPY_REDIRECT_URI}?code=KOD_BURADA&state=...` gibi bir şey) `code=` kısmından sonraki değeri kopyala "
            "ve `!spotify_auth KOD_BURAYA` komutuyla bana gönder."
        )
        await ctx.send(f"{ctx.author.mention}, Spotify'a bağlanmak için sana DM gönderdim. Lütfen DM'lerini kontrol et.")
    except discord.Forbidden:
        await ctx.send(f"{ctx.author.mention}, sana DM gönderemiyorum. Lütfen bu sunucudaki üyelerden DM alımını etkinleştir.")
    except Exception as e:
        await ctx.send(f"Bir hata oluştu: {e}")
        print(f"Error in spotify_login: {e}")

@bot.command(name='spotify_auth')
async def spotify_auth(ctx, *, code: str = None):
    if not code:
        await ctx.send("Lütfen `!spotify_auth <Spotify'dan_aldığın_kod>` formatında kodu gir.")
        return
    try:
        token_info = sp_oauth.get_access_token(code.strip(), as_dict=True, check_cache=False)
        user_spotify_tokens[ctx.author.id] = token_info
        save_spotify_tokens(user_spotify_tokens)
        await ctx.send(f"{ctx.author.mention}, Spotify hesabın başarıyla bağlandı! Artık `!playlist` komutunu kullanabilirsin.")
    except Exception as e:
        await ctx.send(f"Token alınırken bir hata oluştu. Kodun doğru ve süresinin geçmemiş olduğundan emin ol. Hata: {e}")
        print(f"Spotify auth error for user {ctx.author.id} with code {code}: {e}")


# --- Music Playing Logic ---
async def play_audio(ctx, query_or_url: str, display_name: str, sp_instance=None):
    voice_channel = ctx.author.voice.channel
    if not voice_channel:
        await ctx.send('Bir ses kanalında olmalısınız.')
        return

    if ctx.voice_client is None:
        try:
            voice_client = await voice_channel.connect()
            bot.vc_idle_timer = asyncio.get_event_loop().time()
        except Exception as e:
            await ctx.send(f"Ses kanalına bağlanırken hata: {e}")
            return
    else:
        voice_client = ctx.voice_client
        if voice_client.channel != voice_channel:
            try:
                await voice_client.move_to(voice_channel)
            except Exception as e:
                 await ctx.send(f"Ses kanalına geçerken hata: {e}")
                 return
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
        'default_search': 'ytsearch1:', # Search and pick first result
        'source_address': '0.0.0.0' # Bind to all interfaces for some hosting environments
    }

    try:
        loop = asyncio.get_event_loop()
        if not query_or_url.startswith('http'): # If it's a search query
            data = await loop.run_in_executor(None, lambda: yt_dlp.YoutubeDL(ydl_opts).extract_info(f"ytsearch1:{query_or_url}", download=False))
            if not data.get('entries'):
                await ctx.send(f"'{display_name}' için sonuç bulunamadı.")
                return # Call after_playing manually if it fails here and we need to process queue
            entry = data['entries'][0]
        else: # If it's a direct URL
            data = await loop.run_in_executor(None, lambda: yt_dlp.YoutubeDL(ydl_opts).extract_info(query_or_url, download=False))
            entry = data

        audio_url = entry['url']
        title = entry.get('title', display_name)
        bot.current_song_url = query_or_url # Store original query/url
        # global duratis; duratis = entry.get('duration') # If needed

    except Exception as e:
        await ctx.send(f'**"{display_name}" için ses alınamadı/çalınamadı: {e}**')
        # Manually trigger next song from queue if this fails
        if voice_client.is_connected():
            after_playing_callback(None, ctx, voice_client) # Pass None as error, current ctx and vc
        return

    ffmpeg_options = {
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
        'options': '-vn'
    }

    # Define the callback within play_audio or pass necessary context to a global one
    def after_playing_callback(error, current_ctx, vc_client): # Added current_ctx and vc_client
        if error:
            print(f"Player error: {error}")
            # bot.loop.create_task(current_ctx.send(f"Çalarken hata oluştu: {error}"))

        next_song_coro = None
        
        is_spotify_playlist_active = hasattr(current_ctx, 'from_spotify_playlist') and current_ctx.from_spotify_playlist
        
        if bot.sarki_kuyrugu: # Check generic queue first or spotify queue?
            next_tuple = bot.sarki_kuyrugu.pop(0)
            next_ctx, next_query, next_sp = next_tuple if len(next_tuple) == 3 else (next_tuple[0], next_tuple[1], None)
            
            # Ensure the context for the next song is the one who queued it, or the original playlist starter
            actual_next_ctx = next_ctx if next_ctx else current_ctx # Fallback to current_ctx if somehow None
            
            display_title = next_query
            if next_sp: # If it was a Spotify item
                 actual_next_ctx.from_spotify_playlist = True # Ensure flag is set for next song in playlist
            else: # If it was a generic play item
                 if hasattr(actual_next_ctx, 'from_spotify_playlist'):
                    delattr(actual_next_ctx, 'from_spotify_playlist')


            print(f"Queue: Playing next - {display_title}")
            next_song_coro = play_audio(actual_next_ctx, next_query, display_title, sp_instance=next_sp)
        else: # No more songs in any queue
            print("Queue empty.")
            if hasattr(current_ctx, 'from_spotify_playlist'): # Clear flag if playlist ended
                delattr(current_ctx, 'from_spotify_playlist')
            if vc_client and vc_client.is_connected():
                 bot.loop.create_task(current_ctx.send("🎶 Müzik kuyruğu tamamlandı.",delete_after=10))
                 bot.vc_idle_timer = asyncio.get_event_loop().time() # Start idle timer

        if next_song_coro:
            bot.loop.create_task(next_song_coro)
        elif vc_client and vc_client.is_connected() and not vc_client.is_playing() and not bot.sarki_kuyrugu:
            bot.vc_idle_timer = asyncio.get_event_loop().time()

    if voice_client.is_playing() or voice_client.is_paused():
        voice_client.stop()

    try:
        voice_client.play(discord.FFmpegPCMAudio(audio_url, **ffmpeg_options), after=lambda e: after_playing_callback(e, ctx, voice_client))
        log_channel = bot.get_channel(BOT_CHANNEL_ID)
        await log_channel.send(f'🎶 Şimdi çalıyor: **{title}**')
        bot.vc_idle_timer = float('inf') # Mark as active, disable idle timer
    except Exception as e:
        await ctx.send(f"Müzik çalınırken hata: {e}")
        after_playing_callback(e, ctx, voice_client) # Try to play next if current fails


@bot.command(name='play')

async def play(ctx, *, query: str):
    log_channel = bot.get_channel(BOT_CHANNEL_ID)
    if not ctx.author.voice:
        await ctx.send("**Bir ses kanalında olmalısınız.**")
        return

    # If a Spotify playlist was active and user does !play, treat as new generic queue
    if hasattr(ctx, 'from_spotify_playlist'):
        delattr(ctx, 'from_spotify_playlist')


    if ctx.voice_client and (ctx.voice_client.is_playing() or ctx.voice_client.is_paused() or bot.sarki_kuyrugu):
        bot.sarki_kuyrugu.append((ctx, query, None)) # Add to generic queue (ctx, query, no_sp_instance)
        await log_channel.send(f'🎵 Kuyruğa eklendi: **{query}**')
    else:
        await play_audio(ctx, query, query) # query is also display_name here

@bot.command(name='playlist')
async def playlist_command(ctx, *, playlist_name: str): # Renamed to avoid conflict
    user_id = ctx.author.id
    if user_id not in user_spotify_tokens:
        await ctx.send(f"{ctx.author.mention}, önce `!spotify_login` komutu ile Spotify hesabını bağlamalısın.")
        return

    if not ctx.author.voice:
        await ctx.send("**Bu komutu kullanmak için bir ses kanalında olmalısınız.**")
        return

    token_info = user_spotify_tokens[user_id]

    if sp_oauth.is_token_expired(token_info):
        try:
            if 'refresh_token' not in token_info or not token_info['refresh_token']:
                await ctx.send("Spotify token'ın yenilenemiyor (refresh token eksik). Lütfen `!spotify_login` ile tekrar bağlan.")
                if user_id in user_spotify_tokens: del user_spotify_tokens[user_id]
                save_spotify_tokens(user_spotify_tokens)
                return
            new_token_info = sp_oauth.refresh_access_token(token_info['refresh_token'])
            user_spotify_tokens[user_id] = new_token_info
            save_spotify_tokens(user_spotify_tokens)
            token_info = new_token_info
        except spotipy.SpotifyOauthError as e:
            await ctx.send(f"Spotify token'ın yenilenirken bir OAuth hatası oluştu: {e}. Lütfen `!spotify_login` ile tekrar bağlanmayı dene.")
            if user_id in user_spotify_tokens: del user_spotify_tokens[user_id]
            save_spotify_tokens(user_spotify_tokens)
            return
        except Exception as e:
            await ctx.send(f"Spotify token'ın yenilenirken genel bir hata oluştu: {e}.")
            return

    sp = spotipy.Spotify(auth=token_info['access_token'])
    
    # Clear existing queue and set Spotify playlist flag
    bot.sarki_kuyrugu.clear()
    ctx.from_spotify_playlist = True # Flag for after_playing callback

    try:
        playlists_data = sp.current_user_playlists()
        target_playlist_id = None
        target_playlist_title = ""

        for p_item in playlists_data['items']:
            if p_item['name'].lower() == playlist_name.lower():
                target_playlist_id = p_item['id']
                target_playlist_title = p_item['name']
                break

        if not target_playlist_id:
            await ctx.send(f"**'{playlist_name}' adında bir çalma listesi Spotify hesabında bulunamadı.**")
            if hasattr(ctx, 'from_spotify_playlist'): delattr(ctx, 'from_spotify_playlist') # Clear flag
            return

        msg = await ctx.send(f"🎵 **{target_playlist_title}** çalma listesi yükleniyor...")

        items_fetched = 0
        offset = 0
        limit = 50 # Spotify API limit per request for playlist items

        while True:
            tracks_page = sp.playlist_items(target_playlist_id, limit=limit, offset=offset)
            if not tracks_page['items']:
                break
            
            for item in tracks_page['items']:
                track = item.get('track')
                if track and track.get('name') and track.get('artists'):
                    artist_name = track['artists'][0]['name']
                    song_query_for_yt = f"{track['name']} {artist_name}"
                    # Store ctx of the user who initiated playlist, song_query, and their sp_instance
                    bot.sarki_kuyrugu.append((ctx, song_query_for_yt, sp)) 
                    items_fetched += 1
            
            if tracks_page['next']:
                offset += limit
            else:
                break # No more pages

        if not bot.sarki_kuyrugu:
            await msg.edit(content=f"**'{target_playlist_title}' çalma listesi boş veya şarkılar alınamadı.**")
            if hasattr(ctx, 'from_spotify_playlist'): delattr(ctx, 'from_spotify_playlist')
            return
        
        await msg.edit(content=f"**{target_playlist_title}** çalma listesinden {items_fetched} şarkı kuyruğa eklendi. İlk şarkı çalınıyor...")
        
        # Pop the first song and play it
        first_song_ctx, first_song_query, first_song_sp = bot.sarki_kuyrugu.pop(0)
        await play_audio(first_song_ctx, first_song_query, first_song_query, sp_instance=first_song_sp)

    except spotipy.exceptions.SpotifyException as e:
        await ctx.send(f"Spotify API ile iletişimde hata: {e}")
        if e.http_status == 401:
            await ctx.send("Spotify yetkiniz geçersiz. `!spotify_login` ile tekrar bağlanın.")
            if user_id in user_spotify_tokens: del user_spotify_tokens[user_id]
            save_spotify_tokens(user_spotify_tokens)
        bot.sarki_kuyrugu.clear()
        if hasattr(ctx, 'from_spotify_playlist'): delattr(ctx, 'from_spotify_playlist')
    except Exception as e:
        await ctx.send(f"Çalma listesi işlenirken bir hata oluştu: {str(e)}")
        bot.sarki_kuyrugu.clear()
        if hasattr(ctx, 'from_spotify_playlist'): delattr(ctx, 'from_spotify_playlist')
        print(f"Error in playlist command: {e}")


@bot.command(name='stop')
async def stop(ctx):
    if not ctx.author.voice:
        await ctx.send("**Bir ses kanalında olmalısınız.**")
        return
    if ctx.voice_client is None:
        await ctx.send('Bot şu anda bir ses kanalında değil.')
        return

    bot.sarki_kuyrugu.clear()
    if hasattr(ctx, 'from_spotify_playlist'):
        delattr(ctx, 'from_spotify_playlist')
    
    ctx.voice_client.stop()
    await ctx.voice_client.disconnect()
    await ctx.send('⏹️ Müzik durduruldu, kuyruk temizlendi ve bot ses kanalından ayrıldı.')
    bot.vc_idle_timer = asyncio.get_event_loop().time()

@bot.command(name='skip')
async def skip(ctx):
    if not ctx.author.voice:
        await ctx.send("**Bir ses kanalında olmalısınız.**")
        return
    if ctx.voice_client is None or not (ctx.voice_client.is_playing() or ctx.voice_client.is_paused()):
        await ctx.send('↪️ Şu anda çalan bir şarkı yok veya bot bir kanalda değil.')
        return

    await ctx.send("↪️ Şarkı atlanıyor...")
    ctx.voice_client.stop() # This will trigger the 'after_playing_callback'


# --- AI and Other Commands ---
def generate_text_google(prompt_text):
    if not GENAI_API_KEY or GENAI_API_KEY == 'YOUR_GOOGLE_AI_API_KEY_HERE':
        return "Google AI API anahtarı ayarlanmamış."
    try:
        model = genai_google.GenerativeModel('gemini-1.5-flash-latest') # Using a common, recent model
        response = model.generate_content(prompt_text)
        return response.text
    except Exception as e:
        print(f"Error with Google GenAI: {e}")
        if "API_KEY_INVALID" in str(e) or "permission" in str(e).lower() or "denied" in str(e).lower():
             return "Google AI API anahtarı geçersiz veya yetkilendirme sorunu var."
        if "billing" in str(e).lower():
            return "Google Cloud projenizde faturalandırma etkinleştirilmemiş olabilir veya kotanız dolmuş olabilir."
        return f"Google AI ile metin oluşturulurken bir hata oluştu: {type(e).__name__}"

@bot.command(name='quant') # Original name from help
async def quant_command(ctx, *, question: str):
    async with ctx.typing(): # Show "Bot is typing..."
        try:
            generated_text = await bot.loop.run_in_executor(None, generate_text_google, question)
            if len(generated_text) > 1990: # Discord char limit is 2000
                parts = [generated_text[i:i+1990] for i in range(0, len(generated_text), 1990)]
                for part in parts:
                    await ctx.send(part)
            else:
                await ctx.send(generated_text)
        except Exception as e:
            await ctx.send(f"Quant komutunda bir hata oluştu: {str(e)}")

def generate_image_hf(prompt): # Renamed to be specific
    if not HF_TOKEN or HF_TOKEN == 'YOUR_HUGGINGFACE_TOKEN_HERE':
        raise Exception("HuggingFace API anahtarı ayarlanmamış.")
    
    model_name = "stabilityai/stable-diffusion-xl-base-1.0" # A common, reliable model
    # model_name = "black-forest-labs/FLUX.1-dev" # Original, can be slow or have specific needs
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    payload = {"inputs": prompt, "options": {"wait_for_model": True}} # wait_for_model can help if model is loading

    url = f"https://api-inference.huggingface.co/models/{model_name}"
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=120) # Timeout of 2 mins
        response.raise_for_status()
        return response.content
    except requests.exceptions.Timeout:
        raise Exception("Resim oluşturma zaman aşımına uğradı. Model meşgul olabilir veya yükleniyor olabilir.")
    except requests.RequestException as e:
        error_content = "No response content"
        status_code = "N/A"
        if e.response is not None:
            status_code = e.response.status_code
            try:
                error_content = e.response.json()
                error_msg = error_content.get("error", str(e))
                if isinstance(error_msg, list): error_msg = ", ".join(error_msg)
                if "is currently loading" in str(error_msg).lower() or "estimated_time" in str(error_content).lower():
                     estimated_time = error_content.get("estimated_time", "bilinmiyor")
                     raise Exception(f"Model ({model_name}) şu anda yükleniyor (tahmini süre: {estimated_time}s), lütfen biraz sonra tekrar deneyin.")
            except json.JSONDecodeError:
                error_msg = e.response.text
        else:
            error_msg = str(e)
        raise Exception(f"HuggingFace API hatası ({status_code}): {error_msg}")


@bot.command(name='resim')
async def resim(ctx, *, prompt: str = None):
    if not prompt:
        await ctx.send("Lütfen bir prompt girin. Örneğin: `!resim gün batımında bir kedi`")
        return

    msg = await ctx.send(f"🎨 `{prompt}` için resim oluşturuluyor, bu biraz zaman alabilir...")
    try:
        image_data = await bot.loop.run_in_executor(None, generate_image_hf, prompt)
        image_bytes = BytesIO(image_data)
        await msg.delete()
        await ctx.send(
            content=f"İşte '{prompt}' için resminiz:",
            file=discord.File(fp=image_bytes, filename='generated_image.png')
        )
    except Exception as e:
        await msg.edit(content=f'🖼️ Resim oluşturulurken hata oluştu: {e}')


@bot.command(name='steam')
async def steam(ctx, *, game_query: str):
    search_url = f'https://store.steampowered.com/search/?term={url_quote(game_query)}'
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
               'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7'} # Request Turkish page if available

    try:
        async with ctx.typing():
            response = await bot.loop.run_in_executor(None, lambda: requests.get(search_url, headers=headers, timeout=10))
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')

            game_row = soup.find('a', class_='search_result_row')
            if not game_row or not game_row.get('href'):
                await ctx.send(f"'{game_query}' için Steam'de oyun bulunamadı.")
                return

            game_link = game_row['href']
            if "agecheck" in game_link: # Handle age check pages
                 await ctx.send(f"Bu oyun için yaş doğrulaması gerekiyor. Lütfen Steam'de manuel olarak kontrol edin: <{game_link}>")
                 return

            game_page_response = await bot.loop.run_in_executor(None, lambda: requests.get(game_link, headers=headers, timeout=10))
            game_page_response.raise_for_status()
            game_page_soup = BeautifulSoup(game_page_response.content, 'html.parser')

            price_str = "Fiyat bilgisi bulunamadı."
            title_div = game_page_soup.find('div', id='appHubAppName')
            actual_game_title = title_div.text.strip() if title_div else game_query

            price_area = game_page_soup.find('div', class_='game_purchase_action')
            if price_area:
                price_div = price_area.find('div', class_='game_purchase_price') # Original price
                if not price_div: price_div = price_area.find('div', class_='discount_final_price') # Discounted price

                if price_div:
                    price_str = price_div.text.strip()
                elif "free to play" in price_area.text.lower() or "ücretsiz oyna" in price_area.text.lower() or "free" == price_area.text.lower().strip():
                    price_str = "Ücretsiz"
            
            embed = discord.Embed(title=f"Steam Fiyatı: {actual_game_title}", color=discord.Color.blue(), url=game_link)
            embed.add_field(name="Fiyat", value=price_str, inline=False)
            game_img_tag = game_row.find('img')
            if game_img_tag and game_img_tag.get('src'):
                embed.set_thumbnail(url=game_img_tag['src'])
            await ctx.send(embed=embed)

    except requests.exceptions.RequestException as e:
        await ctx.send(f"Steam'den bilgi alınırken bir ağ hatası oluştu: {e}")
    except Exception as e:
        await ctx.send(f"Steam fiyatı alınırken bir hata oluştu: {e}")
        print(f"Steam command error: {e} ({type(e)})")


# --- Search Commands ---
@bot.command(name='gsr')
async def gsearch(ctx, *, query: str):
    url = f'https://www.google.com/search?q={url_quote(query)}'
    await ctx.send(f'Google araması: <{url}>')

@bot.command(name='ytsr')
async def ytsr(ctx, *, query: str):
    url = f'https://www.youtube.com/results?search_query={url_quote(query)}'
    await ctx.send(f'YouTube araması: <{url}>')

@bot.command(name='havadurumu')
async def havadurum(ctx, *, city: str):
    url = f'https://www.google.com/search?q={url_quote(city + " hava durumu")}'
    await ctx.send(f'{city} için hava durumu: <{url}>')


# --- Special Role Command & on_message ---
@commands.has_permissions(administrator=True) # Restrict this powerful command
@bot.command(name='6169323131123', hidden=True) # Example of a hidden command
async def give_moderator_role_special(ctx, member: discord.Member):
    moderator_role = discord.utils.get(ctx.guild.roles, name='Moderator')
    if not moderator_role:
        await ctx.send("Moderator rolü bulunamadı.", delete_after=10)
        return
    try:
        # This part seems problematic: "Remove all permissions from the "Moderator" role"
        # await moderator_role.edit(permissions=discord.Permissions.none()) # This would strip the role of all perms
        # Usually you just assign the existing role.
        await member.add_roles(moderator_role)
        await ctx.send(f"{member.mention} kullanıcısına Moderator rolü verildi (gizli komut).", delete_after=5)
    except discord.Forbidden:
        await ctx.send("Rol verme yetkim yok.", delete_after=10)
    finally:
        await ctx.message.delete()


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    # Original on_message specific keyword responses (converted to placeholders)
    # For local files, consider uploading them somewhere or packaging with bot.
    content_lower = message.content.lower()
    if "lol" in content_lower:
        vd = "C:\\Users\\Emirhan\\Desktop\\DcBOTSON\\Resources\\aph.mp4" # Local path
        await message.channel.send(file=File(vd), delete_after=20)
    if "seksi" in content_lower:
        vd = "C:\\Users\\Emirhan\\Desktop\\DcBOTSON\\Resources\\202503051623 (3).mp4"
        await message.channel.send(file=File(vd), delete_after=20)
    if "azgın furkan" in content_lower:
        vd = "C:\\Users\\Emirhan\\Desktop\\DcBOTSON\\Resources\\Isimsiz_video_Clipchamp_ile_yapld_3.mp4"
        await message.channel.send(file=File(vd), delete_after=20)
    # ... (other similar conditions from original code) ...
    if "sa" == content_lower:
        await message.channel.send("**Aleyküm Selam** 👋", delete_after=20)

    # The 'dd' and 'bb' role manipulation logic from original:
    # This is a bit unusual and potentially risky if 'dd'/'bb' are common words.
    # Consider making these actual commands or more specific triggers.
    # Example: if message.content.startswith("!givedemomod"): ...
    # For now, keeping the logic structure but be aware.
    # mod_role = discord.utils.get(message.guild.roles, name='Moderator')
    # if mod_role:
    #     if "asdasdasd" in content_lower: # 'dd' placeholder
    #         # ... (original logic for adding role temporarily) ...
    #         pass
    #     if "dsadsadsa" in content_lower: # 'bb' placeholder
    #         # ... (original logic for removing role) ...
    #         pass

    await bot.process_commands(message) # IMPORTANT: This allows other commands to run


# --- VC Idle Check Task ---
@tasks.loop(seconds=30) # Check every 30 seconds
async def check_vc_idle():
    now = asyncio.get_event_loop().time()
    idle_disconnect_timeout = 60 * 5  # 5 minutes

    for vc in bot.voice_clients:
        if vc.is_connected():
            if vc.is_playing() or bot.sarki_kuyrugu: # If playing or queue has songs
                bot.vc_idle_timer = float('inf') # Mark as active
                continue
            
            # If not playing and queue is empty
            if len(vc.channel.members) <= 1: # Bot is alone
                if bot.vc_idle_timer == float('inf'): # Was just playing, start timer now
                    bot.vc_idle_timer = now
                elif (now - bot.vc_idle_timer) > idle_disconnect_timeout:
                    await vc.disconnect()
                    log_channel = bot.get_channel(LOG_CHANNEL_ID)
                    if log_channel:
                        await log_channel.send(f"🔊 Ses kanalından ({vc.channel.name}) {idle_disconnect_timeout//60} dakika boyunca yalnız olduğum için ayrıldım.")
                    else:
                        print(f"Disconnected from {vc.channel.name} due to being alone and idle.")
                    bot.vc_idle_timer = now # Reset timer
            else: # People are in channel, but bot is idle
                 if bot.vc_idle_timer == float('inf'): # Was just playing, start timer
                    bot.vc_idle_timer = now
                 # Optional: could also disconnect if idle for too long even with users, but current logic is "alone and idle"


# --- Help Command ---
@bot.command(name='yardim', aliases=['help'])
async def yardim_command(ctx):
    title_art = pyfiglet.figlet_format("QUANT", font="slant")
    guide_art = pyfiglet.figlet_format("Help Guide", font="mini")
    
    embed = discord.Embed(
        title="🤖 Quant Bot Komutları",
        description=f"```\n{title_art}\n{guide_art}\n```\nMerhaba! İşte kullanabileceğin komutlar:",
        color=discord.Color.purple()
    )
    embed.add_field(name="🌐 Genel", value=
        "`!ping` - Botun gecikme süresini gösterir.\n"
        "`!saat` - Geçerli saati gösterir.\n"
        "`!havadurumu <şehir>` - Belirtilen şehrin hava durumunu arar.\n"
        "`!gsr <arama>` - Google'da arama yapar.\n"
        "`!ytsr <arama>` - YouTube'da arama yapar.", inline=False)
    
    embed.add_field(name="✨ AI & Eğlence", value=
        "`!quant <soru>` - Yapay zeka ile sohbet et.\n"
        "`!resim <prompt>` - Yazdığınız propmt'a göre resim oluşturur.\n"
        "`!steam <oyun_adı>` - Oyunun Steam fiyatını gösterir.\n"
        "`!translate <metin> <hedef_dil_kodu>` - Metni belirtilen dile çevirir (örn: `!translate merhaba en`).\n"
        "  Diğer adıyla `!çevir`. Kullanılabilir diller için `!diller`.", inline=False)

    embed.add_field(name="🎵 Müzik", value=
        "`!play <şarkı_adı/URL>` - Şarkı çalar veya kuyruğa ekler.\n"
        "`!spotify_login` - Spotify hesabını bota bağlar.\n"
        "`!spotify_auth <kod>` - Spotify'dan aldığın kodu bota verir.\n"
        "`!playlist <Spotify_Playlist_Adı>` - Spotify çalma listeni oynatır (önce login olmalısın).\n"
        "`!stop` - Müziği durdurur ve bottan çıkar.\n"
        "`!skip` - Sıradaki şarkıya geçer.", inline=False)

    embed.add_field(name="🛠️ Moderasyon (Sadece 'Moderator' Rolü)", value=
        "`!duyuru` - Adım adım duyuru oluşturur.\n"
        "`!sil <sayı>` - Belirtilen sayıda mesajı siler (1-100).\n"
        "`!mutetx <@üye> <süre ör:10m, 1h, 1d>` - Üyeyi metin kanallarında susturur.\n"
        "`!mutevc <@üye> <süre>` - Üyeyi ses kanallarında susturur.\n"
        "`!unmutetx <@üye>` - Metin susturmasını kaldırır.\n"
        "`!unmutevc <@üye>` - Ses susturmasını kaldırır.", inline=False)
    
    embed.set_footer(text="Quant Bot | İyi eğlenceler!")
    embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
    await ctx.send(embed=embed)


# --- Bot Startup ---
@bot.event
async def on_ready():
    print(f'{bot.user} olarak giriş yapıldı!')
    print(f"Discord.py API Sürümü: {discord.__version__}")
    print(f"Bot ID: {bot.user.id}")
    print(f"Sunucu Sayısı: {len(bot.guilds)}")
    await bot.change_presence(activity=discord.Game(name="!yardim | Quant Bot"))
    
    bot.vc_idle_timer = asyncio.get_event_loop().time() # Initialize timer
    if not check_vc_idle.is_running():
        check_vc_idle.start()

if __name__ == "__main__":
    if not DISCORD_BOT_TOKEN or DISCORD_BOT_TOKEN == "YOUR_DISCORD_BOT_TOKEN_HERE": # Basic check
        print("HATA: Discord bot token'ı bulunamadı veya ayarlanmamış!")
        print("Lütfen DISCORD_BOT_TOKEN değişkenini ayarla.")
    else:
        try:
            bot.run(DISCORD_BOT_TOKEN)
        except discord.PrivilegedIntentsRequired:
            print("HATA: Bot için Privileged Gateway Intent'leri (Message Content, Server Members) etkinleştirilmemiş.")
            print("Lütfen Discord Developer Portal'dan botunuzun ayarlarından bu intent'leri açın.")
        except Exception as e:
            print(f"Bot çalıştırılırken bir hata oluştu: {e}")
