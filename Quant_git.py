import discord
from discord import app_commands, File, ui, ButtonStyle
from discord.ext import commands, tasks
import requests
from io import BytesIO
import google.generativeai as genai_google
import datetime
import random
import yt_dlp
import asyncio
from bs4 import BeautifulSoup
import time
from urllib.parse import urlparse, parse_qs, quote as url_quote
from spotipy.oauth2 import SpotifyOAuth
import spotipy
import json
import os
import pyfiglet
from googletrans import Translator, LANGUAGES
import inspect
import re

SPOTIPY_CLIENT_ID = os.getenv("SPOTIPY_CLIENT_ID", "SPOTIPY_CLIENT_ID_HERE")
SPOTIPY_CLIENT_SECRET = os.getenv("SPOTIPY_CLIENT_SECRET", "SPOTIPY_CLIENT_SECRET_HERE")
SPOTIPY_REDIRECT_URI = os.getenv("SPOTIPY_REDIRECT_URI", "http://localhost:8888/callback") 
HF_TOKEN = os.getenv('HF_TOKEN', 'hf_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXX')
GENAI_API_KEY = os.getenv('GENAI_API_KEY', 'GENAI_API_KEY_HERE')
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN", "YOUR_DISCORD_BOT_TOKEN_HERE")
LOG_CHANNEL_ID = "YOUR_LOG_CHANNEL_ID_HERE"  

TOKEN_STORAGE_FILE = "user_spotify_tokens.json"
LEVELS_FILE = "levels.json"
ECONOMY_FILE = "economy.json"
SETTINGS_FILE = "server_settings.json"
WARNINGS_FILE = "warnings.json"

def load_json(filename):
    """Bir JSON dosyasını güvenli bir şekilde yükler."""
    try:
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    except (json.JSONDecodeError, FileNotFoundError):
        return {}

def save_json(filename, data):
    """Bir Python sözlüğünü JSON dosyasına güvenli bir şekilde kaydeder."""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"Hata: {filename} dosyasına kaydedilemedi: {e}")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True
intents.messages = True

bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

bot.sarki_kuyrugu = []
bot.now_playing = {}
bot.current_song_url = None
bot.active_games = {}
bot.xp_cooldowns = {}
bot.vc_idle_timer = 0
bot.blackjack_games = {}
bot.active_battles = {}

bot.levels = load_json(LEVELS_FILE)
bot.economy = load_json(ECONOMY_FILE)
bot.server_settings = load_json(SETTINGS_FILE)
bot.warnings = load_json(WARNINGS_FILE)
user_spotify_tokens = {int(k): v for k, v in load_json(TOKEN_STORAGE_FILE).items()}

def save_spotify_tokens(tokens):
    save_json(TOKEN_STORAGE_FILE, tokens)

try:
    sp_oauth = SpotifyOAuth(client_id=SPOTIPY_CLIENT_ID, client_secret=SPOTIPY_CLIENT_SECRET, redirect_uri=SPOTIPY_REDIRECT_URI, scope="user-library-read playlist-read-private playlist-modify-public")
except Exception as e:
    print(f"Spotify OAuth yapılandırılamadı. Spotify komutları çalışmayabilir. Hata: {e}")

if GENAI_API_KEY:
    try:
        genai_google.configure(api_key=GENAI_API_KEY)
        print("Google Generative AI yapılandırıldı.")
    except Exception as e:
        print(f"Google Generative AI yapılandırılamadı: {e}")



@bot.event
async def on_ready():
    """Bot çalıştığında yapılacaklar."""
    print(f'{bot.user} olarak giriş yapıldı!')
    print(f"Discord.py API Sürümü: {discord.__version__}")
    print(f"Sunucu Sayısı: {len(bot.guilds)}")
    try:
        print("Global komutlar senkronize ediliyor... (Bu işlem yeni botlarda bir saat kadar sürebilir)")
        await bot.tree.sync()
        print("Global komut senkronizasyonu tamamlandı.")
    except Exception as e:
        print(f"Komut senkronizasyonu sırasında hata: {e}")

    await bot.change_presence(activity=discord.Game(name="/help | Quant Bot"))
    bot.vc_idle_timer = bot.loop.time()
    if not check_vc_idle.is_running():
        check_vc_idle.start()

@bot.event
async def on_message(message: discord.Message):
    """Her mesaj gönderildiğinde tetiklenir."""
    if message.author.bot or not message.guild:
        return

    guild_id = str(message.guild.id)
    user_id = str(message.author.id)

    cooldown_key = f"{guild_id}-{user_id}"
    if cooldown_key not in bot.xp_cooldowns or time.time() - bot.xp_cooldowns.get(cooldown_key, 0) > 60:
        bot.levels.setdefault(guild_id, {})
        bot.levels[guild_id].setdefault(user_id, {"xp": 0, "level": 1})

        xp_to_add = random.randint(15, 25)
        bot.levels[guild_id][user_id]["xp"] += xp_to_add

        current_level = bot.levels[guild_id][user_id]["level"]
        xp_for_next_level = int((current_level ** 2) * 100)

        if bot.levels[guild_id][user_id]["xp"] >= xp_for_next_level:
            bot.levels[guild_id][user_id]["level"] += 1
            new_level = bot.levels[guild_id][user_id]["level"]
            bot.levels[guild_id][user_id]["xp"] -= xp_for_next_level
            try:
                await message.channel.send(f"🎉 Tebrikler {message.author.mention}, **Seviye {new_level}** oldun!", delete_after=30)
            except discord.Forbidden:
                pass

        bot.xp_cooldowns[cooldown_key] = time.time()
        save_json(LEVELS_FILE, bot.levels)

    content_lower = message.content.lower()
    if "sa" == content_lower:
        await message.channel.send("**Aleyküm Selam** 👋", delete_after=20)

    await bot.process_commands(message)

@bot.event
async def on_member_join(member: discord.Member):
    """Yeni üye katıldığında tetiklenir."""
    guild_id = str(member.guild.id)
    settings = bot.server_settings.get(guild_id, {})
    channel_id = settings.get("welcome_channel")
    if channel_id and (channel := member.guild.get_channel(channel_id)):
        embed = discord.Embed(description=f"🎉 Sunucumuza hoş geldin, {member.mention}!", color=discord.Color.green(), timestamp=datetime.datetime.now())
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=f"{member.guild.name} | Toplam Üye: {member.guild.member_count}")
        try:
            await channel.send(embed=embed)
        except discord.Forbidden:
            pass

@bot.event
async def on_member_remove(member: discord.Member):
    """Bir üye ayrıldığında tetiklenir."""
    guild_id = str(member.guild.id)
    settings = bot.server_settings.get(guild_id, {})
    channel_id = settings.get("goodbye_channel")
    if channel_id and (channel := member.guild.get_channel(channel_id)):
        embed = discord.Embed(description=f"👋 **{member.display_name}** ({member.name}) aramızdan ayrıldı.", color=discord.Color.red(), timestamp=datetime.datetime.now())
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=f"{member.guild.name} | Toplam Üye: {member.guild.member_count}")
        try:
            await channel.send(embed=embed)
        except discord.Forbidden:
            pass

@bot.event
async def on_message_delete(message: discord.Message):
    if message.author == bot.user or not message.guild: return
    try:
        log_channel = bot.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            embed = discord.Embed(description=f"🗑️ **Mesaj silindi:** {message.author.mention} tarafından\n**Kanal:** {message.channel.mention}\n**İçerik:**\n```{message.content or 'İçerik yok (Embed/Dosya olabilir)'}```", color=discord.Color.orange(), timestamp=datetime.datetime.now(datetime.timezone.utc))
            embed.set_footer(text=f"Kullanıcı ID: {message.author.id}")
            await log_channel.send(embed=embed)
    except Exception:
        pass

@bot.event
async def on_message_edit(before: discord.Message, after: discord.Message):
    if before.author == bot.user or before.content == after.content or not before.guild: return
    try:
        log_channel = bot.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            embed = discord.Embed(description=f"✏️ **Mesaj düzenlendi:** {before.author.mention} tarafından\n**Kanal:** {before.channel.mention}\n[Mesaja Git]({after.jump_url})", color=discord.Color.blue(), timestamp=datetime.datetime.now(datetime.timezone.utc))
            embed.add_field(name="Önceki Hali", value=f"```{before.content or 'İçerik yok'}```", inline=False)
            embed.add_field(name="Sonraki Hali", value=f"```{after.content or 'İçerik yok'}```", inline=False)
            embed.set_footer(text=f"Kullanıcı ID: {before.author.id}")
            await log_channel.send(embed=embed)
    except Exception:
        pass
        
@bot.event
async def on_member_update(before, after):
    if before.roles == after.roles: return
    try:
        log_channel = bot.get_channel(LOG_CHANNEL_ID)
        if not log_channel: return
        added_roles = [role.name for role in after.roles if role not in before.roles]
        removed_roles = [role.name for role in before.roles if role not in after.roles]
        if added_roles:
            await log_channel.send(f"✅ {after.mention} kullanıcısına **{', '.join(added_roles)}** rol(leri) verildi.")
        if removed_roles:
            await log_channel.send(f"❌ {after.mention} kullanıcısından **{', '.join(removed_roles)}** rol(leri) kaldırıldı.")
    except Exception:
        pass
        

async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    """Uygulama komutlarındaki hataları yakalar."""
    error_message = f"Beklenmedik bir hata oluştu: {error}"
    if isinstance(error, app_commands.MissingRole):
        error_message = f"Bu komutu kullanmak için '{error.missing_role}' rolüne sahip olmalısınız."
    elif isinstance(error, app_commands.CommandOnCooldown):
        error_message = f"Bu komut bekleme süresinde. {error.retry_after:.2f} saniye sonra tekrar deneyin."
    elif isinstance(error, app_commands.CheckFailure) or isinstance(error, app_commands.MissingPermissions):
        error_message = "Bu komutu kullanmak için gerekli yetkilere sahip değilsiniz."
    elif isinstance(error, app_commands.CommandInvokeError):
        error_message = f"Komut yürütülürken bir hata oluştu: {error.original}"

    try:
        if interaction.response.is_done():
            await interaction.followup.send(error_message, ephemeral=True)
        else:
            await interaction.response.send_message(error_message, ephemeral=True, delete_after=15)
    except (discord.errors.InteractionResponded, discord.errors.NotFound):
        try:
            await interaction.edit_original_response(content=error_message, view=None, embed=None)
        except Exception as e:
            print(f"Hata mesajı gönderilirken ek bir hata oluştu: {e}")
    print(f"App command error in guild {interaction.guild.name if interaction.guild else 'DM'} ({interaction.guild_id}): {error}")

bot.tree.on_error = on_app_command_error


settings_group = app_commands.Group(name="settings", description="Sunucuya özel bot ayarlarını yönetir.", default_permissions=discord.Permissions(manage_guild=True))

@settings_group.command(name="welcome", description="Hoş geldin mesajlarının gönderileceği kanalı ayarlar.")
async def set_welcome_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    guild_id = str(interaction.guild.id)
    bot.server_settings.setdefault(guild_id, {})
    bot.server_settings[guild_id]["welcome_channel"] = channel.id
    save_json(SETTINGS_FILE, bot.server_settings)
    await interaction.response.send_message(f"✅ Hoş geldin kanalı {channel.mention} olarak ayarlandı.", ephemeral=True)

@settings_group.command(name="goodbye", description="Güle güle mesajlarının gönderileceği kanalı ayarlar.")
async def set_goodbye_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    guild_id = str(interaction.guild.id)
    bot.server_settings.setdefault(guild_id, {})
    bot.server_settings[guild_id]["goodbye_channel"] = channel.id
    save_json(SETTINGS_FILE, bot.server_settings)
    await interaction.response.send_message(f"✅ Güle güle kanalı {channel.mention} olarak ayarlandı.", ephemeral=True)

bot.tree.add_command(settings_group)


def parse_duration(duration_str: str) -> int:
    unit = duration_str[-1].lower()
    value_str = duration_str[:-1]
    if not value_str.isdigit(): raise ValueError("Sayısal değer hatalı.")
    value = int(value_str)
    if unit == 's': return value
    if unit == 'm': return value * 60
    if unit == 'h': return value * 3600
    if unit == 'd': return value * 86400
    raise ValueError("Geçersiz birim. s, m, h, d kullanın.")

@bot.tree.command(name="warn", description="Bir üyeyi sebep belirterek uyarır.")
@app_commands.checks.has_permissions(kick_members=True)
async def warn(interaction: discord.Interaction, member: discord.Member, reason: str):
    if member.bot or member == interaction.user: return await interaction.response.send_message("Kendinizi veya botları uyaramazsınız.", ephemeral=True)
    if member.top_role >= interaction.user.top_role and interaction.guild.owner != interaction.user: return await interaction.response.send_message("Kendinizden daha yüksek veya aynı roldeki birini uyaramazsınız.", ephemeral=True)

    guild_id = str(interaction.guild.id)
    user_id = str(member.id)
    bot.warnings.setdefault(guild_id, {})
    bot.warnings[guild_id].setdefault(user_id, [])
    
    warning_data = {"moderator_id": interaction.user.id, "reason": reason, "timestamp": int(time.time())}
    bot.warnings[guild_id][user_id].append(warning_data)
    save_json(WARNINGS_FILE, bot.warnings)
    
    await interaction.response.send_message(f"✅ {member.mention}, `{reason}` sebebiyle uyarıldı.")
    try: await member.send(f"**{interaction.guild.name}** sunucusunda `{reason}` sebebiyle uyarıldınız.")
    except discord.Forbidden: pass

@bot.tree.command(name="warnings", description="Bir üyenin aldığı tüm uyarıları listeler.")
@app_commands.checks.has_permissions(kick_members=True)
async def list_warnings(interaction: discord.Interaction, member: discord.Member):
    guild_id = str(interaction.guild.id)
    user_id = str(member.id)
    user_warnings = bot.warnings.get(guild_id, {}).get(user_id, [])
    if not user_warnings: return await interaction.response.send_message(f"{member.display_name} adlı kullanıcının hiç uyarısı yok.", ephemeral=True)
        
    embed = discord.Embed(title=f"Uyarılar: {member.display_name}", color=discord.Color.orange())
    for i, warn_data in enumerate(user_warnings, 1):
        mod_id = warn_data["moderator_id"]
        mod = interaction.guild.get_member(mod_id) or f"Bilinmeyen ({mod_id})"
        timestamp = f"<t:{warn_data['timestamp']}:F>"
        embed.add_field(name=f"Uyarı #{i}", value=f"**Sebep:** {warn_data['reason']}\n**Moderatör:** {mod}\n**Tarih:** {timestamp}", inline=False)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name='duyuru', description="Belirtilen kanala bir duyuru gönderir.")
@app_commands.checks.has_permissions(manage_guild=True)
@app_commands.describe(title="Duyurunun başlığı", content="Duyurunun içeriği", channel="Duyurunun gönderileceği metin kanalı")
async def duyuru(interaction: discord.Interaction, title: str, content: str, channel: discord.TextChannel):
    embed = discord.Embed(title=title, description=content, color=discord.Color.blue(), timestamp=datetime.datetime.now(datetime.timezone.utc))
    embed.set_footer(text=f"Duyuru yapan: {interaction.user.display_name}")
    await channel.send(embed=embed)
    await interaction.response.send_message(f"Duyuru başarıyla {channel.mention} kanalına gönderildi!", ephemeral=True)

@bot.tree.command(name='mute', description="Bir üyeyi belirtilen süreyle metin ve ses kanallarında susturur.")
@app_commands.checks.has_permissions(moderate_members=True)
@app_commands.describe(member="Susturulacak üye", duration="Süre (örn: 10m, 1h, 2d)", reason="Sebep")
async def mute(interaction: discord.Interaction, member: discord.Member, duration: str, reason: str = "Belirtilmedi"):
    try:
        delta = datetime.timedelta(seconds=parse_duration(duration))
    except ValueError as e:
        return await interaction.response.send_message(f'Geçersiz süre formatı. Örnek: `1d`, `10h`, `30m`, `5s`. Hata: {e}', ephemeral=True)
    
    await member.timeout(delta, reason=reason)
    await interaction.response.send_message(f"**{member.mention}**, `{duration}` süreyle metin ve ses kanallarında susturuldu. Sebep: {reason}")

@bot.tree.command(name='unmute', description="Üyenin metin&ses susturmasını kaldırır.")
@app_commands.checks.has_permissions(moderate_members=True)
async def unmute(interaction: discord.Interaction, member: discord.Member):
    if member.is_timed_out():
        await member.timeout(None, reason=f"Susturmayı kaldıran: {interaction.user}")
        await interaction.response.send_message(f"**{member.mention}** kullanıcısının susturması kaldırıldı.")
    else:
        await interaction.response.send_message(f"**{member.mention}** zaten susturulmamış.", ephemeral=True)
        
@bot.tree.command(name="sil", description="Belirtilen sayıda mesajı (1-100) siler.")
@app_commands.checks.has_permissions(manage_messages=True)
@app_commands.describe(number="Silinecek mesaj sayısı")
async def sil(interaction: discord.Interaction, number: app_commands.Range[int, 1, 100]):
    await interaction.response.defer(ephemeral=True, thinking=True)
    deleted = await interaction.channel.purge(limit=number)
    await interaction.followup.send(f'✅ {len(deleted)} mesaj başarıyla silindi.', ephemeral=True)




@bot.tree.command(name="rank", description="Kendi seviyenizi veya başka bir üyenin seviyesini gösterir.")
async def rank(interaction: discord.Interaction, member: discord.Member = None):
    await interaction.response.defer()
    member = member or interaction.user
    guild_id = str(interaction.guild.id)
    user_id = str(member.id)
    
    user_data = bot.levels.get(guild_id, {}).get(user_id)
    if not user_data:
        return await interaction.followup.send(f"{member.display_name} henüz hiç XP kazanmamış.", ephemeral=True)
        
    level = user_data.get("level", 1)
    xp = user_data.get("xp", 0)
    xp_for_next_level = int((level ** 2) * 100)
    
    leaderboard = sorted(bot.levels.get(guild_id, {}).items(), key=lambda item: (item[1].get('level', 1), item[1].get('xp', 0)), reverse=True)
    rank_pos = next((i for i, (uid, data) in enumerate(leaderboard, 1) if uid == user_id), 0)
            
    progress = int((xp / xp_for_next_level) * 20) if xp_for_next_level > 0 else 0
    progress_bar = "🟩" * progress + "⬛" * (20 - progress)
    
    embed = discord.Embed(title=f"🏆 {member.display_name} Seviye Kartı", color=member.color or discord.Color.blurple())
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="Seviye", value=f"**{level}**", inline=True)
    embed.add_field(name="Sıralama", value=f"**#{rank_pos}**", inline=True)
    embed.add_field(name="Tecrübe Puanı (XP)", value=f"`{xp} / {xp_for_next_level}`", inline=False)
    embed.add_field(name="İlerleme", value=f"`{progress_bar}`", inline=False)
    await interaction.followup.send(embed=embed)

class LeaderboardView(ui.View):
    def __init__(self, interaction, data, per_page=10):
        super().__init__(timeout=180)
        self.interaction = interaction
        self.data = data
        self.per_page = per_page
        self.current_page = 0
        self.max_pages = (len(data) - 1) // per_page
        self.update_buttons()

    def update_buttons(self):
        self.children[0].disabled = self.current_page == 0
        self.children[1].disabled = self.current_page >= self.max_pages

    async def create_embed(self):
        start = self.current_page * self.per_page
        end = start + self.per_page
        
        embed = discord.Embed(title=f"🏆 {self.interaction.guild.name} Liderlik Tablosu", color=discord.Color.gold())
        
        description = ""
        for i, (user_id, user_data) in enumerate(self.data[start:end], start=start + 1):
            member = self.interaction.guild.get_member(int(user_id))
            name = member.display_name if member else f"Ayrılmış Üye ({user_id[-4:]})"
            level = user_data.get('level', 0)
            xp = user_data.get('xp', 0)
            description += f"`{i}.` **{name}** - Seviye: `{level}` (XP: `{xp}`)\n"
            
        embed.description = description or "Liderlik tablosu boş."
        embed.set_footer(text=f"Sayfa {self.current_page + 1} / {self.max_pages + 1}")
        return embed

    @ui.button(label="Önceki", style=ButtonStyle.primary, emoji="⬅️")
    async def previous_button(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user != self.interaction.user:
            return await interaction.response.send_message("Sadece komutu başlatan kişi sayfaları değiştirebilir.", ephemeral=True)
        self.current_page -= 1
        self.update_buttons()
        embed = await self.create_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @ui.button(label="Sonraki", style=ButtonStyle.primary, emoji="➡️")
    async def next_button(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user != self.interaction.user:
            return await interaction.response.send_message("Sadece komutu başlatan kişi sayfaları değiştirebilir.", ephemeral=True)
        self.current_page += 1
        self.update_buttons()
        embed = await self.create_embed()
        await interaction.response.edit_message(embed=embed, view=self)

@bot.tree.command(name="leaderboard", description="Sunucunun seviye liderlik tablosunu gösterir.")
async def leaderboard(interaction: discord.Interaction):
    await interaction.response.defer()
    guild_id = str(interaction.guild.id)
    guild_levels = bot.levels.get(guild_id, {})
    if not guild_levels: return await interaction.followup.send("Bu sunucuda henüz kimse XP kazanmamış.")
        
    sorted_users = sorted(guild_levels.items(), key=lambda item: (item[1].get('level', 0), item[1].get('xp', 0)), reverse=True)
    
    view = LeaderboardView(interaction, sorted_users)
    embed = await view.create_embed()
    await interaction.followup.send(embed=embed, view=view)

@bot.tree.command(name="daily", description="Günlük Quant ödülünüzü alın.")
@app_commands.checks.cooldown(1, 86400, key=lambda i: (i.guild_id, i.user.id))
async def daily(interaction: discord.Interaction):
    guild_id = str(interaction.guild.id)
    user_id = str(interaction.user.id)
    
    bot.economy.setdefault(guild_id, {})
    bot.economy[guild_id].setdefault(user_id, {"balance": 0})
    
    reward = random.randint(100, 250)
    bot.economy[guild_id][user_id]["balance"] += reward
    save_json(ECONOMY_FILE, bot.economy)
    
    await interaction.response.send_message(f"🎉 Günlük ödülün olan **{reward} Quant** hesabına eklendi!")

@bot.tree.command(name="balance", description="Quant bakiyenizi veya başka bir üyenin bakiyesini gösterir.")
async def balance(interaction: discord.Interaction, member: discord.Member = None):
    member = member or interaction.user
    guild_id = str(interaction.guild.id)
    user_id = str(member.id)
    
    user_balance = bot.economy.get(guild_id, {}).get(user_id, {}).get("balance", 0)
    embed = discord.Embed(title=f"{member.display_name} Bakiye Bilgisi", description=f"💰 Mevcut bakiye: **{user_balance} Quant**", color=discord.Color.green())
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="pay", description="Başka bir üyeye Quant gönderin.")
@app_commands.describe(member="Quant gönderilecek üye", amount="Gönderilecek miktar")
async def pay(interaction: discord.Interaction, member: discord.Member, amount: app_commands.Range[int, 1, None]):
    if member.bot or member == interaction.user: return await interaction.response.send_message("Kendinize veya bir bota para gönderemezsiniz.", ephemeral=True)

    guild_id = str(interaction.guild.id)
    sender_id = str(interaction.user.id)
    receiver_id = str(member.id)

    bot.economy.setdefault(guild_id, {})
    bot.economy[guild_id].setdefault(sender_id, {"balance": 0})
    bot.economy[guild_id].setdefault(receiver_id, {"balance": 0})

    sender_balance = bot.economy[guild_id][sender_id].get("balance", 0)
    if sender_balance < amount: return await interaction.response.send_message(f"Yetersiz bakiye! Sadece **{sender_balance} Quant**'a sahipsin.", ephemeral=True)

    bot.economy[guild_id][sender_id]["balance"] -= amount
    bot.economy[guild_id][receiver_id]["balance"] += amount
    save_json(ECONOMY_FILE, bot.economy)
    await interaction.response.send_message(f"✅ Başarıyla {member.mention} kullanıcısına **{amount} Quant** gönderdin.")


async def play_audio(interaction: discord.Interaction, query_or_url: str, display_name: str, sp_instance=None, repeat_count=1):
    voice_channel = interaction.user.voice.channel
    voice_client = interaction.guild.voice_client

    if not voice_client:
        voice_client = await voice_channel.connect()
    elif voice_client.channel != voice_channel:
        await voice_client.move_to(voice_channel)

    bot.now_playing = {'interaction': interaction, 'query': query_or_url, 'display_name': display_name, 'sp': sp_instance, 'repeats_left': repeat_count}

    ydl_opts = {'format': 'bestaudio/best', 'quiet': True, 'no_warnings': True, 'noplaylist': True, 'default_search': 'ytsearch1:', 'source_address': '0.0.0.0'}

    def after_playing_callback(error, current_interaction, vc):
        if error: print(f"Player error: {error}")
        next_coro = None

        if bot.now_playing and bot.now_playing.get('repeats_left', 1) > 1:
            bot.now_playing['repeats_left'] -= 1
            info = bot.now_playing
            coro_msg = info['interaction'].channel.send(f"🔁 Tekrarlanıyor: **{info['display_name']}** ({info['repeats_left']} tekrar kaldı)", delete_after=10)
            asyncio.run_coroutine_threadsafe(coro_msg, bot.loop)
            next_coro = play_audio(info['interaction'], info['query'], info['display_name'], info['sp'], info['repeats_left'])
        elif bot.sarki_kuyrugu:
            bot.now_playing = {}
            next_song_info = bot.sarki_kuyrugu.pop(0)
            next_coro = play_audio(next_song_info['interaction'], next_song_info['query'], next_song_info['query'], sp_instance=next_song_info.get('sp'), repeat_count=next_song_info.get('repeat', 1))
        else:
            bot.now_playing = {}
            if vc and vc.is_connected():
                coro = current_interaction.channel.send("🎶 Müzik kuyruğu tamamlandı.", delete_after=15)
                asyncio.run_coroutine_threadsafe(coro, bot.loop)
                bot.vc_idle_timer = bot.loop.time()
        
        if next_coro: asyncio.run_coroutine_threadsafe(next_coro, bot.loop)

    try:
        data = await bot.loop.run_in_executor(None, lambda: yt_dlp.YoutubeDL(ydl_opts).extract_info(query_or_url if query_or_url.startswith("http") else f"ytsearch:{query_or_url}", download=False))
        entry = data.get('entries', [data])[0]
        audio_url = entry['url']
        title = entry.get('title', display_name)
        bot.current_song_url = entry.get('webpage_url', query_or_url)
    except Exception as e:
        await interaction.channel.send(f'**"{display_name}" için ses alınamadı/çalınamadı.** Hata: `{e}`', delete_after=15)
        bot.loop.call_soon_threadsafe(after_playing_callback, e, interaction, voice_client)
        return

    if voice_client.is_playing() or voice_client.is_paused(): voice_client.stop()

    try:
        ffmpeg_options = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}
        voice_client.play(discord.FFmpegPCMAudio(audio_url, **ffmpeg_options), after=lambda e: bot.loop.call_soon_threadsafe(after_playing_callback, e, interaction, voice_client))
        repeat_text = f" ({bot.now_playing['repeats_left']} kez)" if bot.now_playing.get('repeats_left', 1) > 1 else ""
        await interaction.channel.send(f'🎶 Şimdi çalıyor: **{title}**{repeat_text}')
        bot.vc_idle_timer = float('inf')
    except Exception as e:
        await interaction.channel.send(f"Müzik çalınırken hata: {e}")
        bot.loop.call_soon_threadsafe(after_playing_callback, e, interaction, voice_client)

@bot.tree.command(name='play', description="Bir şarkıyı çalar veya kuyruğa ekler.")
@app_commands.describe(query="Şarkı adı veya YouTube/Spotify linki", repeats="Şarkının kaç kez tekrarlanacağı (1-20)")
async def play(interaction: discord.Interaction, query: str, repeats: app_commands.Range[int, 1, 20] = 1):
    if not interaction.user.voice: return await interaction.response.send_message("**Bu komutu kullanmak için bir ses kanalında olmalısınız.**", ephemeral=True)
    await interaction.response.defer()

    is_playing = interaction.guild.voice_client and (interaction.guild.voice_client.is_playing() or bot.now_playing)
    display_name = query

    if is_playing or bot.sarki_kuyrugu:
        queue_item = {'interaction': interaction, 'query': query, 'sp': None, 'repeat': repeats}
        bot.sarki_kuyrugu.append(queue_item)
        repeat_text = f" ({repeats} kez)" if repeats > 1 else ""
        await interaction.followup.send(f'🎵 Kuyruğa eklendi: **{display_name}**{repeat_text}')
    else:
        await interaction.followup.send(f"🔎 **{display_name}** aranıyor...")
        await play_audio(interaction, query, display_name, repeat_count=repeats)

@bot.tree.command(name='stop', description="Müziği durdurur, kuyruğu temizler ve kanaldan ayrılır.")
async def stop(interaction: discord.Interaction):
    if not interaction.user.voice: return await interaction.response.send_message("**Bir ses kanalında olmalısınız.**", ephemeral=True)
    vc = interaction.guild.voice_client
    if not vc: return await interaction.response.send_message('Bot şu anda bir ses kanalında değil.', ephemeral=True)
    bot.sarki_kuyrugu.clear()
    bot.now_playing = {}
    await vc.disconnect()
    await interaction.response.send_message('⏹️ Müzik durduruldu, kuyruk temizlendi ve bot kanaldan ayrıldı.')

@bot.tree.command(name='skip', description="Mevcut şarkıyı veya belirtilen sayıda şarkıyı atlar.")
@app_commands.describe(count="Atlanacak şarkı sayısı (varsayılan: 1)")
async def skip(interaction: discord.Interaction, count: app_commands.Range[int, 1, 50] = 1):
    if not interaction.user.voice: return await interaction.response.send_message("**Bir ses kanalında olmalısınız.**", ephemeral=True)
    vc = interaction.guild.voice_client
    if not vc or not (vc.is_playing() or vc.is_paused()): return await interaction.response.send_message('↪️ Şu anda çalan bir şarkı yok.', ephemeral=True)

    skipped_count = 1
    if count > 1:
        removed = min(count - 1, len(bot.sarki_kuyrugu))
        bot.sarki_kuyrugu = bot.sarki_kuyrugu[removed:]
        skipped_count += removed
    
    if bot.now_playing: bot.now_playing['repeats_left'] = 0
    vc.stop()
    await interaction.response.send_message(f"↪️ **{skipped_count}** şarkı atlandı.")

@bot.tree.command(name='skipall', description="Bir şarkının tüm tekrarlarını atlar ve sıradakine geçer.")
async def skipall(interaction: discord.Interaction):
    if not interaction.user.voice: return await interaction.response.send_message("**Bir ses kanalında olmalısınız.**", ephemeral=True)
    vc = interaction.guild.voice_client
    if not vc or not (vc.is_playing() or vc.is_paused()) or not bot.now_playing: return await interaction.response.send_message('↪️ Şu anda tekrarlanan bir şarkı yok.', ephemeral=True)

    await interaction.response.send_message(f"⏭️ **{bot.now_playing['display_name']}** şarkısının tüm tekrarları atlanıyor...")
    if bot.now_playing: bot.now_playing['repeats_left'] = 0
    vc.stop()

@bot.tree.command(name='spotify_login', description="Spotify hesabınızı bota bağlamak için DM'den link yollar.")
async def spotify_login(interaction: discord.Interaction):
    auth_url = sp_oauth.get_authorize_url()
    try:
        await interaction.user.send(f"Lütfen Spotify hesabına erişim izni vermek için şu bağlantıyı ziyaret et:\n{auth_url}\n\nİzin verdikten sonra yönlendirileceğin URL'den (`code=...` kısmındaki) kodu kopyalayıp `/spotify_auth code:KOD` komutuyla bana gönder.")
        await interaction.response.send_message(f"{interaction.user.mention}, DM kutunu kontrol et.", ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message("Sana DM gönderemiyorum. Sunucu ayarlarından DM'lere izin ver.", ephemeral=True)

@bot.tree.command(name='spotify_auth', description="Spotify'dan aldığınız yetkilendirme kodunu girersiniz.")
@app_commands.describe(code="Spotify'dan yönlendirilen URL'deki kod.")
async def spotify_auth(interaction: discord.Interaction, code: str):
    await interaction.response.defer(ephemeral=True)
    try:
        token_info = sp_oauth.get_access_token(code.strip(), as_dict=True, check_cache=False)
        user_spotify_tokens[interaction.user.id] = token_info
        save_spotify_tokens(user_spotify_tokens)
        await interaction.followup.send("Spotify hesabın başarıyla bağlandı! `/playlist` komutunu kullanabilirsin.")
    except Exception as e:
        await interaction.followup.send(f"Token alınırken hata oluştu: {e}")

@bot.tree.command(name='playlist', description="Spotify'daki bir çalma listenizi oynatır.")
@app_commands.describe(playlist_name="Oynatılacak çalma listesinin adı")
async def playlist_command(interaction: discord.Interaction, playlist_name: str):
    await interaction.response.defer()
    if not interaction.user.voice: return await interaction.followup.send("Bu komutu kullanmak için bir ses kanalında olmalısınız.")
    if interaction.user.id not in user_spotify_tokens: return await interaction.followup.send("Önce `/spotify_login` ile Spotify hesabını bağlamalısın.")

    token_info = user_spotify_tokens[interaction.user.id]
    if sp_oauth.is_token_expired(token_info):
        try:
            token_info = sp_oauth.refresh_access_token(token_info['refresh_token'])
            user_spotify_tokens[interaction.user.id] = token_info
            save_spotify_tokens(user_spotify_tokens)
        except Exception as e:
            return await interaction.followup.send(f"Spotify token'ın yenilenemedi. `/spotify_login` ile tekrar bağlan. Hata: {e}")

    sp = spotipy.Spotify(auth=token_info['access_token'])
    try:
        playlists = sp.current_user_playlists()
        target_playlist = next((p for p in playlists['items'] if p['name'].lower() == playlist_name.lower()), None)
        if not target_playlist: return await interaction.followup.send(f"**'{playlist_name}'** adında bir çalma listesi bulunamadı.")
        
        tracks = sp.playlist_items(target_playlist['id'])['items']
        playlist_songs = [{'interaction': interaction, 'query': f"{item['track']['name']} {item['track']['artists'][0]['name']}", 'sp': sp, 'repeat': 1} for item in tracks if item.get('track')]
        if not playlist_songs: return await interaction.followup.send("Çalma listesi boş veya şarkılar okunamadı.")
            
        vc = interaction.guild.voice_client
        if vc and (vc.is_playing() or bot.now_playing):
            bot.sarki_kuyrugu.extend(playlist_songs)
            await interaction.followup.send(f"✅ **{target_playlist['name']}** çalma listesinden {len(playlist_songs)} şarkı kuyruğa eklendi!")
        else:
            bot.sarki_kuyrugu.extend(playlist_songs)
            await interaction.followup.send(f"🎵 **{target_playlist['name']}** çalma listesinden {len(playlist_songs)} şarkı eklendi. Şimdi başlıyor...")
            first_song = bot.sarki_kuyrugu.pop(0)
            await play_audio(first_song['interaction'], first_song['query'], first_song['query'], sp_instance=first_song.get('sp'))
    except Exception as e:
        await interaction.followup.send(f"Playlist işlenirken bir hata oluştu: {e}")


@bot.tree.command(name='quant', description="Yapay zeka ile sohbet edin.")
@app_commands.describe(question="Sormak istediğiniz soru")
async def quant_command(interaction: discord.Interaction, question: str):
    await interaction.response.defer()
    if not GENAI_API_KEY: return await interaction.followup.send("Google AI API anahtarı ayarlanmamış.", ephemeral=True)
    try:
        model = genai_google.GenerativeModel('gemini-1.5-flash-latest')
        response = await bot.loop.run_in_executor(None, lambda: model.generate_content(question))
        text = response.text
        if len(text) > 1990: await interaction.followup.send(text[:1990] + "...")
        else: await interaction.followup.send(text)
    except Exception as e: await interaction.followup.send(f"Google AI hatası: {e}")

@bot.tree.command(name='resim', description="Yapay zeka ile resim oluşturun.")
@app_commands.describe(prompt="Resim için açıklama (İngilizce önerilir)")
async def resim(interaction: discord.Interaction, prompt: str):
    await interaction.response.defer()
    if not HF_TOKEN: return await interaction.followup.send("HuggingFace API anahtarı ayarlanmamış.", ephemeral=True)
    API_URL = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0"
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    try:
        response = await bot.loop.run_in_executor(None, lambda: requests.post(API_URL, headers=headers, json={"inputs": prompt}, timeout=120))
        response.raise_for_status()
        await interaction.followup.send(content=f"🎨 İşte '**{prompt}**' için resminiz:", file=discord.File(fp=BytesIO(response.content), filename='generated_image.png'))
    except Exception as e: await interaction.followup.send(f'🖼️ Resim oluşturulurken hata oluştu: {e}')

@bot.tree.command(name='steam', description="Bir oyunun Steam fiyatını gösterir.")
@app_commands.describe(game_query="Aranacak oyunun adı")
async def steam(interaction: discord.Interaction, game_query: str):
    await interaction.response.defer()
    search_url = f'https://store.steampowered.com/search/?term={url_quote(game_query)}'
    headers = {'User-Agent': 'Mozilla/5.0', 'Accept-Language': 'tr-TR,tr;q=0.9'}
    try:
        response = await bot.loop.run_in_executor(None, lambda: requests.get(search_url, headers=headers, timeout=10))
        soup = BeautifulSoup(response.content, 'html.parser')
        game_row = soup.find('a', class_='search_result_row')
        if not game_row: return await interaction.followup.send(f"'{game_query}' için Steam'de oyun bulunamadı.")
        
        embed = discord.Embed(title=f"Steam Fiyatı: {game_row.find('span', class_='title').text}", url=game_row['href'], color=discord.Color.blue())
        embed.add_field(name="Fiyat", value=game_row.find('div', class_='search_price').text.strip() or "Fiyat Belirtilmemiş")
        embed.set_thumbnail(url=game_row.find('img')['src'])
        await interaction.followup.send(embed=embed)
    except Exception as e: await interaction.followup.send(f"Steam fiyatı alınırken bir hata oluştu: {e}")

@bot.tree.command(name='translate', description="Metni belirtilen dile çevirir.")
@app_commands.describe(text="Çevrilecek metin", target_language="Hedef dil kodu (tr, en) veya adı (turkish, english)")
async def translate_command(interaction: discord.Interaction, text: str, target_language: str):
    await interaction.response.defer()
    try:
        lang_code = next((code for code, name in LANGUAGES.items() if target_language.lower() in [code, name.lower()]), None)
        if not lang_code: return await interaction.followup.send(f"Geçersiz hedef dil: '{target_language}'. `/diller` ile listeye bakabilirsiniz.")
        
        translator = Translator()
        result = await bot.loop.run_in_executor(None, lambda: translator.translate(text, dest=lang_code))
        
        embed = discord.Embed(title="Çeviri Sonucu", color=discord.Color.green())
        embed.add_field(name=f"Kaynak Metin ({LANGUAGES.get(result.src, result.src).title()})", value=f"```{text}```", inline=False)
        embed.add_field(name=f"Çevrilen Metin ({LANGUAGES.get(result.dest, result.dest).title()})", value=f"```{result.text}```", inline=False)
        await interaction.followup.send(embed=embed)
    except Exception as e: await interaction.followup.send(f"Çeviri sırasında bir hata oluştu: {e}")

@bot.tree.command(name="diller", description="Çeviri için kullanılabilir dillerin listesini gösterir.")
async def list_languages(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    lang_list = [f"`{code}`: {name.capitalize()}" for code, name in LANGUAGES.items()]
    description = "\n".join(lang_list)
    messages = [description[i:i+1990] for i in range(0, len(description), 1990)]
    for msg in messages:
        await interaction.followup.send(f"**Kullanılabilir Diller (Kod: Adı):**\n{msg}", ephemeral=True)

def _generate_game_data(rows=10, cols=10):
    item_pairs = [('49', '94'), ('O', 'Q'), ('PEN', 'PAN'), ('8', '6'), ('S', '5'), ('l', 'I')]
    base, target = random.choice(item_pairs)
    answer = (random.randint(1, rows), random.randint(1, cols))
    grid = [[(target if (r, c) == (answer[0], answer[1]) else base) for c in range(1, cols + 1)] for r in range(1, rows + 1)]
    return {"grid": grid, "answer": answer, "target": target}

@bot.tree.command(name='game', description="Farklı olanı bulma oyununu başlatır.")
async def game(interaction: discord.Interaction):
    game_data = _generate_game_data()
    max_len = max(len(str(item)) for row in game_data['grid'] for item in row) + 2
    grid_str = "```\n" + "    " + "".join([str(i).ljust(max_len) for i in range(1, 11)]) + "\n" + "   " + "-" * (10 * max_len) + "\n"
    for i, row in enumerate(game_data['grid']):
        grid_str += f"{(i+1):<2} | " + "".join([str(item).ljust(max_len) for item in row]) + "\n"
    grid_str += "```"
    bot.active_games[interaction.channel_id] = game_data
    embed = discord.Embed(title="🎲 Farklı Olanı Bul!", description=f"Aşağıdaki tabloda farklı olan **{game_data['target']}** öğesinin yerini (`satır`, `sütun`) bul.\nCevabını `/guess` ile gönder.\n{grid_str}", color=discord.Color.gold())
    embed.set_footer(text="Örnek: /guess row: 4 col: 2")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name='guess', description="Farklı olanı bulma oyununda tahminini gönderir.")
@app_commands.describe(row="Hedefin bulunduğu satır numarası", col="Hedefin bulunduğu sütun numarası")
async def guess(interaction: discord.Interaction, row: app_commands.Range[int, 1, 10], col: app_commands.Range[int, 1, 10]):
    if not (game_data := bot.active_games.get(interaction.channel_id)): return await interaction.response.send_message("Bu kanalda aktif bir oyun yok.", ephemeral=True)
    if (row, col) == game_data["answer"]:
        del bot.active_games[interaction.channel_id]
        await interaction.response.send_message(f"🎉 Tebrikler {interaction.user.mention}! Doğru cevap. Oyunu kazandın!")
    else: await interaction.response.send_message(f"Maalesef yanlış cevap, {interaction.user.mention}. Tekrar dene!", ephemeral=True)

@bot.tree.command(name='gsr', description="Google'da arama yapar.")
async def gsr(interaction: discord.Interaction, query: str): await interaction.response.send_message(f'https://www.google.com/search?q={url_quote(query)}')

@bot.tree.command(name='ytsr', description="YouTube'da arama yapar.")
async def ytsr(interaction: discord.Interaction, query: str): await interaction.response.send_message(f'https://www.youtube.com/results?search_query={url_quote(query)}')

@bot.tree.command(name='havadurumu', description="Belirtilen şehrin hava durumunu gösterir.")
async def havadurumu(interaction: discord.Interaction, city: str): await interaction.response.send_message(f'https://www.google.com/search?q={url_quote(city + " hava durumu")}')

@bot.tree.command(name="8ball", description="Sihirli 8 topa bir evet/hayır sorusu sorun.")
async def eight_ball(interaction: discord.Interaction, question: str):
    responses = ["Kesinlikle evet.", "Görünüşe göre iyi.", "Şüphesiz.", "Evet, kesinlikle.", "Buna güvenebilirsin.", "Cevabım hayır.", "Kaynaklarım hayır diyor.", "Pek iyi görünmüyor.", "Çok şüpheli.", "Bence hayır."]
    await interaction.response.send_message(f"🎱 Soru: `{question}`\nCevap: **{random.choice(responses)}**")

@bot.tree.command(name="roll", description="Belirtilen aralıkta bir zar atar (varsayılan: 1-6).")
async def roll(interaction: discord.Interaction, max_number: app_commands.Range[int, 2, 1000] = 6): await interaction.response.send_message(f"🎲 Zar atıldı ve sonuç: **{random.randint(1, max_number)}** (1-{max_number})")

@bot.tree.command(name="flip", description="Yazı tura atar.")
async def flip(interaction: discord.Interaction): await interaction.response.send_message(f"🪙 Para havaya atıldı ve sonuç: **{random.choice(['Yazı', 'Tura'])}**!")

@bot.tree.command(name="poll", description="Basit bir anket oluşturur.")
@app_commands.describe(question="Anket sorusu", options="Seçenekleri virgülle ayırarak yazın (en fazla 4).")
async def poll(interaction: discord.Interaction, question: str, options: str):
    parsed_options = [opt.strip() for opt in options.split(',')][:4]
    if len(parsed_options) < 2: return await interaction.response.send_message("Lütfen en az 2 seçenek belirtin.", ephemeral=True)

    emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣"]
    description = [f"{emojis[i]} {option}" for i, option in enumerate(parsed_options)]
    
    embed = discord.Embed(title=f"📊 Anket: {question}", description="\n".join(description), color=discord.Color.dark_aqua())
    embed.set_footer(text=f"Anketi başlatan: {interaction.user.display_name}")
    
    await interaction.response.send_message(embed=embed)
    message = await interaction.original_response()
    for i in range(len(parsed_options)): await message.add_reaction(emojis[i])
class BattleView(ui.View):
    def __init__(self, challenger: discord.Member, opponent: discord.Member, bet: int):
        super().__init__(timeout=120.0)
        self.challenger = challenger
        self.opponent = opponent
        self.bet = bet
        self.message = None

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if self.message:
            await self.message.edit(content=f"Savaş isteği zaman aşımına uğradı. {self.opponent.mention} cevap vermedi.", view=self)
        if self.challenger.id in bot.active_battles:
             del bot.active_battles[self.challenger.id]


    @ui.button(label="Kabul Et", style=ButtonStyle.success)
    async def accept(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.opponent.id:
            return await interaction.response.send_message("Bu savaş daveti sana gönderilmedi.", ephemeral=True)

        guild_id = str(interaction.guild.id)
        opponent_id = str(self.opponent.id)
        challenger_id = str(self.challenger.id)
        
        opponent_balance = bot.economy.get(guild_id, {}).get(opponent_id, {}).get("balance", 0)
        if opponent_balance < self.bet:
            return await interaction.response.send_message(f"Bu savaşı kabul etmek için yeterli bakiyen yok! Gerekli: **{self.bet} Quant**.", ephemeral=True)

        for item in self.children:
            item.disabled = True

        winner = random.choice([self.challenger, self.opponent])
        loser = self.opponent if winner.id == self.challenger.id else self.challenger

        bot.economy[guild_id][str(winner.id)]["balance"] += self.bet
        bot.economy[guild_id][str(loser.id)]["balance"] -= self.bet
        save_json(ECONOMY_FILE, bot.economy)

        await interaction.response.edit_message(content=f"⚔️ Savaş başladı! ⚔️\n\n**{self.challenger.display_name}** vs **{self.opponent.display_name}**\n\nKazanan: **{winner.mention}**! 🎉\n**{self.bet} Quant** kazandı!", view=self)
        if self.challenger.id in bot.active_battles:
             del bot.active_battles[self.challenger.id]

    @ui.button(label="Reddet", style=ButtonStyle.danger)
    async def decline(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.opponent.id and interaction.user.id != self.challenger.id:
            return await interaction.response.send_message("Bu savaşı yönetemezsin.", ephemeral=True)
            
        for item in self.children:
            item.disabled = True
            
        reason = "reddedildi" if interaction.user.id == self.opponent.id else "iptal edildi"
        await interaction.response.edit_message(content=f"Savaş isteği {interaction.user.mention} tarafından {reason}.", view=self)
        if self.challenger.id in bot.active_battles:
             del bot.active_battles[self.challenger.id]

@bot.tree.command(name="battle", description="Başka bir üyeye karşı bahisli savaş yap.")
@app_commands.describe(opponent="Savaşmak istediğin üye", bet="Bahis miktarı")
async def battle(interaction: discord.Interaction, opponent: discord.Member, bet: app_commands.Range[int, 1, None]):
    if opponent.bot or opponent == interaction.user:
        return await interaction.response.send_message("Kendinle veya bir botla savaşamazsın.", ephemeral=True)
        
    if interaction.user.id in bot.active_battles:
        return await interaction.response.send_message("Zaten gönderilmiş bir savaş isteğin var.", ephemeral=True)

    guild_id = str(interaction.guild.id)
    challenger_id = str(interaction.user.id)
    
    bot.economy.setdefault(guild_id, {}).setdefault(challenger_id, {"balance": 0})
    bot.economy[guild_id].setdefault(str(opponent.id), {"balance": 0})
    
    challenger_balance = bot.economy[guild_id][challenger_id].get("balance", 0)
    if challenger_balance < bet:
        return await interaction.response.send_message(f"Yetersiz bakiye! Bu savaşı başlatmak için **{bet} Quant**'a ihtiyacın var. Bakiyen: **{challenger_balance} Quant**.", ephemeral=True)

    view = BattleView(challenger=interaction.user, opponent=opponent, bet=bet)
    bot.active_battles[interaction.user.id] = True 
    
    message_content = f"Hey {opponent.mention}! {interaction.user.mention} sana **{bet} Quant** için savaş teklif ediyor. Ne dersin?"
    await interaction.response.send_message(message_content, view=view)
    view.message = await interaction.original_response()

KART_DEGERLERI = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, '10': 10, 'J': 10, 'Q': 10, 'K': 10, 'A': 11}
KART_TURU = ['♠️', '♥️', '♦️', '♣️']

def deste_olustur():
    return [f"{deger}{tur}" for tur in KART_TURU for deger in KART_DEGERLERI]

def el_degeri_hesapla(el):
    deger = sum(KART_DEGERLERI[kart[:-2]] for kart in el)
    as_sayisi = el.count('A♠️') + el.count('A♥️') + el.count('A♦️') + el.count('A♣️')
    while deger > 21 and as_sayisi:
        deger -= 10
        as_sayisi -= 1
    return deger

class BlackjackView(ui.View):
    def __init__(self, interaction: discord.Interaction, bet: int):
        super().__init__(timeout=180.0)
        self.interaction = interaction
        self.bet = bet
        self.deste = deste_olustur()
        random.shuffle(self.deste)
        self.oyuncu_eli = [self.deste.pop(), self.deste.pop()]
        self.krupiye_eli = [self.deste.pop(), self.deste.pop()]
        self.message = None

    async def oyun_sonu(self, interaction: discord.Interaction, sonuc: str, kazanc: int):
        for item in self.children:
            item.disabled = True
        
        guild_id = str(interaction.guild.id)
        user_id = str(interaction.user.id)
        
        bot.economy[guild_id][user_id]["balance"] += kazanc
        save_json(ECONOMY_FILE, bot.economy)
        
        embed = await self.embed_olustur(oyun_sonu=True)
        embed.title = f"Blackjack Sonucu: {sonuc}"
        if kazanc > 0:
            embed.description = f"Tebrikler! **{kazanc} Quant** kazandın."
        elif kazanc < 0:
            embed.description = f"Maalesef! **{-kazanc} Quant** kaybettin."
        else:
            embed.description = "Berabere! Bahsin iade edildi."
            
        await interaction.response.edit_message(embed=embed, view=self)
    
        if interaction.user.id in bot.blackjack_games:
            del bot.blackjack_games[interaction.user.id]

    async def embed_olustur(self, oyun_sonu=False):
        oyuncu_degeri = el_degeri_hesapla(self.oyuncu_eli)
        krupiye_gosterilen_el = f"{self.krupiye_eli[0]}  [ ? ]" if not oyun_sonu else "  ".join(self.krupiye_eli)
        krupiye_degeri = el_degeri_hesapla(self.krupiye_eli)

        embed = discord.Embed(title=f"Blackjack Masası | Bahis: {self.bet} Quant", color=discord.Color.green())
        embed.add_field(name=f"{self.interaction.user.display_name}'in Eli ({oyuncu_degeri})", value="  ".join(self.oyuncu_eli), inline=False)
        embed.add_field(name=f"Krupiyenin Eli ({el_degeri_hesapla([self.krupiye_eli[0]]) if not oyun_sonu else krupiye_degeri})", value=krupiye_gosterilen_el, inline=False)
        embed.set_footer(text="Sıra sende!")
        return embed

    @ui.button(label="Kart Çek (Hit)", style=ButtonStyle.success)
    async def hit(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.interaction.user.id:
            await interaction.response.send_message("Bu senin oyunun değil!", ephemeral=True)
            return
            
        self.oyuncu_eli.append(self.deste.pop())
        oyuncu_degeri = el_degeri_hesapla(self.oyuncu_eli)
        
        if oyuncu_degeri > 21:
            await self.oyun_sonu(interaction, "Kaybettin (Bust)!", -self.bet)
        else:
            embed = await self.embed_olustur()
            await interaction.response.edit_message(embed=embed, view=self)

    @ui.button(label="Dur (Stand)", style=ButtonStyle.danger)
    async def stand(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.interaction.user.id:
            await interaction.response.send_message("Bu senin oyunun değil!", ephemeral=True)
            return
            
        krupiye_degeri = el_degeri_hesapla(self.krupiye_eli)
        while krupiye_degeri < 17:
            self.krupiye_eli.append(self.deste.pop())
            krupiye_degeri = el_degeri_hesapla(self.krupiye_eli)

        oyuncu_degeri = el_degeri_hesapla(self.oyuncu_eli)
        
        if krupiye_degeri > 21 or oyuncu_degeri > krupiye_degeri:
            await self.oyun_sonu(interaction, "Kazandın!", self.bet)
        elif krupiye_degeri > oyuncu_degeri:
            await self.oyun_sonu(interaction, "Kaybettin!", -self.bet)
        else:
            await self.oyun_sonu(interaction, "Berabere (Push)", 0)


@bot.tree.command(name="blackjack", description="Blackjack (21) oynayarak Quant kazan veya kaybet.")
@app_commands.describe(bet="Oynamak istediğiniz Quant miktarı.")
async def blackjack(interaction: discord.Interaction, bet: app_commands.Range[int, 10, None]):
    guild_id = str(interaction.guild.id)
    user_id = str(interaction.user.id)

    if user_id in bot.blackjack_games:
        return await interaction.response.send_message("Zaten devam eden bir Blackjack oyunun var.", ephemeral=True)

    bot.economy.setdefault(guild_id, {}).setdefault(user_id, {"balance": 0})
    user_balance = bot.economy[guild_id][user_id].get("balance", 0)

    if user_balance < bet:
        return await interaction.response.send_message(f"Yetersiz bakiye! Bu bahsi oynamak için **{bet} Quant**'a ihtiyacın var. Bakiyen: **{user_balance} Quant**.", ephemeral=True)

    view = BlackjackView(interaction, bet)
    bot.blackjack_games[user_id] = view

    oyuncu_degeri = el_degeri_hesapla(view.oyuncu_eli)
    if oyuncu_degeri == 21:
        kazanc = int(bet * 1.5) 
        await view.oyun_sonu(interaction, "BLACKJACK!", kazanc)
    else:
        embed = await view.embed_olustur()
        await interaction.response.send_message(embed=embed, view=view)

@bot.tree.command(name='ping', description="Botun gecikme süresini ölçer.")
async def ping(interaction: discord.Interaction): await interaction.response.send_message(f'Pong! {round(bot.latency * 1000)}ms')

@bot.tree.command(name='saat', description="Geçerli saati gösterir.")
async def saat(interaction: discord.Interaction): await interaction.response.send_message(f'🕒 Geçerli saat (UTC): {datetime.datetime.now(datetime.timezone.utc).strftime("%H:%M:%S")}')

@bot.tree.command(name="userinfo", description="Bir üye hakkında detaylı bilgi gösterir.")
async def userinfo(interaction: discord.Interaction, member: discord.Member = None):
    member = member or interaction.user
    embed = discord.Embed(title=f"Kullanıcı Bilgisi: {member.display_name}", color=member.color or discord.Color.default(), timestamp=datetime.datetime.now())
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="ID", value=f"`{member.id}`")
    embed.add_field(name="Durum", value=f"`{str(member.status).title()}`")
    embed.add_field(name="En Yüksek Rol", value=member.top_role.mention)
    embed.add_field(name="Sunucuya Katılma", value=f"<t:{int(member.joined_at.timestamp())}:D>", inline=False)
    embed.add_field(name="Discord'a Katılma", value=f"<t:{int(member.created_at.timestamp())}:D>", inline=False)
    roles = [role.mention for role in sorted(member.roles, key=lambda r: r.position, reverse=True) if role.name != "@everyone"]
    if roles: embed.add_field(name=f"Roller [{len(roles)}]", value=" ".join(roles), inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="serverinfo", description="Bu sunucu hakkında detaylı bilgi gösterir.")
async def serverinfo(interaction: discord.Interaction):
    guild = interaction.guild
    embed = discord.Embed(title=f"Sunucu Bilgisi: {guild.name}", color=discord.Color.blue(), timestamp=guild.created_at)
    if guild.icon: embed.set_thumbnail(url=guild.icon.url)
    if guild.banner: embed.set_image(url=guild.banner.url)
    
    embed.add_field(name="Sahip", value=guild.owner.mention, inline=True)
    embed.add_field(name="ID", value=f"`{guild.id}`", inline=True)
    embed.add_field(name="Üyeler", value=f"**{guild.member_count}** ({sum(1 for m in guild.members if not m.bot)} Kullanıcı, {sum(1 for m in guild.members if m.bot)} Bot)", inline=False)
    embed.add_field(name="Kanallar", value=f"Metin: {len(guild.text_channels)}\nSes: {len(guild.voice_channels)}\nKategori: {len(guild.categories)}", inline=True)
    embed.add_field(name="Roller", value=f"**{len(guild.roles)}**", inline=True)
    embed.set_footer(text="Sunucu Oluşturulma Tarihi")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="avatar", description="Bir üyenin profil resmini gösterir.")
async def avatar(interaction: discord.Interaction, member: discord.Member = None):
    member = member or interaction.user
    embed = discord.Embed(title=f"{member.display_name} Avatarı", color=member.color)
    embed.set_image(url=member.display_avatar.url)
    await interaction.response.send_message(embed=embed)


@tasks.loop(seconds=30.0)
async def check_vc_idle():
    """Ses kanallarında boşta kalan botu kontrol eder ve atar."""
    idle_disconnect_timeout = 300  
    for vc in bot.voice_clients:
        if vc.is_connected() and not vc.is_playing() and not bot.sarki_kuyrugu:
            real_members = [m for m in vc.channel.members if not m.bot]
            if not real_members:
                if (bot.loop.time() - bot.vc_idle_timer) > idle_disconnect_timeout:
                    await vc.disconnect()
            else: bot.vc_idle_timer = bot.loop.time()
        else: bot.vc_idle_timer = bot.loop.time()


@bot.tree.command(name='help', description="Botun tüm komutlarını kategorilere ayrılmış olarak listeler.")
async def help_command(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    embed = discord.Embed(title="🤖 Quant Bot Komut Rehberi", description="Merhaba! İşte kullanabileceğin tüm komutlar:", color=discord.Color.purple())
    embed.add_field(name="🛡️ Moderasyon", value="`/sil`, `/mute`, `/unmute`, `/warn`, `/warnings`, `/duyuru`", inline=False)
    embed.add_field(name="🌟 Seviye & Ekonomi", value="`/rank`, `/leaderboard`, `/daily`, `/balance`, `/pay`", inline=False)
    embed.add_field(name="🎵 Müzik", value="`/play`, `/stop`, `/skip`, `/skipall`, `/playlist`, `/spotify_login`, `/spotify_auth`", inline=False)
    embed.add_field(name="✨ AI & Arama", value="`/quant`, `/resim`, `/steam`, `/gsr`, `/ytsr`, `/havadurumu`", inline=False)
    embed.add_field(name="🎉 Eğlence & Oyun", value="`/8ball`, `/roll`, `/flip`, `/poll`, `/game`, `/guess`, `/blackjack`, `/battle`", inline=False)
    embed.add_field(name="🛠️ Yardımcı & Bilgi", value="`/userinfo`, `/serverinfo`, `/avatar`, `/translate`, `/diller`, `/ping`, `/saat`", inline=False)
    embed.add_field(name="⚙️ Sunucu Ayarları (Yönetici)", value="`/settings welcome`, `/settings goodbye`", inline=False)
    embed.set_footer(text="Quant Bot | Kapsamlı ve Gelişmiş")
    await interaction.followup.send(embed=embed)


if __name__ == "__main__":
    if not DISCORD_BOT_TOKEN:
        print("\nHATA: Discord bot token'ı bulunamadı!")
        print("Lütfen kodun en üstündeki DISCORD_BOT_TOKEN değişkenini düzenleyin veya bir ortam değişkeni olarak ayarlayın.\n")
    else:
        try:
            bot.run(DISCORD_BOT_TOKEN)
        except discord.errors.PrivilegedIntentsRequired:
            print("\nHATA: Gerekli Privileged Gateway Intent'leri etkinleştirilmemiş.")
            print("Lütfen https://discord.com/developers/applications adresinden botunuzun ayarlarından 'MESSAGE CONTENT INTENT' ve 'SERVER MEMBERS INTENT' seçeneklerini açın.\n")
        except Exception as e:
            print(f"Bot çalıştırılırken bir hata oluştu: {e}")
