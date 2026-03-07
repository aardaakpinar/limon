# LiMON

Terminal tabanli, onayli ve kontrollu AI ajan.

LiMON; Gemini, Claude ve OpenAI modelleriyle calisir, modelden gelen komutlari once size gosterir, onay verirseniz calistirir.

## Ozellikler

- Coklu model destegi: `gemini`, `claude`, `openai`
- Onay mekanizmasi: Her komut calistirmadan once sorulur
- Dosya islemleri: `write`, `append`, `read`, `delete`, `mkdir`, `list`, `move`
- Shell komutlari (ek guvenlik kontrolleri ile)
- Opsiyonel `app` ve `api` komutlari (varsayilan kapali)
- Sandbox odakli calisma dizini

## Tek Komut Kurulum (Linux/macOS)

```bash
curl -fsSL https://raw.githubusercontent.com/aardaakpinar/limon/main/install.sh | bash
```

Kurulumdan sonra:

```bash
limon --setup
```

Not: Script `~/.local/bin/limon` olusturur. PATH icinde degilse script size gerekli `export PATH=...` satirini verir.

## Manuel Kurulum

```bash
git clone https://github.com/aardaakpinar/limon.git
cd limon
npm install
npm run start
```

## Gereksinimler

- Node.js `>= 18`
- `npm`
- Bir AI saglayici API key'i

## Ilk Kurulum Akisi

`--setup` su adimlari ister:

1. Sandbox calisma dizini
2. Guvenlik engelleri acik/kapali
3. `app` komutlarini ac/kapat
4. `api` komutlarini ac/kapat (+ opsiyonel domain allowlist)
5. Provider secimi
6. API key girisi ve test
7. API key'i config'e yazma tercihi

Config dosyasi: `~/.limon/config.json`

## API Key Ortam Degiskenleri

Config'te key saklamak istemezseniz:

- `LIMON_API_KEY`
- `LIMON_OPENAI_API_KEY` veya `OPENAI_API_KEY`
- `LIMON_CLAUDE_API_KEY` veya `ANTHROPIC_API_KEY`
- `LIMON_GEMINI_API_KEY` veya `GEMINI_API_KEY`

## Kullanim

Etkilesimli:

```bash
npm run start
```

Tek seferlik sorgu:

```bash
node src/index.js -q "projedeki js dosyalarini listele"
```

Kontrol komutlari:

- `--setup`
- `--temizle` (`--clear`)
- `cik` (`exit`, `quit`)

## Guvenlik Notlari

- Komutlar onaysiz calismaz.
- Shell komutlari icin ek riskli desen/syntax engelleri vardir.
- `api` komutlarinda local/private adresler engellenir.
- Gercek OS-level sandbox degildir; yuksek guvenlik gereken ortamlarda container/VM izolasyonu onerilir.

## Proje Yapisi

```text
src/
  index.js        # CLI giris ve ana dongu
  setup.js        # ilk kurulum sihirbazi
  providers.js    # Gemini/Claude/OpenAI entegrasyonlari
  executor.js     # komut calistirma katmani
  security.js     # guvenlik kontrolleri
  interaction.js  # onay akisi
  ui.js           # terminal arayuzu
docs/
  index.html      # landing page
install.sh        # tek komut kurulum script'i
```

## Lisans

MIT
