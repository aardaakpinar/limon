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
ollama pull llama3.1:8b
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
# [4] Ollama (lokal)

# Seçim yap ve talimatları takip et
```

```bash
npm install
npm start
```

## 📖 Kullanım

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
  "ollamaModel": "llama3.1:8b"
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
| `ollamaModel` | Ollama model adı | llama3.1:8b |

### Ortam Değişkenleri

```bash
# API Keys
export LIMON_API_KEY="sk-..."              # Genel API key
export LIMON_GEMINI_API_KEY="..."          # Gemini key
export LIMON_CLAUDE_API_KEY="sk-ant-..."   # Claude key
export LIMON_OPENAI_API_KEY="sk-..."       # OpenAI key

# Ollama
export OLLAMA_HOST="http://localhost:11434"
export OLLAMA_MODEL="llama3.1:8b"

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

Limon, farklı donanım seviyelerine uygun modern LLM modelleriyle çalışır. Model seçimi **performans, kalite ve sistem prompt uyumu** açısından kritiktir.

### 🧠 En İyi Kalite (Yüksek Donanım)

```bash
ollama pull llama3.1:70b
ollama pull qwen2.5:32b-instruct
```

* ✅ En yüksek **system prompt uyumu**
* ✅ En iyi reasoning ve tool-use performansı
* ❗ Çok yüksek RAM/VRAM gerektirir (48GB+ önerilir)

---

### ⚖️ Dengeli (ÖNERİLEN ⭐)

```bash
ollama pull qwen2.5:14b-instruct
ollama pull mistral-nemo
```

* ✅ En iyi **fiyat/performans oranı**
* ✅ System prompt’a güçlü sadakat
* ✅ Agent (Limon gibi) kullanımında en stabil modeller

👉 **Varsayılan öneri:**

```json
"ollamaModel": "qwen2.5:14b-instruct"
```

---

### 💡 Hafif (Orta Sistemler)

```bash
ollama pull llama3.1:8b
```

* ✅ Düşük RAM ile çalışır
* ✅ Genel kullanım için yeterli
* ❗ Uzun görevlerde prompt drift olabilir

---

### ⚠️ Çok Hafif (Sınırlı Kullanım)

```bash
ollama pull llama3.2:3b
ollama pull qwen2.5:3b-instruct
```

* ⚠️ System prompt uyumu zayıf
* ⚠️ Agent davranışında tutarsızlık olabilir
* ✅ Sadece düşük sistemler için

---

## 🎯 Model Seçim Rehberi

| Sistem           | Önerilen Model             |
| ---------------- | -------------------------- |
| 8–16 GB RAM      | llama3.1:8b                |
| 16–32 GB RAM     | qwen2.5:14b-instruct ⭐     |
| 32 GB+ RAM / GPU | qwen2.5:32b / llama3.1:70b |

---

## 🧠 Kritik Bilgi: System Prompt Uyumu

Limon bir **AI agent** olduğu için model seçimi çok önemlidir.

Büyük modeller:

* Kurallara daha sadık kalır
* Komutları daha doğru üretir
* Daha az “halüsinasyon” yapar

Küçük modeller:

* Kuralları unutabilir
* Yanlış komut üretebilir
* Güvenlik riskleri oluşturabilir

👉 Bu yüzden **14B+ modeller önerilir**


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
ollama pull llama3.1:8b

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