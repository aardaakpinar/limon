# 🍋 limon

**Terminalde çalışan, çoklu AI sağlayıcılı komut satırı asistanı.**
Dosya okur/yazar, komut çalıştırır; riskli işlemlerden önce sana sorar.

![Python](https://img.shields.io/badge/python-3.9%2B-blue)
![License](https://img.shields.io/badge/license-GPL--3.0-blue)
![Platform](https://img.shields.io/badge/platform-linux%20%7C%20macOS%20%7C%20windows-lightgrey)

Sağlayıcılar: **ChatGPT (OpenAI)** · **Gemini (Google)** · **Claude (Anthropic)** · **Ollama (yerel)**

![](docs/screenshot.png)

## Kurulum

Python 3.9 veya üstü gerekir.

**Linux / macOS**

```bash
git clone https://github.com/aardaakpinar/limon.git
cd limon
bash install.sh
```

**Windows (PowerShell)**

```powershell
git clone https://github.com/aardaakpinar/limon.git
cd limon
powershell -ExecutionPolicy Bypass -File .\install.ps1
```

Betik kurulumu bir sanal ortamda (`.venv`) yapar ama `limon` komutunu ortamın dışına da ekler. Yani **ortamı etkinleştirmene gerek yok**, `limon` her terminalden çalışır.

- Linux/macOS: komut `~/.local/bin` altına eklenir. Bu klasör PATH'te değilse betik ne yapman gerektiğini söyler.
- Windows: kurulumdan sonra yeni bir terminal aç.
- Proje klasörünü silme veya taşıma; kurulum ona bağlıdır.

Yalnızca bir sağlayıcı kurmak için: `bash install.sh --extras claude` (`openai`, `gemini` veya `all`). Windows'ta: `.\install.ps1 -Extras claude`.

`pipx` kullanıyorsan: `pipx install ".[all]"`

## Kullanım

```bash
limon config                        # sağlayıcı, model, API anahtarı, onay eşiği
limon                               # etkileşimli mod
limon -p "bugünkü tarih nedir?"     # tek seferlik komut
limon uninstall                     # ayarları sil
```

İlk çalıştırmada kurulum sihirbazı kendiliğinden açılır. Sağlayıcıyı seçtiğinde sihirbaz o sağlayıcının varsayılan modelini önerir; başka bir model için adını yazman yeterli.

Etkileşimli modda: `/config` ayarları açar, `/reset` konuşmayı sıfırlar, `exit` veya `Ctrl+D` çıkar.

| Sağlayıcı | Varsayılan model      | API anahtarı        |
| --------- | --------------------- | ------------------- |
| `openai`  | `gpt-4.1`             | `OPENAI_API_KEY`    |
| `gemini`  | `gemini-flash-latest` | `GEMINI_API_KEY`    |
| `claude`  | `claude-sonnet-4-6`   | `ANTHROPIC_API_KEY` |
| `ollama`  | `llama3.1`            | gerekmez            |

Ayarlar `~/.config/limon/config.json` dosyasında saklanır (Windows: `%USERPROFILE%\.config\limon\config.json`).

**Ollama:** `ollama serve` çalışıyor olmalı ve tool-calling destekleyen bir model çekilmiş olmalı (`llama3.1`, `qwen2.5`, `mistral-nemo` vb.):

```bash
ollama pull llama3.1
limon config    # sağlayıcı: ollama
```

## Nasıl çalışır?

1. Bir istek yazarsın. Model gerekirse bir araç çağırır: `read_file`, `write_file`, `delete_file`, `list_dir`, `run_command`, `get_current_datetime`.
2. limon her çağrıya [`danger.py`](limon/danger.py) içindeki kurallara göre **0–10 arası bir tehlike skoru** verir (`rm -rf`, `sudo`, `dd`, `curl | bash`, sistem dizinleri vb.).
3. Skor eşiğe ulaşırsa (varsayılan **5**) senden onay ister; ulaşmazsa işlem doğrudan çalışır.
4. Üzerine yazılan veya silinen dosyaların yedeği `.limon_backups/` klasörüne alınır.

## Özelleştirme

- **Tehlike kuralları:** `limon/danger.py`
- **Yeni araç:** `limon/tools.py` içindeki `TOOL_DEFINITIONS` listesine tanımı, `TOOL_IMPLEMENTATIONS` sözlüğüne fonksiyonu ekle. Tüm sağlayıcılar bunu otomatik kullanır.
- **Yeni sağlayıcı:** `limon/providers/base.py` arayüzünü uygulayan bir dosya ekle.

## Güvenlik

- `run_command` doğrudan kabukta çalışır. Skorlama regex tabanlıdır ve kusursuz değildir; kritik sistemlerde eşiği düşük tut.
- API anahtarların yalnızca yerel config dosyasında durur ve sadece seçtiğin sağlayıcıya gönderilir.
- Yazılım "olduğu gibi" sunulur; önemli sistemlerde kullanmadan önce `danger.py` kurallarını gözden geçir.

## Katkıda bulunma

Fork'la, bir dal aç (`git checkout -b ozellik/yeni-arac`), değişikliğini yap ve pull request gönder. Hata bildirimleri ve öneriler için Issues sekmesini kullanabilirsin.

## Lisans

[GPL-3.0](LICENSE)
