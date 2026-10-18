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

**Linux / macOS** (tek komut, git gerekmez)

```bash
curl -fsSL https://aardaakpinar.github.io/limon/install.sh | bash
```

**Windows (PowerShell)**

```powershell
irm https://aardaakpinar.github.io/limon/install.ps1 | iex
```

Bu komutlar kodları `~/.limon/src` (Windows: `%USERPROFILE%\.limon\src`) altına indirir ve kurar. Aynı komutu tekrar çalıştırmak limon'u günceller.

Sağlayıcı seçmek için: `curl -fsSL https://aardaakpinar.github.io/limon/install.sh | bash -s -- --extras claude`
veya Windows'ta `$env:LIMON_EXTRAS = "claude"; irm https://aardaakpinar.github.io/limon/install.ps1 | iex`.

<details>
<summary>Elle kurulum (git ile)</summary>

```bash
git clone https://github.com/aardaakpinar/limon.git
cd limon
bash install.sh                                            # Linux/macOS
powershell -ExecutionPolicy Bypass -File .\install.ps1     # Windows
```

</details>

Betik kurulumu bir sanal ortamda (`.venv`, tek komut kurulumunda `~/.limon/venv`) yapar ama `limon` komutunu ortamın dışına da ekler. Yani **ortamı etkinleştirmene gerek yok**, `limon` her terminalden çalışır.

- Linux/macOS: komut `~/.local/bin` altına eklenir. Bu klasör PATH'te değilse betik ne yapman gerektiğini söyler.
- Windows: kurulumdan sonra yeni bir terminal aç.
- Kaynak klasörünü (`~/.limon/src` veya klonladığın klasör) silme veya taşıma; kurulum ona bağlıdır.

Yalnızca bir sağlayıcı kurmak için: `bash install.sh --extras claude` (`openai`, `gemini` veya `all`). Windows'ta: `.\install.ps1 -Extras claude`.

PyPI'ye yayınlandıktan sonra: `pipx install "limon[all]"` (veya `pip install "limon[all]"`).
Kaynaktan: `pipx install ".[all]"`.

Tek komutlu kurulum, GitHub'daki **son yayınlanmış sürümü** kurar (henüz yayın yoksa `main`). Belirli bir sürüm veya dal için `LIMON_REF=v0.2.0` ortam değişkenini ver.

## Kullanım

```bash
limon config                        # sağlayıcı, model, API anahtarı, onay eşiği
limon                               # etkileşimli mod
limon -p "bugünkü tarih nedir?"     # tek seferlik komut
limon models                        # sağlayıcının güncel model listesini göster
limon update                        # son sürüme güncelle (--check: yalnızca denetle)
limon --version
limon uninstall                     # ayarları sil
```

İlk çalıştırmada kurulum sihirbazı kendiliğinden açılır. Sağlayıcıyı seçtiğinde sihirbaz o sağlayıcının varsayılan modelini önerir; başka bir model için adını yazman yeterli. Sihirbaz önce sağlayıcıyı ve API anahtarını (Ollama için host) sorar, ardından sağlayıcıdan **canlı model listesini çekip numaralı bir seçim listesi** gösterir: numara yazarak seç, `/metin` ile filtrele (`/` tek başına filtreyi kaldırır), listede olmayan bir model adını doğrudan yaz ya da Enter ile önerilen modeli koru. Liste alınamazsa (anahtar yok, ağ sorunu) hata gösterilir ve model adı elle girilir. Aynı liste, oturum içinde `/model` ile de açılır ve seçim kaydedilir.

Etkileşimli modda: `/config` ayarları açar, `/model` model seçim listesini açar, `/reset` konuşmayı sıfırlar, `exit` veya `Ctrl+D` çıkar.

| Sağlayıcı | Varsayılan model      | API anahtarı        |
| --------- | --------------------- | ------------------- |
| `openai`  | `gpt-4.1`             | `OPENAI_API_KEY`    |
| `gemini`  | `gemini-flash-latest` | `GEMINI_API_KEY`    |
| `claude`  | `claude-sonnet-5-5`   | `ANTHROPIC_API_KEY` |
| `ollama`  | `llama3.1`            | gerekmez            |

Ayarlar `~/.config/limon/config.json` dosyasında saklanır (Windows: `%USERPROFILE%\.config\limon\config.json`).

**Ollama:** `ollama serve` çalışıyor olmalı ve tool-calling destekleyen bir model çekilmiş olmalı (`llama3.1`, `qwen2.5`, `mistral-nemo` vb.):

```bash
ollama pull llama3.1
limon config    # sağlayıcı: ollama
```

## Nasıl çalışır?

1. Bir istek yazarsın. Model gerekirse bir araç çağırır:

   | Araç | Ne yapar |
   | --- | --- |
   | `read_file` | Dosyayı okur (`start_line`/`end_line` ile satır aralığı) |
   | `edit_file` | Dosyada birebir eşleşen metni değiştirir (yedek alır) |
   | `write_file` | Yeni dosya yazar / baştan yazar (yedek alır) |
   | `delete_file` | Dosyayı siler (yedek alır) |
   | `list_dir`, `glob` | Dizin listeler, desene göre dosya bulur (`**/*.py`) |
   | `grep` | Dosya içeriğinde regex arar (`.git`, `.venv`, `.env` vb. atlanır) |
   | `web_fetch` | Web sayfasını okunabilir metne çevirir |
   | `run_command` | Kabukta komut çalıştırır (zaman aşımı en fazla 10 dk) |
   | `get_current_datetime` | Tarih/saat |
2. limon her çağrıya [`danger.py`](limon/danger.py) içindeki kurallara göre **0–10 arası bir tehlike skoru** verir (`rm -rf`, `sudo`, `dd`, `curl | bash`, sistem dizinleri vb.).
3. Skor eşiğe ulaşırsa (varsayılan **5**) senden onay ister; ulaşmazsa işlem doğrudan çalışır. Hassas dosyaları okumak (`~/.ssh`, `.env`, limon'un kendi `config.json`'u, `*.pem`...) ve yerel/özel ağ adreslerine `web_fetch` yapmak da onay gerektirir.
4. Üzerine yazılan veya silinen dosyaların yedeği `.limon_backups/` klasörüne alınır.

## Arka plan sistem ajanı (`limon daemon`)

limon, istenirse arka planda çalışıp sistem olaylarına tepki veren bir **AI sistem ajanına** dönüşür. İlk sürüm **Linux + systemd** içindir; systemd olmayan sistemlerde komutlar açık bir hata verir. Etkileşimli `limon` modu ve mevcut komutlar değişmeden çalışır.

**Ne yapar?** Başarısız servisleri, yeniden başlama döngülerini, journald hata yoğunluğunu ve disk doluluğunu izler. Bir sorun bulunca olayı kaydeder (aynı sorunu tekrar tekrar işlemez), ilgili durumu ve logları toplar, **hassas verileri süzer**, seçili sağlayıcıya (OpenAI/Gemini/Claude/Ollama) teşhis yaptırır; yanıtı şemaya göre doğrular, yerel politikadan geçirir ve gerekirse senden onay ister.

```bash
limon daemon install            # kullanıcı oturumu servisi kurar (root GEREKMEZ), açılışta etkinleştirir
limon daemon start | stop | status
limon events                    # kaydedilen olaylar ve teşhisler
limon diagnose --last 30m       # son 30 dakikayı teşhis et (eylem uygulamaz; öneriler onay kuyruğuna girer)
limon approvals                 # onay bekleyen işlemler
limon approve <id>  |  limon reject <id>
limon daemon uninstall [--purge]
```

Daemon'ın terminali olmadığı için onay gerektiren işlemler kalıcı bir kuyruğa konur; başka bir terminalden `limon approve` ile onaylarsın. Onay, eylemin parmak iziyle bağlıdır.

### Modlar (güvenli varsayılan: `report`)

`~/.config/limon/config.json` içindeki `daemon` bölümü:

```json
{
  "daemon": {
    "mode": "report",
    "watch_units": ["nginx.service"],
    "auto_units": [],
    "allowed_roots": []
  }
}
```

| `mode` | Davranış |
| --- | --- |
| `off` | Yalnızca olayları kaydeder; sağlayıcıya hiçbir şey gönderilmez, hiçbir eylem yapılmaz. |
| `report` *(varsayılan)* | Teşhis eder, eylem planını **onay kuyruğuna** koyar. Sen onaylamadan hiçbir şey uygulanmaz. |
| `auto` | Yalnızca `auto_units` listesindeki, `auto_actions` içindeki (`reset_failed`, `restart_service`) düşük riskli eylemler onaysız yürür. `auto_units` boşsa hiçbir şey otomatik değildir. Korumalı birimler (sshd, systemd-*, dbus, NetworkManager…), dosya düzenleme ve yüksek riskli her şey yine onay ister. |

Diğer ayarlar (hepsi isteğe bağlı, sınırlara kırpılır; internet araması için aşağıya bak): `poll_interval`, `cooldown`, `error_burst_threshold`, `disk_warn`/`disk_crit`, `max_fix_attempts_per_event`, `max_actions_per_unit_per_hour`, `max_actions_per_day`, `retention_days`, `protected_units` (varsayılan koruma listesi küçültülemez, yalnızca genişletilir).

### Eylemler ve güvenlik modeli

AI **kabuk komutu üretemez.** Yalnızca şu tipli eylemleri önerebilir: `report_only`, `reset_failed <birim>`, `restart_service <birim>`, `edit_file <yol> <eski> <yeni>` (varsayılan olarak kapalı; yalnızca `allowed_roots` içinde ve her zaman onayla).

- **Mevcut `danger.py` korunur** ama tek sınır değildir. Asıl sınırlar: eylem izin listesi, hedefin olayla ilgili birim olması (loglardaki bir enjeksiyon "sshd'yi yeniden başlat" dedirtemez), korumalı birimler, yol normalleştirme + izinli kök dizinler (simge bağlantısı kaçışları dahil), saatlik/günlük hız sınırları ve olay başına deneme sınırı (döngü koruması).
- **Güvenilmeyen veri:** loglar prompt'ta `<veri>` bloğunda verilir, talimat olarak uygulanmaz. Teşhiste mevcut `Agent` (dosya/kabuk araçlı) bilerek *kullanılmaz*; sağlayıcıya yalnızca çalıştırılmayan tek bir `submit_diagnosis` şema aracı verilir.
- **Gizli veri:** API anahtarları, token/parola desenleri, özel anahtarlar, `://kullanıcı:parola@` URL'leri sağlayıcıya gitmeden ve diske yazılmadan süzülür. Ortam değişkenleri ve dosya içerikleri sağlayıcıya gönderilmez; alt süreçlere de aktarılmaz.
- **Yürütme:** kabuk yok (argv), zaman aşımı, çıktı sınırı, süreç grubu temizliği. Dosya düzenlemede yedek (`durum_dizini/backups`), atomik yazma, izin koruma; düzeltme sonrası servis sağlıklı değilse otomatik **geri alma**.
- **IPC:** yalnızca Unix domain socket (ağ yok); dizin `0700`, soket `0600`, her bağlantıda `SO_PEERCRED` ile uid denetimi, istek boyutu ve şema doğrulaması.
- **Dayanıklılık:** durum SQLite'ta tutulur. Sağlayıcıya ulaşılamazsa olay kaybolmaz; üstel geri çekilmeyle sınırlı sayıda yeniden denenir. Yeniden başlatmada yarım kalan teşhisler kuyruğa alınır; yürütme sırasında kesilen eylemler **kendiliğinden tekrar çalıştırılmaz**. Audit günlüğü ve olay kayıtları boyut/süre sınırıyla döndürülür/temizlenir.

### İnternet araması (isteğe bağlı, varsayılan kapalı)

Güncel/bilinen bir hata için model, teşhisi göndermeden önce en fazla birkaç **web araması** isteyebilir. Bu, sağlayıcıların yerleşik arama özelliği yerine limon tarafında, sağlayıcıdan bağımsız yapılır: model yalnızca kısa bir sorgu metni önerir (`search_web`), sorguyu limon temizler ve çalıştırır, sonuçları güvenilmeyen veri olarak geri verir. Böylece sorgu sağlayıcı tarafında süzülemeden gitmez ve Ollama dahil dört sağlayıcıda da çalışır.

```json
{ "daemon": { "web_search": "searxng", "web_search_url": "http://localhost:8080" } }
```

| `web_search` | Gereken |
| --- | --- |
| `off` *(varsayılan)* | — |
| `searxng` | Kendi barındırdığın SearXNG; `web_search_url` ve `settings.yml` içinde JSON çıktısı etkin olmalı. Sorgular dışarıya çıkmaz. |
| `brave` | Brave Search API anahtarı: `BRAVE_API_KEY` ortam değişkeni veya `api_keys.brave`. Sorgular Brave'e gider. |

Diğer ayarlar: `web_search_max_rounds` (teşhis başına tur, varsayılan 2), `web_search_daily_limit` (varsayılan 30), `web_search_results` (varsayılan 5).

**Gizlilik ve güvenlik:**
- Sorgudan sırlar, IP, e-posta, URL, `/home/...` yolları, UUID ve uzun rastgele dizgiler çıkarılır; sorgu 120 karakterle sınırlanır. **Ana makine adları otomatik ayıklanamaz**; gönderilen her sorgu audit günlüğünde (`web_search` kayıtları) görülebilir. Gizlilik önemliyse `searxng` ile kendi örneğini kullan.
- Yalnızca arama sonucu başlığı/özeti/URL'si alınır; sonuç sayfaları indirilmez (SSRF ve sayfa içi prompt enjeksiyonu yüzeyi yok).
- Web içeriği modeli yanıltabilir, ama eylemleri yine yerel politika denetler: izinli eylem türleri, olayla ilgili hedef, korumalı birimler, onay kuyruğu.
- Arama başarısız olursa model bilgilendirilir ve eldeki bilgiyle teşhis gönderir; daemon etkilenmez.

### Kurulum kapsamı

| | `limon daemon install` *(varsayılan)* | `limon daemon install --system` |
| --- | --- | --- |
| Çalışan kullanıcı | Sen (root değil) | Ayrı, kısıtlı `limon` sistem kullanıcısı (root değil) |
| Servis | `systemctl --user` (`~/.config/systemd/user`) | `/etc/systemd/system` |
| Yönetebildiği | Kendi oturum servislerin; sistem servislerini yalnızca izler | Sistem servisleri — yalnızca `restart`/`reset-failed`, yalnızca adı geçen birimler (polkit kuralı; `sudo` yok) |
| Gereken | Kullanıcı systemd oturumu | Kurulum için bir kez root; limon'un herkesin okuyabildiği bir yolda kurulu olması (`--python /opt/limon/bin/python`) |
| API anahtarı | `~/.config/limon/config.json` (0600) | `/etc/limon/limon.env` (0640 root:limon) — unit dosyasına **gömülmez** |

Unit dosyası `Restart=on-failure`, `NoNewPrivileges`, `PrivateTmp`, `RestrictAddressFamilies`, `UMask=0077`; sistem kapsamında ek olarak `ProtectSystem=strict`, `ProtectHome`, boş `CapabilityBoundingSet` kullanır. Kurulum tekrar çalıştırılabilir. Oturum kapalıyken de çalışması için `loginctl enable-linger $USER`. `limon daemon uninstall` servisi kaldırır, durum verisini korur (`--purge` siler).

Journal'ı okumak için kullanıcının `systemd-journal` (veya `adm`) grubunda olması gerekebilir.

### Henüz yok

Ayrı ayrıcalıklı yardımcı servis (şimdilik dar polkit kuralı), masaüstü bildirimleri (`Notifier` arayüzü hazır), OpenRC/macOS/Windows adaptörleri, ağ üzerinden kontrol (bilerek yok).

## Proje talimatları (`LIMON.md`)

Çalıştığın klasöre (veya bir üst klasörüne) `LIMON.md` koyarsan içeriği her oturumda modele proje notu olarak verilir. Örnek:

```markdown
Testleri `pytest -q` ile çalıştır. Commit mesajlarını Türkçe yaz. `legacy/` klasörüne dokunma.
```

## Özelleştirme

- **Tehlike kuralları:** `limon/danger.py`
- **Yeni araç:** `limon/tools.py` içindeki `TOOL_DEFINITIONS` listesine tanımı, `TOOL_IMPLEMENTATIONS` sözlüğüne fonksiyonu ekle. Tüm sağlayıcılar bunu otomatik kullanır.
- **Yeni sağlayıcı:** `limon/providers/base.py` arayüzünü uygulayan bir dosya ekle.

## Güvenlik

- `run_command` doğrudan kabukta çalışır. Skorlama regex tabanlıdır ve kusursuz değildir; kritik sistemlerde eşiği düşük tut.
- API anahtarların yalnızca yerel config dosyasında durur ve sadece seçtiğin sağlayıcıya gönderilir.
- Yazılım "olduğu gibi" sunulur; önemli sistemlerde kullanmadan önce `danger.py` kurallarını gözden geçir.

## Sürüm yayınlama

1. `limon/__init__.py` içindeki `__version__` değerini artır ve commit'le.
2. `git tag v0.2.0 && git push --tags`

[`release.yml`](.github/workflows/release.yml) etiketle `__version__`'ın eşleştiğini denetler, testleri çalıştırır, paketi derler, PyPI'ye yükler ve GitHub sürümü oluşturur. Kurulum betikleri ve `limon update` "son sürüm" olarak bu GitHub sürümüne bakar.
PyPI için tek seferlik hazırlık: pypi.org'da `limon` adının boş olduğunu doğrula ve projeyi "trusted publisher" olarak bu depoya/`release.yml` iş akışına bağla (`pypi` ortamı).

Testler: `pip install -e ".[dev]" && pytest`.

## Katkıda bulunma

Fork'la, bir dal aç (`git checkout -b ozellik/yeni-arac`), değişikliğini yap ve pull request gönder. Hata bildirimleri ve öneriler için Issues sekmesini kullanabilirsin.

## Lisans

[GPL-3.0](LICENSE)
