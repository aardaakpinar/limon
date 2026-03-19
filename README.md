# 🍋 Limon - Terminal Tabanlı AI Asistanı

Yerel Ollama kullanan, terminal üzerinden çalışan, güvenli AI asistanı. Kendi bilgisayarınızda çalışan kişisel AI ajanı.

![Version](https://img.shields.io/badge/Version-1.1.0-yellow)
![Node.js](https://img.shields.io/badge/Node.js-18%2B-green)
![Platform](https://img.shields.io/badge/Platform-Linux%20%7C%20macOS%20%7C%20Windows-blue)
![License](https://img.shields.io/badge/License-GPLv3-blue)

## ✨ Özellikler

- 🧠 **Yerel AI**: Ollama, Gemini, Claude, OpenAI desteği
- 🎯 **Sistem Algılama**: Linux/macOS/Windows için otomatik OS-spesifik komutlar
- 💻 **Komut Yürütme**: Terminal komutlarını güvenli şekilde çalıştır
- 📁 **Dosya İşlemleri**: Oku, yaz, sil, taşı, kopyala, listele
- 🌐 **API Çağrıları**: HTTP istekleri yap (GET, POST, PUT, DELETE)
- 🔐 **Güvenli Sandbox**: Belirtilen dizin içinde sınırlı çalışma
- ⚡ **Hızlı**: Yerel işleme, API latency yok
- 🇹🇷 **Türkçe Arayüz**: Tamamen Türkçe komutlar ve çıktılar

## 🚀 Hızlı Başlangıç

### Gereksinimler

- **Node.js** >= 18.0.0
- **Ollama** (lokal AI için) - [indir](https://ollama.ai)
- Veya API Key (Gemini, Claude, OpenAI için)

### 1. Adım: Ollama Kurulumu (Opsiyonel)

```bash
# Ollama'yı indir ve kur (https://ollama.ai)

# Ollama sunucusunu başlat
ollama serve

# Başka terminal'de: Model indir
ollama pull llama2
# Alternatifler: mistral, neural-chat, codellama
```

### 2. Adım: Limon Kurulumu

```bash
# Depoyu klonla veya dosyaları indir
cd limon

# Kurulumu başlat
node index.js --setup

# Kurulum menüsü açılacak:
# [1] Google Gemini
# [2] Anthropic Claude
# [3] OpenAI ChatGPT
# [4] Ollama (lokal) ← Önerilen

# Seçim yap ve talimatları takip et
```

### 3. Adım: İlk Sohbeti Başlat

```bash
node index.js
```

```
  Siz > Masaüstümde deneme.txt oluştur

  Dusunuyor...

  🍋 Limon [Llama2]
  Masaüstünde deneme.txt dosyası oluşturuyorum...
  ────────────────────────────────────────────────

  Calistiriliyor...

  Sonuc:
  | Yazildi: /home/user/Desktop/deneme.txt

  Tamamlandi.

  Siz >
```

## 📖 Kullanım

### İnteraktif Mod (Önerilen)

```bash
node index.js
```

Komutları yazabilirsiniz:

```
Siz > bir todo listesi oluştur
Siz > proje dosyalarını listele
Siz > config.json dosyasını oku
Siz > sistem bilgisini göster
```

### Tek Seferlik Komut

```bash
# -q veya --query ile
node index.js -q "Masaüstündeki dosyaları listele"
node index.js --query "Sistem bilgisini göster"

# Veya direkt
node index.js "Merhaba! Bugün nasılsın?"
```

### İleri Komutlar

```bash
# Kurulumu yeniden yapma
node index.js --setup

# Geçmiş temizle
node index.js --temizle
node index.js --clear

# Çıkış komutu (interaktif modda)
> --quit
```

## 🖥️ Sistem Algılama

Limon otomatik olarak işletim sisteminizi algılar ve uygun komutları kullanır:

### Linux/macOS
```
SISTEM BİLGİSİ:
- İşletim Sistemi: Linux (x64)
- Node.js: v22.22.0
- Ev Dizini: /home/user

→ Komutlar: ls, mkdir, rm, chmod vb.
→ Path: /home/user/Desktop/file.txt
```

### Windows
```
SISTEM BİLGİSİ:
- İşletim Sistemi: Windows (x64)
- Node.js: v22.22.0
- Ev Dizini: C:\Users\user

→ Komutlar: dir, md, del, icacls vb.
→ Path: C:\Users\user\Desktop\file.txt
```

LLM otomatik olarak işletim sisteminize uygun komutlar yazacaktır!

## 🎯 Yapılabilecek İşlemler

### 📁 Dosya İşlemleri

```
"Masaüstümde deneme.txt oluştur"
"config.json dosyasını oku"
"Tüm .log dosyalarını sil"
"src klasörünü backup al"
"file1.txt dosyasını file2.txt olarak kaydet"
"Documents klasöründeki tüm PDF'leri listele"
```

### 💻 Komut Çalıştırma

```
"Sistem bilgisini göster"
"Çalışan uygulamaları listele"
"Disk kullanımını kontrol et"
"Node.js sürümünü göster"
"Ağ bağlantısını test et"
```

### 🌐 API Çağrıları

```
"GitHub API'sinden octocat bilgisini getir"
"JSONPlaceholder API'sinden tüm postları indir"
"Hava durumu API'sinden İstanbul'un hava durumunu al"
"Kendi API'den veri çek"
```

## ⚙️ Yapılandırma

Kurulum sırasında otomatik `~/.limon/config.json` dosyası oluşturulur:

```json
{
  "provider": "ollama",
  "apiKey": "",
  "workDir": "/home/user/limon",
  "agentHome": "/home/user/limon",
  "securityEnabled": true,
  "allowAppLaunch": true,
  "allowApiCalls": true,
  "allowedApiDomains": [],
  "ollamaPort": 11434,
  "ollamaModel": "llama2"
}
```

### Konfigürasyon Seçenekleri

| Seçenek | Açıklama | Varsayılan |
|---------|----------|-----------|
| `provider` | AI sağlayıcı (gemini, claude, openai, ollama) | ollama |
| `apiKey` | API anahtarı (Ollama için gerekli değil) | "" |
| `workDir` | Çalışma dizini | /home/limon |
| `agentHome` | Ajan ev dizini | /home/limon |
| `securityEnabled` | Güvenlik kontrolleri | true |
| `allowAppLaunch` | Uygulama başlatma | true |
| `allowApiCalls` | API çağrıları | true |
| `ollamaPort` | Ollama sunucu portu | 11434 |
| `ollamaModel` | Ollama model adı | llama2 |

### Ortam Değişkenleri

```bash
# API Keys
export LIMON_API_KEY="sk-..."              # Genel API key
export LIMON_GEMINI_API_KEY="..."          # Gemini key
export LIMON_CLAUDE_API_KEY="sk-ant-..."   # Claude key
export LIMON_OPENAI_API_KEY="sk-..."       # OpenAI key

# Ollama
export OLLAMA_HOST="http://localhost:11434"
export OLLAMA_MODEL="llama2"

# Debug
export LIMON_DEBUG="true"
```

## 🔒 Güvenlik

Limon **varsayılan olarak güvenlidir**:

### Koruma Mekanizmaları

- **Path Sandbox**: Sadece belirlenen `workDir` dizini içinde işlem yapabilir
- **Yasaklı Komutlar**: `rm -rf /`, `format C:` gibi tehlikeli komutlar engellenir
- **Shell Syntax Kontrolleri**: Komut zincirleme (`&&`, `|`), path traversal (`../`) engellenir
- **Komut Timeoutu**: Komutlar 30 saniyeden sonra durdurulur
- **User Approval**: Sandbox dışı işlemler kullanıcı onayı gerektirir
- **Logging**: Tüm işlemler kaydedilir

### Yasaklı Komutlar

```
- rm -rf / (Kök dizin silme)
- format C: (Disk formatlama)
- diskpart (Disk bölümleme)
- mkfs (Dosya sistemi oluşturma)
- nc -e (Reverse shell)
- Metasploit (msfconsole, msfvenom)
- ve daha fazlası...
```

### Engellenen Syntax

```
- Komut zincirleme: && || ;
- Pipe: |
- Komut ikamesi: ` $ ( )
- Yönlendirme: < > >> 2>
- Path traversal: ../
```

**⚠️ Uyarı**: `securityEnabled=false` yapmak tehlikelidir. Sadece **tamamen güvenilir ortamlarda** denemeler yapın.

## 📁 Dosya Yapısı

```
limon/
├── index.js                  # Ana giriş noktası
├── setup.js                  # Kurulum ve konfigürasyon
├── config.js                 # Konfigürasyon dosyası yönetimi
├── providers.js              # LLM provider'ları (Gemini, Claude, OpenAI, Ollama)
├── executor.js               # Komut yürütücü
├── security.js               # Güvenlik kontrolleri
├── interaction.js            # Kullanıcı onayı ve etkileşimi
├── ui.js                     # Terminal arayüzü ve renkler
└── README.md                 # Bu dosya

~/.limon/
└── config.json               # Kullanıcı yapılandırması (otomatik oluşturulur)
```

## 📊 Provider Karşılaştırması

| Özellik | Gemini | Claude | OpenAI | Ollama |
|---------|--------|--------|--------|--------|
| API Gerekli | ✅ | ✅ | ✅ | ❌ |
| Lokal | ❌ | ❌ | ❌ | ✅ |
| Offline | ❌ | ❌ | ❌ | ✅ |
| Ücretsiz Tier | ✅ | ❌ | ❌ | ✅ |
| Hız | Orta | Hızlı | Hızlı | Değişken* |
| Kurulum | Kolay | Kolay | Kolay | Orta |

*GPU ile hızlı, CPU'da yavaş

## 🚀 Ollama Model Seçimi

### Hızlı (Düşük Bellek)
```bash
ollama pull neural-chat     # ~2.9 GB
ollama pull openchat        # ~3.5 GB
```

### Dengeli (Önerilen)
```bash
ollama pull mistral         # ~4.1 GB
ollama pull llama2          # ~3.8 GB
```

### Güçlü (Yüksek Kalite)
```bash
ollama pull llama2-uncensored  # ~7 GB
ollama pull openhermes         # ~8 GB
```

### Türkçe İyi
```bash
ollama pull neural-chat     # Türkçe çok iyi
```

## 🧪 Örnekler

### Örnek 1: Dosya Oluşturma

```
Siz > Desktop'ta todo.txt oluştur ve "- İş 1\n- İş 2" yaz

🍋 Limon [Llama2]
Todo dosyası oluşturuyorum...

Calistiriliyor...

Sonuc:
| Yazildi: /home/user/Desktop/todo.txt

Tamamlandi.
```

### Örnek 2: Dosya Okuma

```
Siz > README.md dosyasını oku ve ilk 10 satırını göster

🍋 Limon [Llama2]
README.md dosyasını okuyorum ve ilk satırları gösteriyorum...

Calistiriliyor...

Sonuc:
| # Limon - Terminal Tabanlı AI Asistanı
| Yerel Ollama kullanan, terminal üzerinden çalışan...
| ...
```

### Örnek 3: Sistem Bilgisi

```
Siz > sistem bilgisini göster

🍋 Limon [Llama2]
Sistem bilgisini alıyorum...

Calistiriliyor...

Sonuc:
| Sistem: Linux
| Mimarı: x64
| Node.js: v22.22.0
| Ev Dizini: /root
```

## 🐛 Sorun Giderme

### "Ollama bağlantı hatası"

```
Ollama bağlantı hatası. Ollama'nın localhost:11434 
adresinde çalışıyor olduğundan emin olun.
```

**Çözüm:**
```bash
# Terminal 1: Ollama sunucusunu başlat
ollama serve

# Terminal 2: Limon'u çalıştır
node index.js
```

### "Model bulunamadı"

```
Ollama API hatası (500).
```

**Çözüm:**
```bash
# Modeli indir
ollama pull llama2

# Yüklü modelleri listele
ollama list
```

### "API key gerekli"

Eğer Gemini/Claude/OpenAI seçtiysen:

```bash
# API anahtarını al:
# - Gemini: https://aistudio.google.com/app/apikey
# - Claude: https://console.anthropic.com/settings/keys
# - OpenAI: https://platform.openai.com/api-keys

# Kurulumu yeniden yapma
node index.js --setup
```

### "Komutlar çalışmıyor"

1. `securityEnabled` kontrolü yapın
2. Sandbox (`workDir`) içinde misiniz kontrol edin
3. Path syntax'ı kontrol edin (Linux: `/`, Windows: `\`)
4. Yasaklı komut listesini kontrol edin

### "Performance sorunu"

- Daha küçük model deneyin: `mistral` veya `neural-chat`
- GPU'yu aktif edin
- Ollama sunucusunu farklı portta çalıştırın

## 📊 Performans Metrikleri

- **LLM Yanıtı**: 2-5 saniye (model bağlı)
- **Dosya İşlemi**: <100ms
- **API Çağrısı**: 1-5 saniye (ağ bağlı)
- **Komut Çalıştırma**: 1-10 saniye (komut bağlı)

## 🤝 Katkıda Bulunma

Katkılar her zaman hoştur!

```bash
# Fork edin, branch oluşturun
git checkout -b feature/yeni-ozellik

# Değişikliklerinizi yapın ve test edin
git commit -am 'Yeni özellik: ...'

# Push edin
git push origin feature/yeni-ozellik

# Pull Request açın
```

## 📝 Lisans

Bu proje GNU General Public License v3.0 (GPL-3.0) ile lisanslanmıştır. 

Detaylar için `LICENSE` dosyasına bakın.

## 🍋 Neden "Limon"?

- 🟡 Sarı renk (AI'nin sıcak ve dostça olması gibi)
- 🔄 Modüler ve esneklik (limonun tazelik ve yenilik sembolü)
- 🌍 Açık kaynak (herkesin kullanabileceği)
- 💡 Terminal'de parlak ve renkli çıktı

> "Hayata liman gibi yaklaşma, limon gibi yaklaş!" 🍋

## 📞 İletişim & Destek

- **Issues**: GitHub issues kullanarak hata rapor edin
- **Discussions**: Soru ve önerileri tartışın
- **Docs**: Belgeler için INDEX.md'ye bakın

## 🌟 Teşekkürler

Limon'u kullanan ve geliştiren herkese teşekkürler!

---

**Limon'u Başlatmaya Hazır Mısın?** 🍋

```bash
node index.js --setup    # Kurulumu başlat
node index.js            # Sohbete başla
```