# 🍋 limon

**Linux (ve Windows/macOS) için çoklu AI sağlayıcılı komut satırı asistanı.**
Dosya okur/yazar, kabuk komutları çalıştırır; her işlem için otomatik bir
**tehlike skoru** hesaplayıp riskli olanlarda kullanıcı onayı ister.

![Python](https://img.shields.io/badge/python-3.9%2B-blue)
![License](https://img.shields.io/badge/license-GPL--3.0-blue)
![Platform](https://img.shields.io/badge/platform-linux%20%7C%20macOS%20%7C%20windows-lightgrey)

Desteklenen sağlayıcılar: **ChatGPT (OpenAI)** · **Gemini (Google)** · **Claude (Anthropic)** · **Ollama (yerel)**

```
$ limon
  ██╗     ██╗███╗   ███╗ ██████╗ ███╗   ██╗
  ██║     ██║████╗ ████║██╔═══██╗████╗  ██║
  ██║     ██║██╔████╔██║██║   ██║██╔██╗ ██║
  ██║     ██║██║╚██╔╝██║██║   ██║██║╚██╗██║
  ███████╗██║██║ ╚═╝ ██║╚██████╔╝██║ ╚████║
  ╚══════╝╚═╝╚═╝     ╚═╝ ╚═════╝ ╚═╝  ╚═══╝

> bugünkü tarih nedir?
🕒 get_current_datetime
2026-06-27 ... (Cumartesi, 27 Haziran 2026)

> /home/user/proje/main.py dosyasındaki hataları bul ve düzelt
📄 read_file /home/user/proje/main.py
✏️ write_file /home/user/proje/main.py  💾 Yedek alındı
✓ 1 hata düzeltildi.

> sistemdeki tüm .log dosyalarını sil
⚠ ONAY GEREKİYOR  [████░░░░░░] 4/10
  🖥️ run_command find / -name "*.log" -delete
  Sebep: Sistem dizinine erişim: /
  Devam edilsin mi? [evet / hayır]:
```

## İçindekiler

- [Nasıl çalışır?](#nasıl-çalışır)
- [Kurulum](#kurulum)
    - [Linux / macOS](#linux--macos)
    - [Windows (PowerShell)](#windows-powershell)
- [Yapılandırma](#yapılandırma)
- [Kullanım](#kullanım)
- [Ollama (yerel model) kullanımı](#ollama-yerel-model-kullanımı)
- [Tehlike skoru nasıl hesaplanıyor?](#tehlike-skoru-nasıl-hesaplanıyor)
- [Yeni araç eklemek](#yeni-araç-eklemek)
- [Proje yapısı](#proje-yapısı)
- [Güvenlik notları](#güvenlik-notları)
- [Sorun giderme](#sorun-giderme)
- [Katkıda bulunma](#katkıda-bulunma)
- [Lisans](#lisans)

## Nasıl çalışır?

1. Kullanıcı bir istek yazar.
2. Seçili AI sağlayıcısı (ChatGPT/Gemini/Claude/Ollama) cevap üretir; gerekirse
   bir **araç çağrısı** (`read_file`, `write_file`, `delete_file`, `list_dir`,
   `run_command`, `get_current_datetime`) döndürür.
3. `limon`, çağrılan aracın komutunu/hedefini [`danger.py`](limon/danger.py)
   içindeki kural listesine göre **0–10 arası bir tehlike skoruna** çevirir
   (örn. `rm -rf`, `sudo`, `dd`, `/etc` altına yazma, `curl | bash` gibi
   desenler puan katar).
4. Skor eşiği (varsayılan **5**, `limon config` ile değiştirilebilir) geçerse
   kullanıcıdan onay istenir; geçmezse işlem sessizce/otomatik çalışır.
5. Dosya üzerine yazma/silme işlemlerinde **otomatik yedek** alınır
   (`.limon_backups/` klasörüne).
6. Araç sonucu tekrar modele gönderilir, model son cevabını verene kadar
   bu döngü sürer; nihai cevap kullanıcıya gösterilir.

## Kurulum

### Linux / macOS

```bash
git clone https://github.com/aardaakpinar/limon.git
cd limon
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[all]"     # tüm sağlayıcı SDK'ları ile
```

### Windows (PowerShell)

```powershell
git clone https://github.com/aardaakpinar/limon.git
cd limon
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[all]"
```

> **Script çalıştırma engellenirse:** PowerShell varsayılan olarak imzasız
> script'leri engelleyebilir. Şunu **tek başına, ayrı bir satırda** çalıştırıp
> tekrar deneyin:
>
> ```powershell
> Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
> ```
>
> **`Activate.ps1 bulunamadı` hatası alırsanız:** `.venv` klasörü oluşmamış
> demektir — `dir .venv\Scripts` ile kontrol edip gerekirse `python -m venv .venv`
> komutunu tekrar çalıştırın (bazı sistemlerde `py -3 -m venv .venv` gerekebilir).

Sadece belirli bir sağlayıcıyı kullanacaksanız daha az bağımlılık kurabilirsiniz:

```bash
pip install -e ".[claude]"   # sadece Claude
pip install -e ".[openai]"   # sadece ChatGPT
pip install -e ".[gemini]"   # sadece Gemini
# Ollama için ekstra paket gerekmez (yerel HTTP API kullanılır)
```

Kurulumdan sonra `limon` komutu PATH'e eklenir (sanal ortam aktifken).

## Yapılandırma

İlk çalıştırmada otomatik olarak kurulum sihirbazı açılır, ya da manuel:

```bash
limon config
```

Bu sihirbaz şunları sorar:

- Sağlayıcı: `openai` / `gemini` / `claude` / `ollama`
- Model adı (ör. `gpt-4.1`, `gemini-flash-latest`, `claude-sonnet-4-6`, `llama3.1`)
- API anahtarı (Ollama hariç) — veya ortam değişkeni de kullanılabilir:
    - `OPENAI_API_KEY`, `GEMINI_API_KEY`, `ANTHROPIC_API_KEY`
- Ollama kullanılıyorsa host adresi (varsayılan `http://localhost:11434`)
- Tehlike onay eşiği (0–10)

Ayarlar `~/.config/limon/config.json` içinde saklanır (izinler `600`,
Windows'ta `%USERPROFILE%\.config\limon\config.json`). Bu dosya asla repoya
commit edilmemelidir — `.gitignore` bunu zaten hariç tutuyor.

## Kullanım

```bash
limon                              # etkileşimli REPL
limon -p "bugünkü tarih nedir?"    # tek seferlik komut
```

REPL içinde:

- `/config` — ayarları yeniden aç
- `/reset` — konuşma geçmişini sıfırla
- `exit` / `quit` / `Ctrl+D` — çıkış

## Ollama (yerel model) kullanımı

Ollama'nın yerelde çalışıyor ve tool-calling destekleyen bir model
(`llama3.1`, `qwen2.5`, `mistral-nemo` vb.) çekilmiş olması gerekir:

```bash
ollama serve
ollama pull llama3.1
limon config     # sağlayıcı: ollama, model: llama3.1
```

## Tehlike skoru nasıl hesaplanıyor?

[`limon/danger.py`](limon/danger.py) içinde regex tabanlı bir kural listesi
var: `rm -rf`, fork bomb, `mkfs`, `dd`, disk cihazına yazma, `sudo`,
`chmod 777`, `curl | bash`, `git push --force`, `DROP TABLE`, sistem
dizinlerine (`/etc`, `/boot`, `/root` vb.) erişim gibi onlarca desen
puanlanmış durumda. Skorlar toplanır, üst sınır 10'dur. Kendi ortamınıza
göre bu dosyayı düzenleyerek kuralları özelleştirebilirsiniz.

## Yeni araç eklemek

[`limon/tools.py`](limon/tools.py) içindeki `TOOL_DEFINITIONS` listesine yeni
bir tanım ve `TOOL_IMPLEMENTATIONS` sözlüğüne karşılık gelen fonksiyonu
eklemeniz yeterli — tüm sağlayıcılar bu ortak tanımı otomatik olarak kendi
formatlarına çevirir.

## Proje yapısı

```
limon/
├── limon/
│   ├── cli.py                 REPL, terminal UI, kurulum sihirbazı
│   ├── agent.py                ana döngü: provider <-> tool <-> onay akışı
│   ├── danger.py                tehlike skorlama kuralları
│   ├── tools.py                  araç tanımları + uygulamaları (dosya/komut)
│   ├── config.py                 ayar dosyası okuma/yazma
│   └── providers/
│       ├── base.py                ortak sağlayıcı arayüzü
│       ├── openai_provider.py      ChatGPT (openai SDK)
│       ├── gemini_provider.py      Gemini (google-genai SDK)
│       ├── claude_provider.py      Claude (anthropic SDK)
│       └── ollama_provider.py      Ollama (yerel HTTP API)
├── pyproject.toml
├── LICENSE
└── .gitignore
```

## Güvenlik notları

- `run_command` doğrudan `bash`/kabuk üzerinde çalışır; skorlama bir güvenlik
  ağı sağlar ama **kusursuz değildir** — düzenli ifadelerle eşleşmeyen tehlikeli
  komutlar olabilir. Kritik sistemlerde ekstra dikkatli olun ve düşük eşik
  (`danger_threshold`) kullanın.
- API anahtarlarınız yalnızca yerel `~/.config/limon/config.json` dosyasında
  saklanır, hiçbir yere gönderilmez (sadece ilgili AI sağlayıcısına, isteklerin
  bir parçası olarak).
- Bu proje "olduğu gibi" sunulur; üretim/kritik sistemlerde kullanmadan önce
  kendi risk toleransınıza göre `danger.py` kurallarını gözden geçirin.

## Sorun giderme

**`json.decoder.JSONDecodeError` / config açılmıyor** — config dosyası bozulmuş
olabilir, `limon` bunu artık otomatik tespit edip varsayılana dönüyor
(bozuk dosya `.corrupt` uzantısıyla yedeklenir). Hâlâ sorun yaşıyorsanız
`~/.config/limon/config.json` dosyasını silip `limon config` ile yeniden kurun.

**Gemini'de `thought_signature` hatası** — eski `google-generativeai` paketi
kullanımdan kaldırıldı; bu proje güncel `google-genai` SDK'sını kullanıyor.
`pip install -e ".[all]"` ile bağımlılıkları güncel tutun.

**`Activate.ps1` bulunamadı (Windows)** — bkz. [Windows (PowerShell)](#windows-powershell)
bölümündeki not.

## Katkıda bulunma

Katkılar memnuniyetle karşılanır! Yeni bir sağlayıcı, yeni bir araç ya da
daha iyi tehlike kuralları eklemek isterseniz:

1. Bu repoyu fork'layın
2. Bir özellik dalı oluşturun (`git checkout -b ozellik/yeni-arac`)
3. Değişikliklerinizi yapın ve mümkünse test edin
4. Pull request açın

Hata bildirimleri ve öneriler için Issues sekmesini kullanabilirsiniz.
