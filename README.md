# 🍋 LiMON AI Ajan - Modüler Yapı

Kodun daha kolay geliştirilebilir hale getirilmiş modüler versiyonu.

## Dosya Yapısı

```
limon-modular/
├── index.js                 # Ana uygulama (başlangıç noktası)
├── config.js               # Konfigürasyon yönetimi
├── security.js             # Güvenlik kontrolleri
├── ui.js                   # Terminal UI / Renkler
├── ai-providers.js         # AI API çağrıları (Gemini, Claude, OpenAI)
├── command-executor.js     # Komut yürütücü (shell, file, API)
├── setup.js                # Kurulum ve soru işlemleri
├── interaction.js          # Komut onayı ve etkileşim
└── README.md              # Bu dosya
```

## Modüllerin Açıklaması

### 1. **config.js** - Konfigürasyon Yönetimi
- Config dosyasının yüklenmesi/kaydedilmesi
- `CONFIG_DIR` ve `CONFIG_FILE` sabitlerini tanımlar
- **Export:** `loadConfig()`, `saveConfig()`, `CONFIG_FILE`

### 2. **security.js** - Güvenlik
- Yasaklı komut kalıplarını tanımlar
- Path güvenliği kontrolü (`isPathSafe`)
- Komut engelleme (`checkBlockedCommand`)
- Özel hata sınıfı: `BlockedError`
- **Export:** `DEFAULT_BLOCKED`, `isPathSafe()`, `checkBlockedCommand()`, `BlockedError`

### 3. **ui.js** - Terminal UI
- ANSI renk kodları
- Banner yazdırma
- Log fonksiyonları (info, success, warn, error, blocked, ai)
- **Export:** `c` (renkler), `log` (fonksiyonlar), `hr()`, `printBanner()`

### 4. **ai-providers.js** - AI Entegrasyon
- Google Gemini, Anthropic Claude, OpenAI API çağrıları
- Prompt oluşturma (`buildSystemPrompt`)
- Yanıt analizi (`parseResponse`)
- Konuşma tarihi yönetimi (`clearHistory`)
- **Export:** `askGemini()`, `askClaude()`, `askOpenAI()`, `parseResponse()`, `clearHistory()`

### 5. **command-executor.js** - Komut Yürütücü
- Shell komutları (`shell()`)
- Dosya işlemleri (`file()`)
- API çağrıları (`apiCall()`)
- **Export:** `CommandExecutor` sınıfı

### 6. **setup.js** - Kurulum
- İlk kurulum süreci
- API key testleme
- Soru sorma (`question()`)
- **Export:** `setup()`, `question()`

### 7. **interaction.js** - Etkileşim
- Komut onayı ekranı
- Kullanıcı onayı
- **Export:** `requestApproval()`

### 8. **index.js** - Ana Uygulama
- Tüm modülleri bir araya getir
- REPL döngüsü
- Komut işleme (setup, temizle, çıkış)
- **Başlangıç noktası**

## Kullanım

```bash
node index.js
```

## Geliştirme Rehberi

### Yeni bir komut türü eklemek

1. `command-executor.js` dosyasında `CommandExecutor` sınıfını düzenle
2. `execute()` methodunda yeni case ekle:

```javascript
case "newtype":
    return this.newOperation(cmd);

newOperation(cmd) {
    // İmplementasyon
    return Promise.resolve("Sonuç");
}
```

3. `ai-providers.js` dosyasındaki system prompt'u güncelle

### Yeni bir AI sağlayıcı eklemek

1. `ai-providers.js` dosyasında yeni async fonksiyon ekle:

```javascript
async function askNewProvider(userMessage, apiKey, workDir) {
    history.push({ role: "user", content: userMessage });
    // API çağrısı
    const text = "... yanıt ...";
    history.push({ role: "assistant", content: text });
    return parseResponse(text);
}
```

2. `setup.js` dosyasında sağlayıcı seçeneğini ekle
3. `index.js` dosyasında `askFn` mapping'e ekle

### Güvenlik kuralı eklemek

1. `security.js` dosyasında `DEFAULT_BLOCKED` dizisine ekle:

```javascript
{ pattern: /\byeni_komut\b/, label: "Açıklama" }
```

### UI temasını değiştirmek

1. `ui.js` dosyasındaki renk kodlarını (`c` objesi) düzenle
2. Log fonksiyonlarındaki simgeleri özelleştir

## Avantajları

✅ **Modüler tasarım** - Her dosya tek bir sorumluluğa sahip  
✅ **Bakım kolay** - Değişiklikler izole edilmiş  
✅ **Test etmesi kolay** - Her modül bağımsız olarak test edilebilir  
✅ **Genişletmesi kolay** - Yeni özellikler eklemek basit  
✅ **Okuması kolay** - Her dosya net ve anlaşılır

## Bağımlılıklar

- Node.js (readline, child_process, fs, path, os - built-in)
- Fetch API (Node.js 18+)
- API keys: Gemini, Claude veya OpenAI

## Notlar

- Tüm `require()` ifadeleri mutlak yollarla çalışmak için ayarlanmıştır
- Modüller birbirinden bağımsız olarak kopyalanabilir
- Her modül kendi dependency'lerini belirtir