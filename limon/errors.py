"""
limon.errors
------------
Sağlayıcı SDK'larından (openai, anthropic, google-genai, requests) gelen ham
hataları kullanıcıya gösterilebilir, Türkçe ve kısa mesajlara çevirir.
Mümkünse "ne zaman tekrar denenebilir" bilgisini de (retry_after) çıkarır.
"""

import re
from typing import Optional


class ProviderError(Exception):
    """Kullanıcıya gösterilecek, sadeleştirilmiş sağlayıcı hatası."""

    def __init__(self, message: str, retry_after: Optional[float] = None, raw: Optional[str] = None):
        super().__init__(message)
        self.retry_after = retry_after
        self.raw = raw


def _parse_retry_after(text: str) -> Optional[float]:
    # google-genai: "retryDelay': '41s'" veya "Please retry in 41.34s"
    for pattern in (
        r"retryDelay['\"]?\s*[:=]\s*['\"]?(\d+(?:\.\d+)?)s",
        r"retry in\s+(\d+(?:\.\d+)?)s",
        r"retry-after['\"]?\s*[:=]\s*['\"]?(\d+(?:\.\d+)?)",
    ):
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            try:
                return float(m.group(1))
            except ValueError:
                pass
    return None


def _extract_field(text: str, key: str) -> Optional[str]:
    m = re.search(rf"['\"]{key}['\"]\s*:\s*['\"]([^'\"]+)['\"]", text)
    return m.group(1) if m else None


def humanize_provider_error(e: Exception) -> ProviderError:
    text = str(e)
    lower = text.lower()

    if "429" in text or "resource_exhausted" in lower or "rate limit" in lower or "quota" in lower:
        quota_id = _extract_field(text, "quotaId") or ""
        quota_value = _extract_field(text, "quotaValue")
        model = _extract_field(text, "model")
        retry_after = _parse_retry_after(text)
        is_daily = "day" in quota_id.lower()

        detail = ""
        if quota_value and model:
            detail = f" (günlük ücretsiz limit: {quota_value} istek, model: {model})" if is_daily else f" (limit: {quota_value}, model: {model})"
        elif quota_value:
            detail = f" (limit: {quota_value})"

        if is_daily:
            # Günlük kota bittiyse birkaç saniye beklemek işe yaramaz; boşuna bekletmeyelim.
            msg = (
                f"Bu modelin günlük ücretsiz kullanım kotası doldu{detail}. "
                "Kota genelde ertesi gün (Pasifik saatiyle gece yarısı) sıfırlanır. "
                "Şimdilik 'limon config' ile başka bir model/sağlayıcı seçebilir, "
                "ya da sağlayıcının ücretli planına geçebilirsiniz."
            )
            return ProviderError(msg, retry_after=None, raw=text)

        msg = f"İstek limitine takıldınız (çok sık istek gönderildi){detail}."
        if retry_after:
            msg += f" ~{int(retry_after) + 1} saniye sonra otomatik tekrar denenecek."
        else:
            msg += " Biraz bekleyip tekrar deneyin."
        return ProviderError(msg, retry_after=retry_after, raw=text)

    if "401" in text or "unauthorized" in lower or "invalid api key" in lower or "authentication" in lower or "permission_denied" in lower:
        return ProviderError(
            "API anahtarı geçersiz, eksik ya da yetkisiz görünüyor. "
            "'limon config' ile kontrol edin.",
            raw=text,
        )

    if "timeout" in lower or "timed out" in lower:
        return ProviderError("İstek zaman aşımına uğradı. Bağlantınızı kontrol edip tekrar deneyin.", raw=text)

    if "connection" in lower and ("refused" in lower or "error" in lower or "failed" in lower):
        return ProviderError(
            "Sağlayıcıya bağlanılamadı. (Ollama kullanıyorsanız 'ollama serve' çalışıyor mu?)",
            raw=text,
        )

    if "model not found" in lower or "does not exist" in lower or "404" in text:
        return ProviderError(
            "Model bulunamadı. Model adını 'limon config' ile kontrol edin (yazım hatası olabilir).",
            raw=text,
        )

    short = text if len(text) < 300 else text[:300] + "…"
    return ProviderError(f"Sağlayıcı hatası: {short}", raw=text)