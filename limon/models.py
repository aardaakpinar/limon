"""
limon.models
------------
Sağlayıcının kendi API'sinden güncel model listesini çeker (SDK gerekmez, yalnızca
`requests`). Varsayılan model adları zamanla eskidiği için `limon models` bu listeyi
canlı gösterir.
"""

from typing import Callable, Dict, List, Optional

# Test edilebilsin diye adresler burada toplanır.
ENDPOINTS: Dict[str, str] = {
    "openai": "https://api.openai.com/v1/models",
    "claude": "https://api.anthropic.com/v1/models",
    "gemini": "https://generativelanguage.googleapis.com/v1beta/models",
}

# OpenAI hesabındaki sohbetle ilgisiz modelleri (görüntü, ses, embedding...) ele.
_OPENAI_EXCLUDE = (
    "embedding", "whisper", "tts", "dall-e", "image", "moderation", "transcribe",
    "realtime", "audio", "davinci", "babbage", "search", "computer-use",
)


def _get(url: str, headers: dict, params: Optional[dict] = None) -> dict:
    import requests

    resp = requests.get(url, headers=headers, params=params, timeout=20)
    if resp.status_code >= 400:
        # humanize_provider_error "401", "404", "429" gibi kodları metinden tanır
        raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:300]}")
    return resp.json()


def _list_openai(api_key: str, **_) -> List[str]:
    data = _get(ENDPOINTS["openai"], {"Authorization": f"Bearer {api_key}"})
    ids = [m["id"] for m in data.get("data", [])]
    return sorted(i for i in ids if not any(x in i for x in _OPENAI_EXCLUDE))


def _list_claude(api_key: str, **_) -> List[str]:
    ids: List[str] = []
    after = None
    for _page in range(10):
        params = {"limit": 100}
        if after:
            params["after_id"] = after
        data = _get(
            ENDPOINTS["claude"],
            {"x-api-key": api_key, "anthropic-version": "2023-06-01"},
            params,
        )
        ids += [m["id"] for m in data.get("data", [])]
        if not data.get("has_more"):
            break
        after = data.get("last_id")
    return ids  # API zaten en yeni önce döndürür


def _list_gemini(api_key: str, **_) -> List[str]:
    names: List[str] = []
    token = None
    for _page in range(10):
        params = {"pageSize": 200}
        if token:
            params["pageToken"] = token
        data = _get(ENDPOINTS["gemini"], {"x-goog-api-key": api_key}, params)
        for m in data.get("models", []):
            if "generateContent" in m.get("supportedGenerationMethods", []):
                names.append(m["name"].split("/", 1)[-1])
        token = data.get("nextPageToken")
        if not token:
            break
    return sorted(names)


def _list_ollama(api_key: str = "", host: str = "http://localhost:11434", **_) -> List[str]:
    data = _get(host.rstrip("/") + "/api/tags", {})
    return sorted(m["name"] for m in data.get("models", []))


_LISTERS: Dict[str, Callable[..., List[str]]] = {
    "openai": _list_openai,
    "claude": _list_claude,
    "gemini": _list_gemini,
    "ollama": _list_ollama,
}


def list_models(provider: str, api_key: str = "", ollama_host: str = "http://localhost:11434") -> List[str]:
    """Sağlayıcının kullanılabilir model kimliklerini döndürür.
    Hatalarda ham istisna fırlatır; çağıran errors.humanize_provider_error ile sadeleştirir."""
    lister = _LISTERS.get(provider)
    if lister is None:
        raise ValueError(f"Bilinmeyen sağlayıcı: {provider}")
    return lister(api_key=api_key, host=ollama_host)
