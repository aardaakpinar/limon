"""
limon.picker
------------
Terminalde numaralı seçim listesi (yalnızca stdlib; Windows/macOS/Linux'ta aynı çalışır).
Girdi/çıktı fonksiyonları dışarıdan verilir, böylece test edilebilir.
"""

from typing import Callable, List, Optional

PAGE = 25


def choose_model(
    suggested: str,
    fetch: Callable[[], List[str]],
    ask: Optional[Callable[[str], str]] = None,
    say: Optional[Callable[[str], None]] = None,
    current: str = "",
) -> str:
    """Model seçtirir ve model kimliğini döndürür.

    Liste sağlayıcıdan canlı çekilir (fetch). Çekilemezse hata gösterilir ve
    model adı elle yazılır. Girdiler:
      <numara>   listeden seç      /metin   filtrele (/ tek başına: filtreyi kaldır)
      <ad>       listede olmasa da bu model adını kullan
      Enter      önerilen/mevcut modeli koru

    `ask`/`say` verilmezse varsayılan `input`/`print` kullanılır; varsayılanlar
    import anında bağlanmaz, böylece testler ve sarmalayıcılar `builtins.input`
    değiştirdiğinde de doğru fonksiyon çağrılır.
    """
    ask = ask or input
    say = say or print
    default = suggested or current
    try:
        models = list(fetch())
    except Exception as e:  # ağ, anahtar, kota... seçimi engellemesin
        say(f"Canlı model listesi alınamadı: {e}")
        models = []

    if not models:
        name = ask(f"Model adı [{default}]: ").strip()
        return name or default

    # Önerilen/mevcut model en üstte; listede yoksa da seçenek olarak gösterilir.
    ordered = [m for m in models if m != default]
    if default:
        ordered.insert(0, default)
    flt = ""
    while True:
        shown = [m for m in ordered if flt.lower() in m.lower()] if flt else ordered
        say("")
        if not shown:
            say(f"'{flt}' ile eşleşen model yok. (/ yazarak filtreyi kaldır)")
        for i, m in enumerate(shown[:PAGE], 1):
            tags = []
            if m == default:
                tags.append("varsayılan" if m not in models else "seçili/önerilen")
                if m not in models:
                    tags[-1] += ", listede yok"
            say(f"  {i:>2}. {m}" + (f"  ({tags[0]})" if tags else ""))
        if len(shown) > PAGE:
            say(f"  … {len(shown) - PAGE} model daha — /metin ile filtrele")
        raw = ask(f"Model [numara / ad / /filtre / Enter={default}]: ").strip()
        if not raw:
            return default
        if raw.startswith("/"):
            flt = raw[1:].strip()
            continue
        if raw.isdigit():
            idx = int(raw)
            if 1 <= idx <= min(len(shown), PAGE):
                return shown[idx - 1]
            say(f"Geçersiz numara: {raw} (1-{min(len(shown), PAGE)})")
            continue
        return raw  # listede olmayan özel/yeni model adı
