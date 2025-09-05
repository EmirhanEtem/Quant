# Quant Bot

Quant Bot, Discord sunucuları için geliştirilmiş, çok yönlü ve modüler bir bottur. Moderasyon, müzik (YouTube & Spotify), yapay zeka entegrasyonları (metin ve resim üretimi), seviye/ekonomi sistemi ve çeşitli eğlence komutları ile sunucunuzu daha interaktif ve yönetilebilir hale getirmeyi amaçlar.

![Discord](https://img.shields.io/discord/1279064789116653643?label=Discord&logo=discord&style=for-the-badge)

## ✨ Ana Özellikler

- **🛡️ Gelişmiş Moderasyon:** Üyeleri uyarma, susturma, mesaj silme, duyuru yapma ve detaylı loglama.
- **🎵 Kapsamlı Müzik Sistemi:** YouTube ve Spotify çalma listeleri/şarkıları çalma, şarkı kuyruğu, tekrar etme ve daha fazlası.
- **✨ Yapay Zeka Entegrasyonları:**
  - Google Gemini ile akıllı sohbet (`/quant`).
  - Stable Diffusion ile metinden resim oluşturma (`/resim`).
- **🌟 Seviye & Ekonomi Sistemi:**
  - Mesaj atarak XP kazanın ve seviye atlayın.
  - Liderlik tablosu ile sunucudaki sıralamanızı görün (`/leaderboard`).
  - Günlük ödüller, para transferi ve bahisli oyunlarla sanal ekonomi (`/daily`, `/pay`, `/battle`).
- **🎉 Eğlence ve Oyunlar:**
  - Blackjack (`/blackjack`) ve bahisli Savaş (`/battle`) gibi interaktif oyunlar.
  - Anket, zar atma, yazı-tura ve "farklı olanı bul" gibi klasik eğlence komutları.
- **🛠️ Yardımcı Komutlar:** Kullanıcı/sunucu bilgisi, avatar, çeviri, Steam fiyat sorgulama ve daha fazlası.
- **⚙️ Sunucuya Özel Ayarlar:** Hoş geldin/güle güle mesaj kanallarını ayarlama imkanı.

## 🚀 Kurulum ve Başlatma

Bu botu kendi sunucunuzda çalıştırmak için aşağıdaki adımları izleyin.

### 1. Ön Gereksinimler
- Python 3.8 veya üstü
- Bir Discord Bot Hesabı
- Gerekli API Anahtarları (Google, HuggingFace, Spotify)

### 2. Kurulum
1.  **Projeyi Klonlayın:**
    ```bash
    git clone https://github.com/kullanici/quant-bot.git
    cd quant-bot
    ```

2.  **Gerekli Kütüphaneleri Yükleyin:**
    Proje `requirements.txt` dosyası içermiyorsa, aşağıdaki komutlarla kütüphaneleri manuel olarak yükleyin:
    ```bash
    pip install discord.py google-generativeai requests beautifulsoup4 yt-dlp spotipy pyfiglet googletrans==4.0.0-rc1
    pip install pynacl
    ```

3.  **Yapılandırma (API Anahtarları ve Token'lar):**
    Kod dosyasının en üstündeki değişkenleri kendi bilgilerinizle doldurun veya bir `.env` dosyası oluşturup ortam değişkenleri olarak ayarlayın.
    - `DISCORD_BOT_TOKEN`: Discord Geliştirici Portalı'ndan aldığınız bot token'ı.
    - `GENAI_API_KEY`: Google AI Studio'dan aldığınız Gemini API anahtarı.
    - `HF_TOKEN`: HuggingFace'ten aldığınız `read` yetkisine sahip API anahtarı.
    - `SPOTIPY_CLIENT_ID`: Spotify Developer Dashboard'dan aldığınız Client ID.
    - `SPOTIPY_CLIENT_SECRET`: Spotify Developer Dashboard'dan aldığınız Client Secret.
    - `SPOTIPY_REDIRECT_URI`: Spotify uygulamanızda belirttiğiniz yönlendirme adresi (örn: `http://localhost:8888/callback`).
    - `LOG_CHANNEL_ID`: Moderasyon loglarının gönderileceği Discord metin kanalı ID'si.

4.  **Discord Geliştirici Portalı Ayarları:**
    - Botunuzun ayarlarından **Privileged Gateway Intents** bölümüne gidin.
    - **SERVER MEMBERS INTENT** ve **MESSAGE CONTENT INTENT** seçeneklerini etkinleştirin. Bu, botun üye bilgilerine ve mesaj içeriklerine erişmesi için zorunludur.

5.  **Botu Çalıştırın:**
    ```bash
    python Quant_git.py
    ```

## 📝 Komut Listesi

Bot, slash komutları (`/`) ile çalışır. İşte ana komutların bir listesi:

| Kategori      | Komut               | Açıklama                                                       |
|---------------|---------------------|----------------------------------------------------------------|
| **Moderasyon**| `/warn`             | Bir üyeyi sebep belirterek uyarır.                             |
|               | `/warnings`         | Bir üyenin uyarılarını listeler.                               |
|               | `/mute`             | Bir üyeyi belirtilen süreyle susturur.                         |
|               | `/unmute`           | Bir üyenin susturmasını kaldırır.                              |
|               | `/sil`              | Belirtilen sayıda mesajı siler (1-100).                        |
|               | `/duyuru`           | Belirtilen kanala gömülü bir duyuru gönderir.                  |
| **Seviye**    | `/rank`             | Seviye ve XP bilginizi gösterir.                          |
|               | `/leaderboard`      | Sunucunun seviye liderlik tablosunu gösterir.                  |
|               | `/daily`            | Günlük Quant ödülünüzü alırsınız.                              |
|               | `/balance`          | Quant bakiyenizi gösterir.                                     |
|               | `/pay`              | Başka bir üyeye Quant gönderir.                                |
| **Müzik**     | `/play`             | Bir şarkıyı (YouTube/Spotify) çalar veya kuyruğa ekler.        |
|               | `/stop`             | Müziği durdurur ve kanaldan ayrılır.                           |
|               | `/skip`             | Çalan şarkıyı atlar.                                           |
|               | `/skipall`          | Şarkının tüm tekrarlarını atlar.                               |
|               | `/playlist`         | Bağlı Spotify hesabınızdan bir çalma listesi oynatır.          |
|               | `/spotify_login`    | Spotify hesabınızı bağlamak için yetkilendirme linki gönderir. |
|               | `/spotify_auth`     | Spotify'dan alınan kodu bota girersiniz.                       |
| **Yapay Zeka**| `/quant`            | Yapay zeka ile sohbet edersiniz.                               |
|               | `/resim`            | Yapay zekaya metinden resim çizdirirsiniz.                     |
| **Arama**     | `/steam`            | Bir oyunun Steam fiyatını gösterir.                          |
|               | `/gsr`, `/ytsr`     | Google ve YouTube'da arama yapar.                              |
|               | `/havadurumu`       | Şehir hava durumunu arar.                                      |
| **Eğlence**   | `/8ball`            | Sihirli 8 topa soru sorarsınız.                             |
|               | `/roll`, `/flip`    | Zar atar veya yazı-tura atar.                                  |
|               | `/poll`             | Basit bir anket oluşturur.                                     |
|               | `/game`, `/guess`   | Farklı olanı bulma oyununu başlatır ve tahmin edersiniz.       |
|               | `/battle`           | Başka bir üyeye karşı bahisli savaş yaparsınız.                |
|               | `/blackjack`        | Bahisli Blackjack (21) oynarsınız.                             |
| **Yardımcı**  | `/userinfo`         | Bir üye hakkında detaylı bilgi gösterir.                       |
|               | `/serverinfo`       | Sunucu hakkında detaylı bilgi gösterir.                        |
|               | `/avatar`           | Bir üyenin avatarını gösterir.                                 |
|               | `/translate`        | Metni belirtilen dile çevirir.                                 |
|               | `/ping`, `/saat`    | Botun gecikmesini ve saati gösterir.                           |
| **Ayarlar**   | `/settings welcome` | Hoş geldin mesaj kanalını ayarlar.                             |
|               | `/settings goodbye` | Güle güle mesaj kanalını ayarlar.                              |
