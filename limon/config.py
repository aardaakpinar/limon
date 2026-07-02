"""
limon.config
------------
~/.config/limon/config.json içinde kullanıcı ayarlarını (sağlayıcı, model,
API anahtarları, tehlike eşiği) saklar.
"""

import json
import os

CONFIG_DIR = os.path.expanduser("~/.config/limon")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")

DEFAULT_MODELS = {
    "openai": "gpt-4.1",
    "gemini": "gemini-flash-latest",
    "claude": "claude-sonnet-4-6",
    "ollama": "llama3.1",
}

DEFAULTS = {
    "provider": "claude",
    "model": DEFAULT_MODELS["claude"],
    "danger_threshold": 5,
    "ollama_host": "http://localhost:11434",
    "api_keys": {
        "openai": "",
        "gemini": "",
        "claude": "",
    },
}


def load_config() -> dict:
    if not os.path.exists(CONFIG_PATH):
        return dict(DEFAULTS)
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            raw = f.read().strip()
        if not raw:
            return dict(DEFAULTS)
        data = json.loads(raw)
    except (json.JSONDecodeError, OSError):
        # Bozuk/boş config dosyası - üzerine yazmadan önce yedekle ve varsayılana dön.
        try:
            corrupt_backup = CONFIG_PATH + ".corrupt"
            os.replace(CONFIG_PATH, corrupt_backup)
        except OSError:
            pass
        return dict(DEFAULTS)
    merged = dict(DEFAULTS)
    merged.update(data)
    merged["api_keys"] = {**DEFAULTS["api_keys"], **data.get("api_keys", {})}
    return merged


def save_config(cfg: dict) -> None:
    os.makedirs(CONFIG_DIR, exist_ok=True)
    tmp_path = CONFIG_PATH + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, CONFIG_PATH)  # atomik: ya tamamen eski, ya tamamen yeni içerik
    os.chmod(CONFIG_PATH, 0o600)


def get_api_key(cfg: dict, provider: str) -> str:
    """Önce config dosyasına, sonra ortam değişkenine bakar."""
    env_map = {
        "openai": "OPENAI_API_KEY",
        "gemini": "GEMINI_API_KEY",
        "claude": "ANTHROPIC_API_KEY",
    }
    key = cfg.get("api_keys", {}).get(provider, "")
    if key:
        return key
    return os.environ.get(env_map.get(provider, ""), "")
