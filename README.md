# Quant Discord Bot

Quant, Discord sunucularınız için çok yönlü bir bottur. Müzik çalma, moderasyon, yapay zeka destekli sohbet, Spotify entegrasyonu ve daha fazlasını sunar. Bu bot, kullanıcı dostu bir deneyim sağlamak için tasarlanmıştır.

---

## 🚀 Özellikler

### 🎵 Müzik
- **`!play <şarkı_adı/URL>`**: Şarkı çalar veya kuyruğa ekler.
- **`!playlist <Spotify_Playlist_Adı>`**: Spotify çalma listelerini oynatır (Spotify hesabınızı bağlamanız gerekir).
- **`!stop`**: Müziği durdurur ve botu ses kanalından çıkarır.
- **`!skip`**: Sıradaki şarkıya geçer.

### 🌐 Genel
- **`!ping`**: Botun gecikme süresini gösterir.
- **`!saat`**: Geçerli saati gösterir.
- **`!havadurumu <şehir>`**: Belirtilen şehrin hava durumunu arar.
- **`!gsr <arama>`**: Google'da arama yapar.
- **`!ytsr <arama>`**: YouTube'da arama yapar.

### ✨ Yapay Zeka ve Eğlence
- **`!quant <soru>`**: Yapay zeka ile sohbet et.
- **`!resim <prompt>`**: Yazdığınız prompt'a göre resim oluşturur.
- **`!steam <oyun_adı>`**: Oyunun Steam fiyatını gösterir.

### 🛠️ Moderasyon (Sadece 'Moderator' Rolü)
- **`!duyuru`**: Adım adım duyuru oluşturur.
- **`!sil <sayı>`**: Belirtilen sayıda mesajı siler (1-100).
- **`!mutetx <@üye> <süre>`**: Üyeyi metin kanallarında susturur.
- **`!mutevc <@üye> <süre>`**: Üyeyi ses kanallarında susturur.
- **`!unmutetx <@üye>`**: Metin susturmasını kaldırır.
- **`!unmutevc <@üye>`**: Ses susturmasını kaldırır.

---

## 📦 Kurulum

### 1. Gerekli Bağımlılıkları Yükleyin
```bash
pip install -r requirements.txt
